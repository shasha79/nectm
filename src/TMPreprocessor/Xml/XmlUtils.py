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
from lxml import etree

# Various XML processing utils
class XmlUtils:
  TAG_PREFIX = 'T'
  TAG_PATTERN = re.compile('</?{}[0-9]*/?>'.format(TAG_PREFIX))
  TAG_PLACEHOLDER = 'ELASTICTMTAG'
  SPACE_PLACEHOLDER = 'ELASTICTMSPACE'
  parser = etree.XMLParser(recover=True)

  @staticmethod
  def strip_tags(text):
    text = re.sub("</?[^<>]+/?>", ' ', text) # remove doble space
    return re.sub(' +', ' ', text) #re.sub("</?[^<>]+/?>", '', text)

  # Replace tags with a placeholder text
  # TODO: should it be random number to avoid influencing POS tagger as a side effect? )
  @staticmethod
  def replace_tags(text, placeholder=TAG_PLACEHOLDER, adjacent_space_placeholder=None):
    text = re.sub(XmlUtils.TAG_PATTERN, ' ' + placeholder + ' ', text)
    # Replace spaces adjacent to tag with placeholder to make sure we are not losing them
    # during tokenization/MT/detokenization
    # <a>20 </a><b>Novemver</b> 2016   --> <a> 20 SPACE </a> <b> November </b> SPACE 2016
    if adjacent_space_placeholder:
      # replace spaces right to a tag
      text = re.sub('(\S+)\s{2}' + placeholder, '\\1 ' + adjacent_space_placeholder + ' ' + placeholder, text)
      text = re.sub(placeholder + '\s+' + adjacent_space_placeholder + '\s+' + placeholder,
                    placeholder + ' ' + placeholder, text)

      # replace spaces left to a tag
      text = re.sub(placeholder + '\s{2}(\S+)', placeholder + ' ' + adjacent_space_placeholder + ' \\1', text)
      text = re.sub(placeholder + '\s+' + adjacent_space_placeholder + '\s+' + placeholder,
                    placeholder + ' ' + placeholder, text)

    return text

  @staticmethod
  def extract_tags(text):
    return re.findall("</?[^<>]+/?>", text)

  # I have <X[1]>a dog</X[1]> ---> I have <T1>a dog</T1>
  @staticmethod
  def simplify_tags(text):
    if not re.search("<.*>", text): return text
    return XmlUtils.rename_tags(XmlUtils.fix_tags(text)[0])

  # i = 'Hola <b> esto </b> es una <T1> prueba </T1>' --> '(</?[^<>]+/?>)([^<>]+)(</?[^<>]+/?>)' --> join words with tags
  # i = '< T1 >' or i = < /T1 >
  @staticmethod
  def join_tags(text, in_pattern):
    pattern = re.compile(in_pattern)
    all_tags = re.findall(pattern, text)  # [('<b>', ' esto ', '</b>'), ('<T1>', ' prueba ', '</T1>')]
    for e in all_tags:
      n_string = e[0] + e[1].strip() + e[2]
      text =  text.replace(''.join(e), n_string)#re.sub(''.join(e), n_string, text) # Hola <b>esto</b> es una <T1>prueba</T1>
    return text

  @staticmethod
  def reduce_tags(in_str):  # langs --> ('en', 'es')
    simplified_text = re.sub(re.compile('</?{}[0-9]*/?>'.format('T')), ' T ', in_str)
    return re.sub("\s\s+", " ", simplified_text)  # Yo tengo un <b>gato</b>. Yo tengo un T gato T.


  # Quick & dirty - replace all tag names with TAG_PREFIX to avoid invalid tag names error during parsing
  # return tuple - text with renamed tags and text stripped of tags
  @staticmethod
  def fix_tags(text):
    status = 'O'
    otext = ''
    stext = ''
    for i in range(0, len(text)):
      c = text[i]
      nc = text[i + 1] if i < len(text) - 1 else ''
      pc = text[i - 1] if i > 0 else ''
      if c == '<':
        status = 'I'
        otext += c
        if nc == '/':
          otext += nc
      elif c == '>':
        otext += XmlUtils.TAG_PREFIX
        if pc == '/': otext += pc
        otext += c
        status = 'O'
      elif status != 'I':
        otext += c
        stext += c
    return otext, stext

  # Rename tags using DFS order index
  @staticmethod
  def rename_tags(text):
    tree = etree.fromstring("<root>" + text + "</root>", XmlUtils.parser)
    i = 1
    # Remove redundant tags
    XmlUtils.reduce_tree(tree)
    for e in tree.iterdescendants():
      new_tag = XmlUtils.TAG_PREFIX + str(i)
      try:
        e.tag = new_tag
        e.attrib.clear()
      except AttributeError:
        # For processing instruction or comment, replace the whole element
        pe = e.getparent()
        pe.replace(e, pe.makeelement(new_tag))
      i += 1
    text = etree.tostring(tree, with_tail=True, encoding='utf-8')[len("<root>"):-len("</root>")]
    return text.decode('utf-8')

  # Reduce tag tree by removing tags which doesn't bring additional info
  @staticmethod
  def reduce_tree(tree):
    num_children = 0
    for e in tree.getchildren():
      num_children += 1
      XmlUtils.reduce_tree(e)
    # Case when <T1> <T2> ,,,, </T2> </T1>, replace T1 with T2
    if num_children == 1 and XmlUtils.is_empty_tag(tree):
      pe = tree.getparent()
      if pe is not None: pe.replace(tree, tree.getchildren()[0])
    else:
      # Case: <T1/> <T2/>, replace with <T1/>
      self_closing = []
      to_delete = []
      for e in tree.getchildren():
        if XmlUtils.is_self_closing_tag(e):  # self-closing tag: <T1/>
          self_closing.append(e)
        else:
          # If more than one adjustant self-closing tag, leave only the first one
          if len(self_closing) > 1:
            to_delete += self_closing[1:]
          self_closing.clear()
      # Last round
      # If more than one adjustant self-closing tag, leave only the first one
      if len(self_closing) > 1:
        to_delete += self_closing[1:]
      # Delete found redundant tags
      for e in to_delete:
        tree.remove(e)
    return tree

  @staticmethod
  def recover_tags_pos(text_pos, tags_input):
    tags = list(tags_input)
    pos_with_tags = []
    pos = []
    for word_pos in text_pos:
      # Contatenate POS tags and XML tags
      if word_pos[0] == XmlUtils.TAG_PLACEHOLDER:
        pos_with_tags.append(tags.pop(0))
      elif len(word_pos) < 2:
        continue
      else:
        pos_with_tags.append(word_pos[1])
        pos.append(word_pos[1])
    return pos_with_tags,pos

  @staticmethod
  def is_empty_tag(e):
    if (not e.text or not e.text.strip()) and \
            (not e.tail or not e.tail.strip()): return True
    return False

  @staticmethod
  def is_self_closing_tag(e):
    if isinstance(e, str):
      return re.search('<[^<>]+/>', e)
    if not e.text and (not e.tail or not e.tail.strip()): return True
    return False


  @staticmethod
  def is_opening_tag(e):
    return re.search('<[^<>/]+>', e)
