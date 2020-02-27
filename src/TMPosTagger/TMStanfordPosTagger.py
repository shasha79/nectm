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
#sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))

from nltk.tag import StanfordPOSTagger

from TMPosTagger.TMTokenizer import TMTokenizer # --> To outside the package use this import

stanford_posTagger_home = os.path.join(os.path.abspath(os.path.join(__file__ ,"../../..")),'tools/stanford-postagger-full-2015-12-09')


"""
  @api {INFO} /TMStanfordPOSTagger TMStanfordPOSTagger
  @apiName TMStanfordPOSTagger
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
  Output => [[['Gasoline', 'NN'], [',', ','], ['brake', 'NNP'], ['fluid', 'NN'], [',', ','], ['and', 'CC'], ['coolant', 'NN'], ['will', 'MD'], ['damage', 'VB'], ['the', 'DT'],
  ['finish', 'NN'], ['of', 'IN'], ['painted', 'JJ'], ['and', 'CC'], ['plastic', 'JJ'], ['surfaces', 'NNS'], [':', ':']]]

  #StanfordPOSTagger directory is in tools/stanford-postagger-full-2015-12-09
  #TMStanfordPOSTagger class has a dictionary "models" to specified the language and its models. The models are load on StanfordPOSTagger directory
  * See TMStanfordPOSTagger constructor
"""


class TMStanfordPOSTagger:
  # Available Stanford POS models. TODO: fill entries for other languages
  models = {'EN': 'english-bidirectional-distsim.tagger',
            'ES': 'spanish.tagger',
            'FR': 'french.tagger',
            'DE': 'german-fast.tagger',
            'ZH': 'chinese-distsim.tagger',
            'AR': 'arabic.tagger'
            }

  def __init__(self, language):

    self.language = language
    model = self.models.get(language)
    if not model: raise (Exception("Unsupported language for POS tagging: {}".format(language)))
    # Initialize Stanford POS tagger
    self.st = StanfordPOSTagger(os.path.join(stanford_posTagger_home, 'models', model),
                                          os.path.join(stanford_posTagger_home, 'stanford-postagger.jar'))
    self.preprocessor = TMTokenizer(language)

  def tag_segments(self, texts):

    #Stanford PosTagger receive a list of word.
    tok_sents = [self.preprocessor.tokenizer.process(s).split(' ') for s in texts]
    target_sents = [[[tag.split('#')[0], tag.split('#')[1]] for word, tag in sentence] for sentence in self.st.tag_sents(tok_sents)]
    return target_sents

  #Pos tagger without tokenizer
  def only_tag_segments(self, texts):
    return [[[word, tag] for word, tag in sentence] for sentence in self.st.tag_sents(texts)]#[[element for element in self.st.tag(text.split(' '))] for text in texts]#self.st.tag(s.split('') for s in texts) #

if __name__ == "__main__":
  en = ['Gasoline, brake fluid, and coolant will damage the finish of painted and plastic surfaces:', \
        'Vinyl parts should be washed with the rest of the motorcycle and then treated with a vinyl treatment.',
        'Install the engine oil drain plug and fill in fresh engine oil.',
        'The fuel will deteriorate if left for a long time',
        'A mediator is not needed, an official told the Reuters news agency, an official told the Reuters news agency.']
  es = [
    'La gasolina, el líquido de frenos y el refrigerante dañarán el acabado de las superficies pintadas y plásticas:',
    'Las piezas de vinilo deben lavarse con el resto de la motocicleta y se les debe aplicar posteriormente un tratamiento para vinilo.',
    'Monte el tapón de drenaje de aceite del motor y rellene con aceite de motor nuevo.',
    'El combustible se deteriora si se deja durante mucho tiempo en la motocicleta.',
    'Un mediador no es necesario, dijo un oficial de la agencia de notícias Reuters.']

  s = TMStanfordPOSTagger('EN')
  s.tag_segments(en)

  s = TMStanfordPOSTagger('ES')
  s.tag_segments(es)
