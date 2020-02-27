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
import os, sys
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..'))
import codecs
stopwords_home = os.path.join(os.path.abspath(os.path.join(__file__ ,"../../..")),'tools/stop_words')

from nltk.corpus import stopwords

"""
  @api {INFO} /TMStopWords TMStopWords -- Load list of stopwords for each languages
  @apiName TMStopWords
  @apiVersion 0.1.0
  @apiGroup TMStopWords


  @apiExample {curl} Example & Notes

  # Input: (String) language
  # Output: (List)  list of stopwords

  # Dictionary with language and list of stopwords. Currently, we used the stopword list available in nltk.
    st_dict = {'EN': stopwords.words('english'),
            'ES': stopwords.words('spanish'),
            'FR': stopwords.words('french'),
            'DE': stopwords.words('german')}

  # To include new stopword list for specific language (external file)
    1- Copy the file in tools/stop_words
    2- Create a new entry in "st_dict" e.g. 'new_lang': 'new_list'
    3- Use the fuction "load_stop_words(...)" to load the external list
       Put the following line on the class constructor => if st_list == 'new_list': st_list = self.load_stop_words('new_list')
  * See the constructor as it was add chinise stopword list

"""
class TMStopWords:
  # Available NLTK tokenizer models.
  st_dict = {'EN': stopwords.words('english'),
            'ES': stopwords.words('spanish'),
            'FR': stopwords.words('french'),
            'DE': stopwords.words('german'),
            'PT': stopwords.words('portuguese'),  # portuguese
            'IT': stopwords.words('italian'),
            #'PL': 'tokenizers/punkt/polish.pickle',  # polish
            'NL': stopwords.words('dutch'),  # dutch
            #'ET': 'tokenizers/punkt/estonian.pickle',  # estonian
            'FI': stopwords.words('finnish'),  # finnish
            #'CZ': 'tokenizers/punkt/czech.pickle',  # czech
            'DA': stopwords.words('danish'),  # danish
            #'GR': 'tokenizers/punkt/greek.pickle',  # greek
            'NR': stopwords.words('norwegian'),  # norwegian
            #'SL': 'tokenizers/punkt/slovene.pickle',  # slovene
            'SW': stopwords.words('swedish'),  # swedish
            'TU': stopwords.words('turkish'),  # turkish
            'RU': stopwords.words('russian'), # russian
            'HU': stopwords.words('hungarian'), # hungarian
            'ZH': 'chinese' # extract from https://gist.github.com/dreampuf/5548203
            #'KK': stopwords.words('kazakh'), # kazakh
            }

  def __init__(self, lang):
    self.lang = lang

    st_list = self.st_dict.get(self.lang)

    if st_list == 'chinese': st_list = self.load_stop_words('chinese')

    if not st_list: self.stop_words = []
    self.stop_words = st_list

  def load_stop_words(self,lang):
    st_file = codecs.open(stopwords_home + '/' + lang, 'r')

    return [line.strip('\n') for line in st_file.readlines()]
