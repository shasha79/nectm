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
import os, sys, re
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..'))
sys.path = [p for p in sys.path if p]

import logging
import datetime
import uuid
import json
from elasticsearch import Elasticsearch, helpers
from elasticsearch_dsl import Search

from TMDbApi.TMTranslationUnit import TMTranslationUnit
from TMDbApi.TMUtils import TMUtils
from TMDbApi.TMDbQuery import TMDbQuery
from TMPosTagger.TMTokenizer import TMTokenizer
from TMPreprocessor.TMRegExpPreprocessor import TMRegExpPreprocessor
from TMMatching.TMRegxMatch import TMRegexMatch


# API class for translation memories DB
class TMMonoLing:
  DOC_TYPE = 'tm'

  def __init__(self, **kwargs):
    self.es = Elasticsearch(kwargs = kwargs)
    # Put default index template
    self.es.indices.put_template(name='tm_template', body = self._index_template())
    self.refresh()

    #self.preprocessors = dict()
    self.tokenizers = dict()
    self.regex = dict()

  # Add new segment
  def add_segment(self, segment, ftype):
    # Add segment source and target texts to the correspondent index of ElasticSearch
    id = getattr(segment, ftype + '_id')
    index = TMUtils.lang2es_index(getattr(segment, ftype + '_language'))
    s_result = self.es.index(index=index,
                             doc_type=self.DOC_TYPE,
                             id=id,
                             body = self._segment2doc(segment, ftype))
    return id

  # Bulk segment addition
  def add_segments(self, segments, ftype):
    # Bulk insert
    return self._segment2es_bulk(segments, ftype, 'update', self._segment2doc_upsert)

  # Search for top matching segments
  def query(self, lang, qstring, filter = None):
    index = TMUtils.lang2es_index(lang)
    if not self.index_exists(index): return
    # Query source ES for the text
    query = TMDbQuery(es=self.es,
                      index = index,
                      q=qstring,
                      filter=filter)
    for response,q in query():
      for hit in response:
        yield hit,q

  # Search for top matching segments
  def mquery(self, lang, limit, q_list, filter=None):
    index = TMUtils.lang2es_index(lang)
    if not self.index_exists(index): return
    # Query source ES for the text
    query = TMDbQuery(es=self.es,
                          index=index,
                          q=q_list,
                          filter=filter,
			                    limit=limit)
    for response, q in query():
      yield response
      #for hit in response:
      #  yield hit

  # Get segment by id
  def get(self, lang, id):
    index = TMUtils.lang2es_index(lang)
    if not self.index_exists(index): return

    hit = self.es.get(index=index, id=id)
    if not hit: return None
    return hit['_source']

  # Get multiple segments by id
  def mget(self, ids_lang):
    if not ids_lang: return []
    body = [{
        '_index': TMUtils.lang2es_index(lang),
        '_id' : id
      } for lang,id in ids_lang]
    hits = self.es.mget(body={'docs' : body})
    if not hits: return None
    return [hit.get('_source',None) for hit in hits['docs']]


  # Scan matching segments
  def scan(self, lang, filter = None):
    index = TMUtils.lang2es_index(lang)
    if not self.index_exists(index): return

    query = TMDbQuery(es=self.es, index = index, filter=filter)
    for hit in query.scan():
      # Build segment by querying map and target index
      yield hit

  # Scan all pivot segments
  def scan_pivot(self, pivot_lang, langs):
    index = TMUtils.lang2es_index(pivot_lang)
    if not self.index_exists(index): return

    search = Search(using=self.es, index=index)
    for lang in langs:
      search = search.query('match', target_language=lang)
    for result in search.scan():
      yield result.meta.id

  # Bulk delete segments by id
  def delete(self, lang, ids):
    index = TMUtils.lang2es_index(lang)

    actions = [{'_op_type': 'delete',
                '_id': id,
                '_index' : index,
                '_type': self.DOC_TYPE,
                } for id in ids]
    # Bulk delete
    try:
      status = helpers.bulk(self.es, actions)
    except Exception as e:
      logging.warning(e)
      return str(e)
    return status

  # Should be called after modifying the index
  def refresh(self):
    #self.indexes = self.es.indices.get_aliases() #not supported anymore
    self.indexes = self.es.indices.get_alias("*")

  def index_exists(self, index):
    return self.es.indices.exists(index)

  def get_langs(self):
    return [TMUtils.es_index2lang(l) for l in self.indexes if re.search('^tm_\w{2}$', l)]

  ############### Helper methods ###################
  def _segment2es_bulk(self, segments, ftype, op_type, f_action):
    # Add segment source and target texts to the correspondent index of ElasticSearch in a batch
    actions = []
    added_ids = set()
    for segment in segments:
      id = getattr(segment, ftype + '_id')
      if id in added_ids: continue # avoid duplicates in the same batch
      added_ids.add(id)
      index = TMUtils.lang2es_index(getattr(segment, ftype + '_language'))
      action = {'_id': id,
                '_index' : index,
                '_type' : self.DOC_TYPE,
                '_op_type': op_type,
                '_source' : f_action(segment, ftype) #self._segment2doc(segment, ftype)
                }
      actions.append(action)
    # Bulk insert
    logging.info("Bulk upsert: {}".format(actions))
    s_result = helpers.bulk(self.es, actions)
    self.refresh() # refresh list of indexes (could have been created during insert)
    return s_result

  def _segment2doc(self, segment, ftype):
    text_pos = getattr(segment, ftype + '_pos')
    doc = {'text': getattr(segment, ftype + '_text')}
    # Optional fields (POS, tokenized)
    if hasattr(segment, ftype + '_pos'):
      doc['pos'] = getattr(segment, ftype + '_pos')

    op_ftype = 'source' if ftype == 'target' else 'target'
    # Auxiliary field to facilitate language matrix generation
    doc['target_language'] = [TMUtils.lang2short(TMUtils.str2list(getattr(segment, op_ftype + '_language'))[0])]
    doc['token_cnt'] = self.token_count(getattr(segment, ftype + '_text'), getattr(segment, ftype + '_language'))
    return doc

  def _segment2doc_upsert(self, segment, ftype):
    doc = self._segment2doc(segment, ftype)
    upsert_body = {'upsert': doc, # insert doc as is if it doesn't exist yet
            # If doc exists, then execute this painless scipt:
            # - add target language to the list  and filter unique values by converting to set
            'script' : 'ctx._source.target_language.add(params.language); ctx._source.target_language = ctx._source.target_language.stream().distinct().filter(Objects::nonNull).collect(Collectors.toList()); \
             if (params.pos != null) { ctx._source.pos = params.pos; }',
#             ',
            # parameters to the script
            'params' : { 'language' :  doc['target_language'],
                         'pos' : doc['pos']}
    }
    #return {'doc': doc, 'doc_as_upsert' : True }
    return upsert_body

  # Applied regular expression. tokenize and count the total of words
  def token_count(self, text, lang):

    lang = lang.split('-')[0].upper()
    if not lang in self.regex:
      try:
        self.regex[lang] = TMRegExpPreprocessor(lang)
        logging.info("Loading Regex for {}".format(lang))
      except Exception as e:
        logging.info("Unsupported Regex for {} ".format(lang))
        self.regex[lang] = lang
    if not lang in self.tokenizers:
        try:
          self.tokenizers[lang] = TMTokenizer(lang)
          logging.info("Loading Tokenizer for {}".format(lang))
        except Exception as e:
          self.tokenizers[lang] = lang
          logging.info("Unsupported Tokenizer for {}".format(lang))

    if self.regex[lang] != lang: text = TMRegexMatch.simplified_name(self.regex[lang].process(text))
    if self.tokenizers[lang] != lang: token_cnt = len((self.tokenizers[lang].tokenizer.process(text)).split(' '))
    else:
      if ' ' in text: token_cnt = len(text.split(' '))
      else: token_cnt = 1

    return token_cnt#len((self.tokenizers[lang].tokenizer.process(TMRegexMatch.simplified_name(self.regex[lang].process(text)))).split(' '))

  def _index_template(self):
    template =  {
      "template": "tm_*",
      "settings": {
        "analysis": {
          "analyzer": {
            "folding": {
              "tokenizer": "standard",
              "filter": ["lowercase", "asciifolding"]
            }
          }
        }
      },
      "mappings" : {
        self.DOC_TYPE: {
          "properties": {
            # Field text should analyzed, text.raw shouldn't
            "text": {
              "type": "text",
              "analyzer": "folding"
            },
            "target_language": {
              "type": "keyword",
              "index": "true"
            },
            "pos": {
              "type": "keyword",
              "index": "true"
            },
            "token_cnt": {
              "type": "integer",
              "index": "true"
            }
          }
        }
      }
    }
    print(json.dumps(template))
    return template

if __name__ == "__main__":
  logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

  index = TMMonoLing()
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
  index.add_segment(segment, 'source')
  index.add_segment(segment, 'target')

  logging.info(index.query("Connect the pipe to the female end of the T.", "en-GB"))
  logging.info(index.query("Conecte la tubería al extremo hembra de la T.", "es-ES"))
