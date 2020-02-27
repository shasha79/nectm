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
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..'))
sys.path = [p for p in sys.path if p]

from TMPosTagger.TMTreeTagger import TMTreeTagger
from TMPosTagger.TMStanfordPosTagger import TMStanfordPOSTagger
from TMPosTagger.TMJapanesePosTagger import TMMyKyteaTagger
from TMPosTagger.TMUniversalPosTag import TMUniversalPosTag
from TMPosTagger.TMRDRPOSTagger import TMRDRPOSTagger

#stanford_posTagger_home = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'stanford-postagger-full-2015-12-09')

"""
  @api {INFO} /TMPosTagger TMPosTagger -- Class to initialize the available POS Tagger models
  @apiName TMPostagger
  @apiVersion 0.1.0
  @apiGroup TMPosTagger

  @apiExample {curl} Input & Output:

  # Input: (String) language
  # Output: (Object) model for pos tagging annotation
  # Error: Unsupported unsupported language for POS tagging.
  * The error messages appear on uwsgi.log

  @apiExample {curl} Example & Notes:

  To include new pos tagging model for other languages

  # Define the model for new language
  tools = {'EN' : 'treetagger',
            'DE': 'multilingual',
             'HH': 'posTaggerTemplate'}

  # Create the class to execute the new model
  if tool == 'posTaggerTemplate':
    self.tagger = TMPOSTaggerTemplate(language.upper())
  # All the models must implement a function "tag_segments(self, texts)" for pos tagging.
  # Before pos tagging the input sentences are tokenized

  * See the file TMPOSTaggerTemplate template to add other posTagger
"""
class TMPosTagger:
    # Available POS Tagger models. TODO: fill entries for other languages

    tools = {'EN' : 'treetagger',
              'ES' : 'treetagger',
              'FR': 'treetagger',
              'DE': 'multilingual',
              'IT': 'multilingual', #italian --> treetagger
              'PT': 'multilingual', #portuguese
              'PL': 'multilingual',  # polish --> treetagger
              'RU': 'multilingual',  # russian
              'BG': 'multilingual',  #bulgarian -- treetagger
              'NL': 'multilingual',  #dutch  --> treetagger
              'ET': 'multilingual',  #estonian --> treetagger
              'FI': 'multilingual',  #finnish --> treetagger
              'CR': 'KoNLPy',  #korean
              'JA': 'Kytea',  #Japanese
              'ZH': 'multilingual',#'stanford',  # chinese
              'AR': 'multilingual',
             'HE': 'multilingual', #hebreu
              'CS': 'multilingual', # Czech
              'NO': 'multilingual',  # norwegian
             'SV': 'multilingual',  # swedish
             'HU': 'multilingual',  # hungarian
             'LV': 'multilingual',  # Latvian
             'RO': 'multilingual',  # Romanian
             'SK': 'treetagger',  # Slovak   --> Not in multilingual and there aren't universal match
             'EL': 'multilingual',  # greek
             'DA': 'multilingual',  # danish
             'SL': 'multilingual',  # slovene --> treetagger
             'GA': 'multilingual',  # Irish
             #'HR': 'multilingual',  # Croatian
             # 'LT': 'multilingual',  # Lithuanian
             # 'MT': 'multilingual',  # Maltese
             # 'IS': 'multilingual',  # Icelandic

             }

    def __init__(self, language, universal=None):
      tool = self.tools.get(language.upper())
      self.universal = universal
      self.language = language

      if not tool: raise(Exception("Unsupported language for POS tagging: {}".format(language)))
      if tool == 'stanford':
      # Initialize Stanford POS tagger
        self.tagger = TMStanfordPOSTagger(language.upper())
      # Initialize TreeTagger
      if tool == 'treetagger':
        self.tagger = TMTreeTagger(language.lower())
      # Initialize MeCab
      if tool == 'Kytea':
        self.tagger = TMMyKyteaTagger()
      if tool == 'multilingual':
        self.tagger = TMRDRPOSTagger(language.upper())

    # Store tagged segment as a list of pairs where each pair consists of a word and tag,
    # e.g. "There is a problem => [['There', 'EX'], ['is', 'VBZ'], ['a', 'DT'], ['problem', 'NN']]
    def tag_segments(self, segments):
      sents_tagged = self.tagger.tag_segments(segments) #PosTagger
      if self.universal: #Universal by default
        #Inizialize universalMap
        map_universal = TMUniversalPosTag(self.language)
        sents_tagged = map_universal.map_universal_postagger(sents_tagged)
        #sents_tagged = self.tagger.tag_segments(segments)
      return sents_tagged

    def get_lang_using_universal(self):
      return [lang for lang, pos in self.tools.items() if pos == 'multilingual']

    # def tag_segments(self, segments):
    #
    #   src_sents_tagged = self.tagger[self.src_lang].tag_segments([(s.source_text) for s in segments])
    #   tgt_sents_tagged = self.tagger[self.tgt_lang].tag_segments([(s.target_text) for s in segments])
    #
    #   for (segment, src, tgt) in zip(segments, src_sents_tagged, tgt_sents_tagged):
    #       segment.source_text_pos = src
    #       segment.target_text_pos = tgt
    #
    #   return segments

