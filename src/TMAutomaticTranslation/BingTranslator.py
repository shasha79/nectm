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
from TMAutomaticTranslation.Translator import Translator
import microsofttranslator

from Config.ConfigMTEngines import ENGINE_CONFIG

class BingTranslator(Translator):

  def __init__(self, **kwargs):
    self.KEY = ENGINE_CONFIG.get_engine('bing')['key']
    self.token = None
    self.translator = microsofttranslator.Translator(None, None) # ignore old client api/id

  def get_access_token(self):
    token = requests.post('https://api.cognitive.microsoft.com/sts/v1.0/issueToken',
                      headers={'Ocp-Apim-Subscription-Key': self.KEY}).content
    return token.decode('utf-8')

  def translate_batch(self, text_list, to_lang, from_lang=None):
    # Initial token
    if not self.token:
      self.token = self.get_access_token()

    ttext = None
    i = 0
    while not ttext and i < 2:
      ttext = self._translate(text_list, to_lang=to_lang, from_lang=from_lang)
      # If translation is empty, most likely token has expired - refresh it and try translating again
      if not ttext:
        self.token = self.get_access_token()
        i += 1
    if not ttext: return None
    out_list = [t["TranslatedText"] for t in ttext]
    if len(out_list) == len(text_list):
      return out_list
    return None

  def _translate(self, text_list, to_lang, from_lang):
    self.translator.access_token = self.token
    try:
      result = self.translator.translate_array(text_list, to_lang=to_lang, from_lang=from_lang)
    except:
      logging.info("Bing: failed to translate: {}".format(text_list))
      result=None
    return result