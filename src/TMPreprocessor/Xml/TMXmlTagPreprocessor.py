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
import logging
import sys
sys.path.append("../..")
from lxml import etree

from TMPreprocessor.Xml.XmlUtils import XmlUtils
from TMPreprocessor.Xml.TMXmlTagTransferBasic import TMXmlTagTransferBasic


class TMXmlTagPreprocessor:

  def __init__(self, langs = ('en', 'es')):
    self.parser = etree.XMLParser(recover=True)
    self.langs = langs # tuple (source language, target language)
    self.tag_transfer_basic = TMXmlTagTransferBasic(langs)

  def process(self, text):
    # Check if there any tags at all
    if not re.search("<.*>", text): return text
    # Keep original text and its stripped version
    org_text = text
    text,stext = XmlUtils.fix_tags(text)
    try:
      #print("ORG TEXT: {}, PARSING: {}".format(org_text, text))
      text = XmlUtils.rename_tags(text)
      for e in self.parser.error_log:
        # Check for certain errors which might create problems in TM and therefore remove all tags at once
        if e.type_name == 'ERR_TAG_NAME_MISMATCH' or e.type_name == 'ERR_TAG_NOT_FINISHED':
          logging.warning("Failed to parse segment text into XML: '{}' reason: {}. Removing tags instead".format(org_text, e))
          return stext

    except Exception as ex:
      logging.warning("Failed to rename tags in {}, reason: {}. Removing tags instead: {}".format(org_text, ex, stext) )
      return stext
    return text

  # Transfer XML tags from source to target string. TODO: integrate deep learning solution here
  # For now, default primitive alighment algorithm (by token)
  def transfer_tags(self, s_txt, t_txt):
    return self.tag_transfer_basic(s_txt, t_txt)


if __name__ == "__main__":
  logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO, stream=sys.stdout)
  pp = TMXmlTagPreprocessor(('en', 'es'))
  text = sys.argv[1]
  print("{} --> {}".format(text, pp.process(text)))

  if len(sys.argv) > 2:
    ttext = pp.transfer_tags(sys.argv[1], sys.argv[2])
    print("*** {} --> {}".format(text, ttext))
