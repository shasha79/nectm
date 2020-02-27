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

import codecs
#from collections import defaultdict
from nltk.tag import map_tag

universal_pos_tag_DIR = os.path.join(os.path.abspath(os.path.join(__file__ ,"../../..")),'tools/universal-pos-tags-master')

"""
  @api {INFO} /TMUniversalPosTag TMUniversalPosTag Convert -- POS tags from various treebanks to the universal tagset (Petrov, Das, & McDonald).
  @apiName TMUniversalPosTag
  @apiVersion 0.1.0
  @apiGroup TMPosTagger


  @apiExample {curl} Input & Output:

  # Input:
    (String) language;
    (List) receive a list of sentences
  # Output:
    (List) tagged segment as a list of pairs where each pair consists of a word and tag (universal tag set)

  @apiExample {curl} Example & Notes

  # Receive a list of pairs (word and tag), annotated by TreeTagger
  Input => [[['Gasoline', 'NN'], [',', ','], ['brake', 'NN'], ['fluid', 'NN'], [',', ','], ['and', 'CC'], ['coolant', 'NN'], ['will', 'MD'], ['damage', 'VV'],
  ['the', 'DT'], ['finish', 'NN'], ['of', 'IN'], ['painted', 'JJ'], ['and', 'CC'], ['plastic', 'JJ'], ['surfaces', 'NNS'], [':', ':']]]
  Output => [[['Gasoline', 'NOUN'], [',', 'PUNCT'], ['brake', 'NOUN'], ['fluid', 'NOUN'], [',', 'PUNCT'], ['and', 'CONJ'], ['coolant', 'NOUN'], ['will', 'AUX'],
  ['damage', 'VERB'], ['the', 'DET'], ['finish', 'NOUN'], ['of', 'ADP'], ['painted', 'VERB'], ['and', 'CONJ'], ['plastic', 'ADJ'], ['surfaces', 'NOUN'], [':', 'PUNCT']]]

  # Currently, is available for English, Spanish, French and Japanese

  #TMUniversalPosTag directory is in tools/universal-pos-tags-master
  # TMUniversalPosTag class has a dictionary "maps" to specified the language and its models. The models are load on TMUniversalPosTag directory

  Converting POS tags from various treebanks to the universal tagset of Petrov, Das, & McDonald.

  The tagset consists of the following 12 coarse tags:

  VERB - verbs (all tenses and modes)
  NOUN - nouns (common and proper)
  PRON - pronouns
  ADJ - adjectives
  ADV - adverbs
  ADP - adpositions (prepositions and postpositions)
  CONJ - conjunctions
  DET - determiners
  NUM - cardinal numbers
  PRT - particles or other function words
  X - other: foreign words, typos, abbreviations
  . - punctuation

  * see: http://arxiv.org/abs/1104.2086 and http://code.google.com/p/universal-pos-tags/

  Code based on --> @author: Nathan Schneider (nschneid)
"""
class TMUniversalPosTag():

  maps = { 'EN': 'en-treetagger-pg',
           'ES': 'es-treetagger-pg',
           'FR': 'fr-treetagger-pg',
           'DE': '',
           'IT': '',  # italian
           'PT': '',  # portuguese
           'PL': '',  # polish
           'RU': '',  # russian
           #'BG': 'bg-btb',  # bulgarian
           'NL': '',  # dutch
           'ET': '',  # estonian
           'FI': '',  # finnish
           'CR': '',  # korean
           'JA': 'ja-kytea-pg', # Japanese
           'ZH': 'zh-ctb6',  # chinese
           'AR': '',
           'HE': '',  # hebreu
           'SK': '',  # Slovak
          }

  def __init__(self, language):

    self.map = self.maps.get(language.upper())
    if not self.map: raise (Exception("Unsupported language for map universal POS tagging: {}".format(language)))

  def map_universal_postagger(self, tag_sentence):
    #return [[[word, map_tag(self.map, 'universal', tag)] for word, tag in sentence] for sentence in tag_sentence]
    return [[[word[0], map_tag(self.map, 'universal', word[1])] for word in sentence if len(word)==2] for sentence in tag_sentence]

  #Method to call unversal pos tag without nltk
  '''
    def __init__(self, language):

      #Create a dictionary with pos-tags by language

      self.map = self.maps.get(language.upper())
      COARSE_TAGS = ('VERB', 'NOUN', 'PRON', 'ADJ', 'ADV', 'ADP', 'CONJ', 'DET', 'NUM', 'PRT', 'X', '.')
      if not map: raise (Exception("Unsupported language for Universal PosTagger: {}".format(language)))
      self.dicMap = defaultdict(dict)

      with open(universal_pos_tag_DIR + '/' + self.map) as f:
        for line in f:
          line = line.strip()
          if line == '': continue
          fine, coarse = line.split('\t')
          assert coarse in COARSE_TAGS, 'Unexpected coarse tag: {}'.format(coarse)
          assert fine not in self.dicMap, 'Multiple entries for original tag: {}'.format(fine)
          self.dicMap[fine] = coarse

  def map_tag_tm(self, tag):
    if tag in self.dicMap.keys():
      tag = self.dicMap[tag]
    return tag

  def map_universal_postagger(self, tag_sentence):
    return [[[word[0], self.map_tag_tm(word[1])] for word in sentence if len(word)==2] for sentence in tag_sentence]
  '''





if __name__=='__main__':

    args = parse_args()

    text = [[('When', 'WRB'), ('the', 'DT'), ('motorcycle', 'NN'), ('is', 'VBZ'), ('to', 'TO'), ('be', 'VB'), ('stored', 'VVN'),
            ('for', 'IN'), ('any', 'DT'), ('length', 'NN'), ('of', 'IN'), ('time', 'NN'), (',', ','), ('it', 'PP'), ('should', 'MD'),
            ('be', 'VB'), ('prepared', 'VVN'), ('for', 'IN'), ('storage', 'NN'), ('as', 'RB'), ('follows', 'VVZ'), (':', ':')], \
           [('Run', 'VV'), ('the', 'DT'), ('engine', 'NN'), ('for', 'IN'), ('about', 'RB'), ('five', 'CD'), ('minutes', 'NNS'),
            ('to', 'TO'), ('warm', 'VV'), ('the', 'DT'), ('oil', 'NN'), (',', ','), ('shut', 'VVD'), ('it', 'PP'), ('off', 'RP'),
            ('and', 'CC'), ('drain', 'VV'), ('the', 'DT'), ('engine', 'NN'), ('oil', 'NN'), ('.', 'SENT')]]

    dic = UniversalPosTag('ES')
    print(dic.dicMap)

    #Search tag not exist in map file
    f = codecs.open(args.file, 'r')
    data = f.read().replace('\n', '')
    print(type(eval(data)))

    existItem = {}
    nonExistItem = {}
    for sentence in eval(data):
      #print(sentence)
      posTag_seq = [word[1] for word in sentence]
      #print(' '.join(posTag_seq))

      #posTag_seq = posTag_seq#.split()
      for item in posTag_seq:
        if item in dic.dicMap.keys():
          if item in existItem.keys():
            existItem[item] = existItem[item] + 1
          else:
            existItem[item] = 1
        else:
          if item in nonExistItem.keys():
            nonExistItem[item] = nonExistItem[item] + 1
          else:
            nonExistItem[item] = 1
    print('****EXIST*****')
    print(existItem)
    print('****NON EXIST*****')
    print(nonExistItem)


