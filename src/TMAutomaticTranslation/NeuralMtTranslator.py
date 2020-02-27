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
import requests
import logging
import json
import sys
from TMAutomaticTranslation.Translator import Translator

from Config.ConfigMTEngines import ENGINE_CONFIG

class NeuralMtTranslator(Translator):

  def __init__(self, **kwargs):
    config = ENGINE_CONFIG.get_engine('neuralmt')
    self.URL = config['url']
    self.TOKEN = config['token']

    self.flavor = kwargs.get('flavor')

  def translate_batch(self, text_list, to_lang, from_lang=None):
    ttext = None
    i = 0
    while not ttext and i < 2:
      ttext = self._translate(text_list, to_lang=to_lang, from_lang=from_lang)
      # If translation is empty, try again
      if not ttext:
        i += 1
    if not ttext: return None
    out_list = [t[0]["tgt"] for t in ttext]
    if len(out_list) == len(text_list):
      return out_list
    return None

  def _translate(self, text_list, to_lang, from_lang):
    params = {"src": from_lang,
              "tgt": to_lang,
              "text": text_list,
              "flavor": self.flavor}
    try:
      result = requests.post(self.URL + "/api/v1/translator/translate",
                            headers={"Content-Type": "application/json",
                                     "Authorization" : "JWT {}".format(self.TOKEN)},
                            data=json.dumps(params))
    except:
      logging.info("NeuralMT: failed to translate: {}, reason: {}".format(text_list, sys.exc_info()[1]))
      return None
    return json.loads(result.content.decode('utf-8'))