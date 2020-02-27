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

from TMPosTagger.TMTokenizer import TMTokenizer, TMUNTokenizer
from TMPosTagger.TMPosTagger import TMPosTagger
from TMPosTagger.TMUniversalPosTag import TMUniversalPosTag
from nltk.corpus import stopwords

class TMTextProcessors:
  pos_taggers = dict()
  univ_pos_taggers = dict()
  tokenizers = dict()
  stop_words_list = dict()
  untokenizers = dict()


  @staticmethod
  def pos_tagger(lang):
    if not lang in TMTextProcessors.pos_taggers:
      logging.info("Loading POS tagger for {}".format(lang))
      TMTextProcessors.pos_taggers[lang] = TMPosTagger(lang)
    return TMTextProcessors.pos_taggers[lang]

  @staticmethod
  def univ_pos_tagger(lang):
    if not lang in TMTextProcessors.univ_pos_taggers:
      try:
       TMTextProcessors.univ_pos_taggers[lang] = TMUniversalPosTag(lang)
      except Exception as e:
        TMTextProcessors.univ_pos_taggers[lang] = None
    return TMTextProcessors.univ_pos_taggers[lang]

  @staticmethod
  def tokenizer(lang):
    if not lang in TMTextProcessors.tokenizers:
      TMTextProcessors.tokenizers[lang] = TMTokenizer(lang)
    return TMTextProcessors.tokenizers[lang]

  @staticmethod
  def un_tokenizer(lang):
    if not lang in TMTextProcessors.untokenizers:
      TMTextProcessors.untokenizers[lang] = TMUNTokenizer(lang)
    return TMTextProcessors.untokenizers[lang]#TMTextProcessors.tokenizers[lang]

  @staticmethod
  def stop_words(lang):
    if not lang in TMTextProcessors.stop_words_list:
      TMTextProcessors.stop_words_list[lang] = stopwords.words(lang)
    return TMTextProcessors.stop_words_list[lang]  # TMTextProcessors.tokenizers[lang]



if __name__ == '__main__':
  text = [
    [('When', 'WRB'), ('the', 'DT'), ('motorcycle', 'NN'), ('is', 'VBZ'), ('to', 'TO'), ('be', 'VB'), ('stored', 'VVN'),
     ('for', 'IN'), ('any', 'DT'), ('length', 'NN'), ('of', 'IN'), ('time', 'NN'), (',', ','), ('it', 'PP'),
     ('should', 'MD'),
     ('be', 'VB'), ('prepared', 'VVN'), ('for', 'IN'), ('storage', 'NN'), ('as', 'RB'), ('follows', 'VVZ'), (':', ':')], \
    [('Run', 'VV'), ('the', 'DT'), ('engine', 'NN'), ('for', 'IN'), ('about', 'RB'), ('five', 'CD'), ('minutes', 'NNS'),
     ('to', 'TO'), ('warm', 'VV'), ('the', 'DT'), ('oil', 'NN'), (',', ','), ('shut', 'VVD'), ('it', 'PP'),
     ('off', 'RP'),
     ('and', 'CC'), ('drain', 'VV'), ('the', 'DT'), ('engine', 'NN'), ('oil', 'NN'), ('.', 'SENT')]]

  print("Text: {}".format(text[0]))
  print("Output: {}".format(TMTextProcessors.univ_pos_tagger('en').map_universal_postagger(text)[0]))
