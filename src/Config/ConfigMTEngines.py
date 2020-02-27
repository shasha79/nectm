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
import yaml
import collections


class ConfigMTEngines:
  configMT_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', 'conf', 'enginemt.yml')
  configMT = dict()
  is_loaded = False

  def __init__(self):
    self.configMT = dict()

    if not self.is_loaded:
      self.load(self.configMT_path)
      self.is_loaded = True

  def load(self, conf_file):
    with open(conf_file, 'r') as ymlfile:
      self.configMT = yaml.load(ymlfile)
      self.is_loaded = True

  #OrderedDict([('rule-1', {'target': 'es', 'domain': 'GERAL', 'source': 'en', 'script': 'template1.sh'}),
  #             ('rule-2', {'target': 'any', 'domain': 'any', 'source': 'en', 'script': 'template2.sh'}),
  #             ('rule-3', {'target': 'any', 'domain': 'any', 'source': 'es', 'script': 'template2.sh'})])

  def get_engine_config(self, src_lang=None, tgt_lang=None, in_domain=None):  # domain can be a list, a string or None
    d_domain = dict()
    if isinstance(in_domain, str): in_domain = [in_domain]  # only one domain

    engines = self.configMT.get("engines")
    if not engines: return []

    for rule in engines:
      if (rule['source'] == src_lang or rule['source'] == 'any') and \
        (rule['target'] == tgt_lang or rule['target'] == 'any') and \
        (rule['domain'] in in_domain or rule['domain'] == 'any'):
        d_domain = rule
        break
    return d_domain  # return the sript of the input domain

  def get_engine(self, engine):
    return self.configMT.get(engine)

# Global config
ENGINE_CONFIG = ConfigMTEngines()

if __name__ == "__main__":
  print(ENGINE_CONFIG.configMT)
  print(ENGINE_CONFIG.get_engine_script())
