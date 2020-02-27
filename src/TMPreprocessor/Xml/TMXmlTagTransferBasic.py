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
import re
from TMPreprocessor.Xml.XmlUtils import XmlUtils
from TMMatching.TMTextProcessors import TMTextProcessors

class TMXmlTagTransferBasic:
  def __init__(self, langs):
    self.langs = langs

  def __call__(self, s_txt, t_txt):
    s_tags = XmlUtils.extract_tags(s_txt)
    if not s_tags: return t_txt

    t_tags = XmlUtils.extract_tags(t_txt)
    # Number of tags is equal - just replace one by one
    if len(s_tags) == len(t_tags):
      for s_tag, t_tag in zip(s_tags, t_tags):
        t_txt = t_txt.replace(t_tag, s_tag, 1)
      return t_txt
    else:
      s_toks = TMTextProcessors.tokenizer(self.langs[0]).tokenizer.process(XmlUtils.replace_tags(XmlUtils.fix_tags(s_txt)[0], adjacent_space_placeholder=XmlUtils.SPACE_PLACEHOLDER)).split()
      # TODO: s_universal = self._preprocess(s_toks, self.langs[0])
      # Strip all tags from target text before tokenizing it
      t_toks = TMTextProcessors.tokenizer(self.langs[1]).tokenizer.process(XmlUtils.strip_tags(t_txt)).split()
      #TODO: t_universal = self._preprocess(t_toks, self.langs[1])
      t_toks_new = []
      # Iterate over tokenized source and target text and apply simple alighnment algorithm (by token).
      # Insert source tags at the aligned places in the target text
      ti = 0
      for si in range(0, len(s_toks)):
        count = 1  # init
        if s_toks[si] == XmlUtils.TAG_PLACEHOLDER:
          t_toks_new.append(s_tags.pop(0))
        elif s_toks[si] == XmlUtils.SPACE_PLACEHOLDER:
          t_toks_new.append(XmlUtils.SPACE_PLACEHOLDER)
        elif ti < len(t_toks):
          t_toks_new.append(t_toks[ti])
          ti += 1
        else:
          break  # source is longer than target, stop here
      # Append remaining target tokens
      if ti < len(t_toks): t_toks_new += t_toks[ti:]
      # If not all tags have been aligned, just contatenate remaining ones to the end
      if s_tags: t_toks_new += s_tags
    # Join tokenized text into string. TODO: implement as a part of TMTokenizer class (language-dependent)
    # return self.tok[1].join(t_toks_new)
    ttext_with_tags = XmlUtils.join_tags(' '.join(t_toks_new), '(</?[^<>]+/?>)([^<>]+)(</?[^<>]+/?>)') # --> join words with tags <b> this </b> --> <b>this</b>
    # Handle whitespaces which are adjacent to tags
    ttext_with_tags = re.sub('\s+<', '<', ttext_with_tags)
    ttext_with_tags = re.sub('>\s+', '>', ttext_with_tags)
    ttext_with_tags = re.sub(XmlUtils.SPACE_PLACEHOLDER, '', ttext_with_tags)
    return ttext_with_tags

  def _preprocess(self, text, lang):
    tagger_text = TMTextProcessors.pos_tagger(lang).tag_segments(text) # text is a list of words
    pos = " ".join([word_pos[0][1] for word_pos in tagger_text if len(word_pos[0]) > 1]).split(' ')  # Create a sequences of pos_tags
    # List (sentences) of lists of pairs (word, tag)
    tagged_words = [[[text[p], pos[p]] for p in range(0, len(text))]]
    # If mapping required
    if TMTextProcessors.univ_pos_tagger(lang):
      universal_text = TMTextProcessors.univ_pos_tagger(lang).map_universal_postagger(tagged_words)
      return universal_text[0]
    return tagged_words[0]

  # input: posToSearch , universal pos tag
  # output: index if with the same posTag
  def _get_tgt_position(self, src, text, tgt_exist_position, src_open_tag):
    l_index = [i for i, u in enumerate(text) if u[1] == src] #Search igual posTag in target
    position = src_open_tag
    if l_index != []:
      for i in l_index:
        if i not in tgt_exist_position:
          tgt_exist_position.append(i)
          position = i
          break
    return position # Probably this position was put

