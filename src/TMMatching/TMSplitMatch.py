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
import sys, os

sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))
sys.path = [p for p in sys.path if p]

from TMMatching.TMUtilsMatching import TMUtilsMatching
from TMAutomaticTranslation.TMAutomaticTranslation import TMAutomaticTranslation
import TMDbApi
import logging
import math

class TMSplitMatch():

  #list_query can be a list of sentences or a list of phrases + posTag
  #list_marks can be empty or with marks
  # split_type indicate if there are sentences or phrases
  def __init__(self, list_query, list_marks, src_lang, tgt_lang, split_type, aut_trans, domain):
    self.src_lang = src_lang
    self.tgt_lang = tgt_lang
    self.aut_trans = aut_trans
    self.domain = domain

    self.tmdb_api = TMDbApi.TMDbApi.TMDbApi()

    self.split_type = split_type

    if self.split_type == 'sentence':
      self.list_query = list_query
    if self.split_type == 'phrase':

      if not TMUtilsMatching.empty_list(list_marks): # Search its translation target lang
        self.list_marks = self.tgt_list_marks(list_marks)  # [[], [], ('and', 'CC')]
      else:
        self.list_marks = list_marks
      '''
      [[('-', ':'), ('A', 'DT'), ('framework', 'NN'), ('for', 'IN'), ('the', 'DT'), ('measurement', 'NN'), ('of', 'IN'),
        ('greenhouse', 'NN'), ('gas', 'NN'), ('concentrations', 'NNS'), ('is', 'VBZ'), ('in', 'IN'), ('place', 'NN')],
       [('to', 'TO'), ('understand', 'VV'), ('their', 'PP$'), ('sources', 'NNS')],
       [('sinks', 'NNS'), ('requires', 'VVZ'), ('measuring', 'VVG'), ('transport', 'NN'), ('and', 'CC'), ('flux', 'NN'),
        ('in', 'IN'), ('both', 'CC'), ('the', 'DT'), ('horizontal', 'JJ'), ('and', 'CC'), ('vertical', 'JJ'),
        ('.', 'SENT')]]
      '''
      self.list_query = [' '.join([word for word, post in part]) for part in list_query]
      self.list_pos = [' '.join([pos for word, pos in part]) for part in list_query]
      logging.info("After Split Each parts: {} {}".format(self.list_query, self.list_pos))
    #print(self.list_query)
    #print(self.list_pos)

    #self.query_dic = {'query': self.query}

  def tgt_list_marks(self, list_marks):

    my_puntation_list = ['!', '"', '#', '$', '%', '&', "'", ')', '*', '+', ',', '-', '.', ':', ';', '<', '=', '>', '?','@','\\', ']', '^', '_', '`', '|', '}', '~', '。', '，', '；', '、']

    out_translation = []
    c_list = [(i[0], i[0]) for i in list_marks if i and i[1] not in my_puntation_list] # This list is use to query elasticsearch, using token_count method. This function, estimate the total of token after
    # simplified tags, if there are tags on query. In this case, there are not tags, then I pass the query string in both position of tuple.

    # Call elasticsearch  #
    dic_filter = self.tmdb_api._filter_by_query(c_list, self.src_lang, self.tgt_lang, 1, True)

    out_elastic = [(query, segment[0].target_text.lower()) if segment else (query, []) for query, segment in self.tmdb_api.exact_query([q0 for q0, q1 in c_list], self.src_lang, self.tgt_lang, 10, dic_filter)]  # exact_query(un_match, self.src_lang, self.tgt_lang, limit, exact_length)

    # Call automatic translation
    l_aut_trans = [out_elastic.pop(out_elastic.index((query, tgt)))[0] for query, tgt in out_elastic if not tgt]
    if self.aut_trans and l_aut_trans:
      out_translation = self._execute_aut_trans(l_aut_trans)

    list_marks = self._create_tgt_list(list_marks, out_elastic, out_translation, my_puntation_list)
    return list_marks

  def _create_tgt_list(self, list_marks, out_elastic, out_translation, my_puntation_list):

    list_tgt = []
    for q in list_marks:
      if not q:
        list_tgt.append(q)
      else:
        if q[1] in my_puntation_list:
          list_tgt.append(q[0])
        else:
          if q[0] in [e for e, t in out_elastic]:
            list_tgt.append(out_elastic[0][1])
          else:
            if q[0] in [e for e, t in out_translation]:
              pos = [e for e, t in out_translation].index(q[0])
              list_tgt.append(out_translation[pos][1])
    return list_tgt

  def _execute_aut_trans(self, l_aut_trans):
    tgt = []

    tm_engine = TMAutomaticTranslation.get_engine(self.src_lang, self.tgt_lang, self.domain)

    out_translation = tm_engine.translate(l_aut_trans)
    # Check if translation are ok
    if out_translation:
      i = 0
      for query in l_aut_trans:
        tgt.append((query, out_translation[i].strip('\n')))
        i = i + 1
    else:
      for query in l_aut_trans:
        tgt.append((query, query))
    return tgt

  def _match(self):

    #Create dictionary con query info (posTag and universal)

    if self.split_type == 'sentence':
      list_info_query = [{'tokenizer': self.list_query[j]} for j in range(0, len(self.list_query))]
    else:
      list_info_query = [{'tokenizer': self.list_query[j], 'pos': self.list_pos [j]} for j in range(0, len(self.list_query))]

    # Query Elasticsearch --> out=moses to return only one segment
    l_best_segments = self.tmdb_api.query([TMUtilsMatching.pre_process(q.split(' '), self.src_lang, 'untokenizer', {}) for q in self.list_query], list_info_query, (self.src_lang, self.tgt_lang), pipe=['regex', 'tags', 'posTag'], out='moses', limit=5, domains=None, min_match=80, concordance=False, aut_trans=False, exact_length=False)

    join_source = ''
    join_target = ''
    total_match = 0
    for i in range(0, len(l_best_segments)):
      if l_best_segments[i]:
        segment, match = l_best_segments[i][0]
        join_source = join_source + ' ' + segment.source_text
        join_target = join_target + ' ' + segment.target_text
      else:
          join_source = join_source + ' ' + self.list_query[i]
          join_target = join_target + ' ' + self.list_query[i]
          match = 0
      total_match = total_match + match

      if self.split_type == 'phrase':
        if self.list_marks:
          if self.list_marks[0]:
            mark = self.list_marks.pop(0)[0]
            join_source = join_source + ' ' + mark
            join_target = join_target + ' ' + mark

    total_match = total_match/len(self.list_query)
    #print(join_source + ' ---- ' + join_target + ' ---- ' + str(total_match))
    return join_source, join_target, int(math.floor(total_match))








