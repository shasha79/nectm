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

#******MeCab tag set
#http://stackoverflow.com/questions/5578791/what-is-the-mecab-output-and-the-tagset

#*****Documents
#https://media.readthedocs.org/pdf/konlpy/v0.4.4/konlpy.pdf
#http://stackoverflow.com/questions/30266239/mecab-output-list-of-name-types

#*****Articles
#http://nlp.stanford.edu/manning/papers/acl08-cws-final.pdf
#http://www.mt-archive.info/10/AMTA-2014-Sudoh.pdf
#http://dl.acm.org/citation.cfm?id=2523059

'''
% mecab
The output format significantly differs from ChaSen, becoming:

['太郎\t名詞,固有名詞,人名,名,*,*,太郎,タロウ,タロー\nは\t助詞,係助詞,*,*,*,*,は,ハ,ワ\nこの\t連体詞,*,*,*,*,*,この,コノ,コノ\n
本\t名詞,一般,*,*,*,,*,*,*,*,二,ニ,ニ\n郎\t名詞,一般,*,*,*,*,郎,ロウ,ロー\nを\t助詞,格助詞,一般,*,*,*,を,ヲ,ヲ\n
見\t動詞,自立,*,*,一段,連用形,見る,ミ,ミ\nた\t助動詞,*,ョセイ,ジョセイ\nに\t助詞,格助詞,一般,*,*,*,に,ニ,ニ\n
渡し\t動詞,自立,*,*,五段・サ行,連用形,渡す,ワタシ,ワタシ\nた\t助動詞,*,*,*,特殊・タ,基本形,た,タ,タ\n。\t記号,句点,*,*,*,*,。,。,。\nEOS\n']

or in English:

Original Form\t
Part of Speech,
Part of Speech section 1,
Part of Speech section 2,
Part of Speech section 3,
Conjugated form,
Inflection,
Reading,
Pronounciation
'''

import Mykytea


class TMMyKyteaTagger():

  def __init__(self):

    opt = "-deftag UNK" # Put UNK when a word doesn't appear in the dictionary

    #Mapping extracted from https://gist.github.com/neubig/2555399
    self.EN_TAGS = {'名詞' : 'N',  # Noun
              '代名詞' : 'PRP',  # Pronoun
              '連体詞' : 'DT',  # Adjectival determiner
              '動詞' : 'V',  # Verb
              '形容詞' : 'ADJ',  # Adjective
              '形状詞' : 'ADJV',  # Adjectival verb
              '副詞' : 'ADV', # Adverb
              '助詞' : 'PRT',  # Particle
              '助動詞' : 'AUXV',  # Auxiliary verb
              '補助記号' : '.',  # Punctuation
              '記号' : 'SYM',  # Symbol
              '接尾辞' : 'SUF',  # Suffix
              '接頭辞' : 'PRE',  # Prefix
              '語尾' : 'TAIL',  # Word tail (conjugation)
              '接続詞' : 'CC',  # Conjunction
              'URL' : 'URL',  # URL
              '英単語' : 'ENG',  # English word
              '言いよどみ' : 'FIL',  # Filler
              'web誤脱' : 'MSP',  # Misspelling
              '感動詞' : 'INT',  # Interjection
              '新規未知語' : 'UNK',  # Unclassified unknown word
    }

    self.tagger = Mykytea.Mykytea(opt)

  def kytea2en_pos(self, symbol):

    if symbol in self.EN_TAGS.keys(): return self.EN_TAGS[symbol]
    else: return 'UNK'

  def tag_segments(self,texts):
    tag = [[[word.split('/')[0], self.kytea2en_pos(word.split('/')[1])] for word in self.tagger.getTagsToString(sentence).split(' ') if word] for sentence in texts]
    return tag

  # Japanese Tokenizer
  #Input: String
  #Output: あなた が よく 振る舞 う 場合 、 私 は あなた に 私 の 車 を 与え ま す 。
  def process(self, text):
    return ' '.join([word for word in self.tagger.getWS(text)])



  if __name__ == "__main__":

    pass
    sentence = ['太郎はこの本を二郎を見た女性に渡した。', '太郎はこの本を二郎を見た女性に渡した。']

    mc = TMMyKyteaTagger()
    mc.tag_segments(sentence)