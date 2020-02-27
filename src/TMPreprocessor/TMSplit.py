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

from nltk import RegexpChunkParser
from nltk.chunk.regexp import ChunkRule, SplitRule
from nltk.tree import Tree

from TMMatching.TMTextProcessors import TMTextProcessors
from TMMatching.TMUtilsMatching import TMUtilsMatching
from TMDbApi.TMUtils import TMTimer
import logging

"""
  @api {INFO} /TMSplit RulesPattern -- Class to instantiate the rigth and left pattern to split the sentences. This patterns are useful to create the Tree structure.
  @apiName RulesPattern
  @apiVersion 0.1.0
  @apiGroup TMSplit

  @apiExample {curl} Input & Output:

  # Input:
    (Regular Expression) left pattern
    (Regular Expression) Right pattern
    (Regular Expression) Marks pattern (how split)

 """
class RulesPattern():
  def __init__(self, w_pattern, w_split_left, w_split_right):

    self._pattern = ChunkRule(w_pattern, 'chunk compose clause between conjunction')
    self._split = SplitRule(right_tag_pattern=w_split_right, left_tag_pattern=w_split_left,
                            descr='split the subordinate clause')

  def get_rule_obj(self):
    return [self._pattern, self._split]

  """
   @api {INFO} /TMSplit EnglishRules -- Create a set of rules to split English sentences. Combined posTag and words.
   @apiName EnglishRules
   @apiVersion 0.1.0
   @apiGroup TMSplit

   @apiExample {curl} Input & Output:

  # Input:
    (String) language
  # Output:
    (List) list of English stopwords
    (Dictionary) Set of rules. Each entry of the dictionary contain a "RulesPattern" object.
    (List) List with English universal posTag Map

  * "RulesPattern" is a generic class to specified the patterns to split (left pattern --- split mark --- right pattern)

  * The output of this class are a set of resource and rules to split sentence of specific language.

   @apiExample {curl} Example & Notes

   => Example of rules to split English sentences.
   Split the sentences considered: Conjunctions, punctuation marks and wh_words

   self.rules = {
     'conjunction': RulesPattern('<.*>*<V.*><.*>*<CC><.*>*<V.*><.*>*', '<.*>*<V.*><.*>*', '<CC><.*>*<V.*><.*>*'), #, '<CC>','',''
     'last': RulesPattern('<.*>*<V.*><.*>*<WDT|WP|WRB|IN/that><.*>*<V.*><.*>*',
                                 '<.*>*<V.*><.*>*', '<WDT|WP|WRB|IN/that><.*>*<V.*><.*>*'),
     'comma': RulesPattern('<.*>*<V.*><.*>*<\,|\;|\:|\-><.*>*<V.*><.*>*', '<.*>*<V.*><.*>*',
                               '<\,|\;|\:|\-><.*>*<V.*><.*>*'), #, '<\,|\;|\:|\->', '', ''
   }

  => Example of generic rule

  self.rules = {
    'last': RulesPattern('<.*>*<VERB><.*>*<CONJ|SCONJ><.*>*<VERB><.*>*',  # conjunctions
                                      '<.*>*<VERB><.*>*', '<CONJ><.*>*<VERB><.*>*'),
    'comma': RulesPattern('<.*>*<VERB><.*>*<\.><.*>*<VERB><.*>*', '<.*>*<VERB><.*>*',
                                '<\.><.*>*<VERB><.*>*'),  # comma
        }

  => It's possible create rules for others language, but all the rules must be based on posTag annotation. Use TemplateRule() for that.
  """

class EnglishRules():

  def __init__(self):  # language,#
    self.order = ['comma', 'conjunction', 'compose_sub', 'last'] # 'subordinate', --> Last = subordinate

    self.sw = TMUtilsMatching.check_stopwords('EN') #TMTextProcessors.stop_words('english') #stopwords.words('english')
    self.ut = TMTextProcessors.univ_pos_tagger('EN') #TMUniversalPosTag('EN')
    self.rules = {
                                              #pattern ---> left ---> right
      'conjunction': RulesPattern('<.*>*<V.*><.*>*<CC><.*>*<V.*><.*>*', '<.*>*<V.*><.*>*', '<CC><.*>*<V.*><.*>*'), #, '<CC>','',''
      'last': RulesPattern('<.*>*<V.*><.*>*<WDT|WP|WRB|IN/that><.*>*<V.*><.*>*',
                                  '<.*>*<V.*><.*>*', '<WDT|WP|WRB|IN/that><.*>*<V.*><.*>*'),
      'compose_sub': RulesPattern('<.*>*<V.*><.*>*<CC|\,|\;|\:|\-><WDT|WP|WRB|IN/that><.*>*<V.*><.*>*',
                                  '<.*>*<V.*><.*>*', '<CC|\,|\;|\:|\-><WDT|WP|WRB|IN/that><.*>*<V.*><.*>*'),
      # --> wh_words               <V> <NP|PP>*
      'comma': RulesPattern('<.*>*<V.*><.*>*<\,|\;|\:|\-><.*>*<V.*><.*>*', '<.*>*<V.*><.*>*',
                                '<\,|\;|\:|\-><.*>*<V.*><.*>*'), #, '<\,|\;|\:|\->', '', ''
    }

class EnglishGenericRules():
  def __init__(self):  # language,#
    self.order = ['comma', 'last']# 'conjunction',

    self.sw = TMUtilsMatching.check_stopwords('EN')#TMTextProcessors.stop_words('english')  # stopwords.words('english')
    self.ut = TMTextProcessors.univ_pos_tagger('EN')  # TMUniversalPosTag('EN')
    self.rules = {
    # pattern ---> left ---> right
    'comma': RulesPattern('<.*>*<V.*><.*>*<CC><.*>*<V.*><.*>*', '<.*>*<V.*><.*>*', '<CC><.*>*<V.*><.*>*'),
    'last': RulesPattern('<.*>*<V.*><.*>*<\,|\;|\:|\-><.*>*<V.*><.*>*', '<.*>*<V.*><.*>*',
                               '<\,|\;|\:|\-><.*>*<V.*><.*>*'),
    }

class SpanishRules():
  def __init__(self):
    self.order = ['comma', 'conjunction', 'compose_sub', 'last']#subordinate

    self.sw = TMUtilsMatching.check_stopwords('ES')#TMTextProcessors.stop_words('spanish')#stopwords.words('spanish')
    self.ut = TMTextProcessors.univ_pos_tagger('ES')#TMUniversalPosTag('ES')

    self.rules = {
      'conjunction': RulesPattern('<.*>*<V.*><.*>*<CC|CCNEG|CCAD><.*>*<V.*><.*>*', #, '<CC|CCNEG|CCAD>','',''
                                      '<.*>*<V.*><.*>*', '<CC|CCNEG|CCAD><.*>*<V.*><.*>*'),#'?!<V.*>', '<CC|CCNEG|CCAD><.*>*'
      'comma': RulesPattern('<.*>*<V.*><.*>*<CM|COLON|DASH|SEMICOLON><.*>*<V.*><.*>*', '<.*>*<V.*><.*>*',
                                '<CM|COLON|DASH|SEMICOLON><.*>*<V.*><.*>*'), #, '<CM|COLON|DASH|SEMICOLON>','',''
      'compose_sub': RulesPattern('<.*>*<V.*><.*>*<CC|CCNEG|CCAD|CM|COLON|DASH|SEMICOLON|PREP|PDEL><CQUE|CSUBF|CSUBI|CSUBX|CQ><.*>*<V.*><.*>*',
                                  '<.*>*<V.*><.*>*','<CC|CCNEG|CCAD|CM|COLON|DASH|SEMICOLON|PREP|PDEL><CQUE|CSUBF|CSUBI|CSUBX|CQ><.*>*<V.*><.*>*'),  # --> subordinate
      'last': RulesPattern('<.*>*<V.*><.*>*<CQUE|CSUBF|CSUBI|CSUBX><.*>*<V.*><.*>*', '<.*>*<V.*><.*>*',
                    '<CQUE|CSUBF|CSUBI|CSUBX|CQ><.*>*<V.*><.*>*'), #--> subordinate
    }

class FrenchRules():
      def __init__(self):
        self.order = ['comma', 'last']  # last = conjuntion

        self.sw = TMUtilsMatching.check_stopwords('FR') # stop words
        self.ut = TMTextProcessors.univ_pos_tagger('FR')  # TMUniversalPosTag('ES')

        self.rules = {
          'last': RulesPattern('<.*>*<V.*><.*>*<KON><.*>*<V.*><.*>*',
                                      '<.*>*<V.*><.*>*', '<KON><.*>*<V.*><.*>*'),
          'comma': RulesPattern('<.*>*<V.*><.*>*<PUN|SENT><.*>*<V.*><.*>*', '<.*>*<V.*><.*>*', # Punctuation marks
                                '<PUN|SENT><.*>*<V.*><.*>*')
        }

class GeneralRules():
  def __init__(self, lang):
    self.order = ['comma', 'last']  # subordinate

    self.sw = TMUtilsMatching.check_stopwords(lang)  # stopwords.words('spanish')
    self.ut = TMTextProcessors.univ_pos_tagger(lang)  # TMUniversalPosTag('ES')

    self.rules = {
    'last': RulesPattern('<.*>*<VERB><.*>*<CONJ|SCONJ><.*>*<VERB><.*>*',  # conjunctions
                                      '<.*>*<VERB><.*>*', '<CONJ><.*>*<VERB><.*>*'),
    'comma': RulesPattern('<.*>*<VERB><.*>*<\.><.*>*<VERB><.*>*', '<.*>*<VERB><.*>*',
                                '<\.><.*>*<VERB><.*>*'),  # comma
        }

'''
Template rule class

If used posTag
class TemplateRule():
  def __init__(self, lang):
    self.order = []  # List with the rules sorted

    self.sw =   # Stopword
    self.ut =   # How to convert to universal posTag

    self.rules = { # dictionary of rules
    'last': RulesPattern(pattern_to_find, left_pattern, right_pattern),
        }
'''


"""
  @api {INFO} /TMSplit TMSplit -- Applied split rules combined posTag and words.
  @apiName TMSplit
  @apiVersion 0.1.0
  @apiGroup TMSplit

  @apiExample {curl} Input & Output:

  # Input:
    (String) language
    (String) class_lang (name of the rule). The name is extracted from the conf/elastictm.yml config file
    (List) list of sentences
  # Output: (List) list with each part of input sentences

  # Process
  1- Obtain the rule to split the sentence (Define the rule for each pair of language (conf/elastictm.yml config file))
    Example of config file
    split:
      en-es:
        en: en_specific
      any-any:
        any: generic_geral

  # To split English sentences, when translated from English to Spanish, use "en_especific".
  # "en_especific" is a name that corresponds with a class EnglishRules(), definied in TMSplit.py

  # To include a set of rules for others languages create an entry in conf/elastictm.yml ("split") config file and create a new class in TMSplit.py.

  2- Create a new class in TMSplit.py

  #TMSplit.py constructor instantiate the class for each language.

  e.g. if class_lang == 'en_specific': rule_class = EnglishRules()

  # A template to create a new class is TemplateRule()

  @apiExample {curl} Example & Notes

  => Split example

  - Input: ['CONSIDERING that many of the provisions of the Act annexed to that Treaty of Accession remain relevant; that Article IV-437 ( 2 )
            of the Constitution provides that those provisions must be set out or referred to in a Protocol , so that they remain in force
            and their legal effects are preserved ;']

  - Resulting Tree (After applied split rules):

  * Search "split INFO" in uwsgi.log to see the following Tree representation
  [
    Tree('S', [('CONSIDERING', 'VVG')]),

    Tree('S', [('that', 'IN/that'), ('many', 'JJ'), ('of', 'IN'), ('the', 'DT'), ('provisions', 'NNS'), ('of', 'IN'), ('the', 'DT'), ('Act', 'NP'), ('annexed', 'VVD'),
        ('to', 'TO'), ('that', 'DT'), ('Treaty', 'NP'), ('of', 'IN'), ('Accession', 'NP'), ('remain', 'VVP'), ('relevant', 'JJ')]),
    Tree('S', [(';', ':'), ('that', 'IN/that'), ('Article', 'NP'), ('IV-437', 'NP'), ('(', '('), ('2', 'CD'), (')', ')'), ('of', 'IN'), ('the', 'DT'), ('Constitution', 'NP'),
    ('provides', 'VVZ')]),
    Tree('S', [('that', 'IN/that'), ('those', 'DT'), ('provisions', 'NNS'), ('must', 'MD'), ('be', 'VB'), ('set', 'VVN'), ('out', 'RP')]),
    Tree('S', [('or', 'CC'), ('referred', 'VVD'), ('to', 'TO'), ('in', 'IN'), ('a', 'DT'), ('Protocol', 'NP')]), Tree('S', [(',', ','), ('so', 'IN'), ('that', 'WDT'), ('they', 'PP'),
    ('remain', 'VVP'), ('in', 'IN'), ('force', 'NN')]),
    Tree('S', [('and', 'CC'), ('their', 'PP$'), ('legal', 'JJ'), ('effects', 'NNS'), ('are', 'VBP'), ('preserved', 'VVN'), (';', ':')])
    ]

   - Output sentences

   * Search "After Split Each parts:" in uwsgi.log to see the output of TMSplit.py

    ['CONSIDERING', 'many of the provisions of the Act annexed to that Treaty of Accession remain relevant', 'that Article IV-437 ( 2 ) of the Constitution provides',
    'those provisions must be set out', 'referred to in a Protocol', 'so that they remain in force', 'their legal effects are preserved ;']

"""

# Class that applied split rules combined posTag and words.
class TMSplit():

  def __init__(self, class_lang, lang): #TODO: fill rule class for other languages

    self.lang = lang
    self.class_lang = class_lang

    rule_class = None

    if class_lang == 'en_specific':
      rule_class = EnglishRules()

    if class_lang == 'en_generic':
      rule_class = EnglishGenericRules()

    if class_lang == 'es_specific':
      rule_class = SpanishRules()

    if class_lang == 'es_specific':
      rule_class = SpanishRules()

    if class_lang == 'fr_specific':
      rule_class = FrenchRules()

    if class_lang == 'generic_geral':
      rule_class = GeneralRules(self.lang)

    #rule_class = self.dic_languages.get(class_lang)

    if not rule_class: raise (Exception("Unsupported rule class: {}".format(class_lang)))

    #self.language = lang
    self.timer = TMTimer("TMSplit", logging.INFO)

    self.order = ['initial'] + rule_class.order # --> Order to apply the rules

    self.rules = rule_class.rules # --> Dictionary with rules objects
    self.tools =  rule_class.sw # --> Stop word glossary
    self.uni_posTag = rule_class.ut # --> Universal posTag

  #*********Set of functions to split the senteces

  #Apply a set of rules
  # Return: [Tree('S', [('It', 'PP'), ('was', 'VBD'), ('pointed', 'VVN'), ('out', 'RP'), ('that', 'IN/that'), ('in', 'IN'), ('economies', 'NNS'), ('in', 'IN'),
  # ('transition', 'NN'), ('to', 'TO'), ('a', 'DT'), ('market', 'NN'), ('economy', 'NN')])]
  def clause_chunk(self, text):
    dicSegment_Rules = {}
    # Check if need to transfer to universal posTag
    if self.class_lang == 'generic_geral' and self.lang.upper() not in TMUtilsMatching.pre_process(' ', self.lang.upper(), 'get_lang_universalPOS', {}):
      text_Universal = TMUtilsMatching.pre_process([[[word, pos] for word, pos in text]], self.lang, 'universal_pos_tagger', {})

      if not text_Universal: # If rhere are some problem with universal posTag
        return [Tree('S', text)]

      text = [(word, pos) for word, pos in text_Universal]

    #Run each rule
    for r in self.order:
      if r == 'initial':
        lSentences = [text]  # --> Lista inicial de segmentos a serem processados
      else:
        chunkO = RegexpChunkParser(self.rules[r].get_rule_obj(), chunk_label='splitPoint', root_label='S') # Create chunk Object

        #Process to chunk the segments --> Call each rule in recursive form
        lChunk_Segments = lSentences

        len_actual = 0 #--> Control the split number
        len_previous = len(lSentences)

        while len_actual != len_previous:
          len_previous = len(lChunk_Segments)
          lChunk_Segments = self._recursive_rule(lChunk_Segments,chunkO)
          len_actual = len(lChunk_Segments)

        dicSegment_Rules[r] = lChunk_Segments
        lSentences = lChunk_Segments # --> Load all chunks obtain by one rule
    self.timer.print()
    return dicSegment_Rules['last']

  def _recursive_rule(self, lSentences, chunkO):
    lChunk = []
    self.timer.start("Extend")
    lChunk.extend(chunkO.parse(sentence) for sentence in lSentences)
    self.timer.stop("Extend")
    self.timer.start("Extract sentences")
    listNewSegments = self._extract_segment(lChunk) # --> Convert each tree in a list of segments
    self.timer.stop("Extract sentences")
    return listNewSegments


  def _extract_segment(self,lChunk_Segments):
    l_segment = []

    for element in lChunk_Segments:
      splitSegments = list(element.subtrees(filter=lambda x: x.label() == 'splitPoint'))
      if splitSegments == []:
        l_segment.append(element)
      else:
        for segments in splitSegments:
            l_segment.append(segments.leaves())
    return l_segment

  def split_output(self, split_tree):

    listSegments = []
    split_marks = []
    my_puntation_list = [',', '-', '.', ':', ';', '<', '=', '>', '?']
    # Convert Tree to list of tuple
    for segments in split_tree:
      if isinstance(segments, Tree):
        tup_segments = list(segments.subtrees(filter=lambda x: x.label() == 'S'))
        for s in tup_segments:
          # sentence = [tuple2str(element,sep='_') for element in s.leaves()]
          sentence = [element for element in s.leaves()]
          if sentence[0][0] in self.tools or sentence[0][0] in my_puntation_list:
            split_marks.append(sentence.pop(0)) # Delete the first marks
          #print(sentence)
          listSegments.append(sentence)
      else:
        # sentence = [tuple2str(element, sep='_') for element in segments]
        sentence = [element for element in segments]
        listSegments.append(sentence)
    #splitTask.timer.stop("Print")
    return listSegments, split_marks

  # *********Set of functions to extract segments feature
  def _content_stop_word(self, segment, sw):

    plain_seq = [word[0] for word in segment] # --> Create plain sequence

    posTag_seq = [word[1] for word in segment] # --> Create posTag sequence

    content_W = [posTag_seq[w] for w in range(0, len(plain_seq)) if plain_seq[w] not in sw]  # Content word posTag
    stop_W = [posTag_seq[w] for w in range(0, len(plain_seq)) if plain_seq[w] in sw]  # Stop word posTag
    if stop_W == []: stop_W = ['STOP'] # If the segment have not stop words, then put the sequence STOP
    return ' '.join(content_W), ' '.join(stop_W)

  def extract_feature(self, listSegments):

    listVectors = []
    for segments in listSegments:


      f_vectors = []

      f_vectors.insert(0, listSegments.index(segments))  # segment position
      f_vectors.insert(1, len(segments))  # total word

      content_PosTag, stop_PosTag = self._content_stop_word(segments, self.tools)

      f_vectors.insert(2, self.uni_posTag.map_universal_postagger(content_PosTag))  #Sequence PosTag replace_universal_posTag
      f_vectors.insert(3, self.uni_posTag.map_universal_postagger(stop_PosTag))  #Sequence StopWords PosTag

      listVectors.append(f_vectors)
    return listVectors

  def print_SplitResult(self, dicSegment_Rules, originalSentence):

    listSegments = []
    #print('****' + ' '.join([tuple2str(element, sep='_') for element in originalSentence]))
    for segments in dicSegment_Rules['subordinate']:

      # Convert Tree to list of tuple
      if isinstance(segments, Tree):
        tup_segments = list(segments.subtrees(filter=lambda x: x.label() == 'S'))
        for s in tup_segments:
          # sentence = [tuple2str(element,sep='_') for element in s.leaves()]
          sentence = [element for element in s.leaves()]
          listSegments.append(sentence)
      else:
        # sentence = [tuple2str(element, sep='_') for element in segments]
        sentence = [element for element in segments]
        listSegments.append(sentence)
    # for s in listSegments:
    #  print('\t\t'+' '.join(s))
    return listSegments

  #Rule 2: Extract subsegment between square brackets or parenthesis
  def splitByParth_Brack(self):
    pattern = '\[(.*?)\]|\((.*?)\)'
    src_split = [re.search(pattern, s.source_text).group() for s in self.segments if not None]
    tgt_split = [re.search(pattern, s.target_text).group() for s in self.segments if not None]

    #for (src_split, tgt_split) in zip(src_split,tgt_split):
    #    if src_split and tgt_split

if __name__ == "__main__":
  # pass
  #
  # patternParth = re.compile('\[(.*?)\]')#--> May be it is interesting create a class with differents patterns
  # patternBrack = re.compile('\((.*?)\)')
  #
  # str = ["Pagination.go('formPagination_bottom',2,'Page',true,'1',null,'2013') and [new output it is necessary.]",
  #        "Without Brackets."]
  #
  # for s in str:
  #   print(re.findall(patternParth,s))
  #   print(re.findall(patternBrack,s))

  #segmentation = TMSplitPreprocessor(segments, src_lang=qlangs[0], tgt_lang=qlangs[1])
  #new_src, wew_tgt = segmentation.splitByTokenizer()
  #segmentation.createSegment(new_src, wew_tgt)

  en_sent = [
    [('Gasoline', 'NN'), (',', ','), ('brake', 'NNP'), ('fluid', 'NN'), (',', ','), ('and', 'CC'), ('coolant', 'NN'),
     ('will', 'MD'), ('damage', 'VB'), ('the', 'DT'), ('finish', 'NN'), ('of', 'IN'), ('painted', 'JJ'), ('and', 'CC'),
     ('plastic', 'JJ'), ('surfaces', 'NNS'), (':', ':')],
    [('Vinyl', 'NN'), ('parts', 'NNS'), ('should', 'MD'), ('be', 'VB'), ('washed', 'VBN'), ('with', 'IN'),
     ('the', 'DT'),
     ('rest', 'NN'), ('of', 'IN'), ('the', 'DT'), ('motorcycle', 'NN'), ('and', 'CC'), ('then', 'RB'),
     ('treated', 'VBN'), ('with', 'IN'), ('a', 'DT'), ('vinyl', 'NN'), ('treatment', 'NN'), ('.', '.')],
    [('be', 'VB'), ('washed', 'VBN'), ('with', 'IN'), ('and', 'CC'), ('treated', 'VBN'), ('with', 'IN')],
    [('Vinyl', 'NN'), ('parts', 'NNS'), ('should', 'MD'), ('be', 'VB'), ('washed', 'VBN'), ('with', 'IN'),
     ('the', 'DT'),
     ('rest', 'NN'), ('of', 'IN'), ('the', 'DT'), ('motorcycle', 'NN'), ('and', 'CC'), ('then', 'RB'),
     ('treated', 'VBN'), ('with', 'IN'), ('a', 'DT'), ('vinyl', 'NN'), ('treatment', 'NN'), (',', ','), ('an', 'DT'),
     ('official', 'NN'), ('told', 'VBD'), ('the', 'DT'), ('Reuters', 'NNP'), ('news', 'NN'), ('agency', 'NN'),
     ('.', '.')],
    [('be', 'VB'), ('washed', 'VBN'), ('with', 'IN'), ('and', 'CC'), ('treated', 'VBN'), ('with', 'IN')],
    [('Install', 'VB'), ('the', 'DT'), ('engine', 'NN'), ('oil', 'NN'), ('drain', 'NN'), ('plug', 'NN'), ('and', 'CC'),
     ('fill', 'NN'), ('in', 'IN'), ('fresh', 'JJ'), ('engine', 'NN'), ('oil', 'NN'), ('.', '.')],
    [('The', 'DT'), ('fuel', 'NN'), ('will', 'MD'), ('deteriorate', 'VB'), ('if', 'IN'), ('left', 'VBN'), ('for', 'IN'),
     ('a', 'DT'), ('long', 'JJ'), ('time', 'NN')],
    [('A', 'DT'), ('mediator', 'NN'), ('is', 'VBZ'), ('not', 'RB'), ('needed', 'VBN'), (',', ','), ('an', 'DT'),
     ('official', 'NN'), ('told', 'VBD'), ('the', 'DT'), ('Reuters', 'NNP'), ('news', 'NN'), ('agency', 'NN'),
     (',', ','), ('an', 'DT'), ('official', 'NN'), ('told', 'VBD'), ('the', 'DT'), ('Reuters', 'NNP'), ('news', 'NN'),
     ('agency', 'NN'), ('.', '.')],
    [('Madam', 'NN'), ('President', 'NP'), (',', ','), ('can', 'MD'), ('you', 'PP'), ('tell', 'VV'), ('me', 'PP'),
     ('why', 'WRB'), ('this', 'DT'), ('Parliament', 'NP'), ('does', 'VVZ'), ('not', 'RB'), ('adhere', 'VV'),
     ('to', 'TO'), ('the', 'DT'), ('health', 'NN'), ('and', 'CC'), ('safety', 'NN'), ('legislation', 'NN'),
     ('that', 'IN/that'), ('it', 'PP'), ('actually', 'RB'), ('passes', 'VVZ'), ('?', 'SENT')]
    ]

  #en_sent = [[('Madam', 'NN'), ('President', 'NP'), (',', ','), ('the', 'DT'), ('presentation', 'NN'), ('of', 'IN'), ('the', 'DT'),
  #            ('Prodi', 'NP'), ('Commission', 'NP'), ("'", 'POS'), ('s', 'JJ'), ('political', 'JJ'), ('programme', 'NN'),
  #            ('for', 'IN'), ('the', 'DT'), ('whole', 'JJ'), ('legislature', 'NN'), ('was', 'VBD'), ('initially', 'RB'), ('a', 'DT'),
  #            ('proposal', 'NN'), ('by', 'IN'), ('the', 'DT'), ('Group', 'NP'), ('of', 'IN'), ('the', 'DT'), ('Party', 'NN'), ('of', 'IN'),
  #            ('European', 'JJ'), ('Socialists', 'NNS'), ('which', 'WDT'), ('was', 'VBD'), ('unanimously', 'RB'), ('approved', 'VVN'),
  #            ('by', 'IN'), ('the', 'DT'), ('Conference', 'NP'), ('of', 'IN'), ('Presidents', 'NPS'), ('in', 'IN'), ('September', 'NP'),
  #            ('and', 'CC'), ('which', 'WDT'), ('was', 'VBD'), ('also', 'RB'), ('explicitly', 'RB'), ('accepted', 'VVN'), ('by', 'IN'),
  #            ('President', 'NP'), ('Prodi', 'NP'), (',', ','), ('who', 'WP'), ('reiterated', 'VVD'), ('his', 'PP$'), ('commitment', 'NN'),
  #            ('in', 'IN'), ('his', 'PP$'), ('inaugural', 'JJ'), ('speech', 'NN'), ('.', 'SENT')]]

  splitOBJ = TMSplit('EN')

  for s in en_sent:
    segmentsStructure = splitOBJ.clause_chunk(s)  # --> Split
    print(segmentsStructure)
    vectorsFeature = splitOBJ.extract_feature(segmentsStructure)
    print(vectorsFeature)