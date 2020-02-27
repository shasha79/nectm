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
import os
import re
import pickle
import numpy
import logging

import sys

sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', '..'))
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..' ))
#sys.path.append("../..")
#sys.path.append("../../..")

DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'rnn', 'data')

from TMPosTagger.TMPosTagger import TMPosTagger
from TMPreprocessor.Xml.XmlUtils import XmlUtils

from TMPreprocessor.Xml.rnn.elmansentlstm import model
from TMPreprocessor.Xml.rnn.tools import contextwin

# Tag transfer algorithm based on POS and RNN model
class TMXmlTagTransferRNN:
  def __init__(self, langs, lazy=False):
    self.folder = os.path.join(DATA_DIR, '-'.join(langs))
    self.pos_taggers = [TMPosTagger(lang.split('-')[0], universal=True) for lang in langs]

    self.model_dic = self.rnn = None
    if not lazy:
      try:
        self.model_dic, self.rnn = self._load_rnn()
      except Exception as e:
        print(e)

  def _load_rnn(self):
    self.s = {'verbose': 1,
         'win': 7,  # number of words in the context window
         'nhidden': 100,  # number of hidden units
         'seed': 345,
         'emb_dimension': 100,  # dimension of word embedding
         'nepochs': 100}

    # load the dict
    print('load dict from {}...'.format(self.folder))
    _, _, _,dic = pickle.load(open(self.folder + '/alltag.bio.pkl', 'rb'))
    self.label2idx = dic['labels2idx']
    self.word2idx = dic['words2idx']
    self.idx2label = dict((k, v) for v, k in dic['labels2idx'].items())
    self.idx2word = dict((k, v) for v, k in dic['words2idx'].items())

    vocsize = len(dic['words2idx'])
    nclasses = len(dic['labels2idx'])

    print('load model')
    rnn = model(nh=self.s['nhidden'],
                nc=nclasses,
                ne=vocsize,
                de=self.s['emb_dimension'],
                cs=self.s['win'])
    rnn.load(os.path.join(self.folder, 'alltag-model'))
    return dic,rnn

  # Algorithm for transferring XML tags from source text to target text, for example:
  # I have <X[1]>a dog</X[1]> ---> Yo tengo <X[1]>un perro</X[1]>
  # Algorithm is based on RNN trained on POS data converted to IOB tags. The algorithm needs to POS-tag source text,
  # convert it to IOB, predict IOB for the target text and place original tags into predicted positions in the target text
  def __call__(self, s_txt, t_txt):
    # Extract source tags to be transferred: ['<X[1]>', '</X[1]>']
    print("Source text: {}".format(s_txt))
    s_tags = XmlUtils.extract_tags(s_txt)
    print("Source tags: {}".format(s_tags))
    if not s_tags: return t_txt
    # Remove any tags from the target
    t_txt = XmlUtils.strip_tags(t_txt)

    # Rename tags to avoid problems in XML parser
    # I have <X[1]>a dog</X[1]> ---> I have <T1>a dog</T1>
    s_txt_fixed = XmlUtils.simplify_tags(s_txt)
    s_tags_fixed = XmlUtils.extract_tags(s_txt_fixed)
    print("Fixed source tags: {}".format(s_tags_fixed))
    # Keep mapping of fixed tags to original tags for the final recovery:
    # tags_map = {'<T1>: '<X[1]>', '</T1>': '</X[1]>'}
    assert len(s_tags_fixed) == len(s_tags)
    tags_map = dict(zip(s_tags_fixed, s_tags))
    print("Tags map: {}".format(tags_map))

    # Run POS tagging (before, replace XML tags with a placeholder in the source text):
    # I chase <T1>a dog</T1> --> I chase ELASTICTMTAG a dog ELASTICTMTAG
    # --> I/NOUN have/VERB ELASTICTMTAG/NOUN a/DET dog/NOUN ELASTICTMTAG/NOUN
    s_pos = self.pos_taggers[0].tag_segments([XmlUtils.replace_tags(s_txt_fixed)])[0]
    t_pos = self.pos_taggers[1].tag_segments([t_txt])[0]
    # Recover fixed tags:
    # I,NOUN have,VERB ELASTICTMTAG,NOUN a,DET dog,NOUN ELASTICTMTAG,NOUN
    # ---> NOUN VERB <T1> DET NOUN </T1>
    s_pos_with_tags,s_pos = XmlUtils.recover_tags_pos(s_pos, s_tags_fixed)
    print("S_POS_WITH_TAGS: {}, S_POS: {}, T_POS: {}".format(s_pos_with_tags, s_pos, t_pos))
    # For each tag (T1, T2 etc.), remove other tags and run prediction algorithm, based on IOB tags. Return value
    # is a map of tags to their correspondent indexes in target (tokenized) text
    tag2t_index = self.tags2indexes(s_tags_fixed, s_pos_with_tags, s_pos, [t[1] for t in t_pos])

    # Place tags at predicted indexes in the target text
    t_txt_with_tags = self.place_tags(s_tags_fixed, tag2t_index, tags_map, t_pos)
    if not t_txt_with_tags: return None
    # TODO: join using language-specific "joiner" (opposite of tokenizer)
    return " ".join(t_txt_with_tags)

  def tags2indexes(self, s_tags, s_pos_with_tags, s_pos, t_pos):
    print("tags2indexes: S_TAGS: {}, s_pos_with_tags: {}, S_POS: {}, T_POS: {}".format(s_tags, s_pos_with_tags, s_pos, t_pos))

    tag2index = dict()
    # For each tag (T1, T2 etc.), remove other tags and run prediction algorithm, based on IOB tags
    for tag in s_tags:
      tag_name = self.tag2name(tag)
      # Self-closing tags should be handled with separate model
      if XmlUtils.is_self_closing_tag(tag):
        print("Self-closing tag: {}".format(tag))
        s_iob = self.tag2iob_self_closing(s_pos_with_tags, tag)
        # TODO:
        t_iob = self.predict(s_iob, s_pos, t_pos)
        start_index, end_index = self.iob2indexes(t_iob, self_closing=True)
        tag2index['<{}/>'.format(tag_name)] = start_index
      elif XmlUtils.is_opening_tag(tag):
        print("Opening tag: {}".format(tag))
        s_iob = self.tag2iob(s_pos_with_tags, tag)
        t_iob = self.predict(s_iob, s_pos, t_pos)
        start_index, end_index = self.iob2indexes(t_iob)
        # Store mapping
        tag2index['<{}>'.format(tag_name)] = start_index
        tag2index['</{}>'.format(tag_name)] = end_index
      else:
        # closing tag or  don't do anything
        pass
    return tag2index

  def tag2name(self, tag):
    m = re.search('</?([^<>]+)/?>', tag)
    if m: return m.group(1)
    return None

  def tag2iob(self, pos, tag):
    print("tag2iob: POS: {}, TAG: {}".format(pos, tag))
    iob = []
    tag_name = self.tag2name(tag)
    is_inside = False
    for w in pos:
      print("W: {}".format(w))
      if not re.search("<.*>", w):
        if is_inside:
          if not iob or iob[-1] == 'O':
            iob.append("B-T")
          else:
            iob.append("I-T")
        else:
          iob.append("O")
          is_inside = False
      # opening tag
      elif w == tag:
        is_inside = True
      # closing tag
      elif w == '<{}/>'.format(tag_name):
        is_inside = False
      else:
        # Other tags - skip them
        pass
    return iob

  def tag2iob_self_closing(self, pos, tag):
    # Check if tag is at the beginning or at the end - skip it
    if pos[0] == tag or pos[-1] == tag: return None
    print("POS: {}, TAG: {}".format(pos, tag))
    iob = []
    is_inside = False
    for w in pos:
      if not re.search("<.*>", w):
        if is_inside:
          iob.append("I-T")
          is_inside = False
        else:
          iob.append("0")
      elif iob and w == tag:
        iob[-1] = "B-T"
        is_inside = True
      else:
        # Other tags - skip them
        pass
    return iob

  def iob2indexes(self, t_iob, self_closing=False):
    start_index = end_index = -1
    for i in range(0, len(t_iob)):
      if t_iob[i] == 'B-T':
        start_index = i
        end_index = i+1
      elif t_iob[i] == 'I-T':
        end_index = i
    # For self-closing tags which are in the middle of a sentence, actual tag position is between start and end,
    # e.g. <T1> NOUN VERB </T1> ---> NOUN <T1 />  VERB
    if self_closing == True and end_index > start_index:
      start_index += 1
      end_index = -1
      assert end_index == start_index

    return start_index, end_index

  def place_tags(self, s_tags, tag2t_index, tag2org, t_pos):
    indexes = [tag2t_index[t] for t in s_tags]
    if not all(indexes[i] <= indexes[i + 1] for i in range(len(indexes) - 1)):  # check if the list is monotonically increasing
      # Order is broken. TODO: fallback to token-based solution
      logging.warning("Order of tags is broken: {} -> {}".format(s_tags, indexes))
      return None
    else:
      # Put original tags into predicted indices in the target text
      print("S_TAGS: {}".format(s_tags))
      t_txt_with_tags = []
      for i in range(0, len(t_pos)):
        w, p = t_pos[i]
        while (s_tags and tag2t_index[s_tags[0]] == i):
          t_txt_with_tags.append(tag2org[s_tags.pop(0)])
        t_txt_with_tags.append(w)
      # Append remaining tags (if any) to the end
      if s_tags:
        t_txt_with_tags += [tag2org[t] for t in s_tags]

    # TODO: join using language-specific "joiner" (opposite of tokenizer)
    # Yo tengo <X[1]>un perro</X[1]>
    return t_txt_with_tags

  def predict(self, s_iob, s_pos, t_pos):
    print("predict: S_IOB: {}, S_POS: {}, T_POS: {}".format(s_iob, s_pos, t_pos))
    if not self.rnn:
      self.model_dic, self.rnn = self._load_rnn()

    print('test ...')
    #test_lex = ['NOUN', 'X', 'NOUN', 'NOUN', 'NOUN']
    #test_lex = [self.word2idx[w] for w in test_lex]
    tlex = [self.word2idx[w] for w in t_pos]
    #test_slex = ['NOUN', 'NOUN', 'CONJ', 'NOUN', 'NOUN', 'NOUN']
    #test_slex = [self.word2idx[w] for w in test_slex]
    slex = [self.word2idx[w] for w in s_pos]
    #test_sy = ['O', 'O', 'O', 'B-T', 'I-T', 'I-T']
    #test_sy = [self.label2idx[w] for w in test_sy]
    sy = [self.label2idx[w] for w in s_iob]
    # evaluation // back into the real world : idx -> words
    ty = list(map(lambda x: self.idx2label[x], \
                            self.rnn.classify(numpy.asarray(contextwin(tlex, self.s['win'])).astype('int32'), slex,
                                         sy)))
    # Replace first occurence of I-T with B-T
    for i in range(0, len(ty)):
      if ty[i] == 'I-T' and (i == 0 or ty[i-1] == 'O'):
        ty[i] = 'B-T'
        break
    print("target IOB: {}".format(ty))
    return ty

if __name__ == "__main__":
  logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO, stream=sys.stdout)
  pp = TMXmlTagTransferRNN(('en', 'es'), lazy=True)
  print("Instantiated TMXmlTagTransferRNN")
  print("Target text with transfered text: {}".format(pp(sys.argv[1], sys.argv[2])))
  #pp.predict(['O', 'O', 'O', 'B-T', 'I-T', 'I-T'],
  #           ['NOUN', 'NOUN', 'CONJ', 'NOUN', 'NOUN', 'NOUN'],
  #           ['NOUN', 'X', 'NOUN', 'NOUN', 'NOUN'])
