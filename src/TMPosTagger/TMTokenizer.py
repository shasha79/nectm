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

import subprocess
import shlex
import re
import pexpect


from nltk.tokenize.stanford_segmenter import StanfordSegmenter
from nltk import tokenize
from TMPosTagger.TMJapanesePosTagger import TMMyKyteaTagger
from TMPreprocessor.Xml.XmlUtils import XmlUtils
from TMPosTagger.ExternalDetokenizer.TMDetokenizer import Detokenizer

pragmatic_segmenter_home = os.path.join(os.path.abspath(os.path.join(__file__, "../..")), 'tools/pragmatic_segmenter-master/')
moses_tokenizer_home = os.path.join(os.path.abspath(os.path.join(__file__, "../..")), 'tools/mosesdecoder-master/scripts/tokenizer/')
stanford_tokenizer_home = os.path.join(os.path.abspath(os.path.join(__file__ ,"../..")),'tools/stanford-segmenter-2015-12-09/')

TAG_PREFIX = 'T'  # Paterns to join tags that tokenized split
TOK_PATTERN = re.compile('< /?{}[0-9]*/? >'.format(TAG_PREFIX))
JOIN_PATTERN = '(<)( /?T[0-9]+/? )(>)'

class TMStanfordTokenizer():

  models = {'ZH': 'ctb.gz',
            'AR' : 'arabic-segmenter-atb+bn+arztrain.ser.gz'}

  dics = {'ZH': 'dict-chris6.ser.gz',
         'AR': ''}

  def __init__(self, language):

    self.language = language

    model = self.models.get(language)
    dic = self.dics.get(language)
    if not model: raise (Exception("Unsupported language for tokenizer: {}".format(language)))

    # Initialize Stanford Tokenizer
    self.tm_tokenize = StanfordSegmenter(path_to_jar = os.path.join(stanford_tokenizer_home, 'stanford-segmenter-3.6.0.jar'),
                                 path_to_model = os.path.join(stanford_tokenizer_home, 'data', model),
                                 path_to_dict = os.path.join(stanford_tokenizer_home, 'data', dic),
                                 path_to_sihan_corpora_dict = os.path.join(stanford_tokenizer_home, 'data'),
                                 path_to_slf4j = os.path.join(stanford_tokenizer_home, 'slf4j-api.jar')
                                )
  #Input: String
  #Output: 这 是 斯坦福 中文 分词 器 测试
  def process(self,sentences):
    text = self.tm_tokenize.segment(sentences).strip('\n')
    if re.search(TOK_PATTERN, text):  # Check if the text have tags
      text = XmlUtils.join_tags(text, JOIN_PATTERN)
    return text

  def tokenize_sent(self, text):
    if self.language == 'ZH':
      return [s +'。' for s in text.split('。') if s] # Split by sentence chinese
    #self.tm_tokenize.segment_sents(text)
    return [text]

class TMNLTKTokenizer():
  # Available NLTK tokenizer models.
  models = {'EN': 'tokenizers/punkt/english.pickle',
            'ES': 'tokenizers/punkt/spanish.pickle',
            'FR': 'tokenizers/punkt/french.pickle',
            'DE': 'tokenizers/punkt/german.pickle',
            'PT': 'tokenizers/punkt/portuguese.pickle', #portuguese
            'IT': 'tokenizers/punkt/italian.pickle',
            'PL': 'tokenizers/punkt/polish.pickle',  # polish
            'NL': 'tokenizers/punkt/dutch.pickle',  # dutch
            'ET': 'tokenizers/punkt/estonian.pickle',  # estonian
            'FI': 'tokenizers/punkt/finnish.pickle',  # finnish
            'CS': 'tokenizers/punkt/czech.pickle',  # czech
            'CZ': 'tokenizers/punkt/czech.pickle',  # czech
            'DA': 'tokenizers/punkt/danish.pickle',  # danish
            'EL': 'tokenizers/punkt/greek.pickle',  # greek
            'NO': 'tokenizers/punkt/norwegian.pickle',  # norwegian
            'SL': 'tokenizers/punkt/slovene.pickle',  # slovene
            'SV': 'tokenizers/punkt/swedish.pickle',  # swedish
            'TU': 'tokenizers/punkt/turkish.pickle',  # turkish
            }

  def __init__(self, language):

    self.language = language

    model = self.models.get(self.language)

    if not model: raise (Exception("Unsupported language for Tokenizer: {}".format(language)))
    self.tokenizer = tokenize

  # Split by sentence and words (returns list of lists)
  # Output --> ['Ciao meraviglioso e perfetto mondo!', 'Ciao meraviglioso.'] --> List with the sentence, If only one sentence the list was only one element
  def tokenize_sent(self, text):
    # **********load tokenizer according to the language
    nltk_model = self.models.get(self.language).split('/')[2].split('.')[0]
    return self.tokenizer.sent_tokenize(text,nltk_model)

  #Return a tokenizer text
  #Input: String
  #Output --> Ciao meraviglioso e perfetto mondo !
  def process(self, text):
    # **********load tokenizer according to the language
    nltk_model = self.models.get(self.language).split('/')[2].split('.')[0]
    text = ' '.join(self.tokenizer.word_tokenize(text, nltk_model))
    if re.search(TOK_PATTERN, text):  # Check if the text have tags
      text = XmlUtils.join_tags(text, JOIN_PATTERN)
    return text

    # Class to split in sentences

'''
    @api {INFO} /TMPragmatic TMPragmatic -- Split sentences with punctation (".").
    @apiName TMPragmatic
    @apiVersion 0.1.0
    @apiGroup TMTokenizer


    @apiParam {String} language sentences language.

    @apiSuccess {List} split_sentence List of sentences split by punctuation.

    @apiExample {curl} Example & Notes

    # Input: Hello world. My name is Mr. Smith. I work for the U.S. Government and I live in the U.S. I live in New York.
    # Output: ['Hello world.', 'My name is Mr. Smith.', 'I work for the U.S. Government and I live in the U.S.', 'I live in New York.']

    # The class execute a ruby command line to split the sentences

    # TMPragmatic diretory is in tools/pragmatic_segmenter-master/
'''
class TMPragmatic():

  def __init__(self, language):

    self.args = 'ruby ' + pragmatic_segmenter_home + 'segmenter.rb ' + language.lower()

  # Input: Hello world. My name is Mr. Smith. I work for the U.S. Government and I live in the U.S. I live in New York.
  # Output: ['Hello world.', 'My name is Mr. Smith.', 'I work for the U.S. Government and I live in the U.S.', 'I live in New York.']
  def tokenize_sent(self, text):
      sentences = pexpect.run(self.args + ' ' '"' + text + '"', withexitstatus=False)
      text = [sent for sent in sentences.decode("utf-8").split('\r\n') if sent]
      return text

class TMNLTKTokenizerGeneric():

  def __init__(self, language):
    self.tokenizer = tokenize
    self.sentence = TMNLTKTokenizer('EN')#TMPragmatic(language)

  def process(self, text):
    text = ' '.join(self.tokenizer.wordpunct_tokenize(text))
    if re.search(TOK_PATTERN, text):  # Check if the text have tags
      text = XmlUtils.join_tags(text, JOIN_PATTERN)
    return text

  def tokenize_sent(self, text):
    return self.sentence.tokenize_sent(text)

class TMMosesTokenizer():

  def __init__(self, language):

    #-protected --> specify file with patters to be protected in tokenisation (URLs, etc)
    #-no-escape --> don't perform HTML escaping on apostrophy, quotes
    self.args = shlex.split(moses_tokenizer_home + 'tokenizer.perl -protect -no-escape -l ' + language.lower())
    #self.tokenizer = Popen(self.args, stdin=PIPE, stdout=PIPE)

  #Input: String
  #Output: Esto es un problema muy grande y complicado .
  def process(self, text):
    #Probably if good transform the input text in ' ' + text + '\n'

    tokenizer = subprocess.Popen(self.args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    tok_sents, tok_exc = tokenizer.communicate(input = text.encode('utf8'))
    tokenizer.wait()
    text = (tok_sents.decode("utf-8")).strip('\n')

    if re.search(TOK_PATTERN, text):  # Check if the text have tags
      text = XmlUtils.join_tags(text, JOIN_PATTERN)
    return text

  def tokenize_sent(self, text):
    return [text]

'''
class TMTokenizerTemplate():

  def __init__(self, language):
    self.tokenizer
    self.sentence =

  def process(self, text): #
    return text_word

  def tokenize_sent(self, text):
    return text_sent
'''

"""
  @api {INFO} /TMTokenizer TMTokenizer -- Available Tokenizer models. This class initializes the available models
  @apiName TMTokenizer
  @apiVersion 0.1.0
  @apiGroup TMTokenizer


  @apiExample {curl} Input & Output:

  # Input: (String) language
  # Output: (Object) tokenizer model
  # Error: Unsupported language for Tokenize. This messages appear on uwsgi.log
  * The error messages appear on uwsgi.log

  # The tokenizer models:
    - split sentences with punctation (".") => function "tokenize_sent(self, text)"
      Example
      #Input: 'Labas pasauli. Mano vardas yra p Smithas. Dirbu su JAV vyriausybe ir aš gyventi į JAV, gyvenu Niujorke.'
      #Output: ['Labas pasauli.', 'Mano vardas yra p Smithas.', 'Dirbu su JAV vyriausybe ir aš gyventi į JAV, gyvenu Niujorke.']

    - split into individual words => function "process(self, text)"
      Example
      # Input: '3. 土著知识扎根于土著社区的文化传统和长期习俗。'
      # Output: ' 3 . 土著 知识 扎 根于 土著 社区 的 文化 传统 和 长期 习俗 。'

  @apiExample {curl} Example & Notes

  # List of available class and tokenizer tool
  # - TMMosesTokenizer => Moses (Not currently used)
  # - TMNLTKTokenizerGeneric => Based on regular expression to split into individual words and the TMPragmatic class to split into sentences.
  # - TMStanfordTokenizer => Stanfornd Tokenizer. Currently is used for chinese and arabic. It's very slow.
  # - TMNLTKTokenizer => NLTK

  # All the class must implement a function "process(self, text)" to split the sententes into individual words
  # and "tokenize_sent(self, text)" to split sentences with punctation (".").

  * Search "split by Sentences" on uwsgi.log to see the segmentation with punctation (".").

  To include new tokenizer for other languages
  1- Define the model for new language
  models = {'EN': 'nltk',
            'RU': 'generic',
            'ZH': 'stanford',
            'HH': 'tokenizerTemplate',
  2- Create the class to execute the new model
   if self.models == 'tokenizerTemplate':
      self.tokenizer = TMTokenizerTemplate(language)

  * See the class TMTokenizerTemplate in TMTokenizer file to add other tokenizer

"""
# 'generic' tokenizer use the Pragmatic class to split by sentences. I do that, because the some language that chinese for example, that use Stanford to word and sentence tokenizer
# then if I create a differente class to tokenizer and split sentence I will to execute the Stanford tokenizer in two time and is very expensive.
class TMTokenizer():
  # There are others languages avaliable in moses and nltk.
  # Moses --> look out --> moses/scripts/share/nonbreaking-prefixes
  # Nltk --> look out --> nltk_data/tokenizers/punkt
  models = {'EN': 'nltk', # --> moses
            'ES': 'nltk', #--> moses
            'FR': 'nltk', #--> moses
            'DE': 'nltk', # german #--> moses
            'IT':  'nltk',#'moses',  # italian
            'PT': 'nltk',  # portuguese #--> moses
            'PL': 'nltk',  # polish  #--> moses
            'RU': 'generic',  # russian --> #'moses',
            'BG': 'generic',  # bulgarian
            'NL': 'nltk',  # dutch #--> moses
            'ET': 'nltk',  # estonian
            'FI': 'nltk',  # finnish
            'CR': 'generic', #'KoNLPy',  # korean
            'JA': 'kytea',  # Japanese
            'ZH': 'stanford', # chinese
            'AR': 'generic', # arabic
            'CZ': 'nltk', # czech
            'CS': 'nltk',  # czech
            'DA': 'nltk', # danish
            'EL': 'nltk', # greek --> moses
            'NO': 'nltk', # norwegian
            'SL': 'nltk', # slovene --> moses
            'SV': 'nltk', # swedish --> moses
            'TU': 'nltk', # turkish
            'HE': 'generic', #hb
            'GA': 'generic', # Irish --> moses
            'HU': 'generic', # hungarian --> moses
            'LT': 'generic',  # Lithuanian
            'LV': 'generic', # Latvian --> moses
            'MT': 'generic', # Maltese
            'RO': 'generic', # Romanian --> moses
            'SK': 'generic', # Slovak
            'IS': 'generic',  # Icelandic --> moses
            'HR': 'generic' # Croatian

          }

  def __init__(self, language):
    language = language.upper()
    # Available Tokenizer models. TODO: fill entries for other languages

    self.tool = self.models.get(language.upper())

    if not self.tool: raise (Exception("Unsupported language for Tokenize: {}".format(language)))
    if self.tool == 'stanford':
    # Initialize Stanford
      self.tokenizer = TMStanfordTokenizer(language)
    # Initialize NLTK
    if self.tool == 'nltk':
      self.tokenizer = TMNLTKTokenizer(language)
    # Initialize kytea
    if self.tool == 'kytea':
      self.tokenizer = TMMyKyteaTagger()
    # Initialize Moses
    if self.tool == 'moses':
      self.tokenizer = TMMosesTokenizer(language)
    #Initialize Generic Tokenizer
    if self.tool == 'generic':
      self.tokenizer = TMNLTKTokenizerGeneric(language)

  def un_tokenizer(self, in_text):
    my_puntation_list = ['!', '"', '#', '$', '%', '&', "'", ')', '*', '+', ',', '-', '.', ':', ';', '<', '=', '>', '?', '@',
                         '\\', ']', '^', '_', '`', '|', '}', '~', '。', '，', '；', '、']
    if isinstance(in_text, bytes):
      in_text = in_text.decode('utf8')
      text = ("".join([" " + i if not i.startswith("'") and i not in my_puntation_list else i for i in in_text]).strip()).encode('utf8')
    else:
      text = ("".join([" " + i if not i.startswith("'") and i not in my_puntation_list else i for i in in_text]).strip())
    text = re.sub('\( ', '(', text)
    text = re.sub('\[ ', '[', text)
    text = re.sub('\{ ', '{', text)
    text = re.sub('\/ ', '/', text)
    text = re.sub(' \/', '/', text)
    return text

  # Class to split in sentences
  class TMPragmatic():

    def __init__(self, language):

      args = shlex.split('ruby ' + pragmatic_segmenter_home + 'segmenter.rb ' + language.lower())
      self.segmenter = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

      # Input:
          # text = 'Labas pasauli. Mano vardas yra p Smithas. Dirbu su JAV vyriausybe ir aš gyventi į JAV, gyvenu Niujorke.'
        # lang = 'lt'
      #Output: ['Labas pasauli.', 'Mano vardas yra p Smithas.', 'Dirbu su JAV vyriausybe ir aš gyventi į JAV, gyvenu Niujorke.']

    def tokenize_sent(self, text):
      sentences, tok_exc = self.segmenter.communicate(text.encode('utf8'))
      return [sent for sent in sentences.decode("utf-8").split('\n') if sent]

"""
  @api {INFO} /TMUNTokenizer TMUNTokenizer -- Initialize available Detokenizer models.
  @apiName TMUNTokenizer
  @apiVersion 0.1.0
  @apiGroup TMTokenizer
  @apiPermission admin

  @apiExample {curl} Input & Output:

  # Input:
    (String) language
    (List) List of words.
  # Output: (String) Detokenizer sentence

  # To include new detokenizer for other languages change the function un_tokenizer(self, in_text)
  # Currently, we used  "en" rules to detokenizer several language. We use specific rules to detokenizer english, japanese, italian and czench
"""
class TMUNTokenizer():
    # Use moses untokenizer TODO: fill entries for other languages
  models = {'EN': 'en',  # --> moses
              'ES': 'en',  # --> moses
              'FR': 'fr',  # --> moses
              'DE': 'en',  # german #--> moses
              'IT': 'it',  # 'moses',  # italian
              'PT': 'en',  # portuguese #--> moses
              'PL': 'en',  # polish  #--> moses
              'RU': 'en',  # russian --> #'moses',
              'BG': 'en',  # bulgarian
              'NL': 'en',  # dutch #--> moses
              'ET': 'en',  # estonian
              'FI': 'fi',  # finnish
              'CR': 'en',  # 'KoNLPy',  # korean
              'JA': 'kytea',  # Japanese
              'ZH': 'en',  # chinese
              'AR': 'en',  # arabic
              'CZ': 'en',  # czech
              'CS': 'cs',  # czech
              'DA': 'en',  # danish
              'EL': 'en',  # greek --> moses
              'NO': 'en',  # norwegian
              'SL': 'en',  # slovene --> moses
              'SV': 'en',  # swedish --> moses
              'TU': 'en',  # turkish
              'HE': 'en',  # hb
              'GA': 'en',  # Irish --> moses
              'HU': 'en',  # hungarian --> moses
              'LT': 'en',  # Lithuanian
              'LV': 'en',  # Latvian --> moses
              'MT': 'en',  # Maltese
              'RO': 'en',  # Romanian --> moses
              'SK': 'en',  # Slovak
              'IS': 'en',  # Icelandic --> moses
              'HR': 'en'  # Croatian
     }

  def __init__(self, language):

    self.language = language.upper()
    if self.language == 'ZH' or self.language == 'AR' or self.language == 'CR':
      self.tool = Detokenizer(options={'language':language})

  def un_tokenizer(self, in_text):
    if self.language == 'ZH' or self.language == 'AR' or self.language == 'CR':
      return self.tool.detokenize(' '.join(in_text))
    else:
      my_puntation_list = ['!', '"', '#', '$', '%', '&', "'", ')', '*', '+', ',', '-', '.', ':', ';', '<', '=', '>',
                             '?', '@',
                             '\\', ']', '^', '_', '`', '|', '}', '~', '。', '，', '；', '、']
      if isinstance(in_text, bytes):
        in_text = in_text.decode('utf8')
        text = ("".join(
            [" " + i if not i.startswith("'") and i not in my_puntation_list else i for i in in_text]).strip()).encode(
            'utf8')
      else:
        text = (
          "".join([" " + i if not i.startswith("'") and i not in my_puntation_list else i for i in in_text]).strip())
      text = re.sub('\( ', '(', text)
      text = re.sub('\[ ', '[', text)
      text = re.sub('\{ ', '{', text)
      text = re.sub('\/ ', '/', text)
      text = re.sub(' \/', '/', text)
      return text


  '''
  # Receive a list of words, return a string
  def un_tokenizer(self, text):
    return self.tool.detokenize(' '.join(text))
  '''

