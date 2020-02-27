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
from TMMatching.TMTextProcessors import TMTextProcessors
import pytercpp
import editdistance

class TMUtilsMatching:

  @staticmethod
  def len_compare(str_x, str_y):
    if ((len(str_x) - len(str_y) == 0) or abs(len(str_x) - len(str_y)) == 1):
      return True
    else: return False

  @staticmethod
  def pre_process(text, lang, preprocess, dic_re):
    if preprocess == 'tokenizer':
      process_text = TMTextProcessors.tokenizer(lang).tokenizer.process(text)
    if preprocess == 'reg_exp':
      process_text = dic_re[lang].process(text)
    if preprocess == 'untokenizer':
      process_text = TMTextProcessors.un_tokenizer(text, lang)
    if preprocess == 'pos_tagger':
      posTag_text = TMTextProcessors.pos_tagger(lang).tag_segments([text])
      process_text = " ".join([word_pos[1] for word_pos in posTag_text[0] if len(word_pos) > 1])
    if preprocess == 'universal_pos_tagger':
      # Applied universal postagger
      process_text = TMTextProcessors.univ_pos_tagger(lang).map_universal_postagger(text)
      process_text = process_text[0]
    return process_text

  @staticmethod
  def segment_2_universal(text, pos, lang):
    word_array = text.split(' ')  # word
    pos_array = pos.split(' ')  # pos
    return TMUtilsMatching.pre_process([[[word_array[p], pos_array[p]] for p in range(0, len(word_array))]], lang, 'universal_pos_tagger', {})

  @staticmethod
  # Estimate TER between sources segmets.
  def _ter_score(src_x, src_y):
    ter = pytercpp.ter(src_x.split(), src_y.split())
    if ter > 1: ter = 1
    return (100 - (ter * 100))

  @staticmethod
  def ter_distance(src, tgt):
    return 0.25 - pytercpp.ter(src.lower().split(), tgt.lower().split())

  @staticmethod
  def pos_bool(src, tgt):
    if src != tgt:
      return 0
    else:
      return 1

  @staticmethod
  def position_distance(src, tgt):
    return 1 - (0.25 * abs(int(src) - int(tgt)))

  @staticmethod
  # Estimate edit distance between sources segmets.
  def _edit_distance(src_x, src_y):
    return (100 - ((editdistance.eval(src_x, src_y)/len(src_x)) * 100))