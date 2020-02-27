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

import logging
import zipstream
import datetime
from lxml import etree

from TMOutputer.TMOutputerTmx import TMOutputerTmxLxml as TMXO
from TMDbApi.TMTranslationUnit import TMTranslationUnit


class TMXWriter:
  ENCODING = 'utf-8'

  def __init__(self, filename, srclang):
    self.filename = filename
    self.srclang = srclang
    self.out = TMXO()
    self.tmx_files = dict()

  def _init_tree(self):
    tree = etree.ElementTree(etree.Element('tmx', {'version' : "1.4"}))
    etree.SubElement(tree.getroot(), 'header',
                                    { 'creationtool' : "PangeaTM",
                                      'creationtoolversion':"1",
                                      'segtype' : 'sentence',
                                      'o-tmf' : "various",
                                      'adminlang' : "en-US",
                                      'datatype': "PlainText",
                                      'srclang' : self.srclang,
                                      'creationdate' : datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")
                                      })
    body = etree.SubElement(tree.getroot(), 'body')
    return (tree, body)

  # TODO: extract to a separate TMXBuilder class
  def add_segment(self, segment):
    # TODO: pick a file name from list according to a list of requested files
    fname = segment.file_name[0]
    if not fname in self.tmx_files:
      self.tmx_files[fname] = self._init_tree()
    # Append to body
    self.tmx_files[fname][1].append(self.out.output_segment(segment))

  def write(self):
    z = zipstream.ZipFile(compression=zipstream.ZIP_DEFLATED)
    # Pack all TMX files into zip archive
    for fname,(tree,body) in self.tmx_files.items():
      z.writestr(fname, etree.tostring(tree.getroot(), encoding=self.ENCODING, pretty_print=True, xml_declaration=True))
    # Write archive
    with open(self.filename, 'wb') as f:
      for data in z:
        f.write(data)

# Inheriting ZipFile and overriding its iterator method
# to decouple writing files to the archive from closing it.
# FIXME: nasty usage of ZipFile private methods (write & close). Base class should
# be modified as there is no true reason to keep these methods "superprivate"
class MZipFile(zipstream.ZipFile):
  def __iter__(self):
    for kwargs in self.paths_to_write:
      for data in self._ZipFile__write(**kwargs):
        yield data

    self.paths_to_write = []

  def write_close(self):
    for data in self._ZipFile__close():
      yield data


class TMXIterWriter(TMXWriter):

  def __init__(self, filename, srclang):
    super(TMXIterWriter, self).__init__(filename, srclang)
    (tree, body) = self._init_tree()
    tree_str = etree.tostring(tree.getroot(), pretty_print=True).decode(self.ENCODING)
    print(tree_str)
    # Split artificially skeleton into header and footer
    (self.header, self.footer) = tree_str.split('<body/>')
    self.header += '<body>\n'
    self.footer = '\n</body>' + self.footer

    self.z = MZipFile(compression=zipstream.ZIP_DEFLATED)

  def write_iter(self, seg_iter, fname="pangeatm.tmx"):
    def iterable(iter):
     # First, yield the header
     yield self.header.encode(self.ENCODING)
     # Second, yield all segments
     for s in iter:
       #yield ElementTree.tostring(self.out.output_segment(s), encoding=self.ENCODING) + b'\n'
       yield etree.tostring(self.out.output_segment(s), encoding=self.ENCODING, pretty_print=True) + b'\n'


     # Third, yield the footer
     yield self.footer.encode(self.ENCODING)

    #z = zipstream.ZipFile(compression=zipstream.ZIP_DEFLATED)

    self.z.write_iter(fname, iterable(seg_iter))
    for data in self.z:
      yield data

  def write_close(self):
    for data in self.z.write_close():
      yield data

if __name__ == "__main__":
  logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

  tmwriter = TMXWriter('test1.tmx', 'en-US')
  #tmdb.init_db()
  segment = TMTranslationUnit({
             "source_text": "Connect the pipe to the female end of the T.",
             "source_lang": "en-GB",
             "target_text": "Conecte la tubería al extremo hembra de la T.",
             "target_lang": "es-ES",
             "tm_creation_date" : "20090914T114332Z",
             "tm_change_date" : "20090914T114332Z",
             "industry": "Automotive Manufacturing",
             "type": "Instructions for Use",
             "organization":"Pangeanic"
             })
  tmwriter.add_segments([segment])
  tmwriter.write()
