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
import os
import re
import sys

sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))
sys.path = [p for p in sys.path if p]


from TMPreprocessor.TMRegExpPreprocessor import TMRegExpPreprocessor
from TMMatching.TMUtilsMatching import TMUtilsMatching

class TMRegexMatch():
  PATTERN  = re.compile('(\|.+\|)')

  def __init__(self, src_lang, tgt_lang):

    self.src_lang = src_lang
    self.tgt_lang = tgt_lang
    # Initialize regexp preprocessors
    self.re_pp = dict()
    for lang in [src_lang, tgt_lang]:
      self.re_pp[lang] = TMRegExpPreprocessor(lang)

  # Apply regular expression to src, tgt and replace query values in src and tgt
  def process(self, query_dic, src_text, tgt_text): #, src_pos, tgt_pos

    # pre-process and apply regex to tm_src
    src_re = self.re_pp[self.src_lang].process(src_text)

    if src_text != src_re: # Was applied regex in src

      tgt_re = self.re_pp[self.tgt_lang].process(tgt_text)

      # if query_dic['query_re'] == query_dic['tokenizer']: # Was not applied regular expression on query
      #   if src_re is not None and src_pos is not None:
      #     src_text, src_pos = TMRegexMatch._delete_elements(src_re.split(' '), src_pos.split(' '))
      #   if tgt_re is not None and tgt_pos is not None:
      #     tgt_text, tgt_pos = TMRegexMatch._delete_elements(tgt_re.split(' '), tgt_pos.split(' '))

        #ter = TMUtilsMatching._ter_score(query_dic['tokenizer'], src_text)
      #else: #Transform target into query

      ter = TMUtilsMatching._ter_score(query_dic['query_re'], src_re)
      #Extract patterns (find and replace) value
      src_query_f, src_query_r = TMRegexMatch._extract_find_replace(query_dic['tokenizer'].split(' '), query_dic['query_re'].split(' '))
      tgt_query_f = src_query_f.copy()
      tgt_query_r = src_query_r.copy()
      src_f, src_r = TMRegexMatch._extract_find_replace(src_text.split(' '), src_re.split(' '))
      ter = ter - len(src_f)
      src_text = TMRegexMatch._replace_values(src_query_f, src_query_r, src_re.split(' '), src_f, src_r)

      tgt_f, tgt_r = TMRegexMatch._extract_find_replace(tgt_text.split(' '), tgt_re.split(' '))
      tgt_text = TMRegexMatch._replace_values(tgt_query_f, tgt_query_r, tgt_re.split(' '), tgt_f, tgt_r)

    else:
      ter = TMUtilsMatching._ter_score(query_dic['tokenizer'], src_text) #Regex did't applied
    return tgt_text, src_text, ter #, src_pos, tgt_pos

  @staticmethod
  def _delete_elements(text, text_pos):
    new_text = []
    new_pos = []
    for w in range(0, len(text)-1):
      if re.search(TMRegexMatch.PATTERN, text[w]) is None:
        new_text.append(text[w])
        new_pos.append(text_pos[w])
    return ' '.join(new_text), ' '.join(new_pos)

  # @staticmethod
  # def _replace_values(x_find, x_replace, sentence_re, y_find, y_replace):
  #
  #   if len(x_find) == len(y_find):  # source and target have the same regex
  #     for w in range(0, len(sentence_re)):
  #       if re.search(TMRegexMatch.PATTERN, sentence_re[w]) is not None:
  #         sentence_re[w] = x_replace.pop(0)
  #   else:
  #     # Iterate over tokenized and regex text to replace target/source word by query word (number, e-mail, etc.).
  #     si = 0  # find_replace src
  #     for ti in range(0, len(sentence_re)):
  #       if re.search(TMRegexMatch.PATTERN, sentence_re[ti]) is not None:
  #         if si < len(x_replace):
  #           sentence_re[ti] = x_replace.pop(0)  # put query value
  #         else:
  #           sentence_re[ti] = sentence_re[ti]  # put tm tgt value
  #   return ' '.join(sentence_re)

  # Replace Regex value by query value. Check if values are equal before replace.
  @staticmethod
  def _replace_values(x_find, x_replace, sentence_re, y_find, y_replace):

    if len(x_find) == len(y_find):  # source and target have the same regex
      for w in range(0, len(sentence_re)):
        if re.search(TMRegexMatch.PATTERN, sentence_re[w]) is not None:
          sentence_re[w] = x_replace.pop(0)
    else:
      #xi = 0
      for w in range(0, len(sentence_re)):
        if re.search(TMRegexMatch.PATTERN, sentence_re[w]) is not None:
          if len(x_replace) != 0 :
            replace_value = [[pos, value] for pos, value in enumerate(x_replace) if x_find[pos] == y_find[0]]  # Search regex patterns equals on query and tgt
            if not replace_value:  # pattern not exist in x (query) --> Then put the value than appear in original sentence
              sentence_re[w] = y_replace.pop(0)
              y_find.pop(0)
            else:
              for i in range(0, len(replace_value)): #
                pos, value = replace_value[i]
                if value == y_find[0]:
                  sentence_re[w] = y_replace[0]
                  rm_pos = pos # position where delete the pattern
                  break
                else:
                  sentence_re[w] = replace_value[0][1] # Replace in the query order
                  rm_pos = replace_value[0][0]
              y_replace.pop(0)
              y_find.pop(0)
              x_find.pop(rm_pos)
              x_replace.pop(rm_pos)
            #xi += 1
          else:
            sentence_re[w] = y_replace.pop(0)
            y_find.pop(0)
    return ' '.join(sentence_re)

  @staticmethod
  def _extract_find_replace(text, text_regex):
    replace = []
    find = []
    for plain, tag in zip(text, text_regex):
      if re.search(TMRegexMatch.PATTERN, tag) is not None:
        replace.append(plain)
        find.append(tag)
    return find, replace






