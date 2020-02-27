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

import treetaggerwrapper

from TMPosTagger.TMTokenizer import TMTokenizer

treetagger_posTagger_home = os.path.join(os.path.abspath(os.path.join(__file__ ,"../../..")),'tools/tree-tagger-linux-3.2')

"""
  @api {INFO} /TMTreeTagger TreeTagger
  @apiName TMTreeTagger
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
  Output => [[['Gasoline', 'NN'], [',', ','], ['brake', 'NN'], ['fluid', 'NN'], [',', ','], ['and', 'CC'], ['coolant', 'NN'], ['will', 'MD'],
  ['damage', 'VV'], ['the', 'DT'], ['finish', 'NN'], ['of', 'IN'], ['painted', 'JJ'], ['and', 'CC'], ['plastic', 'JJ'], ['surfaces', 'NNS'], [':', ':']]]

  #TreeTagger directory is in tools/tree-tagger-linux-3.2
  # TMTreeTagger instantiates the model for each language using a python class. See the TMTreeTagger constructor
"""

class TMTreeTagger():

  def __init__(self, language):

    self.tagger = treetaggerwrapper.TreeTagger(TAGLANG = language.lower(), TAGDIR = treetagger_posTagger_home)
    self.preprocessor = TMTokenizer(language.upper())

  def tag_segments(self, texts):
    # Store tagged segment as a list of pairs where each pair consists of a word and tag,
    # e.g. "There is a problem => [['There', 'EX'], ['is', 'VBZ'], ['a', 'DT'], ['problem', 'NN']]
    tok_sents = [self.preprocessor.tokenizer.process(s) for s in texts]
    return [[element.split('\t')[:2] for element in self.tagger.tag_text(text)] for text in tok_sents ]

    # Pos tagger without tokenizer
  def only_tag_segments(self, texts):
    return [[element.split('\t')[:2] for element in self.tagger.tag_text(text)] for text in texts]


if __name__ == "__main__":

  pt = 'Olá mundo maravilhoso e perfeito!'
  it = ['Ciao meraviglioso e perfetto mondo!', 'Ciao meraviglioso.']
  ru = ['Привет прекрасный и совершенный мир!', 'Привет замечательно.']
  fi = ['Hei ihana ja täydellinen maailma!', 'Hei hienoa.']
  bg = ['Здравейте прекрасен и съвършен свят!', 'Здравейте прекрасно.']
  pl = ['Witam wspaniały i doskonały świat!', 'Witam wspaniały.']
  nl = ['Hallo prachtig en perfecte wereld!', 'Hallo geweldig.']
  et = ['Tere imeline ja täiuslik maailm!', 'Tere imeline.']
  en = ['There is a big problem.']

  treeTagger = TMTreeTagger('EN')
  print(treeTagger.tag_segments(en))

  treeTagger = TMTreeTagger('IT')
  treeTagger.tag_segments(it)

  treeTagger = TMTreeTagger('RU')
  treeTagger.tag_segments(ru)

  treeTagger = TMTreeTagger('FI')
  treeTagger.tag_segments(fi)

  treeTagger = TMTreeTagger('BG')
  treeTagger.tag_segments(bg)

  treeTagger = TMTreeTagger('PL')
  treeTagger.tag_segments(pl)

  treeTagger = TMTreeTagger('NL')
  treeTagger.tag_segments(nl)

  treeTagger = TMTreeTagger('ET')
  treeTagger.tag_segments(et)