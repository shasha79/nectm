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
from babel import numbers, Locale
from decimal import Decimal, DecimalException

sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))
sys.path = [p for p in sys.path if p]


from TMPreprocessor.TMRegExpPreprocessor import TMRegExpPreprocessor
from TMMatching.TMUtilsMatching import TMUtilsMatching

class TMTags():

  @staticmethod
  def _match_tags(query, src_text, tgt_text):

    match = 0
    query_strip_tags = TMUtilsMatching.strip_tags(query)  #Strip tags from query
    src_text_strip_tags = TMUtilsMatching.strip_tags(src_text).strip() # Strip tags from src
    tgt_text_strip_tags = TMUtilsMatching.strip_tags(tgt_text).strip()  # Strip tags from tgt

    if query_strip_tags == src_text_strip_tags: # query and src_tm are equals
      match = 100
    return query_strip_tags, src_text_strip_tags, tgt_text_strip_tags, match


class TMRegexMatch():
  PATTERN  = re.compile('(\|[A-Z]+\|){1,3}')
  SIMPLE_PATTERN = re.compile('(\|?[A-Z]+\|)')

  def __init__(self, src_lang, tgt_lang):

    self.src_lang = src_lang
    self.tgt_lang = tgt_lang
    # Initialize regexp preprocessors
    self.re_pp = dict()
    self.pipe = ['formula', 'datetime', 'bullet',  'munit', 'acronym', 'email', 'url', 'number'] #
    for lang in [src_lang, tgt_lang]: #'acronym', 'email', 'url', 'datetime', 'formula', 'number'
      self.re_pp[lang] = TMRegExpPreprocessor(lang, pipe = ['formula', 'datetime', 'bullet', 'munit', 'acronym', 'email', 'url', 'number'])

  @staticmethod
  def simplified_name(text_re): #text_re = '|NUMBER| September |DATETIME| (|ACRONYM|/|FORMULA||BULLET|'

    key = {
      'number': 'N',
      'email': 'E',
      'url': 'U',
      'datetime': 'D',
      'munit': 'M',
      'formula': 'F',
      'acronym': 'A',
      'bullet': 'B'
    }

    name_patterns = [i.strip('|') for i in re.findall('(\|?[A-Z]+\|)', text_re)] #['NUMBER', 'DATETIME', 'ACRONYM', 'FORMULA', 'BULLET']
    for n in name_patterns:
      if n.lower() in key:
        text_re = text_re.replace('|'+n.upper()+'|', key[n.lower()]) #re.sub(n.upper(), self.key[n.lower()], text_re)
    return text_re

  def find_replace(self, q_text, tm_text, q_lang, tm_lang, convert_lang):
    #convert_lang = 'urd'
    tm_text_copy = tm_text
    #print(tm_text)
    already_replace_values = []  # List with values that were already replaced
    for pattern in self.pipe:  # Check each pattern
      while re.search(self.re_pp[q_lang].get_regex(pattern).compiled_regexp, q_text):  # Check the first time
        q_value = self.re_pp[q_lang].get_regex(pattern).get_value(q_text)#re.search(, q_text).group()
        #print('Query: ' + str(q_value))
        q_text = self.re_pp[q_lang].get_regex(pattern).do_replace(q_text, self.re_pp[q_lang]._key2placeholder(pattern)) #re.sub(self.re_pp[self.src_lang].regex[pattern].compiled_regexp, , q_text, 1)
        #print(q_text)
        list_tm_values = []
        #print(re.findall(self.re_pp[tm_lang].get_regex(pattern).compiled_regexp, tm_text))
        for match in re.finditer(self.re_pp[tm_lang].get_regex(pattern).compiled_regexp, tm_text):
          #print('TM')
          #print(match.group())
          tm_value = match.group()

          if q_value == tm_value: # Exist pattern in query and tm and are equal --> keep tm value
            #print('Equal value')
            tm_text = self.re_pp[tm_lang].get_regex(pattern).do_replace(tm_text, self.re_pp[tm_lang]._key2placeholder(pattern)) #re.sub(self.re_pp[self.src_lang].regex[pattern].compiled_regexp, self._key2placeholder(pattern), q_text, 1)
            already_replace_values.append((tm_value, (match.start(), match.end()))) # Add replace value in the tm and position. Position will change after replace
            #print(tm_text)
            break
          else:
            #print('Not Equal value')
            list_tm_values.append(match)
            #print(list_tm_values)
        #print(list_tm_values)
        if list_tm_values: # Exist pattern in query and tm, but are different --> replace tm value by query value
          #print(tm_text_copy)
          #print(re.findall(self.re_pp[tm_lang].get_regex(pattern).compiled_regexp, tm_text_copy))
          #findList = re.findall(self.re_pp[tm_lang].get_regex(pattern).compiled_regexp, tm_text_copy)
          #findList = [tuple(j for j in i if j) for i in findList]
          #print(findList)
          #for l in re.findall(self.re_pp[tm_lang].get_regex(pattern).compiled_regexp, tm_text_copy):
          #  print(' '.join(l).strip())
          for tm_match in re.finditer(self.re_pp[tm_lang].get_regex(pattern).compiled_regexp, tm_text_copy):
            #print('&&&&&&&&&&&&&&&')
            #print(tm_match)
            #print(already_replace_values)
            if tm_match.group() not in [word for (word, pos) in already_replace_values] and \
                    (not TMRegexMatch.check_range(tm_match.start(), [range(ini, end) for (word, (ini, end)) in already_replace_values]) or \
                      not TMRegexMatch.check_range(tm_match.end(), [range(ini, end) for (word, (ini, end)) in already_replace_values])):
              #print('$$$$Vou remplazar isto aqui $$$$ ' + str(tm_match.group()))
              if pattern == 'number':
                #print(q_value)
                #print(convert_lang)
                #print(Locale(convert_lang))
                #if ',' in q_value:
                #  q_value = q_value.replace(',','.')
                  #print(q_value)
                try:
                  current_lang = Locale(convert_lang)
                except UnboundLocalError:
                  current_lang = Locale('en')# 'en' by default
                try:
                  q_value = numbers.format_number(q_value, current_lang)
                except (ValueError, DecimalException):
                  pass
                  #q_value = numbers.format_number(q_value, current_lang)
                  #q_value = numbers.format_number(q_value, Locale('en'))
              #print(q_value)
              tm_text_copy = tm_text_copy.replace(tm_match.group(), q_value, 1)
              break
          #    for match re.finditer()
          #if self.re_pp[tm_lang].get_regex(pattern).get_value(tm_text_copy) not in already_replace_values:
          #tm_text_copy = self.re_pp[tm_lang].get_regex(pattern).do_replace(tm_text_copy, q_value)  # Replace the first occurence of the text
          already_replace_values.append((q_value, (match.start(), match.end())))  # Add replace value in the tm and position. Position will change after replace
          tm_text = self.re_pp[tm_lang].get_regex(pattern).do_replace(tm_text, self.re_pp[tm_lang]._key2placeholder(pattern))  # re.sub(self.re_pp[self.src_lang].regex[pattern].compiled_regexp, self._key2placeholder(pattern), q_text, 1)
        #if find == False:
        #  tm_text = self.re_pp[tm_lang].get_regex(pattern).do_replace(q_text, self.re_pp[tm_lang]._key2placeholder(pattern))
          #print(tm_text)
          #print(tm_text_copy)
    return tm_text_copy

  @staticmethod
  def check_range(value, list_range):
    #print(list_range)
    for each_range in list_range:
      if value in each_range:
        #print(True)
        return True

  '''
  def apply_regex(self, query_re, src_text, ini_editD):
    # pre-process and apply regex to tm_src
    src_re = self.re_pp[self.src_lang].process(src_text)#TMUtilsMatching.pre_process(src_text, self.src_lang, 'reg_exp', self.match['regex'].re_pp)
    #self.re_pp[self.src_lang]. process(src_text) #Applied regex to src        get_pattern_value(src_text)  #

    if src_re != src_text:  # If src has regex pattern
      # Simplified regular expression to keep only one caracter
      s_src_re = TMRegexMatch.simplified_name(src_re)  # re.sub(TMRegexMatch.PATTERN, 'R', src_re)
      print(s_src_re)
      s_query_re = TMRegexMatch.simplified_name(query_re)  # re.sub(TMRegexMatch.PATTERN, 'R', query_re)
      print(s_query_re)
      # compare
      if s_src_re.lower() == s_query_re.lower():  # With simplified regular expression and in lowercase
        match = 0  # Perfect match
      else:  # Edit distance improve to decide if apply or not regular expression, when there are not perfect match
        match = TMUtilsMatching._edit_distance(TMUtilsMatching.reduce_tags(s_query_re).lower(), TMUtilsMatching.reduce_tags(s_src_re).lower())
    else:
      #src_p_value = []
      src_re = src_text
      match = ini_editD
    return src_re, match  #src_p_value,
  '''
  '''
  def transform_regex(self, query_p_value, src_text, src_re, src_p_value, tgt_text, tgt_re, tgt_p_value):

    src_copy_query_p_value = query_p_value.copy()
    tgt_copy_query_p_value = query_p_value.copy()
    #tgt_query_r = src_query_r.copy()

    #src_f, src_r = TMRegexMatch._extract_find_replace(src_text.split(' '), src_re.split(' '))
    src_text = self._replace_values(src_copy_query_p_value, src_p_value, src_re)
    tgt_text = self._replace_values(tgt_copy_query_p_value, tgt_p_value, tgt_re)
    #src_text, src_count_replace = TMRegexMatch._replace_values(src_query_f, src_query_r, src_re.split(' '), src_f, src_r, src_text.split(' '))

    #tgt_f, tgt_r = TMRegexMatch._extract_find_replace(tgt_text.split(' '), tgt_re.split(' '))
    #tgt_text, tgt_count_replace = TMRegexMatch._replace_values(tgt_query_f, tgt_query_r, tgt_re.split(' '), tgt_f, tgt_r, tgt_text.split(' '))
    return src_text, tgt_text

  # Replace Regex value by query value. Check if values are equal before replace.

  def _replace_values(self, x_find_replace, y_find_replace, sentence_re): # x_find, x_replace, sentence_re, y_find, y_replace, sentence

    # x_find_replace --> [('|EMAIL|', 'alex2@pangeanic.co.ar'), ('|EMAIL|', 'lianet@gmail.com'), ('|NUMBER|', '45')]
    # y_find_replace --> [('|EMAIL|', 'alex2@pangeanic.co.ar'), ('|EMAIL|', 'lianet@gmail.com'), ('|DATETIME|', '1960'), ('|NUMBER|', '30')]

    ini_pattern = re.compile('(\|?[A-Z]+\|)')
    for pattern in re.finditer(ini_pattern,sentence_re):
    #while re.search(ini_pattern, sentence_re) is not None:
      #re.search(re.compile('(\|?(EMAIL)+\|)'), sentence_re)
      pattern = pattern.group()#re.search(ini_pattern, sentence_re).group() # Return the pattern (first) |NUMBER|
      #print(pattern)
      if pattern.strip('|').lower() not in self.key:
        sentence_re = sentence_re.replace(pattern, pattern.strip('|'), 1)
        continue
      #print(re.search(re.compile('(\|?(EMAIL)+\|)'), sentence_re))

      #text = re.sub(re.search(self.compiled_regexp, text).group(), placeholder, text)
      #print('Find_REPLACE_VALUES')
      #print(x_find_replace)
      #print(y_find_replace)
      if len(x_find_replace) != 0: # There are pattern without replace on the query
        # Create the list of the pattern on the query --> Search regex patterns equals on query and src or tgt
        #for pos, (p, v) in enumerate(x_find_replace):
          #print(str(x_find_replace[pos]) + '----' + str(y_find_replace[0][0]))

        query_pattern = [(pos, p, v) for pos, (p, v) in enumerate(x_find_replace) if x_find_replace[pos][0] == y_find_replace[0][0]]
        #print(query_pattern)
        if not query_pattern:  # pattern not exist in x (query) --> Then put the value than appear in original (src or tgt) sentence
          sentence_re = sentence_re.replace(pattern, y_find_replace.pop(0)[1], 1)
          #sentence_re = re.sub(re.compile('(\|?(EMAIL)+\|)'), y_find_replace.pop(0)[1], sentence_re, 1) #sentence_re[w] = y_replace.pop(0)
        else:
          equal = False
          rm_pos = 0
          # Search equal values between query and src
          for i in range(0, len(query_pattern)):
            pos, p, v = query_pattern[i] # position, pattern and value
            if v == y_find_replace[0][1]:  # The two value are equal, then does not replace by query, keep the original value
              #sentence_re = re.sub(re.compile('(\|?(EMAIL)+\|)'), y_find_replace.pop(0)[1], sentence_re, 1) #sentence_re[w] = y_replace[0]
              sentence_re = sentence_re.replace(pattern, y_find_replace.pop(0)[1], 1)
              rm_pos = pos  # position where delete the pattern
              equal = True
              #print(pattern)

              #print(sentence_re)
              break  # Break, because the same pattern would be appear more than one time.
          #print(query_pattern[0][1])
          if equal== False:
            #print('Entrou em EQUAL **********')
            #print(query_pattern)
            sentence_re = sentence_re.replace(pattern, query_pattern[0][2], 1)
            #print(sentence_re)
            #sentence_re = re.sub(re.compile('(\|?(EMAIL)+\|)'), query_pattern[0][1], sentence_re, 1) # Replace by the first value on the query
            rm_pos = 0
            y_find_replace.pop(0)
          x_find_replace.pop(rm_pos)
      else:
        sentence_re = sentence_re.replace(pattern, y_find_replace.pop(0)[1], 1)
        #sentence_re = re.sub(re.compile('(\|?(EMAIL)+\|)'), y_find_replace.pop(0)[1], sentence_re, 1)#sentence_re[w] = y_replace.pop(0)
    return sentence_re#, count_replace

  def transform_regex_2(self, query_dic, src_text, src_re, tgt_text, tgt_re):  # tgt_re_tok

    # Extract patterns (find and replace) value
    # src_query_f, src_query_r = TMRegexMatch._extract_find_replace(query_dic['tokenizer'].split(' '), query_dic['tokenizer_re'].split(' '))
    src_query_f, src_query_r = TMRegexMatch._extract_find_replace(query_dic['query'].split(' '), query_dic['query_re'].split(' '))

    tgt_query_f = src_query_f.copy()
    tgt_query_r = src_query_r.copy()

    src_f, src_r = TMRegexMatch._extract_find_replace(src_text.split(' '), src_re.split(' '))
    src_text, src_count_replace = TMRegexMatch._replace_values_2(src_query_f, src_query_r, src_re.split(' '), src_f, src_r, src_text.split(' '))

    tgt_f, tgt_r = TMRegexMatch._extract_find_replace(tgt_text.split(' '), tgt_re.split(' '))
    tgt_text, tgt_count_replace = TMRegexMatch._replace_values_2(tgt_query_f, tgt_query_r, tgt_re.split(' '), tgt_f, tgt_r, tgt_text.split(' '))
    return src_text, tgt_text, src_count_replace

  @staticmethod
  def _delete_elements(text, text_pos):
    new_text = []
    new_pos = []
    for w in range(0, len(text) - 1):
      if re.search(TMRegexMatch.PATTERN, text[w]) is None:
        new_text.append(text[w])
        new_pos.append(text_pos[w])
    return ' '.join(new_text), ' '.join(new_pos)

  # Replace Regex value by query value. Check if values are equal before replace.
  @staticmethod
  def _replace_values_2(x_find, x_replace, sentence_re, y_find, y_replace, sentence):

    # print(x_find)
    # print(x_replace)
    # print(sentence_re)
    # print(y_find)
    # print(y_replace)

    count_replace = 0
    if len(x_find) == len(y_find):  # source and target have the same regex
      for w in range(0, len(sentence_re)):
        if re.search(TMRegexMatch.PATTERN, sentence_re[w]) is not None:
          sentence_re[w] = x_replace.pop(0)
          count_replace += 1
    else:
      for w in range(0, len(sentence_re)):
        if re.search(TMRegexMatch.PATTERN, sentence_re[w]) is not None:
          if len(x_replace) != 0 :
            #for pos, value in enumerate(x_replace):
            replace_value = [[pos, value] for pos, value in enumerate(x_replace) if x_find[pos] == y_find[0]]  # Search regex patterns equals on query and tgt
            if not replace_value:  # pattern not exist in x (query) --> Then put the value than appear in original (src or tgt) sentence
              sentence_re[w] = y_replace.pop(0)
              y_find.pop(0)
            else:
              for i in range(0, len(replace_value)): #
                pos, value = replace_value[i]
                if value == y_find[0]: #The two value are equal, then does not replace by query, keep the original value
                  sentence_re[w] = y_replace[0]
                  rm_pos = pos # position where delete the pattern
                  break # Break, because the same pattern would be appear more than one time.
                else:
                  sentence_re[w] = replace_value[0][1] # Replace in the query order
                  rm_pos = replace_value[0][0]
                  count_replace += 1
              y_replace.pop(0)
              y_find.pop(0)
              x_find.pop(rm_pos)
              x_replace.pop(rm_pos)
          else:
            sentence_re[w] = y_replace.pop(0)
            y_find.pop(0)
        #else:
        #  sentence_re[w] = sentence[w]
    return ' '.join(sentence_re), count_replace

  @staticmethod
  def _extract_find_replace(text, text_regex):
    replace = []
    find = []
    for plain, tag in zip(text, text_regex):
      if re.search(TMRegexMatch.PATTERN, tag) is not None:
        replace.append(plain)
        find.append(tag)
    return find, replace

  # First implementation
  def transform_regex_1(self, query_dic, src_text, src_re, tgt_text):  # segment, src_re, query

    # Apply regular expression to target
    tgt_re = self.re_pp[self.tgt_lang].process(tgt_text).split(' ')  # word list of target with regular expression

    tgt_find_replace = TMRegexMatch._extract_find_replace(tgt_text.split(' '), tgt_re)

    # Replace target regex
    src_find_replace = TMRegexMatch._extract_find_replace(query_dic['tokenizer'].split(' '), src_re.split(' '))
    tgt_text = TMRegexMatch._replace_regex_value(tgt_re, src_find_replace, tgt_find_replace)

    # Replace source regex
    src_find_replace = TMRegexMatch._extract_find_replace(query_dic['tokenizer'].split(' '), src_re.split(' '))
    src_text = TMRegexMatch._replace_regex_value(src_re.split(' '), src_find_replace, tgt_find_replace)
    return src_text, tgt_text

  @staticmethod
  def _extract_find_replace_1(text, text_regx):

    find_replace = []

    for plain, tag in zip(text, text_regx):
      if re.search(TMRegexMatch.PATTERN, tag) is not None:
        find_replace.append(plain)
    return find_replace

  @staticmethod
  def _replace_regex_value_1(sentence, src_find_replace, tgt_find_replace):

    if len(src_find_replace) == len(tgt_find_replace):  # source and target have the same regex
      for w in range(0, len(sentence)):
        if re.search(TMRegexMatch.PATTERN, sentence[w]) is not None:
          sentence[w] = src_find_replace.pop(0)
    else:
      # Iterate over tokenized and regex text to replace target/source word by query word (number, e-mail, etc.).
      si = 0  # find_replace src
      for ti in range(0, len(sentence)):
        if re.search(TMRegexMatch.PATTERN, sentence[ti]) is not None:
          if si < len(src_find_replace):
            sentence[ti] = src_find_replace.pop(0)  # put query value
          else:
            sentence[ti] = sentence[ti]  # put tm tgt value
    sentence = ' '.join(sentence)
    return sentence
  '''


