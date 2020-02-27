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
sys.path.insert(0, sys.path.append(os.path.dirname(__file__)))

'''
Dealing with no UUID serialization support in json
'''
from json import JSONEncoder
from uuid import UUID
import datetime
JSONEncoder_olddefault = JSONEncoder.default
def JSONEncoder_newdefault(self, o):
    if isinstance(o, UUID): return str(o)
    if isinstance(o, datetime.datetime): return str(o)
    if isinstance(o, datetime.date): return o.strftime('%m/%d/%Y')
    if isinstance(o, (list, tuple)): return str(o)
    try:
      enc = JSONEncoder_olddefault(self, o)
    except:
      enc = str(o)
    return enc
JSONEncoder.default = JSONEncoder_newdefault

import TMMapES

# Factory method
def create(engine):
  # FIXME: figure
  engine_map = {
    'elasticsearch': TMMapES.TMMapES,
  }
  if not engine in engine_map:
    raise (Exception('Unsupported MapDB engine: {}, supported ones are {}'.format(engine, engine_map.keys())))

  return engine_map[engine]()
