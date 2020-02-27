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
import sys
sys.path.append("..")
import logging
import json

from TMDbApi.TMTranslationUnit import TMTranslationUnit
from TMOutputer.TMOutputer import TMOutputer

class TMOutputerJson(TMOutputer):

  def output_segment(self, segment):
    return json.dumps(segment.to_dict())

'''
Dealing with no UUID serialization support in json
'''
from json import JSONEncoder
from uuid import UUID
JSONEncoder_olddefault = JSONEncoder.default
def JSONEncoder_newdefault(self, o):
    if isinstance(o, UUID): return str(o)
    return JSONEncoder_olddefault(self, o)
JSONEncoder.default = JSONEncoder_newdefault

if __name__ == "__main__":
  logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

  tmout = TMOutputerJson()
  #tmdb.init_db()
  segment = TMTranslationUnit({
             "source_text": "Connect the pipe to the female end of the T.",
             "source_lang": "en-GB",
             "target_text": "Conecte la tubería al extremo hembra de la T.",
             "target_lang": "es-ES",
             "creation_date" : "20090914T114332Z",
             "change_date" : "20090914T114332Z",
             "industry": "Automotive Manufacturing",
             "type": "Instructions for Use",
             "organization":"Pangeanic"
             })
  print(tmout.output_segment(segment))

