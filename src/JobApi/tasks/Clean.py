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
import sys, os, re
import logging
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))

from JobApi.tasks.Task import Task
from Config.Config import G_CONFIG
from TMDbApi.TMUtils import TMUtils

class CleanTask:
  def __init__(self, task):
    self.langs = task.get_langs()
    self.rules = self._create_rules(G_CONFIG.get_cleaning_rules(self.langs))

  def __call__(self, index, segments_iter):
    for segment in segments_iter:
      self.clean_segment(segment)
      yield segment

  def clean_segment(self, segment):
    segment.dirty_score = self._apply_rules(segment)

  def _create_rules(self, rules):
    # Example of input rules:
    '''
    {'en-es': {'rule2': {'regex': ['English-specific rule', 'Spanish specific rule'], 'score': 5}}, 'es': [],
     'es-en': [], 'en': {'rule2': {'regex': ['English-specific rule'], 'score': 5}},
     'all': {'rule11': {'regex': ['source rule'], 'score': 4},
             'rule1': {'regex': ['source rule', 'target rule'], 'score': 3}}}
    '''
    rules_obj = []
    for key,rule_dict in rules.items():
      if not rule_dict: continue
      for name, rule in rule_dict.items():
        r = Rule.create(self.langs, key, name, rule)
        if r: rules_obj.append(r)
    return rules_obj

  def _apply_rules(self, segment):
    score = 0
    for rule in self.rules:
      score += rule(segment)
    return score

class Rule:
  DEFAULT_SCORE = 1
  def __init__(self, langs, name, rule_dict, rule_langs=None):
    self.langs = langs
    self.name = name
    self.rule_dict = rule_dict
    self.rule_langs = rule_langs

  @staticmethod
  def create(langs, rule_key, rule_name, rule_dict):
    rule_type = rule_dict.get('type', 'regex')

    if rule_type == 'regex':
      return Rule._create_regex_rule(langs, rule_key, rule_name, rule_dict)
    elif rule_type == 'langid':
      rule_lang = None if rule_key == 'all' else rule_key
      return LangidRule(langs, rule_name, rule_dict, rule_lang)
    elif rule_type == 'count':
      rule_lang = None if rule_key == 'all' else rule_key
      return CountRule(langs, rule_name, rule_dict, rule_lang)


  @staticmethod
  def _create_regex_rule(langs, rule_key, rule_name, rule_dict):
    if rule_key == 'all':
      if len(rule_dict["regex"]) == 2: return RegexPairRule(langs, rule_name, rule_dict)
      else: return RegexSingleRule(langs, rule_name, rule_dict)
    elif re.search('^\w{2}-\w{2}$', rule_key):
      return RegexPairRule(langs, rule_name, rule_dict, rule_key.split('-'))
    elif re.search('^\w{2}$', rule_key):
      return RegexSingleRule(langs, rule_name, rule_dict, rule_key)

class RegexPairRule(Rule):
  def __init__(self, langs, name, rule_dict, rule_langs=None):
    super(RegexPairRule, self).__init__(langs, name, rule_dict, rule_langs)
    self.rule_dict["regex"] = [re.compile(r) for r in self.rule_dict["regex"]]
    self.reverse = False

    if rule_langs and not (langs[0] == rule_langs[0] and langs[1] == rule_langs[1]):
      self.reverse = True

      # Reverse languages & their rules
      self.rule_langs = rule_langs[::-1]
      if rule_langs != langs: raise Exception("Trying to apply rules for languages {} on languages: {}".format(langs, rule_langs))
      self.rule_dict["regex"] = self.rule_dict["regex"][::-1]
    if len(self.rule_dict["regex"]) != 2:
      raise Exception("PairRule should have exactly 2 regex")

  def __call__(self, segment):
    if re.search(self.rule_dict["regex"][0], segment.source_text) and \
            re.search(self.rule_dict["regex"][1], segment.target_text):
      return self.rule_dict.get('score', self.DEFAULT_SCORE)
    return 0

class RegexSingleRule(Rule):
  def __init__(self, langs, name, rule_dict, rule_lang=None):
    super(RegexSingleRule, self).__init__(langs, name, rule_dict, rule_lang)
    self.rule_dict["regex"] = [re.compile(r) for r in self.rule_dict["regex"]]


  def __call__(self, segment):
    for lang,type in zip(self.langs, ['source', 'target']):
      if not self.rule_langs or self.rule_langs == lang:
        m = re.search(self.rule_dict["regex"][0], getattr(segment, type + '_text'))
        if m: return self.rule_dict.get('score', self.DEFAULT_SCORE)
    return 0

class LangidRule(Rule):
  DEFAULT_THRESHOLD = 0.75
  def __init__(self, langs, name, rule_dict, rule_lang=None):
    super(LangidRule, self).__init__(langs, name, rule_dict, rule_lang)

  def __call__(self, segment):
    score = 0
    for lang, type in zip(self.langs, ['source', 'target']):
      if not self.rule_langs or self.rule_langs == lang:
        det_lang,prob = TMUtils.detect_lang(getattr(segment, type + '_text'), [lang])
        # If language probability is lower than the threshold,
        # penalize segment with the score proportional to probability
        if prob < self.rule_dict.get('threshold', LangidRule.DEFAULT_THRESHOLD):
          score += self.rule_dict.get('score', self.DEFAULT_SCORE) * (1/prob)
    return score

class CountRule(RegexPairRule):
  def __call__(self, segment):
    counts = []
    for regex,type in zip(self.rule_dict["regex"], ['source', 'target']):
      counts.append(len(re.findall(regex, getattr(segment, type + '_text'))))
    if self._diff(counts):
      return self.rule_dict.get('score', self.DEFAULT_SCORE)
    return 0

  def _diff(self, counts):
    if self.reverse:
      counts = counts[::-1] # reverse counts
    diff = self.rule_dict.get('diff', '1')
    # Percentage handling
    percent = False
    if diff.endswith('%'):
      percent = True
      diff = diff.strip('%')

    # Explicit sign?
    sign = diff.startswith(('-', '+'))

    diff = float(diff)
    # Make sure comparison is done on the requested order
    if diff < 0:
      diff = -diff
      counts = counts[::-1]
    # Actual comparison
    d = counts[1]-counts[0]
    if not sign: d = abs(d)
    #logging.debug("RULE: {}, COUNTS: {}, DIFF: {}, SIGN: {}, ACTUAL DIFF: {}".format(self.name, counts, diff, sign, d))
    if percent:
      if not counts[0]: return True # avoid division by zero
      return (d/counts[0])*100 >= diff
    else:
      return d >= diff

if __name__ == "__main__":
  from Config.Config import G_CONFIG
  G_CONFIG.config_logging()

  task = Task(sys.argv[1])
  # Launch RDD parallel processing
  #task.get_rdd().mapPartitionsWithIndex(CleanTask(task)).foreachPartition(Task.save_segments)
  # Run sequentiak
  Task.maintain_segments(CleanTask(task), task.get_langs(), task.job['params']['filter'])
  task.finalize()