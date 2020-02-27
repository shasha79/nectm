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
sys.path.append("..")
sys.path.append(os.path.join(os.path.abspath(os.path.join(__file__,"../../.."))))

from TMDbApi.TMDbApi import TMDbApi
from TMPosTagger.TMTokenizer import TMTokenizer
from TMPreprocessor.TMRegExpPreprocessor import TMRegExpPreprocessor
from TMPosTagger.TMPosTagger import TMPosTagger
from TMPosTagger.TMUniversalPosTag import TMUniversalPosTag

import logging
import pyter
from TM_TestSet.diff_match_patch import diff_match_patch
import regex #--> install pip3 install regex
from itertools import combinations
import re

class TMMatching:

  def __init__(self, src_input, src_lang, tgt_lang, domain, threshold):
    self.dic_match = dict()
    self.src_input = src_input

    self.src_lang = src_lang.split('-')[0].lower()
    self.tgt_lang = tgt_lang.split('-')[0].lower()
    self.domain = domain
    self.threshold = threshold

  # Matching process
  def execute(self):
    l_best = self.query()
    dic_match = self._cen_p_match(l_best) #Check 100% matching
    if dic_match != {}:
      print('source: ' + self.src_input + 'tm_source: ' + self.dic_match['tm_src'] + 'tm_target: ' + self.dic_match['tm_tgt'] + 'Match: ' + str(self.dic_match['match']))
    else:
      self.dic_match = self.fuzzy_match(l_best)
      if self.dic_match == {}:  #
        print("source: " + src_input + ' tm_target: ' + ' ' + ' Match: ' + str(0))
      else:
        print('source: ' + self.src_input + 'tm_source: ' + self.dic_match['tm_src'] + 'tm_target: ' + self.dic_match['tm_tgt'] + 'Match: ' + str(self.dic_match['match']))


  # Do differents query --> I will put a parameters to execute each query --> Add new queries to TMDbQuery
  def query(self):
    #Select the 10 best results
    db = TMDbApi()
    l_best_segments = []
    count = -1
    for segment, match in db.query(self.src_input, (self.src_lang, self.tgt_lang), filter={'domain': [self.domain]}):
      count = count + 1
      if segment or count <= 100: l_best_segments.append((segment.to_dict(), match))
      else: break
    return l_best_segments

  # Estimate TER between sources segmets.
  def ter_score(self, src_x, src_y): return pyter.ter(src_x.split(), src_y.split())

  def _adjust_match(self, segment, filter, ter):
    if ter > 1:
      ter = 1
    ter = (100 - (ter * 100))
    if filter:
      # Penalize match if segment doesn't match filter
      for fname, fvalues in filter.items():
        if fvalues and not set(fvalues) & set(segment[fname]):
          ter -= 5
    return ter

  #Check 100% match
  def _cen_p_match(self, l_best_segments):
    #print(l_best_segments)
    segment = l_best_segments[0][0]
    match = l_best_segments[0][1]
    ter = self.ter_score(self.src_input, segment['source_text'])
    logging.info("initial ter: {}".format(ter))
    if match == 100 and 'Q' not in segment.keys() and ter == 0:  # 100% match --> Return match considering domain
        # logging.info("source: {}, tm_source: {}, tm_target: {}, match: {}".format(src_input, segment['source_text'], segment['target_text'], str(ter)))
       self.dic_match = self._create_dic_match(segment, ter)
    return self.dic_match

  def _create_dic_match(self, segment, ter):
    filter = {'domain': ['Automotive']}
    print(filter)
    self.dic_match['tm_src'] = segment['source_text']
    print(self.dic_match['tm_src'])
    self.dic_match['tm_tgt'] = segment['target_text']
    print(self.dic_match['tm_tgt'])
    self.dic_match['match'] = self._adjust_match(segment, filter, ter)
    print(self.dic_match)
    return self.dic_match

  def fuzzy_match(self, l_best_segments):

    logging.info("Improve Fuzzy match")

    fuzzy_alg = TMFuzzyMatch(self.src_input, self.src_lang, self.tgt_lang, self.dic_match, self.threshold, l_best_segments) #Class to improve fuzzy match

    self.dic_match = fuzzy_alg.process()

    return self.dic_match

  def fuzzy_match_posTagger(self, l_best_segments):

    logging.info("Improve Fuzzy match pos tagger")

    fuzzy_alg = TMFuzzyMatch_PosTagger(self.src_input, self.src_lang, self.tgt_lang, self.dic_match, self.threshold,
                             l_best_segments)  # Class to improve fuzzy match

    self.dic_match = fuzzy_alg.process()

    return self.dic_match

    # ************It is necessary check the domain***************
  #   if (improve_ter <= ter) and (
  #             improve_ter < 0.25):  # Fuzzy Match and was possible improve ter value --> Return match considering domain
  #     print("source: " + src_input + ' tm_target: ' + process_match['reg_exp']['tm_tgt_re'] + ' Match: ' + str(
  #       self._adjust_match(segment, filter, improve_ter)))
  #     break
  #   if (
  #               count == 10 or improve_ter > ter) and ter < 0.25:  # Fuzzy Match, but wasn't improved ter value --> Return elasticsearch match
  #     print("source: " + src_input + ' tm_target: ' + segment['target_text'] + ' Match: ' + str(
  #       self._adjust_match(segment, filter, ter)))
  #     todo_ok = False
  #     break
  #
  # else:
  # todo_ok = False

# ************************************************************************************
class TMFuzzyMatch(TMMatching):

  def __init__(self, src_input, src_lang, tgt_lang, dic_match, threshold, l_best_segments):


    super().__init__(src_input, src_lang, tgt_lang, dic_match, threshold)
    self.l_best_segments = l_best_segments

    #self.pipe = ['tokenizer', 'reg_exp', 'pos_tagger', 'sent_split']
    #self.processor = {'reg_exp': TMRegExpPreprocessor(),
    #                  'sent_split': 'split'}  # TMSplitPreprocessor()

  def pre_process(self, text, lang, preprocess):
    if preprocess == 'tokenizer':
      process_text = TMTokenizer(lang).tokenizer.process(text)
    if preprocess == 'reg_exp':
      process_text = TMRegExpPreprocessor(lang).process(text)
    return process_text

  def process(self):

    dic_fuzzy = {}

    # pre-process input source
    dic_fuzzy['src_tok'] = self.pre_process(self.src_input, self.src_lang, 'tokenizer')
    dic_fuzzy['src_re'] = self.pre_process(dic_fuzzy['src_tok'], self.src_lang, 'reg_exp')

    for segment in self.l_best_segments:
      #Check if elasticsearch segment is better that a threshold
      elastic_ter = self.ter_score(self.src_input, segment[0]['source_text'])
      print('Elastic_ter ' + str(elastic_ter))
      if elastic_ter <= self.threshold: # Probably it is possible improve the matching value
        dic_fuzzy, improve_ter = self.apply_regex(segment, dic_fuzzy, elastic_ter) #Apply transformations in tm source to approximate it to input_source
        print('improve_ter ' + str(improve_ter))
        if improve_ter < elastic_ter: # Transform source and target sentence to approximate to input_source
          segment_transform = self.transform_apply_regex(segment, dic_fuzzy)
          self.dic_match = self._create_dic_match(segment_transform, improve_ter)
          break
        if improve_ter >= elastic_ter: #Applied another transformation
          #self.dic_match = self._create_dic_match(segment[0], elastic_ter)
          self.dic_match = self.fuzzy_match_posTagger(self.l_best_segments) #pos_pattern --> It will analysed all the segments
          break
      else:
        # pos_pattern --> It will analysed all the segments
        #self.dic_match = self.fuzzy_match_posTagger(self.l_best_segments)
        segment[0]['target_text'] = self.src_input # Moses will translate
        self.dic_match = self._create_dic_match(segment[0], elastic_ter)
        break
        # print input_source without translation
    #return self.match_dic, improve_ter
    return self.dic_match

  def apply_regex(self, segment, dic_fuzzy, elastic_ter):

    #Apply regular expression
    dic_fuzzy['tm_src_tok'] = self.pre_process(segment[0]['source_text'], self.src_lang, 'tokenizer')
    dic_fuzzy['tm_src_re'] = TMRegExpPreprocessor(self.src_lang).process(dic_fuzzy['tm_src_tok'])

    #Check if regular expression was applied
    if dic_fuzzy['tm_src_re'] != dic_fuzzy['tm_src_tok']: # Was applied regular expression
      improve_ter = self.ter_score(dic_fuzzy['src_re'], dic_fuzzy['tm_src_re'])
    else:
      improve_ter = 2 * elastic_ter # Put a gad TER, because regular expression doesn't improve the match

    return dic_fuzzy, improve_ter

  def transform_apply_regex(self, segment ,dic_fuzzy):

    segment = segment[0]
    # Apply regular expression to target
    dic_fuzzy['tm_tgt_tok'] = self.pre_process(segment['target_text'], self.src_lang, 'tokenizer')
    dic_fuzzy['tm_tgt_re'] = TMRegExpPreprocessor(self.src_lang).process(dic_fuzzy['tm_tgt_tok'])

    dmp = diff_match_patch()
    diffs = dmp.diff_main(dic_fuzzy['src_tok'], dic_fuzzy['tm_src_re'])# Identified differences
    dmp.diff_cleanupSemantic(diffs)

    find = [tup[1] for tup in diffs if tup[0] == 1]
    replace = [tup[1] for tup in diffs if tup[0] == -1]

    for i in range(0, len(find)):  # Replace the differences in target segment
      if find[i] in dic_fuzzy['tm_tgt_re']:
        segment['target_text'] = dic_fuzzy['tm_tgt_re'].replace(find[i], replace[i], 1)
      else:  # Search by each pattern into the sequence
        segment['target_text'] = self._sub_each_part(find[i], replace[i], dic_fuzzy['tm_tgt_re'])
    #print(segment)
    return segment

  def _sub_each_part(self, pattern, replace, tagger_sentence):

    tagger_sentence = tagger_sentence.replace(u'\xa0', u' ')
    #tagger_pattern = regex.findall(r'[' + pattern + ']+', tagger_sentence, flags=regex.BESTMATCH, overlapped=False)
    words_tagger_sentence = tagger_sentence.split(' ')
    for word in words_tagger_sentence:
      if regex.findall(r'(\|.+\|)', word) != []:  # Only replace patterns
        pos_word = words_tagger_sentence.index(word)
        if word in pattern.split(' '):
          pos_pattern = pattern.split(' ').index(word)
          word_replace = replace.split(' ')[pos_pattern]
          words_tagger_sentence[pos_word] = word_replace
    return (' '.join(words_tagger_sentence))

#************************************************************************************
class TMFuzzyMatch_PosTagger(TMMatching):

  def __init__(self, src_input, src_lang, tgt_lang, dic_match, threshold, l_best_segments):
    super().__init__(src_input, src_lang, tgt_lang, dic_match, threshold)
    self.l_best_segments = l_best_segments

  def pre_process(self, text, lang, preprocess):

    if preprocess == 'tokenizer':
      process_text = TMTokenizer(lang).tokenizer.process(text)
    if preprocess == 'pos_tagger':
      posTag_text = TMPosTagger(lang).tag_segments([text])
      process_text = " ".join([word_pos[1] for word_pos in posTag_text[0] if len(word_pos) > 1])
    if preprocess == 'universal_pos_tagger':
      #Applied universal postagger
      process_text = TMUniversalPosTag(lang).map_universal_postagger(text)
      process_text = process_text[0]
    return process_text

  def process(self):

    dic_fuzzy = {}

    # pre-process input source
    dic_fuzzy['src_tok'] = self.pre_process(self.src_input, self.src_lang, 'tokenizer')
    dic_fuzzy['src_pos'] = self.pre_process(self.src_input, self.src_lang, 'pos_tagger')
    dic_fuzzy['src_universal'] = self.segment_2_universal(dic_fuzzy['src_tok'], dic_fuzzy['src_pos'], self.src_lang)

    for segment in self.l_best_segments:
      #pre-process each segment
      segment[0]['source_text'] = self.pre_process(segment[0]['source_text'], self.src_lang, 'tokenizer')
      # [word, pos] tm_src segment
      dic_fuzzy['src_word_pos'] = self.segment_2_universal(segment[0]['source_text'], segment[0]['source_pos'], self.src_lang)

      #In this step I knwow that elasticsearch TER segment wasn't improve with regular expression
      elastic_ter = self.ter_score(dic_fuzzy['src_tok'], segment[0]['source_text'])
      print('Elastic_ter ' + str(elastic_ter))

      #Check segments with same or similar pos tagger
      pos_ter = self.ter_score(dic_fuzzy['src_pos'], segment[0]['source_pos'])
      print(pos_ter)
      if (len(dic_fuzzy['src_pos'].split(' ')) - len(dic_fuzzy['src_word_pos']) == 0): # --> Replace or shift pos_ter == 0:
        print('Distance == 0')
        ter_by_word = self._src2src_match(dic_fuzzy['src_universal'], dic_fuzzy['src_word_pos']) # Create one structure with insert, delete and replace between input_src an tm_src
        print(ter_by_word)
        #Create a target part
        self.dic_match = self._align_source_target(ter_by_word, dic_fuzzy, segment)
        break
      if (len(dic_fuzzy['src_pos'].split(' ')) - len(dic_fuzzy['src_word_pos']) == 1):#pos_ter!=0:#(len(list(set(dic_fuzzy['src_pos']) - set(dic_fuzzy['src_word_pos']))) == 1):
        # There are insert or delete
        print('Distance == 1')
        print(segment[0]['source_text'])
        pass
        break
      else:# (len(list(set(dic_fuzzy['src_pos']) - set(dic_fuzzy['src_word_pos']))) == 1):#Not identified pos tagger pattern
        pass
        break
    return self.dic_match

  # Search correspondece between unmatch source and target
  def _align_source_target(self, ter_align, dic_fuzzy, segment):

    #[('Final', 'ADJ', 'FINAL', 'ADJ', 0), ('declaration', 'NOUN', 'ACT', 'NOUN', 'R')] --> tuple with unmatch word
    for tup in ter_align:
      if tup[4] == 'R':
        #target_word = self.score_freq_appear(tup[0], tup[1]) #Search target to replace or mark without translation
        #print(target_word)

        # Adjust tm_source
        w_src_sentence = segment[0]['source_text'].split(' ')
        pos_source = w_src_sentence.index(tup[2])
        w_src_sentence[pos_source] = tup[0]
        new_src = ' '.join(w_src_sentence)

        improve_ter = self.ter_score(dic_fuzzy['src_tok'], new_src)
        print('Improve TER ' + str(improve_ter))
        if improve_ter <= self.threshold:
          tgt_word, tgt_index = self._create_target_expression(tup, ter_align, dic_fuzzy, segment)
          w_tgt_sentence = segment[0]['target_text'].split(' ')
          w_tgt_sentence[tgt_index] = tup[0]
          segment[0]['target_text'] = ' '.join(w_tgt_sentence)

        #w_src_sentence = segment[0]['source_text'].lower().split(' ')
        #src_index = w_src_sentence.index(tup[2].lower())
        #w_src_sentence[src_index] = tup[0]
        #segment[0]['source_text'] = ' '.join(w_src_sentence)
        #improve_ter = self.ter_score(self.src_input, segment[0]['source_text'])
        #print(improve_ter)
        self.dic_match = self._create_dic_match(segment[0], improve_ter)
        break
    return self.dic_match


  # Indicate in the target expression the unmatch word (1- Using [word, pos tag] when source an target have the same pos tag, otherwise use only word) --> Search coocurrence
  def _create_target_expression(self, tup, ter_align, dic_fuzzy, segment):

    un_match_src = tup[2]

    if tup[1]==tup[3]: # Check if src_input and tm_src unmatch word have the same pos tag (Decided if use or not the pos tag to search the target unmatch word)
      pos_source = tup[1] #Contain src_input and tm_src unmatch word
      dic_target = self._dic_target_with_pos(segment, pos_source, un_match_src)
    else: #Only use the word to detect the unmatch position
      dic_target = self._dic_target_without_pos(segment)

    target_word = sorted(dic_target.items(), key=lambda item: item[1], reverse=True)[0]  # Retorn the slowest frequency of word
    return target_word[0], segment[0]['target_text'].lower().split(' ').index(target_word[0])

  # Check the ocurrences of the target words with pos tag
  def _dic_target_with_pos(self, segment, pos_source, un_match_src):
    dic_target = {}

    tgt_2_universal = ' '.join(p for w, p in self.segment_2_universal(segment[0]['target_text'], segment[0]['target_pos'], self.tgt_lang))
    tgt_2_universal_arr = tgt_2_universal.split(' ')

    indices = []

    for p in range(0, len(tgt_2_universal_arr)):  # Search all the words with the same pos pattern in tm_src, ex. NOUN
      r = re.compile(r'\b%s\b' % (pos_source)).search(tgt_2_universal_arr[p])
      if r: indices.append(p)
    print(indices)
    if indices == []: # Universal pos tag failer, then doesn't used pos
      dic_target = self._dic_target_without_pos(segment, un_match_src)
    else:
      print(indices)
      # Check ocorrences of target in the retrieve segments --> If word there isn't part of translation their occurences is slow
      for p in indices:
        target_word = segment[0]['target_text'].lower().split(' ')[p]
        dic_target[target_word] = self.target_importance(target_word, un_match_src)
    print(dic_target)
    return dic_target

  # Check the ocurrences of the target words without pos tag
  def _dic_target_without_pos(self, segment, un_match_src):
    dic_target = {}
    tgt_word = segment[0]['target_text'].split(' ')
    for w in range(0, len(tgt_word)):
      dic_target[tgt_word[w]] = self.target_importance(tgt_word[w], un_match_src)
    return dic_target

  # Check the occurence score of target words that belong to target part of the segment, with the source segment with pos tag patter like input_src
  def target_importance(self, un_word, un_match_src):
    count = 0
    for segment in self.l_best_segments:
      if (self.match_word(un_word, segment[0]['target_text']) != None) and (self.match_word(un_match_src, segment[0]['source_text']) != None):  #word with pos in tm source segments:
        count = count + 1
    return count



  # Check the occurence score between unmatch word and target words in target segments
  def score_freq_appear(self, un_word, pos_word):

    target_w_dic = {}
    for segment in self.l_best_segments:

      # Convert universal pos_tag source and target segment
      segment[0]['source_pos'] = self.segment_2_universal(segment[0]['source_text'], segment[0]['source_pos'], self.src_lang)
      segment[0]['target_pos'] = self.segment_2_universal(segment[0]['target_text'], segment[0]['target_pos'], self.tgt_lang)

      if self.match_word_pos(un_word, pos_word, segment[0]['source_pos']) != []:  # word with pos in tm source segments:
        # Create target word dictionary
        #for target in set((segment[0]['target_text'].lower()).split(' ')):
        for target_word, pos in segment[0]['target_pos']:
          target_word = target_word.lower()
          if pos == pos_word:
            if target_word in target_w_dic:
              target_w_dic[target_word] = target_w_dic[target_word] + 1
            else:
              target_w_dic[target_word] = 1
    order_target = sorted(target_w_dic.items(), key=lambda item: item[1], reverse=True)
    print(sorted(target_w_dic.items(), key=lambda item: item[1], reverse=True))
    return order_target[0][0]

  def _src2src_match(self, src_universal, src_tm_word_pos):
    len_input = len(src_universal)
    len_arr_tm = len(src_tm_word_pos)

    ter_by_word = []
    # Replace operation
    if len_input == len_arr_tm: #There are a replace
      for w in range(0, len(src_universal)):
        if self.ter_score(src_universal[w][0].lower(), src_tm_word_pos[w][0].lower()) == 0: ter_by_word.append((src_universal[w][0], src_universal[w][1], src_tm_word_pos[w][0], src_tm_word_pos[w][1], 0))
        else: ter_by_word.append((src_universal[w][0], src_universal[w][1], src_tm_word_pos[w][0], src_tm_word_pos[w][1], 'R'))
    #Delete operation
    if len_input < len_arr_tm:
      for w in range(0, len(src_tm_word_pos)):
        if w<=len_input:
          if self.ter_score(src_universal[w][0].lower(), src_tm_word_pos[w][0].lower()) == 0: ter_by_word.append((src_universal[w][0], src_universal[w][1], src_tm_word_pos[w][0], src_tm_word_pos[w][1], 0))
          else: ter_by_word.append((src_universal[w][0], src_universal[w][1], src_tm_word_pos[w][0], src_tm_word_pos[w][1], 'R'))
        else: ter_by_word.append((' ', src_tm_word_pos[w][0], src_tm_word_pos[w][1], 'D'))
    # Insert operation
    if len_input > len_arr_tm:
      for w in range(0, len(src_universal)):
        if w <= len_arr_tm:
          if self.ter_score(src_universal[w][0].lower(), src_tm_word_pos[w][0].lower()) == 0: ter_by_word.append((src_universal[w][0], src_universal[w][1], src_tm_word_pos[w][0], src_tm_word_pos[w][1], 0))
          else: ter_by_word.append((src_universal[w][0], src_universal[w][1], src_tm_word_pos[w][0], src_tm_word_pos[w][1], 'R'))
        else: ter_by_word.append((src_universal[w][0], src_universal[w][1], ' ', 'I'))
    return ter_by_word

  def segment_2_universal(self, text, pos, lang):
    word_array = text.split(' ')  # word
    pos_array = pos.split(' ')  # pos
    return self.pre_process([[[word_array[p], pos_array[p]] for p in range(0, len(word_array))]], lang, 'universal_pos_tagger')

  def match_word_pos(self, word, pos_word, segment_universal_pos):

    # print(re.compile(r'\b%s\b' % (word.lower())).search(sentence.lower()))
    # print(re.compile(r'\b%s\b' % (pos)).search(pos_sentence))
    return [x for x in segment_universal_pos if x[0].lower() == word.lower() and x[1] == pos_word]


  def match_word(self, word, sentence):

    #print(re.compile(r'\b%s\b' % (word.lower())).search(sentence.lower()))
    #print(re.compile(r'\b%s\b' % (pos)).search(pos_sentence))
    return re.compile(r'\b%s\b' % (word.lower())).search(sentence.lower())#re.compile(r'\b%s\b' % (i)).search(phrase)

    #for i in output:
    #  yield i
      #print(output)

      #
      # if elastic_ter <= self.threshold:  # Probably it is possible improve the matching value
      #   dic_fuzzy, improve_ter = self.apply_regex(segment, dic_fuzzy,
      #                                             elastic_ter)  # Apply transformations in tm source to approximate it to input_source
      #   print('improve_ter ' + str(improve_ter))
      #   if improve_ter < elastic_ter:  # Transform source and target sentence to approximate to input_source
      #     segment_transform = self.transform_apply_regex(segment, dic_fuzzy)
      #     self.dic_match = self._create_dic_match(segment_transform, improve_ter)
      #     break
      #   if improve_ter >= elastic_ter:  # Applied another transformation
      #     self.dic_match = self._create_dic_match(segment[0], elastic_ter)
      #     break
      # else:
      #   # pos_pattern
      #   self.dic_match = self.fuzzy_match_posTagger(self.l_best_segments)
      #   break
      #   # print input_source without translation
      #   break
    # return self.match_dic, improve_ter
    return self.dic_match

  def one_unmached_word(self): # Check if the difference between input_source and tm_source is only one word



    pass


if __name__ == "__main__":

  src_lang = 'en-GB'
  tgt_lang = 'es-ES'



  #logging.info(db.query("( Official Journal of the European Union L 251 of 26 September 2007 )", "en-GB", 'es-ES'))

  set_segments = ['not to be compelled to testify against themselves or to confess guilt.',
                  "The heading does not appear in the signed Second Additional Protocol, but in keeping with the Publication Office's style, it does appear in the published version (OJ L 253, 03.02.1983, p. 33).",
                  'The following paragraph shall be added in Article 48',
                  'This Decision shall enter into force on 14 December 2013, provided that all the notifications under Article 103(1) of the EEA Agreement have been made.',
                  'Consumption integral', 'No existe nada parecido a esto', 'Final declaration', 'No constitutional requirements selected.']



  for src_input in set_segments:
    print(src_input)
    tm_match = TMMatching(src_input, src_lang, tgt_lang, 'Automotive', 0.25)
    tm_match.execute()


'''



def transform_tm_source(self, segment, dic_fuzzy):

    #improve_ter = 1
    dic_process = {}
    # while improve_ter > ter: # That improve_ter would be > ter not necessary is the best solution, probably it is important to analysed others preprocess
    for p in self.pipe:

      if p == 'tokenizer':
        dic_fuzzy['tm_src_tok'] = self.pre_process(segment['source_text'], self.src_lang, 'tokenizer')

      if p == 'reg_exp':
        dic_fuzzy['tm_src_re'] = TMRegExpPreprocessor(self.src_lang).process(dic_fuzzy['tm_src_tok'])
        #self.match_dic['tm_tgt_re'] = TMRegExpPreprocessor(tgt_lang).process(segment['target_text'])

      score_ter = self.ter_score(dic_fuzzy['src_re'], dic_fuzzy['tm_src_re'])
      if score_ter <= self.threshold: # Improve after replace with regular expression

        l_bb_segments.append(dic_fuzzy)

          dic_process, improve_ter = self.check_matching_regex(dic_process, src_input, ter)  # --> Apply Substitution
        if improve_ter <= ter: break
          # else:
        if p == 'pos_pattern':
          pass

      return dic_process, improve_ter


    # Create new sources
    if first_stage_candidate != []:
      for segment in first_stage_candidate:
        print(segment[0]['source_text'])
        #Check diferences between input_source and tm_src
        dmp = diff_match_patch()
        diffs = dmp.diff_main(src_input.lower(), segment[0]['source_text'].lower())  # Identified differences
        #diffs = dmp.diff_main('match com w e com w0', 'match com w')  # Identified differences

        dmp.diff_cleanupSemantic(diffs)
        print(diffs)

        match = [tup[1].strip(' ') for tup in diffs if tup[0] == 0]
        #unmacth_tm_source = [tup[1] for tup in diffs if tup[0] == 1]
        #unmacth_source = [tup[1] for tup in diffs if tup[0] == -1]
        list_match.append(' '.join(match))
      print(list_match)
      # Generate new sources using match sequences
      l_artificial_src = list(combinations(list_match, len(dic_fuzzy['src_tok'].split(' '))))
      for each_art_src in l_artificial_src:
        artificial_src = ' '.join(each_art_src)
        if self.ter_score(dic_fuzzy['src_tok'].lower(), artificial_src) == 0:
          # align new source with target (generate target)
          self.align_source_target(' '.join(each_art_src))
          print(' '.join(each_art_src))
          break

    def align_source_target(self, artificial_source):

    for w in artificial_source.split(' '):
      target_w_dic = {}
      print(w)
      for segment in self.l_best_segments:
        if self.match_word(w, (segment[0]['source_text']))!=None: #w in set_source_word:
          # Create target word dictionary
          print(segment[0]['source_text'] + ' ' + segment[0]['source_pos'])
          print(segment[0]['target_text'].lower() + ' ' + segment[0]['target_pos'])
          for target in set((segment[0]['target_text'].lower()).split(' ')):
            if target in target_w_dic: target_w_dic[target] = target_w_dic[target] + 1
            else: target_w_dic[target] = 1
        #sorted(target_w_dic.items(), key=lambda item: item[1], reverse=True)
      print(sorted(target_w_dic.items(), key=lambda item: item[1], reverse=True))
        #print(set_target_word)

    return 0


    #iter = re.finditer(r'\b%s\b' % (pos_source), tgt_2_universal.split(' '))
    #indices = [m.start(0) for m in iter]
    #print(indices)

    #p = re.compile(pos_source)

    #m = p.search(segment[0]['target_pos']);
    #print(m.group())
    #print(m.span())

    #tagger_pattern = regex.findall(pos_source, segment[0]['target_pos'], flags=regex.BESTMATCH, overlapped=False)
    #print(tagger_pattern)
    # if len(tagger_pattern) == 1:
    #
    #   segment['target_text'] =  dic_fuzzy['tm_tgt_re'].replace(find[i], replace[i], 1)
    #
    #   self.dic_match = self._create_dic_match(segment_transform, improve_ter)
    #
    # else:




    #   tgt_word_pos = [[[tgt_word_array[p], tgt_pos_array[p]] for p in range(0, len(tgt_word_array))]]
    #   tgt_universal = self.pre_process(tgt_word_pos, self.tgt_lang, 'universal_pos_tagger')
    #   print(tgt_universal)
    #
    #   if self.match_word(un_word, (segment[0]['source_text'])) != None:  # word in set_source_word:
    #     # Create target word dictionary
    #     for target in set((segment[0]['target_text'].lower()).split(' ')):
    #       if target in target_w_dic:
    #         target_w_dic[target] = target_w_dic[target] + 1
    #       else:
    #         target_w_dic[target] = 1
    # order_target = sorted(target_w_dic.items(), key=lambda item: item[1], reverse=True)
    # print(sorted(target_w_dic.items(), key=lambda item: item[1], reverse=True))
    # return order_target[0][0]



'''