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
import datetime
import re
from TMDbApi.TMUtils import TMUtils
# Bidirectional map abstract class
class TMMap:
  def add_segment(self, segment):
    pass
  # Bulk addition
  def add_segments(self, segments):
    pass

  # Get target id by looking for a mapping
  def get(self, source_id, source_lang, target_lang):
    pass

  def delete(self, source_lang, target_lang, source_ids):
    pass


  # Convert segment to mapping doc
  def _segment2doc(self, segment):
    # Initialize/update DB date fields
    now_str = TMUtils.date2str(datetime.datetime.now())
    if not segment.insert_date: segment.insert_date = now_str
    if not segment.check_date: segment.check_date = TMUtils.date2str(datetime.datetime(1970, 1, 1))
    segment.update_date = now_str

    return {'source_id': segment.source_id,
            'target_id': segment.target_id,
            'source_text': segment.source_text,
            'target_text': segment.target_text,
            'source_language': segment.source_language,
            'target_language': segment.target_language,
            'source_metadata': segment.source_metadata,
            'target_metadata': segment.target_metadata,
            'metadata': segment.metadata,
            'tuid': segment.tuid,
            'industry':TMUtils.str2list(segment.industry),
            'type': TMUtils.str2list(segment.type),
            'organization': TMUtils.str2list(segment.organization),
            'file_name': TMUtils.str2list(segment.file_name),
            'domain': TMUtils.str2list(segment.domain),
            'tm_creation_date': segment.tm_creation_date,
            'tm_change_date': segment.tm_change_date,
            'insert_date': segment.insert_date,
            'update_date': segment.update_date,
            'check_date': segment.check_date,
            'check_version': segment.check_version,
            'dirty_score': segment.dirty_score,
            'username': segment.username

            }
