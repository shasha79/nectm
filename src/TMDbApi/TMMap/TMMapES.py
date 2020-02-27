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
import uuid
import re
import logging
import datetime
from elasticsearch import Elasticsearch, helpers
from elasticsearch_dsl import Search, MultiSearch, Q
import networkx

from TMDbApi.TMMap.TMMap import TMMap
from TMDbApi.TMUtils import TMUtils, TMTimer
from TMDbApi.TMDbQuery import TMDbQuery


class TMMapES(TMMap):
  UPSERT_SCRIPT='upsert_segment'

  def __init__(self):
    self.es = Elasticsearch(timeout=30, max_retries=3, retry_on_timeout=True)
    self.DOC_TYPE = 'id_map'
    self.refresh_lang_graph()
    self.es.indices.put_template(name='map_template', body=self._index_template())
    self.es.put_script(TMMapES.UPSERT_SCRIPT, body=self._upsert_script())
    self.scan_size = 9999999

    self.timer = TMTimer("TMMapES")

  def add_segment(self, segment):
    m_index,swap = self._get_index(segment.source_language, segment.target_language, create_missing=True)
    doc = self._segment2doc(segment)
    if swap: self._swap(doc)
    # Add segment source and target texts to the correspondent index of ElasticSearch
    s_result = self.es.index(index=m_index, doc_type=self.DOC_TYPE, id=self._allocate_id(segment, swap),
                             body = doc,
                              ignore=409) # don't throw exception if a document already exists
    return s_result

  def add_segments(self, segments):
    if not segments:
      return

    actions = []
    for segment in segments:
      self.timer.start("add_segment:get_index")
      m_index, swap = self._get_index(segment.source_language, segment.target_language, create_missing=True)
      self.timer.stop("add_segment:get_index")
      self.timer.start("add_segment:segment2doc")
      doc = self._segment2doc(segment)
      if swap: self._swap(doc)
      upsert_doc = self._doc_upsert(doc)
      self.timer.stop("add_segment:segment2doc")
      self.timer.start("add_segment:swap_doc")
      self.timer.stop("add_segment:swap_doc")
      action = {'_id': self._allocate_id(segment, swap),
                '_index' : m_index,
                '_type' : 'id_map',
                '_op_type': 'update',
                '_source' : upsert_doc,
                }
      actions.append(action)
    # Bulk operation
    logging.info("Bulk upsert (map): {}".format(actions))
    
    self.timer.start("add_segment:es_index")
    s_result = helpers.bulk(self.es, actions)
    self.timer.stop("add_segment:es_index")
    return s_result

  def count_scan(self, langs, filter = None):
    query,swap = self._create_query(langs, filter)
    if not query: return 0 # index doesn't exist
    return query.count

  def scan(self, langs, filter = None):
    query,swap = self._create_query(langs, filter)
    for hit in query.scan():
      if swap: hit = self._swap(hit)
      # Check if a source/target docs match the pattern(s) if given
      matches_pattern = not filter or self._match_pattern(hit['source_text'], filter.get('squery')) and \
                                      self._match_pattern(hit['target_text'], filter.get('tquery'))
      # Yield actual segment
      if matches_pattern:
        yield hit

  # bidirectional query
  def get(self, source_id, source_lang, target_lang):
    search, swap = self._create_search(source_id, source_lang, target_lang)
    if not search: return None,None
    res = search.execute()
    hits = res.to_dict()['hits']['hits']
    if not hits: return None,None
    ret_doc = hits[0]['_source']
    # Exchange source and target (if needed)
    if swap: ret_doc = self._swap(ret_doc)
    return uuid.UUID(ret_doc['target_id']),ret_doc

  # multi-get (bidirectional)
  def mget(self, id_langs, return_multiple=False):
    if not id_langs: return []
    msearch = MultiSearch(using=self.es)
    search_swap = []
    for source_id,source_lang,target_lang in id_langs:
      search,swap = self._create_search(source_id,source_lang,target_lang)
      if search:
        # Sort by update date so in case of multiple segments having the same source, the latest one will be returned
        search = search.sort('-update_date')
        msearch = msearch.add(search)
        search_swap.append(swap)

    responses = msearch.execute()
    results = []
    for res,swap in zip(responses,search_swap):
      try:
        if not 'hits' in res or not res.hits.total:
          results.append(None)
          continue
        for ret_doc in res.hits:
          # Exchange source and target (if needed)
          if swap: ret_doc = self._swap(ret_doc)
          results.append(ret_doc)
          if not return_multiple: break
      except:
        # Exception is thrown if Response is in some invalid state (no hits, hits are empty)
        logging.warning("Invalid Response object: {}".format(res.to_dict()))
        results.append(None)
        continue
    return results


  def delete(self, langs, docs, filter, force_delete=False):
    source_lang, target_lang = langs
    filter_list_attrs = {attr: value for attr,value in filter.items() if attr in TMDbQuery.list_attrs}

    deleted_ids = [list(), list()] # source and target

    m_index,swap = self._get_index(source_lang, target_lang)
    if not m_index: return deleted_ids

    actions = []
    for doc in docs:
      # Commmon action fields
      action = {'_id': doc['_id'],
                '_index': m_index,
                '_type': self.DOC_TYPE
                }
      del doc['_id'] # id is not part of the doc
      if force_delete or not filter_list_attrs:
        action['_op_type'] = 'delete'
      else:
        for attr,value_list in filter_list_attrs.items():
          assert(doc[attr])
          doc[attr] = list(set(doc[attr]) - set(value_list)) # delete from the list of values all those in filter
          # If no values left in at least one of the attributes -> map doc can be safely deleted
          if not doc[attr]:
            action['_op_type'] = 'delete'
            deleted_ids[0].append(doc['source_id'])
            deleted_ids[1].append(doc['target_id'])
            break
      # If not marked for delete -> update it
      if not '_op_type' in action:
        action['_op_type'] = 'index'
        action['_source'] = doc
      actions.append(action)
    # Bulk operation (update/delete)
    try:
      status = helpers.bulk(self.es, actions)
      logging.info("Map Delete status: {}".format(status))

    except Exception as e:
      print("MAP DELETE EXCEPTION: {}".format(e))

      logging.warning(e)
    return deleted_ids

  # Check if given list of monolingual source ids exist in any map
  def mexist(self, src_lang, src_ids):
    if not src_ids: return []
    tgt_langs = [target_lang for target_lang in self.lang_graph.neighbors(src_lang)]

    MEXIST_BATCH_SIZE = 10
    results = []
    for i in range(0, len(src_ids), MEXIST_BATCH_SIZE):
      msearch = MultiSearch(using=self.es)
      for source_id in src_ids[i:i+MEXIST_BATCH_SIZE]:
        search = self._create_search_mindexes(source_id, src_lang, tgt_langs)
        if search:
          msearch = msearch.add(search)
      responses = msearch.execute()
      for res in responses:
        try:
          results.append(bool('hits' in res and res.hits.total))
        except:
          # Exception is thrown if Response is in some invalid state (no hits, hits are empty)
          logging.warning("Invalid Response object: {}".format(res.to_dict()))
          results.append(None)
    return results

  # Count number of segments
  def count(self, langs):
    m_index,swap = self._get_index(langs[0], langs[1])
    if not m_index: return []
    search =  Search(using=self.es, index=m_index).params(search_type="count")
    res = search.execute()
    return res.to_dict()['hits']['total']

  def get_duplicates(self, langs, filter):
    query,swap = self._create_query(langs, filter)
    if not query: return []

    src_tgt = 'source' if not swap else 'target'
    res = query.duplicates(field='{}_text'.format(src_tgt))
    return res

  # Count number of segments for multiple language pairs
  def mcount(self):
    search = Search(using=self.es, index="{}*".format(TMUtils.MAP_PREFIX))
    search.aggs.bucket('values', 'terms', field='_index', size=999999)
    res = search.execute()
    if not hasattr(res, 'aggregations') or 'values' not in res.aggregations: return dict()
    return dict([(re.sub("^{}".format(TMUtils.MAP_PREFIX), "", f.key),f.doc_count) for f in res.aggregations['values'].buckets])

  def mcount_buckets(self, buckets):
    ms = MultiSearch(using=self.es)
    for bucket_name in buckets:
      search = Search(using=self.es, index="{}*".format(TMUtils.MAP_PREFIX))
      search.aggs.bucket('indexes', 'terms', field='_index', size=999999).bucket('values', 'terms', field=bucket_name, size=999999)
      ms = ms.add(search)

    mres = ms.execute()

    lang2buckets = dict()
    for bucket_name,res in zip(buckets, mres):
      if hasattr(res, "aggregations") and 'indexes' in res.aggregations:
        triple_list = [(re.sub("^{}".format(TMUtils.MAP_PREFIX), "", x.key), y.key, y.doc_count) for x in  res.aggregations['indexes'].buckets for y in x['values'].buckets]
        for lang_pair,bucket_value,count in triple_list:
          lang2buckets.setdefault(lang_pair, dict()).setdefault(bucket_name, dict())[bucket_value] = count

    return lang2buckets

  # Generate doc based on 2 docs with pivot
  def generate_pivot(self, sdoc, tdoc):
    if sdoc['source_id'] != tdoc['source_id']:
       logging.error("Invalid pair for pivot generation: sdoc {}, tdoc {}".format(sdoc,tdoc))
    assert(sdoc['source_id'] == tdoc['source_id']) # make sure pivot exists
    # Result doc
    doc = dict()
    for attr in ['id', 'language', 'text']:
      doc['source_'+attr] = sdoc['target_'+attr]
      doc['target_'+attr] = tdoc['target_'+attr]
    for attr in TMDbQuery.str_attrs:
      if not attr in sdoc: continue
      # TODO: should it be union or intersection?
      doc[attr] = sdoc[attr] + tdoc[attr] if sdoc.get(attr) and tdoc.get(attr) else None
        
    for attr in ['tm_creation_date', 'tm_change_date', 'insert_date', 'update_date']:
      doc[attr] = TMUtils.date2str(datetime.datetime.now())
    doc['check_date'] = TMUtils.date2str(datetime.datetime(1970, 1, 1))
    return doc

  # Build & return language graph
  def get_lang_graph(self):
    self.refresh()
    lang_graph = networkx.Graph()
    # Build language connection graph
    for index in self.indexes:
      m = re.search('map_([a-z]{2})_([a-z]{2})', index)
      if m:
        lang_graph.add_edge(m.group(1), m.group(2))
    return lang_graph

  # Should be called after modifying the index
  def refresh(self):
    self.indexes = self.es.indices.get_alias("*")

  def refresh_lang_graph(self):
    self.lang_graph = self.get_lang_graph()

  # Get list of all values (aggregated) for the given field
  def get_aggr_values(self, field, langs, filter):
    query,swap = self._create_query(langs, filter)
    if not query: return []
    return query.aggs(field)

  def _create_query(self, langs, filter=None):
    source_lang,target_lang = langs
    m_index,swap = self._get_index(source_lang, target_lang)
    if not m_index: return None,None

    query = TMDbQuery(es=self.es, index=m_index, filter=filter)
    return query,swap

  def _create_search(self, source_id, source_lang, target_lang):
    m_index,swap = self._get_index(source_lang, target_lang)
    if not m_index: return None,None
    qfield = "source_id" if not swap else "target_id"

    search =  Search(using=self.es, index=m_index)
    search.query = Q('term', **{qfield: source_id})
    return search,swap

  def _create_search_mindexes(self, source_id, source_lang, target_langs):
    m_indexes = [self._get_index(source_lang, tgt_lang)[0] for tgt_lang in target_langs] # take only m_index, swap is not interested
    search = Search(using=self.es, index=m_indexes)
    # FIXME: search only source_id or target_id according to index direction,  otherwise it might return results from incorect language (having the same id due to exact the same text)
    search.query = Q('term', source_id=source_id) | Q('term', target_id=source_id)
    return search

  def _match_pattern(self, text, pattern):
    if not pattern: return True
    return re.search(pattern, text)

  # Returns tuple (index_name, is_swapped)
  def _get_index(self, source_lang, target_lang, create_missing=False):
    m_index = TMUtils.es_index2mapdb(TMUtils.lang2es_index(source_lang),
                                     TMUtils.lang2es_index(target_lang))

    if self.es.indices.exists(index=m_index): return m_index,False
    # Try reverse index
    r_index = TMUtils.es_index2mapdb(TMUtils.lang2es_index(target_lang),
                                     TMUtils.lang2es_index(source_lang))
    # Found reverse index - use it
    if self.es.indices.exists(r_index): return r_index,True
    if not create_missing: return None,None
    # Neither direct, nor reverse index exist - create a direct one
    try:
      self.es.indices.create(m_index)
    except:
      pass
    self.refresh_lang_graph()
    return m_index,False

  def _allocate_id(self, segment, swap=False):
    s_t_list = ["source", "target"] if not swap else ["target", "source"]
    istr = ""
    # ID is UUID created from concatenation of source/target texts and their metadata (pre and post metatags)
    for s_t in s_t_list:
      istr += getattr(segment, "{}_text".format(s_t))
      metadata_attr = "{}_metadata".format(s_t)
      if getattr(segment, metadata_attr):
        # metadata is a dictionary; create its string representation sorted by keys
        for key in sorted(getattr(segment, metadata_attr).keys()):
          istr +=  "{}->{}".format(key, getattr(segment, metadata_attr)[key])

    return uuid.uuid5(uuid.NAMESPACE_URL, istr)

  def _swap(self, doc):
    for field in ['id', 'language', 'text']:
      src = 'source_' + field
      tgt = 'target_' + field
      # Exchange source and target
      tmp = doc[src]
      doc[src] = doc[tgt]
      doc[tgt] = tmp
    return doc

  def _doc_upsert(self, doc):
    #params = { d :  doc.get(d, 'none') for d in TMDbQuery.list_attrs + TMDbQuery.num_attrs + ['update_date']}
    params = { "source" : doc }
    upsert_body = {'upsert': doc, # insert doc as is if it doesn't exist yet
            # If doc exists, then execute this groovy scipt:
            # - add attribute to the list  and filter unique values by converting to set
            'script' : {
              'id': TMMapES.UPSERT_SCRIPT,
               # parameters to the script
               'params' : params,
            }
    }
    #return {'doc': doc, 'doc_as_upsert' : True }
    #print("UPSERT BODY: {}".format(upsert_body))
    return upsert_body


  def _index_template(self):
    props = dict()
    # Create mapping for field: source_id, target_text etc.
    for t in ['source', 'target']:
      for f in ['id', 'text', 'language']:
        props['_'.join([t, f])] = {
          "type": "keyword",
          "index": "true"
        }

    for f in TMDbQuery.date_attrs:
      props[f] = {
              "type": "date",
              "format": "basic_date_time_no_millis"
            }

    for f in TMDbQuery.str_attrs + ["check_version"]:
      props[f] = {
        "type": "keyword",
        "index": "true"
      }

    props["dirty_score"] = {
      "type": "integer",
    }

    template =  {
      "template": "map_*",
      "mappings": {
        self.DOC_TYPE: {
          "properties": props
        }
      }
    }
    return template


  def _upsert_script(self):
    script = ''
    # create script for upserting segments, e.g each attribute will be list
    # to which new value will be concatenated
    for attr in TMDbQuery.list_attrs:
      #script += 'ctx._source.{} = (ctx._source.{}) ? ctx._source.{} + {} as Set: [{}]; '.format(*([attr]*5))
      script += """ if (ctx._source.{} != null) {{
      if (params.source.{} != null) {{
          for(int i=0; i<params.source.{}.size(); i++) {{
              if (! ctx._source.{}.contains(params.source.{}.get(i))) {{
                  ctx._source.{}.add(params.source.{}.get(i));
              }}
          }}    
      }}      
    }} else {{ 
      ctx._source.{} = [params.source.{}]; }} """.format(*([attr]*9))
      #script += 'ctx._source.{} = (ctx._source.{}) ? new HashSet(ctx._source.{} + [params.source.{}]): [params.source.{}]; '.format(*([attr]*5))
    #script += script + 'ctx._source.dirty_score = dirty_score ? dirty_score : ctx._source.dirty_score;'
    script += script + 'ctx._source.dirty_score = params.source.dirty_score;' # Alex decided: If no rule was applied, then dirty_score = 0
    script += script + 'ctx._source.update_date = params.source.update_date;'
    print(script)
    #return {'script': { 'inline': script, 'lang': 'painless' } }
    return {'script': { 'source': script, 'lang': 'painless' } }



