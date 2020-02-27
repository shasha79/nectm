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
import re
from langid.langid import LanguageIdentifier, model


class TMUtils:
  # create lang identified with normalized probabilities
  lang_id = LanguageIdentifier.from_modelstring(model, norm_probs=True)
  TM_PREFIX='tm_'
  MAP_PREFIX='map_'

  @staticmethod
  def lang2locale(lang):
    return lang.lower().replace('-', '_')

  @staticmethod
  def lang2short(lang):
    return lang.lower().split('-')[0]

  @staticmethod
  def lang2es_index(lang):
    lang = lang.lower()[:2]
    TMUtils.validate_lang(lang)
    return TMUtils.TM_PREFIX + lang

  @staticmethod
  def es_index2lang(index):
    return re.sub('^{}'.format(TMUtils.TM_PREFIX), '', index)

  @staticmethod
  def validate_lang(lang):
    import iso639
    if not iso639.is_valid639_1(lang): raise Exception("Unknown language: {}".format(lang))

  @staticmethod
  def es_index2mapdb(src_index, tgt_index):
    # en + es = en_es
    return TMUtils.MAP_PREFIX + '_'.join([index.replace(TMUtils.TM_PREFIX, '') for index in [src_index, tgt_index]])

  @staticmethod
  def date2str(dt):
    return dt.strftime('%Y%m%dT%H%M%SZ')

  @staticmethod
  def str2list(s):
    if isinstance(s, str): return [s]
    return s

  @staticmethod
  def list2str(l):
    return l[0] if isinstance(l, (list, tuple)) else l

  @staticmethod
  def detect_lang(text, set_langs = None):
    # Restrict detected language to a given set or allow all of them
    TMUtils.lang_id.set_languages(set_langs)
    # Returns tuple : ('en', 0.34344)
    # TODO: use C as it is much faster
    l = TMUtils.lang_id.classify(text)
    return l

  @staticmethod
  def clean_empty_domains(es):
    from elasticsearch_dsl import Search
    search = Search(using=es, index="map_*").query("match", domain="")[:1000]
    for hit in search:
      domains = [d for d in hit.domain if d]
      hit_dict = hit.to_dict()
      hit_dict["domain"] = domains
      s_result = es.index(index=hit.meta.index, doc_type=hit.meta.doc_type, id=hit.meta.id,
                               body=hit_dict,
                               ignore=409)  # don't throw exception if a document already exists

from timeit import default_timer as timer

class TMTimer:
  def __init__(self, name = "", log_level=logging.DEBUG):
    self.stages = dict()
    self.ts = dict()
    self.name = name
    self.log_level = log_level

  def start(self, stage):
    if not stage in self.stages:
      self.stages[stage] = 0
    self.ts[stage] = timer()

  def stop(self, stage):
    if not stage in self.stages or not stage in self.ts:
      return;
    self.stages[stage] += timer() - self.ts[stage]
    del self.ts[stage]

  def print(self):
    for stage,ts in self.stages.items():
      logging.log(self.log_level, "==== Execution time of stage {}::{}:{}".format(self.name,stage, ts))


if __name__ == "__main__":
  from elasticsearch import Elasticsearch
  es = Elasticsearch()
  TMUtils.clean_empty_domains(es)
