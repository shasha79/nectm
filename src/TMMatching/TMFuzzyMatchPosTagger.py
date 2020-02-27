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
import logging
import itertools

sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))
sys.path = [p for p in sys.path if p]

from TMMatching.TMUtilsMatching import TMUtilsMatching

class TMFuzzyMatchPosTagger():

  def __init__(self, src_lang, tgt_lang):
    self.src_lang = src_lang
    self.tgt_lang = tgt_lang

  def process(self, query_dic, tgt_text, src_text, src_pos, tgt_pos, align_features):

    tgt_word = None
    tgt_position = None
    operation = None
    un_match = None
    src_position = None

    src_word_pos = TMUtilsMatching.segment_2_universal(src_text.lower(), src_pos, self.src_lang) #self._segment_2_universal(segment.source_text, segment.source_pos, self.src_lang) # [word, pos] tm_src segment
    query_universal = []
    #Check if segments are equal of with only one diference (posTag)
    query_tok = query_dic['tokenizer'].lower()
    for i in range(0, len(query_dic['universal'].split(' '))):
      query_universal.append([query_tok.split(' ')[i], query_dic['universal'].split(' ')[i]])
    #list(zip(query_dic['tokenizer'].split(' '), query_dic['universal'].split(' ')))
    logging.info("Differences between PosTag: {} ".format(TMUtilsMatching.len_compare(query_universal, src_word_pos)))
    if TMUtilsMatching.len_compare(query_universal, src_word_pos) is True and (query_dic['tokenizer'] != src_text):
      # Obtain un_match word and its features

      if len(query_universal) == len(src_word_pos):
        operation = 'R' # Load the unmatch between query and src --> un_match = un_match_q _ un_match_s
        un_match, un_pos, src_position = TMFuzzyMatchPosTagger._get_src_unmatch(query_universal, src_word_pos) # Replace (query and src)
        if un_match is not None:
          tgt_word, tgt_position = self._align_source_target(un_match.split('_')[1], un_pos.split('_')[1], src_position.split('_')[1], tgt_text, tgt_pos, align_features)
          tgt_word = un_match.split('_')[0]
      elif len(query_universal) > len(src_word_pos): # Insert a new word in target
        operation = 'I'
        un_match, un_pos, src_position = TMFuzzyMatchPosTagger._get_src_unmatch(query_universal, src_word_pos)  # Insert --> return word from query
        tgt_word = un_match
        tgt_position = src_position
      else:  # Delete a new word in target
        operation = 'D'
        un_match, un_pos, src_position = TMFuzzyMatchPosTagger._get_src_unmatch(src_word_pos, query_universal)  # Delete --> return word from src
        if un_match is not None:
          tgt_word, tgt_position = self._align_source_target(un_match, un_pos, src_position, tgt_text, tgt_pos, align_features)
    return tgt_word, tgt_position, operation, un_match, src_position

  # Method to obtain the query and tm_src unmatch word, posTag of unmatch word and position
  @staticmethod
  def _get_src_unmatch(i_str_pos, j_str_pos):

    un_match = None
    un_pos = None
    position = None

    i_str = [w[0].lower() for w in i_str_pos]  # words (i --> longer sentences)
    i_pos = [w[1] for w in i_str_pos] # pos

    j_str = [w[0].lower() for w in j_str_pos]  # words (j --> shorter sentences)
    j_pos = [w[1] for w in j_str_pos]  # pos

    for i in range(0, len(j_str_pos)):  # Shorter sentence
      word = j_str_pos[i][0].lower()
      i_str, i_pos, j_str, j_pos = TMFuzzyMatchPosTagger._check_src_word(word, i_str, i_pos, j_str, j_pos)  # Delete from longer sentence when there are match

    if len(i_str_pos) == len(j_str_pos):
      if len(i_str) == 1 and len(j_str) == 1: #Appear only one replace, more than one return 0
        un_match_q, un_pos_q, position_q = TMFuzzyMatchPosTagger._get_unmatch(i_str[0], i_pos[0], i_str_pos) # un_match info in query
        un_match_s, un_pos_s, position_s = TMFuzzyMatchPosTagger._get_unmatch(j_str[0], j_pos[0], j_str_pos) # un_match info in src
        un_match = un_match_q + ' _ ' + un_match_s
        un_pos = un_pos_q + ' _ ' + un_pos_s
        position = str(position_q) + ' _ ' + str(position_s)
    else:
      if len(i_str) == 1: # Exist and un_match --> return the value respect the longest sequence
        un_match, un_pos, position = TMFuzzyMatchPosTagger._get_unmatch(i_str[0], i_pos[0], i_str_pos)
    return un_match, un_pos, position

  @staticmethod
  def _check_src_word(word, i_str, i_pos, j_str, j_pos):
    if TMFuzzyMatchPosTagger._match_word(word, i_str):  # Check if the word exist in another sentence
      i_index = i_str.index(word)
      i_str.pop(i_index)
      i_pos.pop(i_index)
      j_index = j_str.index(word)
      j_str.pop(j_index)
      j_pos.pop(j_index)
    return i_str, i_pos, j_str, j_pos

  @staticmethod
  def _get_unmatch(word, pos, word_pos_sentence): # Problem: always return the firs ocorrence
    position = word_pos_sentence.index([word,pos])
    return word_pos_sentence[position][0], word_pos_sentence[position][1], position

  @staticmethod
  # Seach word and pos in sentence
  def _match_word_pos(word, pos_word, segment_universal_pos):
    return [x for x in segment_universal_pos if x[0].lower() == word.lower() and x[1] == pos_word]

  # Search word in sentence
  @staticmethod
  def _match_word(word, sentence):
    return [x for x in sentence if x.lower() == word.lower()]

  # Search correspondece between unmatch source and target
  # Input: query and tm_src alignment and the more similar segment
  # Output: ((tgt_word_aling, position), aling_score) -->  (('Decisión', 2), 7.25); operation; query unmatch word;   query unmatch word position
  def _align_source_target(self, un_match, un_pos, position, tgt_text, tgt_pos, align_features):

    tgt_dic = {}  # list of pairs of words

    tgt_word_pos = TMUtilsMatching.segment_2_universal(tgt_text.lower(), tgt_pos, self.tgt_lang)
    for i in range(0, len(tgt_word_pos)):
      value_similarity = 0
      for f in align_features:
        if f == 'word_ter':  # TER between words
            value_similarity = value_similarity + TMUtilsMatching.ter_distance(un_match, tgt_word_pos[i][0])
        if f == 'posTag':  # Boolean PosTag
          value_similarity = value_similarity + TMUtilsMatching.pos_bool(un_pos, tgt_word_pos[i][1])
        if f == 'position':  # Word position
          value_similarity = value_similarity + TMUtilsMatching.position_distance(position, i)
        #if f == 'frequency':  # frequency of pairs of words
        #  value_similarity = value_similarity + self.target_importance(un_word, tgt_word_pos[i][0], segment,best_segments)
      # Dictionary have the target word and the position of the word in the target sentence
      tgt_dic[(tgt_word_pos[i][0], i)] = value_similarity
    tgt_align = sorted(tgt_dic.items(), key=lambda item: item[1], reverse=True)[0]  # Select the highest score
    return tgt_align[0][0], tgt_align[0][1]# un_word, un_position  # Retorn the word with biggest score



  # # Search correspondece between unmatch source and target
  # # [('Final', 'ADJ', 'FINAL', 'ADJ', 0), ('declaration', 'NOUN', 'ACT', 'NOUN', 'R')] --> tuple with unmatch word
  # # Input: query and tm_src alignment and the more similar segment
  # # Output: ((tgt_word_aling, position), aling_score) -->  (('Decisión', 2), 7.25); operation; query unmatch word;   query unmatch word position
  # def _align_source_target(self, ter_align, segment, align_features, best_segments):
  #
  #   tgt_dic = {} # list of pairs of words
  #
  #   # pre-process tm_tgt
  #   #segment.target_text = TMUtilsMatching.pre_process(segment.target_text, self.tgt_lang, 'tokenizer', {})
  #   tgt_word_pos = TMUtilsMatching.segment_2_universal(segment.target_text, segment.target_pos, self.tgt_lang)
  #   #self._segment_2_universal(segment.target_text, segment.target_pos, self.tgt_lang)
  #
  #   for tup in ter_align:
  #     if tup[4] == 'R' or tup[4] == 'D' or tup[4] == 'I':
  #       if tup[4] == 'I': # The unmacth word does not exist in tm source, then the unmatch word is on query
  #         un_word = tup[0]
  #       else:
  #         un_word = tup[2] # Unmatch word in tm_src
  #         un_postagger = tup[3] # Unmatch word posTag
  #       un_position = ter_align.index(tup) # Unmacth word position
  #       operation = tup[4] # Insert, Delete or Replace
  #
  #       if tup[2] == '': # tm_src haven't the word, then there aren't alignment --> Insert operation
  #         tgt_align = (('',''),0)
  #       else:
  #         for i in range(0,len(tgt_word_pos)):
  #           value_similarity = 0
  #           for f in align_features:
  #             if f == 'word_ter': #TER between words
  #               value_similarity = value_similarity + TMFuzzyMatchPosTagger.ter_distance(un_word, tgt_word_pos[i][0])
  #             if f == 'posTag': # Boolean PosTag
  #               value_similarity = value_similarity + TMFuzzyMatchPosTagger.pos_bool(un_postagger, tgt_word_pos[i][1])
  #             if f == 'position': # Word position
  #               value_similarity = value_similarity + TMFuzzyMatchPosTagger.position_distance(un_position, i)
  #             if f == 'frequency': # frequency of pairs of words
  #               value_similarity = value_similarity + self.target_importance(un_word, tgt_word_pos[i][0], segment, best_segments)
  #           #Dictionary have the target word and the position of the word in the target sentence
  #           tgt_dic[(tgt_word_pos[i][0],i)]= value_similarity
  #         tgt_align = sorted(tgt_dic.items(), key=lambda item: item[1], reverse=True)[0] #Select the highest score
  #         if tup[4] == 'R':
  #           un_word = tup[0]
  #       break
  #   return tgt_align, operation, un_word, un_position  #Retorn the word with biggest score

  # Check the occurence score of target words that belong to target part of the segment, with the source segment with pos tag patter like input_src
  def target_importance(self, un_word, un_match_src, l_best_segments):
    count = 0
    for segment in l_best_segments:
      if (TMFuzzyMatchPosTagger._match_word(un_word, segment[0].source_text.split(''))) and (TMFuzzyMatchPosTagger._match_word(un_match_src, segment[0].target_text).split('')):  #word with pos in tm source segments:
        count = count + 1
    return count

  #Detect Replace, Insert and shift between query and tm_src --> I want to detect what part of tm_source will be delete, insert or replace
  #query and src have universal pos tag
  #[('Final', 'ADJ', 'FINAL', 'ADJ', 0), ('declaration', 'NOUN', 'ACT', 'NOUN', 'R')] --> tuple with unmatch word
  # def _src2src_match(self, qstring, tm_src):
  #   ter_by_word = []
  #   # Replace operation
  #   print(qstring)
  #   print(tm_src)
  #   if len(qstring) == len(tm_src): #There are a replace or shift
  #     for input, tm in zip(qstring, tm_src):
  #       if input[0].lower() == tm[0].lower(): ter_by_word.append((input[0], input[1], tm[0], tm[1], 0))
  #       else: ter_by_word.append((input[0], input[1], tm[0], tm[1], 'R')) # Falta el ***shift***
  #  #Delete or Insert operation
  #   else:
  #     j = 0
  #     for i in range(0, len(qstring)):
  #       ter_by_word = self._check_src_word(qstring[i][0], qstring[i][1], tm_src, ter_by_word) # Check each query word
  #       if j < len(tm_src): # still there are words into source and target to analyse
  #         j = j + 1
  #       else: # source input is longer than tm source --> Insert word in target
  #         for w in range(j+1, len(qstring)):
  #           ter_by_word.append((qstring[w][0], qstring[w][1], '', '', 'I')) # add the rest of query word into tm source
  #         break
  #     if j < len(tm_src): #tm source is longer than input source
  #       for i in range(0, len(tm_src)): #Check what word is necessary to delete from tm source
  #         tm_src_w = [w[2] for w in ter_by_word]
  #         if not TMFuzzyMatchPosTagger._match_word(tm_src[i][0], tm_src_w):
  #           ter_by_word.append(('', '', tm_src[i][0], tm_src[i][1], 'D')) # put into the align structure what word into the tm source will be delete
  #   return ter_by_word

  # Detect Replace, Insert and shift between query and tm_src --> I want to detect what part of tm_source will be delete, insert or replace
  # query and src have universal pos tag
  # [('Final', 'ADJ', 'FINAL', 'ADJ', 0), ('declaration', 'NOUN', 'ACT', 'NOUN', 'R')] --> tuple with unmatch word
  # def _src2src_match(self, qstring, tm_src):
  #   ter_by_word = []
  #   # Replace operation
  #   q_words = [w[0] for w in qstring] # words in query
  #   q_pos = [w[1] for w in qstring] # pos in query
  #
  #   s_words = [w[0] for w in tm_src]  # words in src
  #   s_pos = [w[1] for w in tm_src]  # pos in src
  #
  #   if len(q_pos) == len(s_pos):  # There are a replace or shift
  #     for i in range(0,len(qstring)):
  #       if q_words[i].lower() != s_words[i].lower():
  #           ter_by_word.append((q_words[i], q_pos[i], i, s_words[i], s_pos[i], 'R'))  # Falta el ***shift***
  #     # Delete or Insert operation
  #   else:
  #       j = 0
  #       for i in range(0, len(qstring)):
  #         ter_by_word = self._check_src_word(qstring[i][0], qstring[i][1], tm_src, ter_by_word)  # Check each query word
  #         if j < len(tm_src):  # still there are words into source and target to analyse
  #           j = j + 1
  #         else:  # source input is longer than tm source --> Insert word in target
  #           for w in range(j + 1, len(qstring)):
  #             ter_by_word.append((qstring[w][0], qstring[w][1], '', '', 'I'))  # add the rest of query word into tm source
  #           break
  #       if j < len(tm_src):  # tm source is longer than input source
  #         for i in range(0, len(tm_src)):  # Check what word is necessary to delete from tm source
  #           tm_src_w = [w[2] for w in ter_by_word]
  #           if not TMFuzzyMatchPosTagger._match_word(tm_src[i][0], tm_src_w):
  #             ter_by_word.append(('', '', tm_src[i][0], tm_src[i][1],
  #                                 'D'))  # put into the align structure what word into the tm source will be delete
  #     return ter_by_word