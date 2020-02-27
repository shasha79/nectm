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
from lxml import etree
import zipfile
import os
import sys
import logging
import re
from io import StringIO
import chardet

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

dtd_path = os.path.join(os.path.abspath(os.path.join(__file__ ,"../../..")),'tools/validate_tmx/tmx14.dtd')

from TMDbApi.TMTranslationUnit import TMTranslationUnit
from TMDbApi.TMUtils import TMUtils
from TMPreprocessor.Xml.TMXmlTagPreprocessor import TMXmlTagPreprocessor
class TMXParser():
  NS = 'http://www.w3.org/XML/1998/namespace'

  def __init__(self, fname, domain = None, lang_pairs=[], username=None):
    self.fname = fname #path + TMX file (may be zipped)
    self.domain = domain #TMX domain
    self.lang_pairs = lang_pairs
    self.username = username
    self.dtd_file = etree.DTD(open(dtd_path, 'rb'))

    self.tags_pp = TMXmlTagPreprocessor()

  # Get all language pairs from TMX
  def language_pairs(self):
    segments = []
    language_pairs = set()
    for segment in self.parse():
      langs_before = len(language_pairs)
      language_pairs.add((segment.source_language, segment.target_language))
      if langs_before == len(language_pairs): # no new pairs added -> stop
        break
    return list(language_pairs)

  def parse(self):
    logging.warning("Parsing {}, language pairs: {}".format(self.fname, self.lang_pairs))
    fname, fext = os.path.splitext(self.fname)
    if fext == '.zip':
      zip = zipfile.ZipFile(self.fname, 'r')
      tmx_fnames = zip.namelist()
    else:
      zip = None
      tmx_fnames = [self.fname]

    for tmx_fname in tmx_fnames:
      self.tmx_fname = os.path.basename(tmx_fname)
      if self.tmx_fname:
        tmx_file = zip.open(tmx_fname) if zip else open(tmx_fname, mode="rb")
        context = etree.iterparse(tmx_file, events=('end',), tag='tu')  #, dtd_validation=True, load_dtd=False remove_comments = True, remove_blank_text = True, no_network = True
        try:
          i = 0
          for segment in self._iterate(context): # If found any invalid part in xml, stop the process
            if not i % 5000:
              logging.warning("Parsed {} segments".format(i))
              logging.info("Sample segment: {}".format(segment.to_dict()))
            i += 1
            yield segment
        except etree.XMLSyntaxError:  # check if file is well formed
          logging.info('Skipping invalid XML {}'.format(self.tmx_fname))

  def _iterate(self,context):
    # Extract from --> http:/text/www.ibm.com/developerworks/xml/library/x-hiperfparse/
    for event, elem in context:
        for seg in self._parse_tm(elem):
          yield seg
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]
    del context

  def _parse_tm(self, element):
    seg_dict = {}
    seg_dict['domain'] = self.domain
    seg_dict['file_name'] = self.tmx_fname

    seg_dict['tm_creation_date'] = element.attrib.get('creationdate')
    seg_dict['tm_change_date'] = element.attrib.get('changedate')
    seg_dict['tuid'] = element.attrib.get('tuid')

    # Extract few properties into several fields
    list_Prop = element.xpath('prop')
    dict_Prop = dict([(e.attrib.get('type'), e.text) for e in list_Prop])
    seg_dict['industry'] = dict_Prop.get('tda-industry')
    seg_dict['type'] = dict_Prop.get('tda-type')
    seg_dict['organization'] = dict_Prop.get('tda-org')

    # Parse all properties into metadata dict field
    seg_dict['metadata'] = self._parse_metadata(element)

    tuv = element.xpath('tuv')
    seg = element.xpath('tuv/seg')

    if self.username:
      seg_dict['username'] = self.username

    # Generate segments with all regquested language pairs
    lang_dict_gen = [self._fill_lang(tuv, seg)] if not self.lang_pairs else self._gen_lang_pairs(tuv, seg)
    for d in lang_dict_gen:
      segment = TMTranslationUnit() # TODO: use object pool to avoid new object creation
      seg_dict.update(d)
      segment.reset(seg_dict)
      if not segment.source_id or not segment.target_id:
        logging.warning("Skipping empty ( after processing ) segment: {}".format(segment.to_dict()))
        continue
      yield segment


  def _gen_lang_pairs(self, tuv, seg):
    # Get all languages in the given tu
    lang_map = dict()
    for tu, seg in zip(tuv, seg):
      #lang = TMUtils.lang2short(tu.attrib.get('{%s}lang' % self.NS))
      lang = TMUtils.lang2short((self._get_lang(tu)))#(tu.attrib.get('lang'))
      if not lang in lang_map: lang_map[lang] = []
      lang_map[lang].append((tu, seg))

    # Generate all requested pairs (note: one tu can contain multiple translations for
    # the same language
    for s_lang, t_lang in self.lang_pairs:
      for s_tuv, s_seg in lang_map.get(s_lang, []):
        for t_tuv, t_seg in lang_map.get(t_lang, []):
          yield self._fill_lang((s_tuv, t_tuv), (s_seg, t_seg))

  def _get_lang(self, tu):
    lang = tu.attrib.get('{%s}lang' % self.NS)
    if lang is None:
      lang = tu.attrib.get('lang')
    return lang


  def _fill_lang(self, tuv, seg):
    d = dict()
    d['source_language'] = TMUtils.lang2short(self._get_lang(tuv[0]))#tuv[0].attrib.get('lang')#get('{%s}lang' % self.NS)
    d['target_language'] = TMUtils.lang2short(self._get_lang(tuv[1])) #tuv[1].attrib.get('lang')#get('{%s}lang' % self.NS)

    d['source_text'] = self._get_text(seg[0])
    if isinstance(d['source_text'], bytes):
      d['source_text'] = d['source_text'].decode('utf8').encode('utf8')

    d['target_text'] = self._get_text(seg[1])
    if isinstance(d['target_text'], bytes):
      d['target_text'] = d['target_text'].decode('utf8').encode('utf8')

    d['source_metadata'] = self._parse_metadata(tuv[0])
    d['target_metadata'] = self._parse_metadata(tuv[1])
    return d

  def _get_text(self, seg):
    text = ""
    for t in seg.itertext():
      text += t
    text = self.tags_pp.process(text)
    return text

  def _parse_metadata(self, element):
    props = element.xpath('prop')
    metadata = {}
    for prop in props:
      prop_type = prop.attrib.get('type')
      metadata[prop_type] = prop.text
    return metadata

if __name__ == "__main__":
  logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO, stream=sys.stdout)
  parser = TMXParser(sys.argv[1])
  for segment in parser.parse():
    print("SEGMENT: {}".format(segment.__dict__))
