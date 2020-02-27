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
import json

from redis import Redis

from TMDbApi.TMMap.TMMap import TMMap

# Redis by itself doesn't suit to be TMMap but merely can be used as a cache to speed up
# TODO: separate instance for separate language pair or use prefixes to avoid key collision

class TMMapRedis(TMMap):
  def __init__(self):
    self.redis = Redis()

  def add_segment(self, segment):
    #m_index = TMUtils.es_index2mongodb(TMUtils.lang2es_index(segment.source_lang),
    #                                   TMUtils.lang2es_index(segment.target_lang))
    s_result = self.redis.set(segment.source_id, self._segment2doc(segment))
    return s_result

  def add_segments(self, segments):
    if not segments:
      return
    #m_index = TMUtils.es_index2mongodb(TMUtils.lang2es_index(segments[0].source_lang),
    #                                   TMUtils.lang2es_index(segments[0].target_lang))
    pipe = self.redis.pipeline()
    for segment in segments:
      pipe.set(segment.source_id, self._segment2doc(segment))
    result = pipe.execute()
    return result

  # TODO: implement bidirectional query
  def get(self, source_id, source_lang, target_lang):
    #m_index = TMUtils.es_index2mongodb(TMUtils.lang2es_index(source_lang),
    #                               TMUtils.lang2es_index(target_lang))
    res = self.redis.get(source_id)
    if not res: return None
    return uuid.UUID(json.loads(res.decode('utf-8'))['target_id'])

  def _segment2doc(self, segment):
    return json.dumps(super()._segment2doc(segment))
