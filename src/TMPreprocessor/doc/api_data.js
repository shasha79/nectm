/*
 * Copyright (c) 2020 Pangeanic SL.
 *
 * This file is part of NEC TM
 * (see https://github.com/shasha79/nectm).
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
define({ "api": [
  {
    "type": "INFO",
    "url": "/TMSplit",
    "title": "EnglishRules -- Create a set of rules to split English sentences. Combined posTag and words.",
    "name": "EnglishRules",
    "version": "0.1.0",
    "group": "TMSplit",
    "examples": [
      {
        "title": "Input & Output:",
        "content": "\n# Input:\n  (String) language\n# Output:\n  (List) list of English stopwords\n  (Dictionary) Set of rules. Each entry of the dictionary contain a \"RulesPattern\" object.\n  (List) List with English universal posTag Map\n\n* \"RulesPattern\" is a generic class to specified the patterns to split (left pattern --- split mark --- right pattern)\n\n* The output of this class are a set of resource and rules to split sentence of specific language.",
        "type": "curl"
      },
      {
        "title": "Example & Notes",
        "content": "\n => Example of rules to split English sentences.\n Split the sentences considered: Conjunctions, punctuation marks and wh_words\n\n self.rules = {\n   'conjunction': RulesPattern('<.*>*<V.*><.*>*<CC><.*>*<V.*><.*>*', '<.*>*<V.*><.*>*', '<CC><.*>*<V.*><.*>*'), #, '<CC>','',''\n   'last': RulesPattern('<.*>*<V.*><.*>*<WDT|WP|WRB|IN/that><.*>*<V.*><.*>*',\n                               '<.*>*<V.*><.*>*', '<WDT|WP|WRB|IN/that><.*>*<V.*><.*>*'),\n   'comma': RulesPattern('<.*>*<V.*><.*>*<\\,|\\;|\\:|\\-><.*>*<V.*><.*>*', '<.*>*<V.*><.*>*',\n                             '<\\,|\\;|\\:|\\-><.*>*<V.*><.*>*'), #, '<\\,|\\;|\\:|\\->', '', ''\n }\n\n=> Example of generic rule\n\nself.rules = {\n  'last': RulesPattern('<.*>*<VERB><.*>*<CONJ|SCONJ><.*>*<VERB><.*>*',  # conjunctions\n                                    '<.*>*<VERB><.*>*', '<CONJ><.*>*<VERB><.*>*'),\n  'comma': RulesPattern('<.*>*<VERB><.*>*<\\.><.*>*<VERB><.*>*', '<.*>*<VERB><.*>*',\n                              '<\\.><.*>*<VERB><.*>*'),  # comma\n      }\n\n=> It's possible create rules for others language, but all the rules must be based on posTag annotation. Use TemplateRule() for that.",
        "type": "curl"
      }
    ],
    "filename": "./TMSplit.py",
    "groupTitle": "TMSplit"
  },
  {
    "type": "INFO",
    "url": "/TMSplit",
    "title": "RulesPattern -- Class to instantiate the rigth and left pattern to split the sentences. This patterns are useful to create the Tree structure.",
    "name": "RulesPattern",
    "version": "0.1.0",
    "group": "TMSplit",
    "examples": [
      {
        "title": "Input & Output:",
        "content": "\n# Input:\n  (Regular Expression) left pattern\n  (Regular Expression) Right pattern\n  (Regular Expression) Marks pattern (how split)",
        "type": "curl"
      }
    ],
    "filename": "./TMSplit.py",
    "groupTitle": "TMSplit"
  },
  {
    "type": "INFO",
    "url": "/TMSplit",
    "title": "TMSplit -- Applied split rules combined posTag and words.",
    "name": "TMSplit",
    "version": "0.1.0",
    "group": "TMSplit",
    "examples": [
      {
        "title": "Input & Output:",
        "content": "\n# Input:\n  (String) language\n  (String) class_lang (name of the rule). The name is extracted from the conf/elastictm.yml config file\n  (List) list of sentences\n# Output: (List) list with each part of input sentences\n\n# Process\n1- Obtain the rule to split the sentence (Define the rule for each pair of language (conf/elastictm.yml config file))\n  Example of config file\n  split:\n    en-es:\n      en: en_specific\n    any-any:\n      any: generic_geral\n\n# To split English sentences, when translated from English to Spanish, use \"en_especific\".\n# \"en_especific\" is a name that corresponds with a class EnglishRules(), definied in TMSplit.py\n\n# To include a set of rules for others languages create an entry in conf/elastictm.yml (\"split\") config file and create a new class in TMSplit.py.\n\n2- Create a new class in TMSplit.py\n\n#TMSplit.py constructor instantiate the class for each language.\n\ne.g. if class_lang == 'en_specific': rule_class = EnglishRules()\n\n# A template to create a new class is TemplateRule()",
        "type": "curl"
      },
      {
        "title": "Example & Notes",
        "content": "\n=> Split example\n\n- Input: ['CONSIDERING that many of the provisions of the Act annexed to that Treaty of Accession remain relevant; that Article IV-437 ( 2 )\n          of the Constitution provides that those provisions must be set out or referred to in a Protocol , so that they remain in force\n          and their legal effects are preserved ;']\n\n- Resulting Tree (After applied split rules):\n\n* Search \"split INFO\" in uwsgi.log to see the following Tree representation\n[\n  Tree('S', [('CONSIDERING', 'VVG')]),\n\n  Tree('S', [('that', 'IN/that'), ('many', 'JJ'), ('of', 'IN'), ('the', 'DT'), ('provisions', 'NNS'), ('of', 'IN'), ('the', 'DT'), ('Act', 'NP'), ('annexed', 'VVD'),\n      ('to', 'TO'), ('that', 'DT'), ('Treaty', 'NP'), ('of', 'IN'), ('Accession', 'NP'), ('remain', 'VVP'), ('relevant', 'JJ')]),\n  Tree('S', [(';', ':'), ('that', 'IN/that'), ('Article', 'NP'), ('IV-437', 'NP'), ('(', '('), ('2', 'CD'), (')', ')'), ('of', 'IN'), ('the', 'DT'), ('Constitution', 'NP'),\n  ('provides', 'VVZ')]),\n  Tree('S', [('that', 'IN/that'), ('those', 'DT'), ('provisions', 'NNS'), ('must', 'MD'), ('be', 'VB'), ('set', 'VVN'), ('out', 'RP')]),\n  Tree('S', [('or', 'CC'), ('referred', 'VVD'), ('to', 'TO'), ('in', 'IN'), ('a', 'DT'), ('Protocol', 'NP')]), Tree('S', [(',', ','), ('so', 'IN'), ('that', 'WDT'), ('they', 'PP'),\n  ('remain', 'VVP'), ('in', 'IN'), ('force', 'NN')]),\n  Tree('S', [('and', 'CC'), ('their', 'PP$'), ('legal', 'JJ'), ('effects', 'NNS'), ('are', 'VBP'), ('preserved', 'VVN'), (';', ':')])\n  ]\n\n - Output sentences\n\n * Search \"After Split Each parts:\" in uwsgi.log to see the output of TMSplit.py\n\n  ['CONSIDERING', 'many of the provisions of the Act annexed to that Treaty of Accession remain relevant', 'that Article IV-437 ( 2 ) of the Constitution provides',\n  'those provisions must be set out', 'referred to in a Protocol', 'so that they remain in force', 'their legal effects are preserved ;']",
        "type": "curl"
      }
    ],
    "filename": "./TMSplit.py",
    "groupTitle": "TMSplit"
  }
] });