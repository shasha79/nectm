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

import editdistance

from TMAutomaticTranslation.TMAutomaticTranslation import TMAutomaticTranslation
from TMMatching.TMTextProcessors import TMTextProcessors
from TMPosTagger.TMStopWords import TMStopWords
from TMPreprocessor.Xml.TMXmlTagPreprocessor import TMXmlTagPreprocessor
from TMPreprocessor.Xml.XmlUtils import XmlUtils

class TMUtilsMatching:

  tags = dict()
  stop_words = dict()

  @staticmethod
  def check_stopwords(langs):  # langs --> ('en', 'es')
    langs = langs.upper()
    if not langs in TMUtilsMatching.stop_words:
      TMUtilsMatching.stop_words[langs] = TMStopWords(langs)
    return TMUtilsMatching.stop_words[langs].stop_words

  @staticmethod
  def process_tags(langs):  # langs --> ('en', 'es')
    if not langs in TMUtilsMatching.tags:
      TMUtilsMatching.tags[langs] = TMXmlTagPreprocessor(langs)
    return TMUtilsMatching.tags[langs]#re.sub("\s\s+", " ", simplified_text)  # Yo tengo un <b>gato</b>. Yo tengo un T gato T.

  @staticmethod
  def len_compare(str_x, str_y):
    if ((len(str_x) - len(str_y) == 0) or abs(len(str_x) - len(str_y)) == 1):
      return True
    else: return False

  @staticmethod
  def strip_tags(str_in):
    return re.sub("\s\s+", " ", XmlUtils.strip_tags(str_in))

  @staticmethod
  def reduce_tags(str_in):
    return XmlUtils.reduce_tags(str_in)

  @staticmethod
  def transfer_tags(query_str, tm_str, langs):
    return TMUtilsMatching.process_tags(langs).transfer_tags(query_str, tm_str)

  @staticmethod #Check if list of list is empty
  def empty_list(input_list):
    """Recursively iterate through values in nested lists."""
    for item in input_list:
      if not isinstance(item, list) or not TMUtilsMatching.empty_list(item):
        return False
    return True

  # @staticmethod
  # def restore_tags(text, text_re):
  #   for w in range(0, len(text_re)):
  #     if text_re[w] == '<TR>' or text_re[w] == '</TR>':
  #       text_re[w] = text[w]
  #   return ' '.join(text_re)

  @staticmethod
  def regex_pattern_value(text, lang, dic_re):
    return dic_re[lang].get_pattern_value(text)

  @staticmethod
  def pre_process(text, lang, preprocess, dic_re):
    if preprocess == 'tokenizer':
      text = TMTextProcessors.tokenizer(lang).tokenizer.process(text)
    if preprocess == 'reg_exp':
      text = dic_re[lang].process(text)
    if preprocess == 'untokenizer':
      text = TMTextProcessors.un_tokenizer(lang).un_tokenizer(text)
    if preprocess == 'pos_tagger':
      posTag_text = TMTextProcessors.pos_tagger(lang).tag_segments([text])
      text = " ".join([word_pos[1] for word_pos in posTag_text[0] if len(word_pos) > 1])
    if preprocess == 'get_lang_universalPOS':
      text = TMTextProcessors.pos_tagger(lang).get_lang_using_universal()
    if preprocess == 'universal_pos_tagger': # Applied universal postagger
      if TMTextProcessors.univ_pos_tagger(lang):
        process_text = TMTextProcessors.univ_pos_tagger(lang).map_universal_postagger(text)
        text = process_text[0]
    if preprocess == 'tags': # Uniform tags . --> # lang = ('en','es')
      text = TMUtilsMatching.process_tags(lang).process(text) # Yo tengo un <b>gato</b>. --> Yo tengo un <T1>gato</T1>
    if preprocess == 'split_sentences':
      text = TMTextProcessors.tokenizer(lang).tokenizer.tokenize_sent(text)
    return text

    # Problems: Tags simplification include blank space, that probably is a problem for the subsequences steps.


  '''
    Original to elastic Tag: Yo tengo un <b>gato</b>. --> Yo tengo un <T1>gato</T1>.
    Elastic Tag to T: Yo tengo un <b>gato</b>. Yo tengo un  T gato T . --> multiple blank space
    Yo tengo un <b>gato</b>. Yo tengo un T gato T . # Delete multiple blank space, but "." is tokenizer

  '''
  # @staticmethod
  # def simplified_tags(in_str):  #langs --> ('en', 'es')
  #   simplified_text = re.sub(TMTextProcessors.TAG_PATTERN, ' ' + TMTextProcessors.TAG_PREFIX + ' ', in_str)
  #   return re.sub("\s\s+", " ", simplified_text)  # Yo tengo un <b>gato</b>. Yo tengo un T gato T.

  # @staticmethod
  # def unified_tags(in_str, langs):  # langs --> ('en', 'es')
  #   if not langs in TMTextProcessors.tags:
  #     TMTextProcessors.tags[langs] = TMXmlTagPreprocessor(langs)
  #     #simplified_text = re.sub(TMTextProcessors.TAG_PATTERN, ' ' + TMTextProcessors.TAG_PREFIX + ' ', in_str)
  #   return re.sub("\s\s+", " ", simplified_text)  # Yo tengo un <b>gato</b>. Yo tengo un T gato T.

  @staticmethod
  def segment_2_universal(text, pos, lang):
    word_array = text.split(' ')  # word
    pos_array = pos.split(' ')  # pos

    array_text = text

    if len(word_array) == len(pos_array):
      array_text = [[[word_array[p], pos_array[p]] for p in range(0, len(word_array))]]

    if lang not in TMUtilsMatching.pre_process(' ', lang, 'get_lang_universalPOS', {}):#['de', 'pt', 'ru', 'zh', 'ar', 'he', 'cs', 'no', 'sv', 'hu', 'lv', 'ro', 'el', 'da', 'ga', 'nl', 'et', 'fi', 'sl', 'pl', 'it', 'bg']:
      universal_text = TMUtilsMatching.pre_process(array_text, lang, 'universal_pos_tagger', {})

      if universal_text == array_text: # Not exit a map file
        universal_text = universal_text[0]#[[[word_array[p], pos_array[p]] for p in range(0, len(word_array)) if len(word_array[p])==2]]

      return universal_text
    else: # Return a list with [word, pos]
      return array_text[0] #[[word_array[p], pos_array[p]] for p in range(0, len(word_array)) if len(word_array[p])==2]

  #@staticmethod
  # Estimate TER between sources segmets.
  #def _ter_score(src_x, src_y):
  #  ter = pytercpp.ter(src_x.split(), src_y.split())
  #  if ter > 1: ter = 1
  #  return (100 - (ter * 100))

  @staticmethod
  def un_match_distance(src, tgt): # 0 --> bad; 1 --> better
    return 1 - editdistance.eval(src.strip(' '), tgt.strip(' '))/max(len(src.strip(' ')), len(tgt.strip(' ')))#0.25 - editdistance.eval(src.strip(' '), tgt.strip(' '))#pytercpp.ter(src.lower().split(), tgt.lower().split())

  @staticmethod
  def pos_bool(src, tgt):

    if src.strip() != tgt.strip():
      return 0
    else:
      return 0.75

  @staticmethod # 0 --> bad; 1 --> better (D=0 --> 1; D=1 --> 0,75; D=2 --> 0,5; D=3 --> 0,75; D>=4 --> 0)
  def position_distance(src, tgt):
    positionD = 1 - (0.25 * abs(int(src) - int(tgt)))
    if positionD < 0:
      positionD = 0
    return positionD #1 - (0.25 * abs(int(src) - int(tgt)))

  @staticmethod
  # Estimate edit distance between sources segmets.
  def _edit_distance(src_x, src_y):
    return editdistance.eval(src_x, src_y)#(100 - ((editdistance.eval(src_x, src_y)/len(src_x)) * 100))

  # @staticmethod
  # def simplified_tags(src, tgt):
  #   return 1 - (0.25 * abs(int(src) - int(tgt)))