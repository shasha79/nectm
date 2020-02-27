#!/usr/bin/python3
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
import argparse
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, filename='tmx2db.log')

from TMX.TMXFileIterator import TMXFileIterator
from TMX.TMXParser import TMXParser
from TMDbApi.TMDbApi import TMDbApi

from random import shuffle


def add():
  for f in it:
    parser = TMXParser(f)
    segments = parser.parse()
    print(parser.fileName)
    db.add_segments(segments)

def query(num):
  for f in it:
    parser = TMXParser(f)
    segments = parser.parse()[:num]
    shuffle(segments)
    logging.info("Querying {} segments".format(len(segments)))
    for segment in segments:
      db.query(segment.source_text, qlangs)
    logging.info("Done querying")

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('-a', '--add', action="store_true", help="Add segments to the DB")
  parser.add_argument('-q', '--query', action="store_true", help="Query segments from the DB")
  parser.add_argument('-nq', '--num_query', type=int, help="Limit queries to this number", default=-1)
  parser.add_argument('-i', '--init', action="store_true", help="Init DB")
  parser.add_argument('-pt', '--pos_tag', action="store_true", help="Run POS tagger on segment texts")
  parser.add_argument('-sp', '--split_seg', action="store_true", help="Run Split rules on segment texts")

  parser.add_argument('-d', '--dir', type=str, help="Root directory for TMX file tree")
  parser.add_argument('-f', '--file', type=str, help="Single TMX file")
  parser.add_argument('-md', '--map_db', choices=['elasticsearch', 'mongodb', 'couchdb', 'redis', 'mysql', 'postgresql'],
                      help='Choose underlying driver for Map DB',
                      default='elasticsearch')
  return parser.parse_args()

if __name__ == "__main__":
  args = parse_args()
  if args.file:
    it = [args.file]
  else:
    it = TMXFileIterator(args.dir)

  db = TMDbApi(args.map_db)
  if args.init:
      db.init_db()
  # TODO: get from command line
  qlangs = ('en-GB', 'es-ES')
  #qlangs = ('en-GB', 'fr-FR')
  if args.add:
    add()
  if args.query:
      query(args.num_query)