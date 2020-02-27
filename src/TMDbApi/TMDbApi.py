#!/usr/bin/python3
#
# Copyright (c) 2020 Pangeanic SL.
#
# This file is part of NEC TM
# (see https://github.com/shasha79/nectm).
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
import os, sys
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..'))
sys.path = [p for p in sys.path if p]

import uuid
import logging
import re
from  networkx.algorithms.shortest_paths.generic import shortest_path_length, shortest_path
import operator
import math
import datetime

# Do not remove - weird packaging issue requires this libraries
# to be included here and not inside TMRegExpPreprocessor
import babel.numbers, babel.dates

from TMDbApi.TMTranslationUnit import TMTranslationUnit
from TMDbApi import TMMap
from TMDbApi.TMMonoLing import TMMonoLing
from TMPreprocessor.Xml.XmlUtils import XmlUtils
from TMMatching.TMMatching import TMMatching
from TMMatching.TMUtilsMatching import TMUtilsMatching
from TMAutomaticTranslation.TMAutomaticTranslation import TMAutomaticTranslation
from TMDbApi.TMUtils import TMTimer
from Config.Config import G_CONFIG
from timeit import default_timer as timer

from RestApi.Models import Tags

# API class for translation memories DB
class TMDbApi:
  DOC_TYPE = 'tm'
  BATCH_SIZE = 2000
  MGET_BATCH_SIZE = 100
  TRANSLATE_BATCH_SIZE = 100
  DATE_FORMAT = "%Y%m%dT%H%M%SZ" # ES 'basic_date_time_no_millis' format

  Q_TOKEN_COUNT = G_CONFIG.get_query_token_count()
  MATCH_TIME = G_CONFIG.get_wait_query_time()
  QUERY_PENALIZE = G_CONFIG.get_query_penalize()
  DIRTY_THRESHOLD = G_CONFIG.get_dirty_threshold()

  def __init__(self, map_engine = 'elasticsearch', **kwargs):
    self.ml_index = TMMonoLing(timeout=30, max_retries=3, retry_on_timeout=True)
    self.seg_map = TMMap.create(map_engine)
    self.timer = TMTimer("TMDbApi")
    self.scan_size = 0
    self._migrate_tags()

  # Migrate tags (if needed) from
  def _migrate_tags(self):
    stats = self.mstats()
    Tags.get_add_tags(stats.get("domain", dict()).keys())

  # Add new segment
  def add_segment(self, segment):
    # Add segment source and target texts to the correspondent index of ElasticSearch
    self.ml_index.add_segment(segment, 'source')
    self.ml_index.add_segment(segment, 'target')

    self.seg_map.add_segment(segment)

  # Bulk segment addition
  def add_segments(self, segments_iter):
    # Send bulk update requests for both ES monolingual index and map
    batch = batch_status = []
    logging.info("Started add_segments")
    for segment in segments_iter:
      # Add to batch, when the batch exceeds given size, perform actual bulk insertion
      batch.append(segment)
      if len(batch) >= self.BATCH_SIZE:
        batch_status.append(self._add_segments(batch))
        batch.clear()
    batch_status.append(self._add_segments(batch))
    self.seg_map.refresh()
    logging.info("Finished add_segments")
    self.timer.print()
    self.seg_map.timer.print()
    return batch_status

  def _filter_by_query(self, query, src_lang, tgt_lang, total_token, exact_length):
    dic_filter = []

    if isinstance(query, list):
      if exact_length: # Split method search segments with exact lenght
        for value in [self.ml_index.token_count(q_o_tags, src_lang) for q, q_o_tags in query]:

          if value -1 < 0: inf = 1
          else: inf = value -1

          dic_filter.append({'target_language': tgt_lang, 'token_cnt': {"gte": inf, "lte": value + 1}})  # source language
          logging.info("Lenght Query SEARCH EXACT : {} ".format(value))

      else: # Normal query estinate the length of segments
        for value in [self.ml_index.token_count(q_o_tags, src_lang) for q, q_o_tags in query]: # source language
          logging.info("Lenght Query : {} ".format(value))
          inf = value - math.ceil((self.Q_TOKEN_COUNT * value) / 100)
          logging.info("Search minimum lenght : {} ".format(inf))
          sup = value + math.ceil((self.Q_TOKEN_COUNT * value) / 100)
          logging.info("Search maximum lenght : {} ".format(sup))
          if inf < 0: inf = 1
          dic_filter.append({'target_language': tgt_lang, 'token_cnt': {"gte": inf, "lte": sup}}) # source language
    else: # PosTag method search one word, then exact lenght
      dic_filter.append({'target_language': tgt_lang, 'token_cnt': {"gte": total_token, "lte": total_token}}) # target language
    return dic_filter

  def exact_query(self, qlist, src_lang, tgt_lang, limit, dic_filter):

    #dic_filter = self._filter_by_query(qlist, src_lang, tgt_lang ,total_token, exact_length) #Pass source language
    list_segments = []
    for q, response in zip(qlist, self.ml_index.mquery(src_lang, limit, [q for q in qlist], filter=[f for f in dic_filter])):
      segments = []
      src_hits = [src_hit for src_hit in response]  # turn iterator into list to be reentrant

      # Build segment by querying map and target index
      map_docs = self._msrc_id2tgt_id(src_hits, src_lang, tgt_lang)

      target_ids = [(tgt_lang, d['target_id']) for d in map_docs]

      for src_hit, map_doc, tgt_doc in zip(src_hits, map_docs, self.ml_index.mget(target_ids)):
        segments.append(self._doc2segment(map_doc, sd=src_hit.to_dict(), td=tgt_doc))
      list_segments.append((q, segments))
    return list_segments

  def query(self, qparams):
      # Drop tags from query
      q_out_tags = [(q, XmlUtils.strip_tags(q)) for q in qparams.qlist]
      if not qparams.qinfo:
        qparams.qinfo = [dict() for q in qparams.qlist]

      out_segments = [] # list of lists of tuples :(segment, ter)
      if qparams.concordance:
        dic_filter = [{'target_language': qparams.target_lang}]
      else:
        # Extract query length
        dic_filter = self._filter_by_query(q_out_tags, qparams.source_lang, qparams.target_lang, '-', qparams.exact_length) # Doesn't pass the total token, the function calculate the value for each query  -->  target_lang
      if qparams.aut_trans: list_to_translate = []
      # Query source ES for the text
      self.timer.start("monoling_query")

      for q, qinfo ,response in zip(qparams.qlist, qparams.qinfo ,self.ml_index.mquery(qparams.source_lang, qparams.limit, [q_o_tags for q, q_o_tags in q_out_tags], filter = [f for f in dic_filter])):
        self.timer.stop("monoling_query")
        out_segments.append((q, self._query(q, qinfo, response, qparams)))  # create new list for current query

      if qparams.aut_trans:
        logging.info("Machine Translation")
        last_output = []
        if not out_segments:
          for query in qparams.qlist:
            segment = TMTranslationUnit()
            segment.source_text = query
            out_segments += [(query, ([(segment, 0)], False)) ]
        tm_engine = TMAutomaticTranslation.get_engine(qparams.source_lang, qparams.target_lang, qparams.domains)
        for i in range(0, len(out_segments), self.TRANSLATE_BATCH_SIZE):
          #for each_query in self.execute_machine_translation(tm_engine, qparams.source_lang, qparams.target_lang, out_segments[i:i + self.TRANSLATE_BATCH_SIZE], qparams.min_match):
          for each_query in self.machine_translate(tm_engine, qparams.source_lang, qparams.target_lang,
                                                               out_segments[i:i + self.TRANSLATE_BATCH_SIZE],
                                                               qparams.min_match):
            last_output.append(each_query)
      else:
        last_output = [(segments,False) for query, (segments, match_check) in out_segments]
      self.timer.stop("match_time_query")
      return last_output

  def _prepare_target_text(self, query, segment, translation, source_lang, target_lang):
    segment.source_text = query
    segment.domain = []
    segment.file_name = []

    if re.search("</?[^<>]+/?>", query) is not None:  # If there are tags on query
      tgt_tags = TMUtilsMatching.transfer_tags(segment.source_text, translation, (source_lang, target_lang))
      segment.target_text = TMUtilsMatching.pre_process(tgt_tags.split(' '), target_lang, 'untokenizer', {})
    else:
      segment.target_text = translation.strip('\n')
    logging.info("Translate less minumum_match : {} {}".format(segment.source_text + ' -- ', translation))

    return segment


  def machine_translate(self, tm_engine ,source_lang, target_lang, in_segments, min_match):
    mt_texts = []
    mt_flags = []
    # Build list of texts to machine translate
    for query, (segments, match_check) in in_segments:
      mt_flags.append(match_check)
      if not match_check:
        mt_texts.append(XmlUtils.strip_tags(query))
    # No text suitable for MT - return input segments (False = Non-MT)
    if not mt_texts: return [(segments, False) for query, (segments, match_check) in in_segments]
    # Actual MT translation
    translated_texts = tm_engine.translate(mt_texts)
    # Fill output by either machine translation or segment
    out_segments = []
    for ttext, (query,(segments, match_check)) in zip(translated_texts, in_segments):
      if not segments:
        out_segments_per_q = []
      elif not match_check:
        out_segments_per_q = ([(self._prepare_target_text(query, segments[0][0], ttext ,source_lang, target_lang), min_match)] if translated_texts else [],True) # True = MT
      else:
        out_segments_per_q = (segments,False) # False = not MT
      out_segments.append(out_segments_per_q)
    return out_segments

  # Count number of segments in scan
  def count_scan(self, langs, filter = None):
    return self.seg_map.count_scan(langs, filter)

  # Scan matching segments
  def scan(self, langs, filter = None):
    for hit in self.seg_map.scan(langs, filter):
      yield self._doc2segment(hit.to_dict())

  # Scan matching segments
  def get_duplicates(self, langs, filter=None):
    for mid,hit in self.seg_map.get_duplicates(langs, filter):
      yield self._doc2segment(hit.to_dict())

  def get_duplicates_to_delete(self, langs, filter=None):
    unique_src = ""
    for mid,hit in self.seg_map.get_duplicates(langs, filter):
      tu = self._doc2segment(hit.to_dict())
      tu.id = mid
      # Source text is equal to previously seen unique source text -> yield to delete
      if tu.source_text == unique_src:
        yield tu
      else:
        unique_src = tu.source_text
  # Delete matching segments
  def delete(self, langs, filter = None, duplicates_only=False):
    self.seg_map.refresh_lang_graph()
    i = 0
    all = 0
    docs = list()
    # Scan all matching segments and delete them in batches
    scan_fun = self.seg_map.scan if not duplicates_only else self.get_duplicates_to_delete
    for hit in scan_fun(langs, filter):
      doc = hit.to_dict()
      doc['_id'] = hit.meta.id if not duplicates_only else hit.id
      docs.append(doc)
      i += 1
      # Batch max - invoke actual deletion
      if i > self.BATCH_SIZE:
        self._delete(langs, docs, filter, force_delete=duplicates_only)
        all += len(docs)
        logging.info("Deleted {} translation units".format(all))
        docs.clear()
        i = 0
    # Delete all remaining ones
    self._delete(langs, docs, filter, force_delete=duplicates_only)
    all += len(docs)
    logging.info("Final: deleted {} translation units".format(all))

  # Check if language pair exists
  def has_langs(self, langs):
    return shortest_path_length(self.seg_map.get_lang_graph(), langs[0], langs[1]) == 1

  def get_all_langs(self):
    lang_graph = self.seg_map.get_lang_graph()
    langs = [lang_pair for lang_pair in lang_graph.edges_iter()]
    return langs

  # Return list of file names for given language pair and filter
  def file_names(self, langs, filter=None):
    return [f[0] for f in self.seg_map.get_aggr_values('file_name', langs, filter)]

  # Generate new language pair by using pivot language, e.g.
  # (en, es) and (en, fr) will produce (es, fr) pair pivoted by en
  # TODO: support filters
  def generate(self, langs, pivot_lang=None, domains=None):
    if not pivot_lang:
      pivot_lang = self._find_pivot_lang(langs)
      if not pivot_lang:
        logging.warning("Failed to generate language map for {}".format(langs))
        return

    batch_mget = []
    for pivot_id,pivot_doc in self.ml_index.scan_pivot(pivot_lang, langs):
      batch_mget += [(pivot_id, pivot_lang, lang) for lang in langs]
      # Reached batch limit - generate segments
      if len(batch_mget) >= self.MGET_BATCH_SIZE:
        for segment in self._generate_batch(batch_mget, domains):
          yield segment
        batch_mget = []
    # Generate segments for remaining incomplete batch
    for segment in self._generate_batch(batch_mget, domains):
      yield segment

  # Return various statistics
  def stats(self):
    stats = dict()
    lang_graph = self.seg_map.get_lang_graph()

    lang_pairs = dict()
    for lang_pair in lang_graph.edges_iter():
      lang_pair_str = "_".join(lang_pair)
      lang_pairs[lang_pair_str] = dict()
      lang_pairs[lang_pair_str]['count'] = self.seg_map.count(lang_pair)
      # TODO: takes too long to get all queries. Cache results
      #for field in ['file_name', 'organization', 'domain', 'industry', 'language', 'type']:
      for field in ['file_name', 'domain']:
        lang_pairs[lang_pair_str][field] = self.seg_map.get_aggr_values(field, lang_pair, None)
    stats['lang_pairs'] = lang_pairs
    stats['query_timer'] = sorted(self.timer.stages.items(), key=operator.itemgetter(1), reverse=True)
    return stats

  def mstats(self):
    stats = dict()
    stats['lang_pairs'] = self.seg_map.mcount_buckets(['file_name', 'domain'])
    for lp,bucket_dict in stats['lang_pairs'].items():
      for bucket_name,bucket_value_dict in bucket_dict.items():
        for bucket_value,count in bucket_value_dict.items():
          d = stats.setdefault(bucket_name, dict())
          d.setdefault(bucket_value, 0)
          d[bucket_value] += count
    for lp,count in self.seg_map.mcount().items():
      stats['lang_pairs'][lp]['count'] = count

    stats['query_timer'] = sorted(self.timer.stages.items(), key=operator.itemgetter(1), reverse=True)
    return stats

  ############### Helper methods ###################
  def _query(self, q, qinfo, ml_response, qparams):
    self.timer.start("match_time_query")
    l_best_segments = []
    src_hits = [src_hit for src_hit in ml_response] # turn iterator into list to be reentrant
    src_hits_map = {src_hit.meta.id: src_hit for src_hit in src_hits}
    # Build segment by querying map and target index
    self.timer.start("src2tgt")
    map_docs = None
    try:
      map_docs = self._msrc_id2tgt_id(src_hits, qparams.source_lang, qparams.target_lang, return_multiple=True)
    except ValueError:
      logging.info("Unsupported index for target: {}".format(qparams.target_lang))
      #if not map_docs: raise (ValueError("Unsupported index for target: {}".format(target_lang)))

    if map_docs:
      target_ids = []
      for d in map_docs:
        target_id = d['target_id'] if d else "DUMMY_ID"
        target_ids.append((qparams.target_lang, target_id))
      self.timer.stop("src2tgt")
      self.timer.start("doc2segment")
      count = 0
      for map_doc, tgt_doc in zip(map_docs, self.ml_index.mget(target_ids)):
        if not map_doc: continue
        src_hit = src_hits_map[map_doc["source_id"]]
        segment = self._doc2segment(map_doc, sd=src_hit.to_dict(), td=tgt_doc)
        count = count + 1

        if segment and count <= (2 * qparams.limit):
            l_best_segments.append((segment, 0))
        else:
            break
      self.timer.stop("doc2segment")
      # If concordance mode is requested, return here without matching postprocessing -- return elasticsearch segments
      if qparams.concordance: return self._match(q, qinfo, l_best_segments, qparams)
    logging.info("Best segments(1): {}".format(l_best_segments))
    # Call automatic translation if elasticsearch doesn't find any segment
    if not l_best_segments:
      l_best_segments.append((TMTranslationUnit(
        {'source_text': ' ', 'target_text': ' ', 'source_language': qparams.source_lang,
         'target_language': qparams.target_lang, 'domain': qparams.domains, 'file_name': '', 'tm_creation_date': '',
         'tm_change_date': '', 'username': ''}),0))

    # Improve ElasticSearch match
    out_segments, check_match = self._match(q, qinfo, l_best_segments, qparams)
    logging.info("Best segments(2): {}".format(out_segments))

    return out_segments, check_match

  def _generate_batch(self, batch_mget, domains):
    pivots = self.seg_map.mget(batch_mget)
    # Pivots is a flat list with source pivots at even indexes and target pivots at odd ones
    # Merge source & target pivot map docs
    for j in range(0, len(pivots), 2):
      if pivots[j] and pivots[j + 1]:
        map_doc = self.seg_map.generate_pivot(pivots[j].to_dict(), pivots[j + 1].to_dict())
        # Skip document which don't belong to one of the given domains. TODO: support other fields like in general filter
        if domains and not (set(domains) & set(map_doc['domain'])):
          continue
        # Actual segment generation
        yield self._doc2segment(map_doc)

  # Select the best segment (Matching method) Return if there are good segments or need automatic translation
  def _match(self, qstring, qinfo, l_best_segments, qparams):

    match = False # Variable to check if there are segments with good ter or need automatic translation

    if not l_best_segments: return [],0
    tm_match = TMMatching(qstring, qinfo, qparams.source_lang, qparams.target_lang, qparams.out, qparams.min_match, qparams.domains, qparams.aut_trans, qparams.pipe)
    self.timer.start("match:execute")
    segments = tm_match.execute(l_best_segments, ['word_ter', 'posTag', 'position', 'glossary'], qparams.concordance)  # ['regex', 'posTag']:
    self.timer.stop("match:execute")
    # For concordance search, just return found segments
    if qparams.concordance:
      return segments, match
    # Else, try improving matching
    new_segments = []
    logging.info("Match segments: {}".format(segments))
    for segment, ter in segments: # This one is for each segment
      # Check time
      wait_time  = self.MATCH_TIME[0] if qparams.aut_trans else self.MATCH_TIME[1]
      if timer() - self.timer.ts["match_time_query"] > wait_time:
        if not new_segments: new_segments = segments # make sure we are not returning empty results
        logging.info("Matching segments (1)")
        break

      # Adjust match % according to filters
      if ter >= qparams.min_match:
        self.timer.start("adjust_match")
        ter = self._adjust_match(segment, qparams.domains, ter)
        self.timer.stop("adjust_match")
        new_segments.append((segment, ter))
        match = True
      elif qparams.aut_trans and len(segments) == 1: # Mark segment as one needed to machine-translate
        match = False
        new_segments.append((segment, ter))
    new_segments.sort(key = lambda x: (x[1], x[0].tm_change_date) if (x[0].tm_change_date is not None) else (x[1], str(datetime.datetime(1970, 1, 1))), reverse = True)
    logging.info("New match segments: {}".format(new_segments))

    tm_match.timer.print()
    return new_segments, match

  def _add_segments(self, segments):
    batch_status = []
    self.timer.start("add_segments:source")
    batch_status.append(self.ml_index.add_segments(segments, 'source'))
    self.timer.stop("add_segments:source")
    self.timer.start("add_segments:target")
    batch_status.append(self.ml_index.add_segments(segments, 'target'))
    self.timer.stop("add_segments:target")
    self.timer.start("add_segments:map")
    batch_status.append(self.seg_map.add_segments(segments))
    self.timer.stop("add_segments:map")
    logging.info('Added {} segments, status: {}'.format(len(segments), batch_status))
    return batch_status

  def _find_pivot_lang(self, langs):
    langs = [l.lower() for l in langs]
    lang_graph = self.seg_map.get_lang_graph()
    path_len = shortest_path_length(lang_graph, langs[0], langs[1])
    if path_len != 2:
      return None
    # Find shortest path
    path = shortest_path(lang_graph, langs[0], langs[1])
    assert (len(path) == 3)
    # Get a pivot language and scan all pivot segments
    return path[1]


  def _src_id2tgt_id(self, src_id, source_lang, target_lang):
    # Query  mapping segment
    target_id,map_doc = self.seg_map.get(uuid.UUID(src_id), source_lang, target_lang)
    if not target_id:
      logging.warning("Can't find matching segment for {}".format(src_id))
      return None,None
    else:
      assert isinstance(target_id, uuid.UUID)
    return target_id,map_doc

  def _msrc_id2tgt_id(self, src_hits, source_lang, target_lang, return_multiple=False):
    margs = [(uuid.UUID(src_hit.meta.id), source_lang, target_lang) for src_hit in src_hits]
    return self.seg_map.mget(margs, return_multiple=return_multiple)

  def _delete(self, langs, docs, filter, force_delete):
    source_lang, target_lang = langs
    # Delete map doc, returns tuple of 2 lists: deleted source and target ids
    deleted_ids = self.seg_map.delete(langs, docs, filter, force_delete)
    logging.info("After deleting from map: {} source and {} target potential orphan segments".format(len(deleted_ids[0]), len(deleted_ids[1])))

    # Check and delete only orphans (for source and target)
    for lang,ids in zip(langs,deleted_ids):
      ids_exist = self.seg_map.mexist(source_lang, ids)
      ids_to_delete = [id for id,exists in zip(ids, ids_exist) if not exists]
      logging.info("Lang: {}, actual orphans to delete: {}".format(lang.upper(), len(ids_to_delete)))
      self.ml_index.delete(lang, ids_to_delete)

  def _doc2segment(self, md, sd=None, td=None):
    doc = md
    if sd: doc['source_pos'] = sd.get('pos')
    if td: doc['target_pos'] = td.get('pos')
    segment = TMTranslationUnit(doc)
    return segment

  def _adjust_match(self, segment, domains, match):
    if domains:
      if not set(domains) & set(getattr(segment, 'domain')):
        match -= self.QUERY_PENALIZE[0]
    if self._is_dirty(segment):
      match -= self.QUERY_PENALIZE[1]
    return match

  def _is_dirty(self, segment):
    if segment.dirty_score and segment.dirty_score >= self.DIRTY_THRESHOLD:
      return True
    return False

if __name__ == "__main__":
  logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

  tmdb = TMDbApi()
  #tmdb.init_db()
  segment = TMTranslationUnit({
             "source_text": "Connect the pipe to the female end of the T.",
             "source_lang": "en-GB",
             "target_text": "Conecte la tubería al extremo hembra de la T.",
             "target_lang": "es-ES",
             "tm_creation_date" : "20090914T114332Z",
             "tm_change_date" : "20090914T114332Z",
             "industry": "Automotive Manufacturing",
             "type": "Instructions for Use",
             "organization":"Pangeanic"
             })
  tmdb.add_segment(segment)
  logging.info(tmdb.query("Connect the pipe to the female end of the T.", "en-GB", 'es-ES'))

