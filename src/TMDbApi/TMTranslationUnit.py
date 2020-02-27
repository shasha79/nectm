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
import uuid


class TMTranslationUnit:
  attributes = ['source_text', 'target_text',
                'source_id', 'target_id',
                'source_language', 'target_language',
                'source_metadata', 'target_metadata', 'metadata',
                'source_pos', 'target_pos',
                'tuid', 'dirty_score', 'username',
                'industry', 'type', 'file_name', 'domain', 'organization',
                'tm_creation_date', 'tm_change_date',
                'insert_date', 'update_date', 'check_date', 'check_version']
  def __init__(self, sdict={}):
    self.reset(sdict)

  def reset(self, sdict):
    # Initialize segment fields
    for attr in self.attributes:
      val = None if not attr in sdict else sdict[attr]
      setattr(self, attr, val)
    # allocate ids
    self._allocate_id('source')
    self._allocate_id('target')

  def _allocate_id(self, type):
    text = getattr(self, type + '_text')
    if text:
      setattr(self, type + '_id', uuid.uuid5(uuid.NAMESPACE_URL, text))

  def to_dict(self):
    return dict([(a, getattr(self, a)) for a in self.attributes])

  def to_dict_short(self):
    return dict([(a, getattr(self, a)) for a in ['source_text', 'target_text', 'source_metadata', 'target_metadata'] if getattr(self, a)])
