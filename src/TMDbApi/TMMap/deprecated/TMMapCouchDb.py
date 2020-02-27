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
import couchdb
import uuid

from TMDbApi.TMMap.TMMap import TMMap
from TMDbApi.TMUtils import TMUtils

# ID map implementation based on MongoDB
class TMMapCouchDb(TMMap):
  def __init__(self):
    self.server = couchdb.Server()

  def add_segment(self, segment):
    m_index = TMUtils.es_index2mapdb(TMUtils.lang2es_index(segment.source_lang),
                                     TMUtils.lang2es_index(segment.target_lang))
    return self.server[m_index].update([self._segment2doc(segment)])


  def add_segments(self, segments):
    if not segments:
      return
    m_index = TMUtils.es_index2mapdb(TMUtils.lang2es_index(segments[0].source_lang),
                                     TMUtils.lang2es_index(segments[0].target_lang))
    try:
      db = self.server[m_index]
    except:
      db = self.server.create(m_index)

    return db.update([self._segment2doc(s) for s in segments])

  def _segment2doc(self, segment):
    doc = super()._segment2doc(segment)
    doc['_id'] = segment.source_id.hex
    return doc

  # TODO: implement bidirectional query
  def get(self, source_id, source_lang, target_lang):
    m_index = TMUtils.es_index2mapdb(TMUtils.lang2es_index(source_lang),
                                     TMUtils.lang2es_index(target_lang))
    doc = self.server[m_index].get(source_id.hex)
    if doc: return uuid.UUID(doc['target_id'])
    return None
