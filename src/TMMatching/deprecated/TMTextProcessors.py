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
from TMPosTagger.TMTokenizer import TMTokenizer
from TMPosTagger.TMPosTagger import TMPosTagger
from TMPosTagger.TMUniversalPosTag import TMUniversalPosTag

class TMTextProcessors:
  pos_taggers = dict()
  univ_pos_taggers = dict()
  tokenizers = dict()

  @staticmethod
  def pos_tagger(lang):
    lang = lang.upper()
    if not lang in TMTextProcessors.pos_taggers:
      logging.info("Loading POS tagger for {}".format(lang))
      TMTextProcessors.pos_taggers[lang] = TMPosTagger(lang)
    return TMTextProcessors.pos_taggers[lang]

  @staticmethod
  def univ_pos_tagger(lang):
    lang = lang.upper()
    if not lang in TMTextProcessors.univ_pos_taggers:
      TMTextProcessors.univ_pos_taggers[lang] = TMUniversalPosTag(lang)
    return TMTextProcessors.univ_pos_taggers[lang]

  @staticmethod
  def tokenizer(lang):
    lang = lang.upper()
    if not lang in TMTextProcessors.tokenizers:
      TMTextProcessors.tokenizers[lang] = TMTokenizer(lang)
    return TMTextProcessors.tokenizers[lang]

  @staticmethod
  def un_tokenizer(in_str, lang):
    lang = lang.upper()
    if not lang in TMTextProcessors.tokenizers:
      TMTextProcessors.tokenizers[lang] = TMTokenizer(lang)
    return TMTokenizer.un_tokenizer(in_str)#TMTextProcessors.tokenizers[lang]