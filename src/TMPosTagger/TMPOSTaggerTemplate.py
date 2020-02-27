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
'''
import os

from TMPosTagger.TMTokenizer import TMTokenizer

# Import the new posTagger

# If posTagger is external tool, definied tool directory
#template_posTagger_home =

class TMPOSTaggerTemplate:
  # Available Stanford POS models. TODO: fill entries for other languages

  def __init__(self, language):

    self.language = language

    # Initialize Template POS tagger
    #self.template =
    self.preprocessor = TMTokenizer(language)

  def tag_segments(self, texts):

    tag_text =
    return tag_text

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

  s = TMPOSTaggerTemplate('EN')
  s.tag_segments(en)

'''