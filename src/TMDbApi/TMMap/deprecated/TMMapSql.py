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
from sqlalchemy import *
from sqlalchemy.sql import text
import logging

from TMDbApi.TMMap.TMMap import TMMap
from TMDbApi.TMUtils import TMUtils


class TMMapSql(TMMap):
  def __init__(self, url):
    self.sql = create_engine(url)
    self.conn = self.sql.connect()
    self.tables = dict()

    #self.ids = set()

  def add_segment(self, segment):
    t = self._segment2table(segment)
    doc = self._segment2doc(segment)
    logging.info("Adding {}".format(doc))
    try:
      self.conn.execute(t.insert(doc))
    except:
      # Update
      self.conn.execute(t.update().where( t.c.source_id == segment.source_id ).values(doc))

  def add_segments(self, segments):
    for s in segments: self.add_segment(s)
    logging.info("Added {}".format(len(segments)))

  # Bulk addition
  def add_segments_DISABLED(self, segments):
    if not segments:
      return
    logging.info("Added {}".format(len(segments)))
    docs = [self._segment2doc(s) for s in segments]

    #for d in segments:
    #  if d.source_id in self.ids: raise Exception("Duplicate entry: {}".format(d.__dict__))
    #  self.ids.add(d.source_id )

    t = self._segment2table(segments[0])
    # Create temporary table
    tt = self._segment2table(segments[0], '_tmp')

    # SQL engines don't really support bulk upsert operation thus the quickest
    # way is to create temporary table and then insert/update destination

    # Clear temp table
    self.conn.execute(tt.delete())
    self.conn.execute(tt.insert(docs))

    j = tt.outerjoin(t, t.c.source_id != tt.c.source_id)
    sel = tt.select(tt).select_from(j).where(t.c.source_id == None)
    ins = t.insert().from_select(['source_id', 'target_id', 'creation_date', 'change_date'], sel)

    upd = t.update().values(target_id = tt.c.target_id,
                            creation_date = tt.c.creation_date,
                            change_date = tt.c.change_date) \
                    .where(tt.c.source_id == t.c.source_id)
    res = self.conn.execute(ins)
    res = self.conn.execute(upd)

  # Get target id by looking for a mapping.
  def get(self, source_id, source_lang, target_lang):
    tname = TMUtils.es_index2mapdb(TMUtils.lang2es_index(source_lang),
                                   TMUtils.lang2es_index(target_lang))
    if not tname in self.tables: raise Exception("Language pair : {} - {} doesn't exist".format(source_lang, target_lang))
    # TODO: implement bidirectional query
    t = self.tables[tname]
    res = self.conn.execute(t.select(t.target_id).where(t.source_id == source_id))
    if res:
      return res.fetchone()[0]
    return None

  def _segment2table(self, segment, suffix = None):
    tname = TMUtils.es_index2mapdb(TMUtils.lang2es_index(segment.source_lang),
                                     TMUtils.lang2es_index(segment.target_lang))
    if suffix: tname += suffix
    if not tname in self.tables:
      md = MetaData()
      self.tables[tname] = Table(tname, md,
                                 Column('id', Integer, primary_key=True),
                                 Column('source_id', GUID, index=True),
                                 Column('target_id', GUID, index=True),
                                 Column('creation_date', TIMESTAMP),
                                 Column('change_date', TIMESTAMP),
                                 mysql_engine='InnoDB',
                                 mysql_charset='utf8')
      md.bind = self.conn
      self.tables[tname].create(checkfirst=True)
    return self.tables[tname]


class TMMapMySql(TMMapSql):
  def __init__(self):
    super(TMMapMySql, self).__init__('mysql+pymysql://root:pangeanic@localhost/map')

class TMMapPostgreSql(TMMapSql):
  def __init__(self):
    super(TMMapPostgreSql, self).__init__('postgresql://root@localhost/map')

# TODO: move to a separate file
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID
import uuid

class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses Postgresql's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.

    """
    impl = CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                # hexstring
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return uuid.UUID(value)