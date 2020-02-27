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
import xml.etree.ElementTree as ElementTree
import logging
import datetime

from TMDbApi.TMTranslationUnit import TMTranslationUnit
from TMOutputer.TMOutputer import TMOutputer as Output
from TMDbApi.TMUtils import TMUtils

# <tu srclang="en-GB"
#     creationdate="20090914T114332Z"
#     changedate="20090914T114332Z"
#     tuid="en-GB_es-ES_989946">
# <prop type="tda-industry">Automotive Manufacturing</prop>
# <prop type="tda-type">Instructions for Use</prop>
# <prop type="tda-org">Pangeanic</prop>
# <prop type="tda-prod">Default</prop>
# <tuv xml:lang="en-GB">
# <seg>Connect the pipe to the female end of the T.</seg>
# </tuv>
# <tuv xml:lang="es-ES">
# <seg>Conecte la tubería al extremo hembra de la T.</seg>
# </tuv>
# </tu>
class TMOutputerTmx(Output):
  ElementTree.register_namespace('xml', 'http://www.w3.org/XML/1998/namespace')

  def output_segment(self, segment):
    e = ElementTree.Element('tu')
    e.set('srclang', TMUtils.list2str(segment.source_language))
    dt = segment.tm_creation_date if segment.tm_creation_date else TMUtils.date2str(datetime.datetime.now())
    e.set('creationdate', dt)
    dt = segment.tm_change_date if segment.tm_change_date else TMUtils.date2str(datetime.datetime.now())
    e.set('changedate', dt)
    if segment.tuid:
      e.set('tuid', str(segment.tuid))

    if segment.industry:
      ElementTree.SubElement(e, 'prop', {'type' : "tda-industry"}).text = segment.industry[0]
    if segment.type:  
      ElementTree.SubElement(e, 'prop', {'type' : "tda-type"}).text = segment.type[0]
    if segment.organization:
      ElementTree.SubElement(e, 'prop', {'type' : "tda-org"}).text = segment.organization[0]
    ElementTree.SubElement(e, 'prop', {'type' : "tda-prod"}).text = "Default"

    for t in ['source', 'target']:
      tuv = ElementTree.SubElement(e, 'tuv', {'{http://www.w3.org/XML/1998/namespace}lang' : TMUtils.list2str(getattr(segment, t + '_language'))})
      ElementTree.SubElement(tuv, 'seg').text = getattr(segment, t + '_text')

    return e

from lxml import etree

class TMOutputerTmxLxml(Output):
  etree.register_namespace('xml', 'http://www.w3.org/XML/1998/namespace')

  def output_segment(self, segment):
    e = etree.Element('tu')
    e.set('srclang', TMUtils.list2str(segment.source_language))
    dt = segment.tm_creation_date if segment.tm_creation_date else TMUtils.date2str(datetime.datetime.now())
    e.set('creationdate', dt)
    dt = segment.tm_change_date if segment.tm_change_date else TMUtils.date2str(datetime.datetime.now())
    e.set('changedate', dt)
    if segment.tuid:
      e.set('tuid', str(segment.tuid))
    if segment.username:
      e.set('creationid', segment.username)

    if segment.industry:
      etree.SubElement(e, 'prop', {'type' : "tda-industry"}).text = self.list2str(segment.industry)
    if segment.type:
      etree.SubElement(e, 'prop', {'type' : "tda-type"}).text = self.list2str(segment.type)
    if segment.organization:
      etree.SubElement(e, 'prop', {'type' : "tda-org"}).text = self.list2str(segment.organization)
      etree.SubElement(e, 'prop', {'type' : "tda-prod"}).text = "Default"
    if segment.metadata:
      for prop_type,prop_text in segment.metadata.items():
        if not prop_type.startswith('tda-'): # skip already handled props
          etree.SubElement(e, 'prop', {'type': prop_type}).text = prop_text

    for t in ['source', 'target']:
      tuv = etree.SubElement(e, 'tuv', {'{http://www.w3.org/XML/1998/namespace}lang' : TMUtils.list2str(getattr(segment, t + '_language'))})
      if getattr(segment, t + '_pos'):
        etree.SubElement(tuv, 'prop', {'type': "pos"}).text = getattr(segment, t + '_pos')
      if getattr(segment, t + '_metadata'):
        for prop_type, prop_text in getattr(segment, t + '_metadata').items():
          etree.SubElement(tuv, 'prop', {'type': prop_type}).text = prop_text

      etree.SubElement(tuv, 'seg').text = getattr(segment, t + '_text')

    return e

  def list2str(self, l):
    if not l: return ""
    if not isinstance(l, list): return l
    fl = self.flatten_list(l)
    return " ".join([f for f in fl if f])

  def flatten_list(self, l):
    if l == []:
      return l
    if isinstance(l[0], list):
      return self.flatten_list(l[0]) + self.flatten_list(l[1:])
    return l[:1] + self.flatten_list(l[1:])


if __name__ == "__main__":
  logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

  tmout = TMOutputerTmx()
  #tmdb.init_db()
  segment = TMTranslationUnit({
             "source_text": "Connect the pipe to the female end of the T.",
             "source_lang": "en-GB",
             "target_text": "Conecte la tubería al extremo hembra de la T.",
             "target_lang": "es-ES",
             "creation_date" : "20090914T114332Z",
             "change_date" : "20090914T114332Z",
             "industry": "Automotive Manufacturing",
             "type": "Instructions for Use",
             "organization":"Pangeanic"
             })
  print(ElementTree.tostring(tmout.output_segment(segment)))
