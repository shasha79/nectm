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
import logging
from elasticsearch_dsl import MultiSearch, Search, Q

class TMDbQuery:

  # Bilingual filter
  str_attrs = ['file_name', 'organization', 'domain', 'industry', 'language', 'tuid', 'type', 'username']
  date_attrs = ['tm_change_date', 'tm_creation_date', 'insert_date', 'update_date', 'check_date']
  num_attrs = ['dirty_score']
  # These attributes contain list of strings (ovelaps with str_attrs)
  list_attrs = ['file_name', 'organization', 'domain', 'industry', 'language', 'type']


  #Monolingual filter
  monoling_num_attrs = ['token_cnt']
  monoling_str_attrs = ['target_language']

  attrs = str_attrs + date_attrs

  def __init__(self, es, index, limit=10, q=None, filter=None):
    self.search = list()#Search(using=es, index=index)
    self.msearch = MultiSearch(using=es, index=index)
    self.queries = list()
    self.num_segs = 0
    self.limit = limit
    # Build queries
    if isinstance(q, str):
      q = [q]
    self._build(q)
    # Build filter(s)
    if isinstance(filter, dict):
      filter = [filter]
    self._filter(filter, es, index)

  def __call__(self):
    # Add all queries to MultiSearch
    msearch = self.msearch
    for q, f in zip(self.queries, self.search):
      msearch = msearch.add(f.query(q)[:self.limit]) # Specific filter for each querie

    # Execute queries
    responses = msearch.execute()
    # Process responses
    for q, response in zip(self.queries, responses):
      if not hasattr(response, 'error'):
        yield response,q.text

  @property
  def count(self):
    if self.num_segs: return self.num_segs
    # Count total scan size
    for q, f in zip(self.queries, self.search):
      search = f.query(q)
      self.num_segs += search[:1].execute().hits.total
    return self.num_segs

  def scan(self):
    # Count total scan size
    for q, f in zip(self.queries, self.search):
      search = f.query(q)
      for hit in search.scan():
        yield hit


  def aggs(self, field):
    search = self.search[0]
    bucket_name = 'values'
    search.aggs.bucket(bucket_name, 'terms', field=field, size=999999)
    response = search.execute()
    if not response.hits.total or bucket_name not in response.aggregations: return []
    values = [(f.key,f.doc_count) for f in response.aggregations[bucket_name].buckets]
    return values

  # Nested buckets - first, bucket all documents by field values, then bucket them by ES index (language pair)
  def aggs_by_index(self, field):
    search = self.search[0]
    bucket_name = 'values'
    search.aggs.bucket(bucket_name, 'terms', field=field, size=0).bucket('indexes', 'terms', field='_index', size=0)
    response = search.execute()
    if not response.hits.total: return []
    values = [b for f in response.aggregations[bucket_name].buckets for b in f['indexes'].buckets]
    return values

  def duplicates(self, field):
    search = self.search[0].params(search_type="count")
    bucket_name = 'duplicates'
    search.aggs.bucket('duplicates', 'terms', field=field, size=0, min_doc_count=2).metric(
      'top_docs', 'top_hits', size=100, sort=[{"update_date": {"order": "desc"}}])
    response = search.execute()
    if not response.hits.total: return []
    values = [(b._id,b._source) for f in response.aggregations[bucket_name].buckets for b in f['top_docs']['hits']['hits']]

    return values

  def _build(self, q_list):
    if not q_list:
      self.queries.append(Q())
      return
    # Build list of queries sorted by match in a decreasing order
    for q in q_list:
      self.queries.append(Q("match", text=q))

  def _filter(self, filter, es, index):
    if not filter:
      self.search.append(Search(using=es, index=index))
      return
    for each_f in filter:
      f = Search(using=es, index=index)
      # Build string-field filters
      for attr in self.monoling_str_attrs:
        if attr in each_f:
          f = f.filter('match', **{attr : each_f[attr]})
      # TODO: figure out the difference to filter by 'terms' and 'match'
      for attr in self.str_attrs:
        if attr in each_f:
          f = f.filter('terms', **{attr : each_f[attr]})
      # Build date-field filters
      for attr in self.date_attrs + self.num_attrs + self.monoling_num_attrs:
        a = each_f.get(attr)
        if a: f = f.filter('range', **{attr : each_f[attr]})
      logging.info("ES query: {}".format(f.to_dict()))
      self.search.append(f)


if __name__ == '__main__':
  from elasticsearch import Elasticsearch
  es = Elasticsearch()
  index = "map_en_es"
  q = TMDbQuery(es, index)
  print([r.to_dict() for r in q.duplicates("source_text")])
