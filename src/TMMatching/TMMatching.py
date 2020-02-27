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

mt_engine_path = os.path.join(os.path.abspath(os.path.join(__file__, "../../..")), 'conf/sh_engines/')

from TMMatching.TMRegxMatch import TMRegexMatch, TMTags
from TMMatching.TMPosMatch import TMPosMatch
from TMDbApi.TMUtils import TMTimer
from TMMatching.TMUtilsMatching import TMUtilsMatching
from kombu.utils.encoding import safe_str
from TMPreprocessor.Xml.XmlUtils import XmlUtils
from TMMatching.TMSplitMatch import TMSplitMatch
from Config.Config import G_CONFIG
from TMPreprocessor.TMSplit import TMSplit
from TMAutomaticTranslation.TMAutomaticTranslation import TMAutomaticTranslation

import logging
import operator
import re
import math


# Matching algorithm principal class
class TMMatching:

  split = dict()

  def __init__(self, query, query_dic ,src_lang, tgt_lang, out, min_match, domain, aut_trans, pipe= None):
    self.query = query # Here query is the query string

    self.query_dic = query_dic

    self.src_lang = src_lang.lower()
    self.tgt_lang = tgt_lang.lower()
    self.out = out
    self.min_match = min_match
    self.timer = TMTimer("TMMatching", logging.INFO)
    self.machine_translation= aut_trans

    # Validate pipe
    self.match, self.pipe = self._validate_pipe(pipe)

    self.domain = domain
    self.tm_translator = TMAutomaticTranslation.get_engine(src_lang, tgt_lang, domain)
    self.trans_segments = []


  def _validate_pipe(self, pipe):
    match_process = {
      'regex': None,
      'posTag': None,
      'tags': TMTags()
    }

    try:
      match_process['regex'] = TMRegexMatch(self.src_lang, self.tgt_lang)
      logging.info("Loading regex for matching")
    except ValueError:
      if 'regex' in pipe:
        pipe.pop(pipe.index('regex'))
        logging.info("Unsupported regex for matching")

    query_out_tags = XmlUtils.replace_tags(self.query)

    try:
      if 'tokenizer' not in self.query_dic:
        self.query_dic['tokenizer'] = TMUtilsMatching.pre_process(query_out_tags, self.src_lang, 'tokenizer', {})
      logging.info("Loading Tokenizer for {}".format(self.src_lang))

      try:
        if 'pos' not in self.query_dic:
          self.query_dic['pos'] = TMUtilsMatching.pre_process(self.query_dic['tokenizer'], self.src_lang, 'pos_tagger', {})
        match_process['posTag'] = TMPosMatch(self.src_lang, self.tgt_lang)
        logging.info("Loading regex for matching")
      except Exception as e:
        if 'posTag' in pipe:
          pipe.pop(pipe.index('posTag'))
          logging.info("Unsupported posTag for matching")
    except Exception as e:
      if 'posTag' in pipe:
        pipe.pop(pipe.index('posTag'))
        logging.info("Unsupported Tokenizer for {}".format(self.src_lang))

    return match_process, pipe

  def execute(self, l_best_segments, align_features, concordance):

    # show the status of the process
    status = '' #--> indicated if match or not match
    equal = False # --> indicated if applied equal sequences or not
    self.timer.start("preprocess")
    self.query_dic = self._preprocess()  # uniform tags on query
    self.timer.stop("preprocess")

    # 1. sort segment list
    rank_segments = self._match_rank(l_best_segments)
    logging.info("SEGMENTS FROM ELASTICSEARCH")
    for seg in rank_segments:
      logging.info(u"{}".format(safe_str(seg[0][0].source_text)))

    if concordance:
      return [(segment[0][0], segment[1]) for segment in rank_segments]

    else:
      # 2. Analised the first segment
      segment = rank_segments[0][0][0]  # Check the best (first) segment
      ini_editD = rank_segments[0][1]
      src_re = rank_segments[0][0][2] # src after applied regex
      src_re_reduce = rank_segments[0][0][3] # src after simplified regex

      if self.query_dic['query'] == segment.source_text:  # The strings are identical

        logging.info("Identical Segments (Query -- Source): {} {}".format(safe_str(self.query_dic['query'] + ' -- '),safe_str(segment.source_text))) # source and query ar identical, then is not necessary untokenizer or check upper or lower
        equal = True
        editD = ini_editD
        print('---------- ' + str(editD))
        self.trans_segments, status = self._deals_output(segment, editD, self.trans_segments, False, status) # decide next step

      else: # The best is not 100% match --> applied transformations
        logging.info("Different Segments (Query -- Source -- Target): {} {} {}".format(safe_str(self.query_dic['query']+ ' -- '), safe_str(segment.source_text+ ' -- '), safe_str(segment.target_text)))
        segment, editD, status, equal, status_tokenizer = self.execute_segment(segment, src_re, src_re_reduce, ini_editD, align_features, equal)
        if status == 'find': # or status == 'translate'
          segment.source_text, segment.target_text, status_tokenizer = self.style_string(segment.source_text, segment.target_text, status_tokenizer)  # Adjust source and tgt text
          self.trans_segments, status = self._deals_output(segment, editD, self.trans_segments, status_tokenizer, status)
        if status == 'break': # There are not match on ElasticTM
          return self.trans_segments

      # 3. TM output --> Analized the list with the others segments
      if status == 'continue':
        if len(self.trans_segments) == 1: # The first element was 100% match
          rank_segments = rank_segments[1:]
        # Check if the retrieve segments are 100% match or apply transformations
        for seg_info in rank_segments:
          segment = seg_info[0][0]
          ini_editD = seg_info[1]
          src_re = seg_info[0][2]  # src after applied regex
          src_re_reduce = seg_info[0][3]  # src after simplified regex
          logging.info("(TM output) Need more segment (Query -- Source -- Target): {} {} {}".format(safe_str(self.query_dic['query']+ ' -- '), safe_str(segment.source_text+ ' -- '), safe_str(segment.target_text)))
          segment, editD, status, equal, status_tokenizer = self.execute_segment(segment, src_re, src_re_reduce, ini_editD, align_features, equal)
          if status == 'find': # or status == 'translate'
            segment.source_text, segment.target_text, status_tokenizer = self.style_string(segment.source_text, segment.target_text, status_tokenizer)  # Adjust source and tgt text
            self.trans_segments, status = self._deals_output(segment, editD, self.trans_segments, status_tokenizer, status) # decide next step
          if status == 'break': #Meaning that the last segment has editD less that a threshold
            break
          if status == 'continue':
            continue
      return self.trans_segments

  #Process only one segment
  def execute_segment(self, segment, src_re, src_re_reduce, ini_editD, align_features, equal):
    logging.info("Applied match PIPE")
    tgt_text = segment.target_text
    src_text = segment.source_text
    status = ''

    editD = ini_editD
    status_tokenizer = False
    if equal:
      if self.query == src_text:
        return segment, editD, 'find', equal, status_tokenizer
      else:
        equal = False
    if not equal:
      for op in self.pipe: #Indicate by parameters
        if op == 'regex':
          if self.query_dic['query'] != self.query_dic['query_re']: # If query has regex   #and not TMMatching.check_upper_equal(self.query_dic['query'], self.query_dic['query_re'])
              logging.info("Applied Regex")
              self.timer.start("_regx_match")
              # ************************** Compare query_re with src_re --> simplified
              match = ini_editD
              if src_re != src_text:
                if src_re_reduce.lower() == self.query_dic['query_re_reduce'].lower():  # With simplified regular expression and in lowercase
                  match = 100  # Perfect match
                tgt_text, src_text = self._regex_transform(segment.source_text, segment.target_text)
                ini_editD = self._tm_edit_distance(self.query_dic['query'],src_text, self.query_dic['query_re_reduce'], src_re_reduce) #match
                logging.info("After applied Regex Segment: {} {} {}".format(safe_str(src_text+ ' -- '), safe_str(tgt_text+ ' -- '), safe_str(ini_editD)))
              if match == 100:
                status = 'find'
              self.timer.stop("_regx_match")
        if op == 'tags':
          logging.info("Delete Tags")
          self.timer.start("_tags_match")
          src_text, tgt_text, status, reduce, ini_editD = self._match_tags(src_text, src_re_reduce, tgt_text, status, ini_editD)
          logging.info("After applied Tags: {} {} {}".format(safe_str(src_text+ ' -- '), safe_str(tgt_text+ ' -- '), safe_str(ini_editD)))
          self.timer.stop("_tags_match")

        if op == 'posTag':
          self.timer.start("fuzzy_match")
          upper = False
          if segment.source_pos is not None and segment.target_pos is not None:  # This part need the pos tagger annotation
            squery, tok_query, pos_query = self.check_query_parameters()
            logging.info("Apply posTag matching")
            self.timer.start("fuzzy_preprocess")
            if status_tokenizer == False:  # Tokenize source and target
              tgt_text = TMUtilsMatching.pre_process(tgt_text, self.tgt_lang, 'tokenizer', {})  # Pre-process tgt
              src_text = TMUtilsMatching.pre_process(src_text, self.src_lang, 'tokenizer', {})  # Tokenize tm_src
              self.query_dic['query_re_reduce_tok'] = TMUtilsMatching.pre_process(self.query_dic['query_re_reduce'], self.src_lang, 'tokenizer', {})  # Tokenize the simplified query
              status_tokenizer = True

            if 'universal' not in self.query_dic:
              self.query_dic['universal'] = TMUtilsMatching.segment_2_universal(tok_query.lower(), pos_query, self.src_lang)
            #print(self.query_dic['universal'])
            src_word_pos = TMUtilsMatching.segment_2_universal(src_text.lower(), segment.source_pos, self.src_lang)  # [word, pos] tm_src segment
            tgt_word_pos = TMUtilsMatching.segment_2_universal(tgt_text.lower(), segment.target_pos, self.tgt_lang)  # [word, pos] tm_tgt segment

            self.timer.stop("fuzzy_preprocess")
            if isinstance(self.query_dic['universal'], list) and isinstance(src_word_pos, list) and isinstance(tgt_word_pos, list):

              logging.info("Check unmatch word --> PosTag")
              if TMUtilsMatching.len_compare(pos_query.split(' '), segment.source_pos.split(' ')) is True and (tok_query != src_text):
                logging.info("Query and source have same length or only one difference")

                self.timer.start("search unmatch")
                tgt_un_match, tgt_position, operation, src_un_match, src_position, pos_tag = self._combine_feature_match(tok_query, src_word_pos, tgt_word_pos, align_features)
                self.timer.stop("search unmatch")
                logging.info("Unmatch word and operation: {} {}".format(safe_str(src_un_match), safe_str(operation), safe_str(ini_editD)))
                self.timer.start("create target unmatch")

                if src_un_match is not None:
                  # Create new src
                  src_text, upper = self._create_target_expression(src_text, src_position, operation, src_un_match, 'source', upper, pos_tag)
                  # Improve edit distance
                  src_re = TMUtilsMatching.pre_process(src_text, self.src_lang, 'reg_exp', self.match['regex'].re_pp)
                  src_re_reduce = TMRegexMatch.simplified_name(src_re)
                  penalize_match = self._improve_match(src_un_match, operation)
                  ini_editD = self._tm_edit_distance(tok_query.lower(), src_text.lower(), self.query_dic['query_re_reduce_tok'].lower(), src_re_reduce.lower()) - penalize_match  # match
                  # Create new tgt
                if tgt_un_match is not None:
                  tgt_text, upper = self._create_target_expression(tgt_text, tgt_position, operation, tgt_un_match, 'target', upper, pos_tag)  # tgt_word,
                self.timer.stop("create target unmatch")
                logging.info("After applied posTag: {} {}".format(safe_str(src_text+ ' -- '), safe_str(tgt_text+ ' -- '), safe_str(ini_editD)))
          self.timer.stop("fuzzy_match")

        # Check if find or break some transformation
        if ini_editD > editD:
          editD = ini_editD
        if status == 'find' or status == 'break':
          segment.source_text = src_text
          segment.target_text = tgt_text
          return segment, editD, status, equal, status_tokenizer
      if editD >= self.min_match:
        segment.source_text = src_text
        segment.target_text = tgt_text
        status = 'find'
      else:
        #Call split rules
        if 'split' in self.pipe and not self.trans_segments: # Applied split if exist posTagger for source language  and self.query_dic['pos']

          src_text = None
          tgt_text = None
          editSplit = 0

          # Split by sentences.
          list_sentences = TMUtilsMatching.pre_process(self.query_dic['tokenizer'], self.src_lang, 'split_sentences', {})
          logging.info("split by Sentences : {} ".format(list_sentences))

          # Check sentence first
          if len(list_sentences) > 1:

            split_match = TMSplitMatch([TMUtilsMatching.pre_process(q.split(' '), self.src_lang, 'untokenizer', {}) for q in list_sentences], [], self.src_lang, self.tgt_lang, 'sentence', self.machine_translation, self.domain)
            src_text, tgt_text, editSplit = split_match._match()
            #print('*****Only sentences *****')
            #print(src_text)
            #print(tgt_text)
            #print(editSplit)

          if editSplit >= self.min_match:  # Check if split method return segments from ActivaTM
            segment.source_text, segment.target_text, editD = src_text, tgt_text, editSplit

          else: # Split in small phrase
            # Check if exist split for an especific pairs of languages
            lang_class = G_CONFIG.get_split_rules(self.src_lang, self.tgt_lang)

            if lang_class:
              logging.info("Split Query by Phrase")
              all_split, all_marks = self._splitByPhrase(lang_class, list_sentences)

              # Check if any split rule was applied
              if len(all_split) > 1:
                  # print(list_query_split)
                split_match = TMSplitMatch(all_split, all_marks, self.src_lang, self.tgt_lang, 'phrase', self.machine_translation, self.domain)
                src_text, tgt_text, editSplit = split_match._match()

                if editSplit >= self.min_match: #Check if split method return segments from ActivaTM
                  segment.source_text, segment.target_text, editD = src_text, tgt_text, editSplit

        if editD >= self.min_match:
          status = 'find'
          status_tokenizer = True
        else:
          if not self.trans_segments:  #If doesn't found any match, prepare segment to automatic translation. If there aren't automatic translation, then return []
            #logging.info("Prepare Automatic Translation : ")
            self.trans_segments.append((segment, editD))
          status = 'break' # If exist segment on the list, break the for and there aren't translation
    return segment, editD, status, equal, status_tokenizer

  # Send and input sentence into subsegments usng rules based on posTag annotation
  def _splitByPhrase(self, lang_class, list_sentences):

    splitTask = TMMatching.split_source(lang_class, self.src_lang)  # class with the rule for specific language and language

    list_word_pos = []
    if 'pos' in self.query_dic:
      i = 0
      for each_sent in list_sentences:
        # Create word_pos
        len_e = len(each_sent.split())
        list_word_pos.append([(w, p) for w, p in zip(each_sent.split(), self.query_dic['pos'].split()[i:i + len_e])])
        i = i + len_e

    # TODO: Call another method to applied other rules that don't need posTag anotation --> ELSE STATEMENT

      '''
   if list_sentences:
     i = 0
     for each_sent in list_sentences:
       # Create word_pos
       len_e = len(each_sent.split())
       list_word_pos.append([(w, p) for w, p in zip(each_sent.split(), self.query_dic['pos'].split()[i:i + len_e])])
       i = i + len_e
   else:
     if 'pos' in self.query_dic: list_word_pos.append([(w, p) for w, p in zip(self.query_dic['tokenizer'].split(), self.query_dic['pos'].split())])
   '''

    all_split = []
    all_marks = []
    for sentence in list_word_pos:
      segmentsStructure = splitTask.clause_chunk(sentence)  # preProcess.split_process(p_segments)

      logging.info("split INFO : {} ".format(segmentsStructure))
      # print(segmentsStructure)

      list_query_split, list_marks_split = splitTask.split_output(segmentsStructure)

      if len(list_query_split) > 1:
        for e_part in list_query_split:
          all_split.append(e_part)
          if list_marks_split:
            all_marks.append(list_marks_split.pop(0))
      else:
        all_split.append(sentence)
        all_marks.append([])

    logging.info("split Output : {} ".format(all_split))
    logging.info("split Sequences : {} ".format(all_marks))
    return all_split, all_marks

  #*********General Functions***********
  def _deals_output(self, segment, editD, trans_segments, status_tokenizer, status):
    if self.out == 'moses': # Moses output is tokenizer
      if status_tokenizer == False:# tokenize output
        segment.source_text = TMUtilsMatching.pre_process(segment.source_text, self.src_lang, 'tokenizer', {})
        segment.target_text = TMUtilsMatching.pre_process(segment.target_text, self.tgt_lang, 'tokenizer', {})
      trans_segments.append((segment, editD))
      return trans_segments, 'break'
    else:
      if status_tokenizer == True:  # TM output is untokenizer
        segment.target_text = TMUtilsMatching.pre_process(segment.target_text.split(' '), self.tgt_lang, 'untokenizer', {})
        segment.source_text = TMUtilsMatching.pre_process(segment.source_text.split(' '), self.src_lang, 'untokenizer', {})
      trans_segments.append((segment, editD))
      if status == 'translate': status = 'break'
      else: status = 'continue'
      #if editD == 100: # Add this if to obtain better matching time
      #  status = 'break'
    logging.info("Final Output (Query -- Source -- Target): {} {} {}".format(safe_str(self.query_dic['query'] + ' -- '), safe_str(segment.source_text + ' -- '), safe_str(segment.target_text)))
    return trans_segments, status

  def style_string(self, src_text, tgt_text, status_tokenizer):
    #Check upper and lower case
    if src_text and tgt_text:
      src_text, tgt_text = self._transform_case(src_text, tgt_text)
      # Transfer XML tags (if needed)
      self.timer.start("transfer_tags")
      if re.search("</?[^<>]+/?>", self.query) is not None: # transfer tags only if query has and tgt and src don't
        status_tokenizer = True
        if (re.search("</?[^<>]+/?>", src_text) is None):
          src_text = TMUtilsMatching.transfer_tags(self.query, src_text, (self.src_lang, self.tgt_lang))
        if (re.search("</?[^<>]+/?>", tgt_text) is None):
          tgt_text = TMUtilsMatching.transfer_tags(self.query, tgt_text, (self.src_lang, self.tgt_lang))
      self.timer.stop("transfer_tags")
    return src_text, tgt_text, status_tokenizer

  def _transform_case(self, src_text, tgt_text):
    #All cases (first word phrase; all first word and all upper all lower)
    if self.query.istitle(): # All the first words are upper
      src_text = src_text.title()
      tgt_text = tgt_text.title()
    else:
      if self.query[0].istitle(): #Only the first word is upper
        src_text = src_text[0].upper() + src_text[1:]
        tgt_text = tgt_text[0].upper() + tgt_text[1:]
    if self.query.isupper(): # All in upper case
      src_text = src_text.upper()
      tgt_text = tgt_text.upper()
    if self.query.islower(): # All in lower case
      src_text = src_text.lower()
      tgt_text = tgt_text.lower()
    return src_text, tgt_text

  def _preprocess(self):
    self.query_dic['query'] = self.query

    if re.search("<.*>", self.query):  # Uniform tags --> # Yo tengo un <b>gato</b>. --> Yo tengo un <T1>gato</T1>
      self.query_dic['query_tags'] = TMUtilsMatching.pre_process(self.query, (self.src_lang, self.tgt_lang), 'tags', {})

      self.query_dic['query'] = self.query_dic['query_tags'] # query now have the tags <T1>gato</T1>

    if 'regex' in self.pipe: self.query_dic['query_re'] = TMUtilsMatching.pre_process(self.query_dic['query'], self.src_lang, 'reg_exp', self.match['regex'].re_pp)
    else: self.query_dic['query_re'] = self.query_dic['query']
    self.query_dic['query_re_reduce'] = TMRegexMatch.simplified_name(self.query_dic['query_re'])

    return self.query_dic

  # Good explanation about editdistance --> http://stackoverflow.com/questions/10405440/percentage-rank-of-matches-using-levenshtein-distance-matching
  # http://math.stackexchange.com/questions/1776860/convert-levenshtein-distance-to-percents
  # Ways to estimate the match percent --> https://www.tm-town.com/blog/the-fuzziness-of-fuzzy-matches
  def _tm_edit_distance(self, q_text, s_text, q_simplified, s_simplified):
    # Corner case - matching artificial empty segment -> giving minimal score
    if q_text and not s_text.strip():
      return 1
    #Always reduce the tags to count only one element
    '''
    print('**original**')
    print(q_text)
    print('**src**')
    print(s_text)
    print('**originalS**')
    print(q_simplified)
    print('**srcS**')
    print(s_simplified)
    '''
    # 1) ********** Obtain words and stop words sequences
    q_onlyW, q_st_word = TMMatching._only_word_sequence(q_text, self.src_lang)
    s_onlyW, s_st_word = TMMatching._only_word_sequence(s_text, self.src_lang)
    '''
    print(q_onlyW)
    print(s_onlyW)
    print(q_st_word)
    print(s_st_word)
    '''
    if not q_onlyW and not q_st_word:
    #print(self.src_lang)
    #if self.src_lang=='zh':
      editD = 100 - (TMUtilsMatching._edit_distance(q_text, s_text)) #* 100
    else:
      # Normal editDistance, without puntuation marks and only word, without stop words
      nchar_diff = TMUtilsMatching._edit_distance(' '.join(q_onlyW), ' '.join(s_onlyW))  # Consider all the words, without any substitution
      #print(q_onlyW)
      #print(s_onlyW)
      nchar_len = len(' '.join(q_onlyW)) + len(' '.join(s_onlyW))
      if nchar_len == 0: nchar_len = 1
      #print(nchar_len)
      char_diff = (2*nchar_diff)/(nchar_len)  # total of charaters

      # 2) ********* Simplified --> Convert to letter and keep only puntuation marks
      q_replaceW, q_onlyS = TMMatching._symbol_sequence(q_simplified)  # Original query

      # Ex. '- 3.67 housing units constructed under the $ #  home % ownership saving scheme in the Hanano/ and (Hamdaniya districts;' --> - N N N N N N $ #  N % N N N N N N/ N (N N;
      s_replaceW, s_onlyS = TMMatching._symbol_sequence(s_simplified) # Original tm_src

      if (len(s_onlyS) == 0 and len(q_onlyS) == 0): # There are not symbol
        n_symbol_diff = 0
      else:
        n_symbol_diff = TMUtilsMatching._edit_distance(q_replaceW, s_replaceW) #(' '.join(q_onlyS), ' '.join(s_onlyS))/2#

      len_symbols = len(q_replaceW.split(' ')) + len(q_replaceW.split(' '))  # len(q_onlyS) + len(s_onlyS)
      if len_symbols == 0: len_symbols = 1

      symbol_diff = (2*n_symbol_diff)/len_symbols


      # 3) ********* Exist or not exist the query words on source
      nword_diff = set(q_onlyW).difference(s_onlyW) # Replace regular expression by only one word
      onlyW_len = len(q_onlyW)
      if onlyW_len == 0: onlyW_len = 1
      word_diff = (len(nword_diff))/onlyW_len # only query words

      # 4) ********* Stop words
      stop_words = True
      if (len(q_st_word) == 0 and len(s_st_word) == 0):  # There are not stop word or this language doesn't have stop words list
        stop_words = False

      if stop_words:
        n_st_diff = TMUtilsMatching._edit_distance(' '.join(q_st_word), ' '.join(s_st_word))
        len_stop_word = len(' '.join(q_st_word)) + len(' '.join(s_st_word))
        stop_word_diff = (2 * n_st_diff)/len_stop_word

        editD = (1 - ((0.70 * (char_diff)) + (0.10 * (word_diff)) + (0.10 * (symbol_diff)) + (0.10 * (stop_word_diff)))) * 100
      else:
        editD = (1 - ((0.70 * (char_diff)) + (0.15 * (word_diff)) + (0.15 * (symbol_diff)))) * 100

    if editD < 0:
      editD = 10
    return int(math.floor(editD))

  # Match Kanji --> u'[\u4E00-\u9FFF]+'
  # Match Hiragana --> u'[\u3040-\u309Fー]+'
  # Match Katakana --> u'[\u30A0-\u30FF]+
  @staticmethod
  def _only_word_sequence(text, lang): # Receive original sequence
    only_word = []
    only_st = []
    l_src_st = TMUtilsMatching.check_stopwords(lang)
    for match in re.finditer(r'[a-zA-Z0-9\u4e00-\u9fff\u3040-\u309Fー\u30A0-\u30FF]+', text):  # Get all the words and numbers

      if l_src_st: # For some language we don't have stopwords list
        if match.group() in l_src_st:
          only_st.append(match.group())
        else:
          only_st.append('P')
          only_word.append(match.group())

    return only_word, only_st

  @staticmethod
  def _symbol_sequence(text): # Receive simplified sequence, without elements match with regular expression
    only_symbol = []
    for match in re.finditer(r'[a-zA-Z0-9\u4e00-\u9fff\u3040-\u309Fー\u30A0-\u30FF]+', text):  text = text.replace(match.group(), 'P', 1) # Replace all words by
    for match in re.finditer(r'[^\w\s]', text): only_symbol.append(match.group()) # Obtain list os symbols #  r'[^a-zA-Z0-9\s]+'
    return text, only_symbol

  # Input : list of segments; query
  # Output: Sort the list of all the segmets [(segment, editD); ...(segment, editD)] considering edit distance
  def _match_rank(self, best_segments):
    self.timer.start("rank segments")
    editD_score = []
    if 'query_tags' in self.query_dic: # Simplified tags
      query = TMUtilsMatching.reduce_tags(self.query_dic['query_tags']) # Yo tengo un <T1>gato</T1>. Yo tengo un T gato T.
    else:
      query = self.query_dic['query']

    for i in range(0, len(best_segments)):
      segment = best_segments[i]
      # Simplified tags in tm source
      if re.search("</?T[0-9]*/?>", segment[0].source_text):
        src_text = TMUtilsMatching.reduce_tags(segment[0].source_text) # Simplified tags in tm source and target
      else: src_text = segment[0].source_text
      # Applied Regex and simplified
      if 'regex' in self.pipe: src_re = TMUtilsMatching.pre_process(src_text, self.src_lang, 'reg_exp', self.match['regex'].re_pp)
      else: src_re = src_text


      src_re_reduce = TMRegexMatch.simplified_name(src_re)
      best_segments[i] = (segment[0], segment[1], src_re, src_re_reduce)
      editD_score.append(self._tm_edit_distance(query, src_text, self.query_dic['query_re_reduce'], src_re_reduce))  # EditD with tags simplied TMUtilsMatching._edit_distance(query, src_text)
    self.timer.stop("rank segments")
    return sorted(zip(best_segments, editD_score), key=operator.itemgetter(1), reverse=True)

  #Check if delete the tags improve the editD, Yes replace the src and tgt, else keep initial src and tgt
  def _match_tags(self, src_text, src_re_reduce, tgt_text, status, ini_editD):
    reduce = False
    out_tags_query, src_text, tgt_text, match = TMTags._match_tags(self.query_dic['query'], src_text, tgt_text)
    if match == 100:
      status = 'find'
    else:
      match = self._tm_edit_distance(out_tags_query, src_text, TMUtilsMatching.strip_tags(self.query_dic['query_re_reduce']).strip(), TMUtilsMatching.strip_tags(src_re_reduce).strip())
      if self.query_dic['query'] != out_tags_query:
        self.query_dic['query'] = out_tags_query
        reduce = True
      if match >= ini_editD:
        ini_editD = match
    return src_text, tgt_text, status, reduce, ini_editD

  #************PosTag functions*************

  def check_query_parameters(self):
    if 'pos' not in self.query_dic:  # Applied pos and universal on query --> only the firt time
      if 'tokenizer' not in self.query_dic:  # The first transformation is posTag --> any other were applied
        query_out_tags = XmlUtils.replace_tags(self.query_dic['query'])
        self.query_dic['tokenizer'] = TMUtilsMatching.pre_process(query_out_tags, self.src_lang, 'tokenizer', {})
      self.query_dic['pos'] = TMUtilsMatching.pre_process(self.query_dic['tokenizer'], self.src_lang, 'pos_tagger', {})
    return self.query_dic['query'], self.query_dic['tokenizer'], self.query_dic['pos']

  def _combine_feature_match(self, tok_query, src_word_pos, tgt_word_pos, align_features):
    tgt_un_match, tgt_position, operation, src_un_match, src_position, pos_tag = self.match['posTag'].process(tok_query, self.query_dic['universal'], src_word_pos, tgt_word_pos, align_features)
    return tgt_un_match, tgt_position, operation, src_un_match, src_position, pos_tag

  def _improve_match(self, query_info, operation):
    query_word = query_info.split(' _ ')

    if operation == 'R': #Estimate editD between the words
      return (TMUtilsMatching._edit_distance(query_word[0], query_word[1]) / 2)
    else:
      return (len(query_word[0]) / 2) # EditD is equal ao total de characters add or delete from the string


  # Input: align target word, position of target word, unmatch input src word, operation (R, I or D), position of word in src input, best segment
  # src_text, src_un_match, src_position, operation, src_un_match, 'source'
  def _create_target_expression(self, text, position, operation, query_info,part, upper, pos_Tag):  # tgt_text, tgt_word, tgt_position, operation, src_un_match, part
    query_word = query_info.split(' _ ')[0].strip()
    text = text.split(' ')
    if operation == 'R':
      if pos_Tag == '.': # Check if punctuation marks
        text[int(position.split(' _ ')[1])] = query_word
      else:
        if not upper:
          if query_word.upper() in self.query:
            upper = True
        if part == 'target':
          candidate_translation = self._obtain_translation(query_word, 1)
          if candidate_translation:
            logging.info("Candidate translations: {}".format(candidate_translation)) 
            if upper: text[position] = candidate_translation.upper()#self._obtain_translation(query_word, 1, 1).upper()
            else: text[position] = candidate_translation#self._obtain_translation(query_word, 1, 1)
        else:
          if upper: text[int(position.split(' _ ')[1])] = query_word.upper()
          else: text[int(position.split(' _ ')[1])] = query_word
    if operation == 'D':
      text.pop(position)
    if operation == 'I':
      if len(text) > position:
        if part == 'target' and pos_Tag != '.':
          for x in reversed([query_word]): text.insert(position, self._obtain_translation(x, 1)) #Return only one word from elasticsearch  text.insert(position,self.tm_translator.translate(x))#
        else:
          for x in reversed([query_word]): text.insert(position, x)
      else:
        if part == 'target' and pos_Tag != '.':
          candidate_translation = self._obtain_translation(query_word, 4) # Return at least 4 words from elasticsearch
          if candidate_translation: text.append(candidate_translation)#  self._obtain_translation(query_word, 1, 1) text.append(self.tm_translator.translate(query_word))  # tgt_word
        else:
          text.append(query_word) #
    text = [t for t in text if t] # remove empty words/lists
    logging.info("TEXT: {}".format(text))
    return ' '.join(text), upper

  def _obtain_translation(self, query_word, limit):

    # Search translation on Elasticsearch
    candidate_translation = self.match['posTag'].search_exact_value(query_word, limit)[0]  # Search translation on ElasticTM
    if not candidate_translation:
      wordT = query_word
      if self.machine_translation:
        machine_translation = self.tm_translator.translate(query_word)
        if machine_translation: wordT = machine_translation
      logging.info("Automatic Translate : {}".format(wordT))
      return wordT  # Automatic translation
    else:
      # print('Traducão ElasticTM ' + candidate_translation[0])
      # print(candidate_translation)
      ct = candidate_translation[0]
      if ct and type(ct) is list: ct = ct[0]
      return ct




  #*********Regex functions**********
  # Input --> Query, original tgt_text, src_text
  # Output --> tgt_text, src_text, ter
  def _regex_transform(self, src_text, tgt_text):

    src_text = self.match['regex'].find_replace(self.query_dic['query'], src_text, self.src_lang, self.src_lang, self.src_lang)
    tgt_text = self.match['regex'].find_replace(self.query_dic['query'], tgt_text, self.src_lang, self.tgt_lang, self.tgt_lang)
    return tgt_text, src_text

  @staticmethod
  def check_upper_equal(qtext, rtext):
    if all(x == rtext.split(' ')[0] for x in rtext.split(' ')) and qtext.isupper(): return True

  @staticmethod
  def split_source(class_lang, lang):
    if not lang in TMMatching.split:
      logging.info("Loading Split rules for {}".format(lang))
      TMMatching.split[lang] = TMSplit(class_lang, lang)
    return TMMatching.split[lang]


  '''
    #*******************Tags******************
    @staticmethod
    def _check_puntuation_marks(q_word_pos, tm_word_pos, tm_text):

      print('+++++++++++++++++++++++++++++')
      print(q_word_pos)
      print(tm_word_pos)
      print(tm_text)

      query_pos, query_words = [w[1] for w in q_word_pos], [w[0] for w in q_word_pos]
      tm_pos, tm_words = [w[1] for w in tm_word_pos], [w[0] for w in tm_word_pos]

      #Check length
      if len(query_pos) == len(tm_pos): # Replace operation
        # Replace
      elif len(query_pos) > len(tm_pos):  # Insert a new word in target
        # Insert
      else:
        # Delete

      #query_words = [w[0].lower() for w in query_pos]
      #print(query_words)
      #print(query_pos)
      #tm_pos = [w[1] for w,p  in tm_word_pos]
      #tm_words = [w[0].lower() for w in tm_word_pos]

      # Insert puntuation marks in src and tgt --> Exist on query and not on src and tgt
      #if '.' in list(set(query_pos) - set(tm_pos)):
      #  print('****INSERT*****')
      #  q_pos = query_pos.index('.')
      #  print(query_pos)
      #  q_word = query_words[q_pos]
      #  print(query_words[q_pos])
      #  if q_pos == len(query_pos) or q_pos < len(tm_word_pos): # puntuation on last position
      #    tm_word_pos.append([query_words[q_pos],'.'])
      #    tm_text + ' ' + query_words[q_pos]



      # print('****DELETE*****')
      # print(list(set(src_pos)-set(query_pos)))

      #return tm_word_pos, tm_text
    '''
