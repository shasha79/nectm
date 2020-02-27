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
sys.path.append("..")
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))
sys.path = [p for p in sys.path if p]

from TMMatching.TMRegxMatch import TMRegexMatch
from TMMatching.TMFuzzyMatchPosTagger import TMFuzzyMatchPosTagger
from TMPreprocessor.Xml.XmlUtils import XmlUtils
from TMDbApi.TMUtils import TMTimer;
from TMMatching.TMUtilsMatching import TMUtilsMatching

import logging
import editdistance
import operator
from translate import Translator


#logging.basicConfig(level=logging.INFO)
#logger = logging.getLogger(__name__)

#from TM_TestSet.diff_match_patch import diff_match_patch
#import regex #--> install pip3 install regex
#from itertools import combinations

# Matching algorithm principal class
class TMMatching:


  def __init__(self, query, src_lang, tgt_lang):
    self.query = query # Here query is the query string
    self.src_lang = src_lang.lower()
    self.tgt_lang = tgt_lang.lower()
    self.timer = TMTimer("TMMatching", logging.INFO)
    self.tm_translator = Translator(to_lang=self.tgt_lang)

  #Query elasticTM and analizes results to obtain target match
  # Matching process
  def execute(self, threshold, l_best_segments, match_process, align_features, concordance):#, output
    self.timer.start("preprocess")
    query_dic = self._preprocess(self.query, self.src_lang) # Tokenize, posTag and universal query string
    self.timer.stop("preprocess")

    if concordance:
      return self._match_rank_concordance(l_best_segments)
    else:
      rank_segments = self._match_rank(l_best_segments, threshold)
      trans_segments = []
      # Check if the retrieve segments are 100% match or apply transformations
      for segment in rank_segments:
        #segment = segment[0]
        if segment.source_text == self.query: # 100% match --> Return match considering domain
          ter = 100
          if self.query.isupper():
            segment.source_text = segment.source_text.upper()
          if self.query.islower():
            segment.source_text = segment.source_text.lower()
          #trans_segments.append((segment,ter))
        else:
          #Pre-process source and target
          tgt_text = TMUtilsMatching.pre_process(segment.target_text, self.tgt_lang, 'tokenizer', {})  # Pre-process tgt
          src_text = TMUtilsMatching.pre_process(segment.source_text, self.src_lang, 'tokenizer', {})  # Tokenize tm_src
          if 'regex' in match_process:
            if (query_dic['tokenizer'] == query_dic['query_re']):
              ter = TMUtilsMatching._ter_score(query_dic['tokenizer'], src_text)  # Regex did't applied on query
            else:
              self.timer.start("_regx_match")
              tgt_text, src_text, ter = self._regx_match(query_dic, src_text, tgt_text)#, segment.source_pos, segment.target_pos
              self.timer.stop("_regx_match")
              logging.info("Applied Regex Segment: {} {} {}".format(tgt_text, src_text, str(ter)))
          else:
            ter = TMUtilsMatching._ter_score(query_dic['tokenizer'], src_text)  # Regex did't enter as a parameter
          if ter < threshold:
            logging.info("TER less threshold: {} ".format(str(ter)))
            continue
          if 'posTag' in match_process and ter != 100:  #Check segments with only one difference
            if segment.source_pos is not None and segment.target_pos is not None: #This part need the pos tagger annotation
              self.timer.start("fuzzy_match")
              #target_word (to D, R, or I), target_position, operation(R I or D),src_un_match(some time have source or query information)
              tgt_word, tgt_position, operation, src_un_match, src_position = self._combine_feature_match(query_dic, tgt_text, src_text, segment.source_pos, segment.target_pos, align_features)

              logging.info("Un_match: {} {} ".format(tgt_word, operation))

              if src_un_match is not None:
                src_text = self._create_target_expression(src_text, src_position, operation, src_un_match,'source')#src_un_match,
                # src_text = src_text.split(' ')
                # if operation == 'R':
                #   src_text[int(src_position.split(' _ ')[1])] = tgt_word
                # if operation == 'I':
                #   new_src_text = src_text[:int(src_position)] + [src_un_match] + src_text[int(src_position):]
                #   #new_src_text.append(src_un_match)
                #   #new_src_text = new_src_text + src_text[int(src_position):]
                #   src_text = new_src_text
                # if operation == 'D':
                #   src_text.pop(int(src_position))
                # src_text = ' '.join(src_text)
              if tgt_word is not None:
                tgt_text = self._create_target_expression(tgt_text, tgt_position, operation, src_un_match, 'target')#tgt_word,

                self.timer.stop("fuzzy_match")
          segment.source_text = TMUtilsMatching.pre_process(src_text.split(' '), self.src_lang, 'untokenizer', {})
          segment.target_text = TMUtilsMatching.pre_process(tgt_text.split(' '), self.tgt_lang, 'untokenizer', {})
          logging.info("Target segment: {}".format(segment.target_text))
          if self.query.isupper():
            segment.source_text = segment.source_text.upper()
            segment.target_text = segment.target_text.upper()
          if self.query.islower():
            segment.source_text = segment.source_text.lower()
            segment.target_text = segment.target_text.lower()
        trans_segments.append((segment, ter))
      return trans_segments

  # Input: align target word, position of target word, unmatch input src word, operation (R, I or D), position of word in src input, best segment
  #src_text, src_un_match, src_position, operation, src_un_match, 'source'
  def _create_target_expression(self, text, position, operation, query_info, part):#tgt_text, tgt_word, tgt_position, operation, src_un_match, part
    query_word = query_info.split(' _ ')[0]
    text = text.split(' ')
    if operation == 'R':
      if part == 'target':
        text[position] = self.tm_translator.translate(query_word)  # tgt_word
      else:
        text[int(position.split(' _ ')[1])] = query_word
    if operation == 'D':
      text.pop(position)
    if operation == 'I':
      if len(text) > position:
        if part == 'target':
          for x in reversed([query_word]): text.insert(position, self.tm_translator.translate(x))
          #[text[i:] + [query_word] + text[:i] for i in range(len(text), -1, -1)]
        else:
          for x in reversed([query_word]): text.insert(position, x)
          #text.insert(position, self.tm_translator.translate(query_word))  # tgt_word
      else:
        if part == 'target':
          text.append(self.tm_translator.translate(query_word))  # tgt_word
        else: text.append(self.tm_translator.translate(query_word))
    return ' '.join(text)

    # query_word = src_un_match.split(' _ ')[0]
    # tgt_text = tgt_text.split(' ')
    # if operation == 'R':
    #   tgt_text[tgt_position] = self.tm_translator.translate(query_word)#tgt_word
    # if operation == 'D':
    #   tgt_text.pop(tgt_position)
    # if operation == 'I':
    #   if len(tgt_text) > tgt_position:
    #     tgt_text.insert(tgt_position, self.tm_translator.translate(query_word)) #tgt_word
    #   else:
    #     tgt_text.append(self.tm_translator.translate(query_word)) #tgt_word
    # return ' '.join(tgt_text)

  # Input --> Query, original tgt_text, src_text
  # Output --> tgt_text, src_text, ter
  def _regx_match(self, query_dic, src_text, tgt_text):#, src_pos, tgt_pos
    logging.info("Applied Regex")
    fuzzy_alg = TMRegexMatch(self.src_lang, self.tgt_lang)  # Class to improve fuzzy match #, self.best_segments
    return fuzzy_alg.process(query_dic, src_text, tgt_text) #, src_pos, tgt_pos

  def _combine_feature_match(self, query_dic, tgt_text, src_text, src_pos, tgt_pos, align_features):

    logging.info("Apply posTag matching")
    fuzzy_alg = TMFuzzyMatchPosTagger(self.src_lang, self.tgt_lang)  # Class to improve fuzzy match
    tgt_un_match, tgt_position, operation, src_un_match, src_position = fuzzy_alg.process(query_dic, tgt_text, src_text, src_pos, tgt_pos, align_features)
    return tgt_un_match, tgt_position, operation, src_un_match, src_position

  def _preprocess(self, text, lang):

    dic_query = {}
    s_tags = XmlUtils.extract_tags(text)
    if not s_tags:
      dic_query['query'] = text
    else:
      dic_query['query'] = XmlUtils.strip_tags(text)  # split tag to do the match

    dic_query['tokenizer'] = TMUtilsMatching.pre_process(dic_query['query'], self.src_lang, 'tokenizer', {})
    dic_query['pos'] = TMUtilsMatching.pre_process(dic_query['tokenizer'], lang, 'pos_tagger', {})
    dic_query['universal'] = TMUtilsMatching.segment_2_universal(dic_query['tokenizer'].lower(), dic_query['pos'],lang)  # universal_text[0]
    dic_query['universal'] = dic_query['pos']


    regex_class = TMRegexMatch(self.src_lang, self.tgt_lang)  # Class to improve fuzzy match
    dic_query['query_re'] = TMUtilsMatching.pre_process(dic_query['tokenizer'], self.src_lang, 'reg_exp', regex_class.re_pp)
    return dic_query

  # Different way to select segments; 1) if TM output --> ter > threshold 2) if moses output if ter > threshold or only one difference between posTag
  # Input : list of segments; query
  # Output: list of all the segmets [(segment,ter); ...(segment,ter)]
  def _match_rank(self, best_segments, threshold):#, output
      segments = []
      self.timer.start("ter")
      l_ter_score = [TMUtilsMatching._edit_distance(self.query, segment[0].source_text) for segment in best_segments]
      self.timer.stop("ter")
      l_best_sort = sorted(zip(best_segments, l_ter_score), key=operator.itemgetter(1), reverse=True)
      for segment, ter in l_best_sort:  # TM output --> only show segments with ter > threshold
        if ter >= threshold-10:
          segments.append((segment[0]))
        else:
          break
      return segments

  def _match_rank_concordance(self, best_segments):  # , output
    self.timer.start("ter")
    l_ter_score = [TMUtilsMatching._ter_score(self.query, segment[0].source_text) for segment in best_segments]
    self.timer.stop("ter")
    l_best_sort = sorted(zip(best_segments, l_ter_score), key=operator.itemgetter(1), reverse=True)
    return [(segment[0][0], segment[1]) for segment in l_best_sort]