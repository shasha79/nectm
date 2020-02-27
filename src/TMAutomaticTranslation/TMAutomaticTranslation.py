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
import logging
from TMAutomaticTranslation.BingTranslator import BingTranslator
from TMAutomaticTranslation.NeuralMtTranslator import NeuralMtTranslator
from TMAutomaticTranslation.PangeaMtTranslator import PangeaMtTranslator
from Config.ConfigMTEngines import ENGINE_CONFIG


class TMAutomaticTranslation:

  translators = {'bing': BingTranslator,
                 'neuralmt': NeuralMtTranslator,
                 'pangeamt': PangeaMtTranslator}
  engines = dict()

  def __init__(self, src_lang, tgt_lang, mt_engine):
    self.src_lang = src_lang
    self.tgt_lang = tgt_lang
    self.translator = mt_engine

  @staticmethod
  def get_engine(src_lang, tgt_lang, domain):
    if not domain: domain = ""
    key = "{}-{}-{}".format(src_lang, tgt_lang, domain)
    if not key in TMAutomaticTranslation.engines:
      engine_config = TMAutomaticTranslation.get_engine_config(src_lang, tgt_lang, domain)
      logging.info("Loading translation engine for: {}, config: {}".format(key, engine_config))
      TMAutomaticTranslation.engines[key] = TMAutomaticTranslation(src_lang, tgt_lang,
                                                                   TMAutomaticTranslation.translators[engine_config['engine']](**engine_config))
    return TMAutomaticTranslation.engines[key]

  # Get engine configuration
  @staticmethod
  def get_engine_config(src_lang, tgt_lang, domain):
    mt_domain = 'any' if not domain else domain
    config = ENGINE_CONFIG.get_engine_config(src_lang, tgt_lang, mt_domain)
    return config

  # Translate a list of segments. Receive a list of segments and return a list of translated segments
  def translate(self, str_or_list):
    return self.translator.translate(str_or_list, self.tgt_lang, self.src_lang)



if __name__ == "__main__":
  bt = TMAutomaticTranslation('en', 'es')
  print(bt.translate(["What is your name?", "Who are you?"]))
  print(bt.translate("What is your name?"))
