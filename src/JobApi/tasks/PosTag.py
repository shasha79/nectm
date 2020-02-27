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
import sys, os, re, tempfile, datetime
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))

from JobApi.tasks.Task import Task
from TMDbApi.TMUtils import TMUtils
from TMPreprocessor.Xml.XmlUtils import XmlUtils

class PosTagTask:
  def __init__(self, task):
    self.langs = task.get_langs()
    self.is_universal = task.job.get('universal', False)

  # Tag segments method
  def __call__(self, index, segments_iter):
    # Import should be inside the function to avoid serializing all pos tagger dependencies
    # for parallel execution
    sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))
    sys.path = [p for p in sys.path if p]
    from TMPosTagger.TMPosTagger import TMPosTagger

    # Cache all segments. Though it might be expensive in terms of memory, but we need
    # to gather all texts for POS tagger batch and then store back
    # batch of POS-tagged results. Batch should be small enough by splitting to sufficiently
    # large number of Spark jobs
    segments = [s for s in segments_iter]
    # Initialize PosTaggers for source and target languages
    pos_taggers = [TMPosTagger(lang.split('-')[0], universal=self.is_universal) for lang in self.langs]
    # Invoke POS taggers for source and target segments
    src_texts = pos_taggers[0].tag_segments([XmlUtils.replace_tags(s.source_text) for s in segments])
    tgt_texts = pos_taggers[1].tag_segments([XmlUtils.replace_tags(s.target_text) for s in segments])
    # Store POS tags with XML tags as a training data. TODO: make it optional
    f = open(tempfile.gettempdir() + "/pos_tags-{}-{}.txt".format(TMUtils.date2str(datetime.datetime.now()), index),
             'w')
    iobs = open(tempfile.gettempdir() + "/iob_tags-{}-{}.txt".format(TMUtils.date2str(datetime.datetime.now()), index),
              'w')
    for s, stext, ttext in zip(segments, src_texts, tgt_texts):
      s.source_pos = self.tags2string(stext)
      s.target_pos = self.tags2string(ttext)
      # Write POS tags (+XML tags) to text file to be used as a training data
      if re.match(XmlUtils.TAG_PATTERN, s.source_text):
        f.write("{}\n{}\n\n".format(self.tags2string_xml_tags(s.source_text, stext),
                                    self.tags2string_xml_tags(s.target_text, ttext)))
        for s,t in zip(self.tags2string_iob_tags(s.source_text, stext),
                       self.tags2string_iob_tags(s.target_text, ttext)):
          iobs.write("{}\n{}\n\n".format(s,t))

    f.close()
    iobs.close()
    return segments

  def tags2string(self, text_pos):
    return " ".join([word_pos[1] for word_pos in text_pos if
                     len(word_pos) > 1 and word_pos[0] != XmlUtils.TAG_PLACEHOLDER])

  def tags2string_xml_tags(self, text, text_pos):
    pos_str = self.tags2string(text_pos)
    # If no XML tags found, just return concatenated POS tags
    tags = XmlUtils.extract_tags(text)
    if not tags: return pos_str
    pos = []

    for word_pos in text_pos:
      # Contatenate POS tags and XML tags into the string
      if word_pos[0] == XmlUtils.TAG_PLACEHOLDER:
        pos.append(tags.pop(0))
      elif len(word_pos) < 2:
        continue
      else:
        pos.append(word_pos[1])

    return " ".join(pos)

  def tags2string_iob_tags(self, text, text_pos):
    pos_str = self.tags2string(text_pos)
    # If no XML tags found, just return concatenated POS tags
    tags = XmlUtils.extract_tags(text)
    if not tags: return pos_str
    pos = []

    for word_pos in text_pos:
      # Contatenate POS tags and XML tags into the string
      if word_pos[0] == XmlUtils.TAG_PLACEHOLDER:
        pos.append(tags.pop(0))
      elif len(word_pos) < 2:
        continue
      else:
        pos.append(word_pos[1])

    iobs = []
    for w in pos:
      if self.is_self_closing_tag(w):
        iob = self.tag2iob(pos, w)
        if iob:
          iobs.append(iob)
    return iobs

  def tag2iob(self, pos, tag):
    # Check if tag is at the beginning or at the end - skip it
    if pos[0] == tag or pos[-1] == tag: return None
    print("POS: {}, TAG: {}".format(pos, tag))
    iob = []
    is_inside = False
    for w in pos:
      if not re.search("<.*>", w):
        if is_inside:
          iob.append("{}/I-T".format(w))
          is_inside = False
        else:
          iob.append("{}/O".format(w))
      elif iob and w == tag:
        iob[-1] = iob[-1].replace('/O', '/B-T')
        is_inside = True
      else:
        # Other tags - skip them
        pass
    return " ".join(iob)
  def is_self_closing_tag(self, tag):
    return re.match('<[^<>]+/>', tag)

if __name__ == "__main__":
  from Config.Config import G_CONFIG
  G_CONFIG.config_logging()

  task = Task(sys.argv[1])
  # Launch RDD parallel processing
  task.get_rdd().mapPartitionsWithIndex(PosTagTask(task)).foreachPartition(Task.save_segments)
  task.finalize()

