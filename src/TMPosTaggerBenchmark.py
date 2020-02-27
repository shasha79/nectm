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

import argparse
import copy
import datetime

from TMX.TMXFileIterator import TMXFileIterator
from TMX.TMXParser import TMXParser

from TMPosTagger.TMStanfordPosTagger import TMStanfordPOSTagger
from TMPosTagger.TMTreeTagger import TMTreeTagger
from TMPosTagger.TMTokenizer import TMTokenizer
from TMPosTagger.TMPosTagger import TMRDRPOSTagger
#from TMPosTagger.TMPosTagger import TMPolyglotPosTagger

import time

class Timer(object):
    def __init__(self, verbose=False):
        self.verbose = verbose

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.secs = self.end - self.start
        self.msecs = self.secs * 1000  # millisecs
        if self.verbose:
            print(' time: %f ms' % self.msecs)

def add():
  for f in it:
    parser = TMXParser(f)
    segments = parser.parse()
  return segments


def select_segments(totalSegments,listSegments):
  listSegments = list(listSegments)
  while len(listSegments) < totalSegments:
    listSegments = listSegments + copy.deepcopy(listSegments)
  if len(listSegments)>= totalSegments:
    listSegments = listSegments[0:totalSegments]
  return listSegments

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('-d', '--dir', type=str, help="Root directory for TMX file tree")
  parser.add_argument('-f', '--file', type=str, help="Single TMX file")
  parser.add_argument('-q', '--totalSegments', type=int, help="Total segments to tagger", default=1)
  parser.add_argument('-t', '--tagger', choices=['tree', 'stanford', 'polyglot', 'multilingual'], default='tree', help='Choose a PosTagger tool',
                      nargs='*')
  return parser.parse_args()

if __name__ == "__main__":
  args = parse_args()

  if args.file:
    it = [args.file]
  else:
    it = TMXFileIterator(args.dir)

  qlangs = ('en-EN', 'es-ES')
  #listSegments = add()

  listSegments = ['Gasoline, brake fluid, and coolant will damage the finish of painted and plastic surfaces:']

  #Select segments to process
  with Timer() as t:
    listSegmentsToProcess = select_segments(args.totalSegments,listSegments)
  print("=> time to create list of segments: %s " % time.strftime("%H:%M:%S", time.gmtime(t.secs)))
  print("=> total segments: %s " % len(listSegmentsToProcess))

  with Timer() as t:
    #tok_sents = [TMTokenizer('EN').tokenizer.process(s.source_text) for s in listSegmentsToProcess]
    tok_sents = [TMTokenizer('EN').tokenizer.process(s) for s in listSegments]
    print(tok_sents)
  print("=> time to tokenize the list of segments: %s " % time.strftime("%H:%M:%S", time.gmtime(t.secs)))
  #
  stanford_tokens_string = [text.split(' ') for text in tok_sents]
  for tool in args.tagger:
    if tool=='stanford': #--> stanford
      with Timer() as t:
        # Call Stanford PosTagger
        st = TMStanfordPOSTagger('EN')
      print("=> time to load Stanford: %s " % time.strftime("%H:%M:%S", time.gmtime(t.secs)))
      with Timer() as t:
        tok_sents = st.only_tag_segments([s for s in stanford_tokens_string])
        print(tok_sents)
      print("=> time to tagger Stanford: %s " % time.strftime("%H:%M:%S", time.gmtime(t.secs)))

    if tool=='tree': #--> tree

      with Timer() as t:
        # Call TreeTagger PosTagger
        treeTagger = TMTreeTagger('EN')
      print("=> time to load TreeTagger: %s " % time.strftime("%H:%M:%S", time.gmtime(t.secs)))

      with Timer() as t:
        tok_sents = treeTagger.only_tag_segments([s for s in tok_sents])
        print(tok_sents)
      print("=> time to tagger TreeTagger: %s " % time.strftime("%H:%M:%S", time.gmtime(t.secs)))

    if tool == 'multilingual':  # --> tree

      with Timer() as t:
        # Call TreeTagger PosTagger
        multilingual = TMRDRPOSTagger('EN')
      print("=> time to load TMRDRPOSTagger: %s " % time.strftime("%H:%M:%S", time.gmtime(t.secs)))

      with Timer() as t:
        tok_sents = multilingual.only_tag_segments([s for s in tok_sents])
        print(tok_sents)
      print("=> time to tagger TMRDRPOSTagger: %s " % time.strftime("%H:%M:%S", time.gmtime(t.secs)))
    #
    # if tool=='polyglot': #--> polyglot
    #   joinSentece = [(' ').join(s) for s in tok_sents]
    #   with Timer() as t:
    #     # Call Polyglot PosTagger
    #     for sentence in [s for s in joinSentece]:
    #       pg = TMPolyglotPosTagger(sentence, 'EN')
    #       pg.tool.pos_tags
    #   print("=> time Polyglot: %s " % time.strftime("%H:%M:%S", time.gmtime(t.secs)))


