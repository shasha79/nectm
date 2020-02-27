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
from pymongo import MongoClient
from pymongo.errors import BulkWriteError

from TMDbApi.TMMap.TMMap import TMMap
from TMDbApi.TMUtils import TMUtils


# ID map implementation based on MongoDB
class TMMapMongoDb(TMMap):
  def __init__(self):
    self.mongo_client = MongoClient()
    self.mongo_db = self.mongo_client.tm


  def add_segment(self, segment):
    # Add MongoDB document
    m_index = TMUtils.es_index2mapdb(TMUtils.lang2es_index(segment.source_lang),
                                     TMUtils.lang2es_index(segment.target_lang))
    # TODO: do not update if creation date is older than existing one
    m_result = self.mongo_db[m_index].update_one({'source_id': segment.source_id},
                                                 {'$set': self._segment2doc(segment) },
                                                 upsert=True)  # insert if doesn't exist
    return m_result

  def add_segments(self, segments):
    bulk = None
    for segment in segments:
      if not bulk:
        m_index = TMUtils.es_index2mapdb(TMUtils.lang2es_index(segment.source_lang),
                                         TMUtils.lang2es_index(segment.target_lang))
        bulk = self.mongo_db[m_index].initialize_unordered_bulk_op()
      bulk.find({'source_id': segment.source_id}) \
        .update_one({'$set': self._segment2doc(segment) })

    try:
      result = bulk.execute()
    except BulkWriteError as bwe:
      result = bwe.details
      logging.error(bwe.details)
    return result

  def get(self, source_id, source_lang, target_lang):
    src_index = TMUtils.lang2es_index(source_lang)
    tgt_index = TMUtils.lang2es_index(target_lang)
    m_index = TMUtils.es_index2mapdb(src_index, tgt_index)
    m_results =  self.mongo_db[m_index].find({'source_id':source_id})
    if not m_results or not m_results.count():
      return None
    return m_results[0]['target_id']
