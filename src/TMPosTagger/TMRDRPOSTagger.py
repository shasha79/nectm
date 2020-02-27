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

cwd = os.getcwd()
from tools.RDRPOSTagger.pSCRDRtagger.RDRPOSTagger import RDRPOSTagger
from Utility.Utils import readDictionary
# Workaround for RDRPOSTagger changing current directory (sic!!) during import
os.chdir(cwd)
#from TMPosTagger.TMTokenizer import TMTokenizer

multilingual_posTagger_home = os.path.join(os.path.abspath(os.path.join(__file__,"../../../")), 'tools/RDRPOSTagger/Models')


'''
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

@see: http://arxiv.org/abs/1104.2086 and http://code.google.com/p/universal-pos-tags/

Code based on --> @author: Nathan Schneider (nschneid)
'''

"""
  @api {INFO} /TMRDRPOSTagger -- TMRDRPOSTagger Based on the universal tagset
  @apiName TMRDRPOSTagger
  @apiVersion 0.1.0
  @apiGroup TMPosTagger

  @apiExample {curl} Input & Output:

  # Input:
    (String) language;
    (List) receive a list of sentences
  # Output:
    (List) tagged segment as a list of pairs where each pair consists of a word and tag

  @apiExample {curl} Example & Notes

  Input => ['Gasoline, brake fluid, and coolant will damage the finish of painted and plastic surfaces:']
  Output => [[['Gasoline', 'NOUN'], [',', 'PUNCT'], ['brake', 'NOUN'], ['fluid', 'NOUN'], [',', 'PUNCT'], ['and', 'CONJ'], ['coolant', 'NOUN'], ['will', 'AUX'],
  ['damage', 'VERB'], ['the', 'DET'], ['finish', 'NOUN'], ['of', 'ADP'], ['painted', 'VERB'], ['and', 'CONJ'], ['plastic', 'ADJ'], ['surfaces', 'NOUN'], [':', 'PUNCT']]]

  #TMRDRPOSTagger directory is in tools/RDRPOSTagger
  #TMRDRPOSTagger class has a dictionary "models" to specified the language and its models. The models are load on TMRDRPOSTagger directory
  * See TMRDRPOSTagger constructor
"""

class TMRDRPOSTagger():
  models = {'EN': 'UniPOS/UD_English/train.UniPOS.RDR', #specific tag set
            'DE': 'UniPOS/UD_German/train.UniPOS.RDR',
            'ZH': 'UniPOS/UD_Chinese/train.UniPOS.RDR', #universal tag set
            'RU': 'UniPOS/UD_Russian-SynTagRus/train.UniPOS.RDR', #universal tag set
            'HE': 'UniPOS/UD_Hebrew/train.UniPOS.RDR', #universal tag set
            'AR': 'UniPOS/UD_Arabic/train.UniPOS.RDR',
            'CS': 'UniPOS/UD_Czech/train.UniPOS.RDR',  # Czech
            'NO': 'UniPOS/UD_Norwegian/train.UniPOS.RDR',  # norwegian
            'SV': 'UniPOS/UD_Swedish/train.UniPOS.RDR',  # swedish
            'HU': 'UniPOS/UD_Hungarian/train.UniPOS.RDR',  # hungarian
            'LV': 'UniPOS/UD_Latvian/train.UniPOS.RDR',  # Latvian
            'RO': 'UniPOS/UD_Romanian/train.UniPOS.RDR',  # Romanian
            'EL': 'UniPOS/UD_Greek/train.UniPOS.RDR',  # greek
            'DA': 'UniPOS/UD_Danish/train.UniPOS.RDR',  # danish
            'GA': 'UniPOS/UD_Irish/train.UniPOS.RDR',  # Irish
            'PT': 'UniPOS/UD_Portuguese/train.UniPOS.RDR',  # European Portuguese

            'IT': 'UniPOS/UD_Italian/train.UniPOS.RDR',#'POS/Italian.RDR',  # italian
            'PL': 'UniPOS/UD_Polish/train.UniPOS.RDR',  #polish
            'NL': 'UniPOS/UD_Dutch/train.UniPOS.RDR',  # dutch
            'ET': 'UniPOS/UD_Estonian/train.UniPOS.RDR',  # estonian
            'FI': 'UniPOS/UD_Finnish/train.UniPOS.RDR',  # #finnish
            'SL': 'UniPOS/UD_Slovenian/train.UniPOS.RDR',  # slovene
            'BG': 'UniPOS/UD_Bulgarian/train.UniPOS.RDR',  # bulgarian

            # 'LT': 'multilingual',  # Lithuanian
            # 'MT': 'multilingual',  # Maltese
            # 'IS': 'multilingual',  # Icelandic
            }

  dicts = { 'EN': 'UniPOS/UD_English/train.UniPOS.DICT',
            'DE': 'UniPOS/UD_German/train.UniPOS.DICT',#'POS/German.DICT',
            'ZH': 'UniPOS/UD_Chinese/train.UniPOS.DICT',
            'RU': 'UniPOS/UD_Russian-SynTagRus/train.UniPOS.DICT',
            'HE': 'UniPOS/UD_Hebrew/train.UniPOS.DICT',
            'AR': 'UniPOS/UD_Arabic/train.UniPOS.DICT',
            'CS': 'UniPOS/UD_Czech/train.UniPOS.DICT',  # Czech
            'NO': 'UniPOS/UD_Norwegian/train.UniPOS.DICT',  # norwegian
            'SV': 'UniPOS/UD_Swedish/train.UniPOS.DICT',  # swedish
            'HU': 'UniPOS/UD_Hungarian/train.UniPOS.DICT',  # hungarian
            'LV': 'UniPOS/UD_Latvian/train.UniPOS.DICT',  # Latvian
            'RO': 'UniPOS/UD_Romanian/train.UniPOS.DICT',  # Romanian
            'EL': 'UniPOS/UD_Greek/train.UniPOS.DICT',  # greek
            'DA': 'UniPOS/UD_Danish/train.UniPOS.DICT',  # danish
            'GA': 'UniPOS/UD_Irish/train.UniPOS.DICT',  # Irish
            'PT': 'UniPOS/UD_Portuguese/train.UniPOS.DICT',  # European Portuguese

            'IT': 'UniPOS/UD_Italian/train.UniPOS.DICT',#'POS/Italian.DICT', # italian
            'PL': 'UniPOS/UD_Polish/train.UniPOS.DICT', #polish
            'NL': 'UniPOS/UD_Dutch/train.UniPOS.DICT', # dutch
            'ET': 'UniPOS/UD_Estonian/train.UniPOS.DICT', #estonian
            'FI': 'UniPOS/UD_Finnish/train.UniPOS.DICT', #finnish
            'SL': 'UniPOS/UD_Slovenian/train.UniPOS.DICT', # slovene
            'BG': 'UniPOS/UD_Bulgarian/train.UniPOS.DICT',  # bulgarian

            # 'LT': 'multilingual',  # Lithuanian
            # 'MT': 'multilingual',  # Maltese
            # 'IS': 'multilingual',  # Icelandic
            }

  def __init__(self, language):
    self.language = language

    model = self.models.get(language)
    lexicon = self.dicts.get(language)
    if not model: raise (Exception("Unsupported language for POS tagging: {}".format(language)))

    self.tagger = RDRPOSTagger()

    # Load the POS tagging model for X language
    self.tagger.constructSCRDRtreeFromRDRfile(os.path.join(multilingual_posTagger_home, model))

    # Load the lexicon for X language
    self.dict = readDictionary(os.path.join(multilingual_posTagger_home, lexicon))

    # Inicialize Tokenizer for X language
    #self.preprocessor = TMTokenizer(language)


  def tag_segments(self, texts):
    # ****Output --> [[['There', 'EX'], ['is', 'VBZ'], ['a', 'DT'], ['big', 'JJ'], ['problem', 'NN'], ['.', '.']],
    # [['There', 'EX'], ['are', 'VBP'], ['another', 'DT'], ['important', 'JJ'], ['problem', 'NN'], ['.', '.']]]
      #tok_sents = [self.preprocessor.tokenizer.process(s) for s in texts] #Return a list
      return [[[element.split('/')[0],element.split('/')[1]] for element in self.tagger.tagRawSentence(self.dict, s).split(' ')] for s in texts]#target_sents

  # Pos tagger without tokenizer
  def only_tag_segments(self, texts):
    return [[[element.split('/')[0], element.split('/')[1]] for element in
             self.tagger.tagRawSentence(self.dict, s).split(' ')] for s in texts]
