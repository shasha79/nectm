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
import itertools
import logging

from TMX.TMXParser import TMXParser
from TMPreprocessor.TMSplit import TMSplit
from TMPosTagger.TMTokenizer import TMTokenizer
from TMPosTagger.TMPosTagger import TMPosTagger
from TMMatching.TMUtilsMatching import TMUtilsMatching
from nltk.tree import Tree
import codecs
import logging
from Config.Config import G_CONFIG


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('-d', '--dir', type=str, help="Root directory for TMX file tree")
  parser.add_argument('-f', '--file', type=str, help="Simple TMX file")
  parser.add_argument('-s', '--source', type=str, help="Single TMX file")
  parser.add_argument('-t', '--target', type=str, help="Single TMX file")
  return parser.parse_args()


def print_align(ori_segments, align_position, src_split_struct, tgt_split_struct):
  count = 0

  print(len(ori_segments))
  print(len(src_split_struct))
  print(len(tgt_split_struct))
  print(len(align_position))

  for i in range(0, len(ori_segments)):  # --> for all sentences

    if align_position[i] != [] and len(align_position[i]) == len(set(align_position[i])):
    #   print(align_position[i])
    # else:
    #   print('*******' + ' '.join(map(str, align_position[i])))

      count = count + 1
      ori_source = ori_segments[i].source_text
      ori_target = ori_segments[i].target_text

      print(' '.join(map(str, ori_source)) + '\t' + ' '.join(map(str, ori_target)))  # --> print original sentence
      print('\n')
      split_source = src_split_struct[i][0]
      split_target = tgt_split_struct[i][0]

      for j in range(0, len(align_position[i])):
        value_target = align_position[i] #--> List with align position
        #print(value_target)
        print(' '.join(map(str, split_source[j])))
        #+ '\t' +
        print(' '.join(map(str, split_target[value_target[j]])))
        print('\n')
  print('Generated segments ' + str(count))

if __name__ == "__main__":

  args = parse_args()

  lang = args.source

  file = codecs.open(args.file, 'r')


  lang_class = G_CONFIG.get_split_rules(args.source, args.target)
  #print(lang_class)
  if lang_class:
    #print('########Call Split########')
    #src_text, tgt_text, editSplit = split_sentences(lang_class)

    #Split
    splitTask = TMSplit(lang_class, args.source)

    # Tokenizer
    tok = TMTokenizer(lang.upper()).tokenizer
    pos = TMPosTagger(lang.upper())

    for eline in file.readlines():
      tok_sentences = tok.process(eline)
      print(tok_sentences)
      pos_sentence = [element for word, element in pos.tag_segments([tok_sentences])[0]]


      # Split several steps

      list_sentences = TMUtilsMatching.pre_process(tok_sentences, args.source, 'split_sentences', {})
      #print('+++++++++++++++++')
      #print(list_sentences)

      list_word_pos = []
      if list_sentences:
        i = 0
        for each_sent in list_sentences:
          # Create word_pos
          len_e = len(each_sent.split())
          list_word_pos.append([(w, p) for w, p in zip(each_sent.split(), pos_sentence[i:i + len_e])])
          i = i + len_e
      else:
        list_word_pos = [[(w, p) for w, p in zip(tok_sentences.split(), pos_sentence)]]
      #print(list_word_pos)

      # print(word_pos)
      # segmentsStructure = []
      all_split = []
      all_marks = []
      for sentence in list_word_pos:
        #print(sentence)
        segmentsStructure = splitTask.clause_chunk(sentence)  # preProcess.split_process(p_segments)
        #print(segmentsStructure)
        #print('----split INFO---')
        #logging.info("split INFO : {} ".format(segmentsStructure))
        #print(segmentsStructure)

        list_query_split, list_marks_split = splitTask.split_output(segmentsStructure)
        #print(list_query_split)

        if len(list_query_split) > 1:
          for e_part in list_query_split:
            all_split.append(e_part)
            if list_marks_split:
              all_marks.append(list_marks_split.pop(0))
        else:
          all_split.append(sentence)
          all_marks.append([])

      for i in range(0, len(all_split)):
        mark = ''
        sent = ''
        spos = ''
        #if l_best_segments[i]:
        #  segment, match = l_best_segments[i][0]
        #  join_source = join_source + ' ' + segment.source_text
        #  join_target = join_target + ' ' + segment.target_text
        #else:
        for word, wpos in all_split[i]:
          sent = sent + ' ' + word
          spos = spos + ' ' + wpos
        if all_marks:
          if all_marks[0]:
            curr_mark = all_marks.pop(0)
            mark = mark + ' ' + curr_mark[0] + '_' + curr_mark[1]

        print('\t' + sent + '\t' + spos + '\t' + mark)