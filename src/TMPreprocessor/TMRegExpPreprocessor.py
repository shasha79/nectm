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
import logging
import re
import sys
sys.path.append("..")

import babel.numbers
from babel.units import *
#from arrow import locales
from TMPreprocessor import locales

class TMRegExpPreprocessor:
  def __init__(self, lc = 'en_US', pipe = ['formula', 'datetime', 'bullet', 'munit', 'acronym', 'email', 'url', 'number']):
    self.regexp = {
      'number'  : Number(lc),
      'email'   : Email(),
      'url'     : Url(),
      'datetime': DateTime(lc),
      'munit'   : MeasurementUnit(lc),
      'formula' : Formula(lc),
      'acronym' : Acronym(),
      'bullet'  : Bullet(lc)

    }
    self.pipe = pipe
    # Validate pipe
    assert(self.validate_pipe(pipe))


  def get_regex(self, name):
    return  self.regexp[name]

  def validate_pipe(self, pipe):
    for p in pipe:
      if not p in self.regexp: return False
    return True

  def process(self, text):
    for pattern in self.pipe:
      text = self.regexp[pattern].process(text, self._key2placeholder(pattern))
    return text

  def get_pattern_value(self, text):

    pattern_value_list = []
    for pattern in self.pipe:
      individual_list, text = self.regexp[pattern].get_pattern_value(text, self._key2placeholder(pattern)) #get_text(text)
      if individual_list:
        pattern_value_list.append(individual_list)
    return [item for sublist in pattern_value_list for item in sublist], text

  def _key2placeholder(self, key):
    return '|{}|'.format(key.upper())

class RegExp(object):
  def __init__(self, regexp):
    self.regexp = regexp
    self.compiled_regexp = re.compile(self.regexp, re.I|re.X)

  def process(self, text, placeholder):
    return re.sub(self.compiled_regexp, placeholder, text)

  def get_pattern_value(self, text, placeholder):

    pattern_value_list = []

    while re.search(self.compiled_regexp, text):
      pattern_value_list.append((placeholder,re.search(self.compiled_regexp, text).group()))
      #pattern_value_list.append((placeholder, self.what_replace(text)))
      text = re.sub(re.search(self.compiled_regexp, text).group(), placeholder, text)
      #text = self.process_replace(text, placeholder)
    return pattern_value_list, text

  # Get locale-specific ordinal pattern
  def _get_ordinal_pattern(self, lc):
    return lc.ordinal_day_re if hasattr(lc, 'ordinal_day_re') else ""

  def do_replace(self, text, replace_value):
    if re.search(self.compiled_regexp, text):
      text = text.replace(re.search(self.compiled_regexp, text).group(), replace_value, 1)
    return text

  def get_value(self, text):
    return re.search(self.compiled_regexp, text).group()

class Url(RegExp):
  def __init__(self):
    super(Url, self).__init__(
      # reference: http://daringfireball.net/2010/07/improved_regex_for_matching_urls
      r'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?\xab\xbb\u201c\u201d\u2018\u2019]))'
    )

class Email(RegExp):
  def __init__(self):
    super(Email, self).__init__(
      # reference: http://www.regular-expressions.info/email.html
      '[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}'    )

class Number(RegExp):
  def __init__(self, lc):
    # reference: http://www.regular-expressions.info/floatingpoint.html
    super(Number, self).__init__('(?<!\<T)(?<!\<\/T)[0-9GROUP_SYMBOL]*DEC_SYMBOL?[0-9]+([eE][-+]?[0-9]+)?')#|(?<!\<\/T)
    # Use decimal and group symbol according to locale
    self.regexp = re.sub('DEC_SYMBOL', babel.numbers.get_decimal_symbol(lc), self.regexp)
    self.regexp = re.sub('GROUP_SYMBOL', babel.numbers.get_group_symbol(lc), self.regexp)
    # Concatenate ordinal pattern (if exists)
    ordinal_pattern = self._get_ordinal_pattern(locales.get_locale(lc))
    if ordinal_pattern:
      self.regexp = "(" + ordinal_pattern + ")|(" + self.regexp + ")"
    #logging.info("Number regexp: {}, ordinal pattern: {}".format(self.regexp, ordinal_pattern))
    # recompile regexp
    self.compiled_regexp = re.compile(self.regexp, re.I | re.U)

  def get_pattern(self):
    return self.regexp

# Adapted from https://github.com/stevepeak/timestring/blob/master/timestring/timestring_re.py
class DateTime(RegExp):
  def __init__(self, lc):
    self.lc = locales.get_locale(lc)
    # create match for localized months names, for ex.:
    #january|february|march|april|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sept?|oct|nov|dec
    self.months = "|".join([m for m in self.lc.month_names + self.lc.month_abbreviations if m])
    # 5th, 3º, etc
    self.ordinal_pattern = self._get_ordinal_pattern(self.lc)
    self.patterns = [
    # =-=-=-= Matches Y-M-D, M-D-Y ex. "january 5, 2012", "january 5th, '12", "jan 5th 2012" =-=-=-= )
    #  """ + self.ordinal_pattern + """
      """
        (
            ((?P<year_6>(([12][089]\d{2})|('\d{2})))?([\.\/\-\s]+)?)
            (?P<month>""" + self.months + """)[\.\/\-\s]
            """ + self.ordinal_pattern + """
            (,?\s(?P<year>([12][089]|')?\d{2}))?
        )
    """,
      # =-=-=-= Matches "2012/12/11", "2013-09-10T", "5/23/2012", "05/2012", "2012" =-=-=-= )
    """
      (
            ((?P<year_3>[12][089]\d{2})[/-](?P<month_3>[01]?\d)([./-](?P<date_3>[0-3]?\d))?)T?
                |
            ((?P<month_2>[01]?\d)[./-](?P<date_2>[0-3]?\d)[./-](?P<year_2>(([12][089]\d{2})|(\d{2}))))
                |
            ((?P<month_4>[01]?\d)[./-](?P<year_4>([12][089]\d{2})|(\d{2})))
                |
            (?P<year_5>([12][089]\d{2})|('\d{2}))
      )
    """,
      #  (?  # =-=-=-= Matches "01:20", "6:35 pm", "7am" =-=-=-= )
    # """
    # (
    #   ((?P<hour>[012]?[0-9]):(?P<minute>[0-5]\d)\s*(?P<am>am|pm))
    #     |
    #   ((?P<hour_2>[012]?[0-9]):(?P<minute_2>[0-5]\d)(:(?P<seconds>[0-5]\d))?)
    #     |
    #   ((?P<hour_3>[012]?[0-9])\s*(?P<am_1>am|pm|o'?clock))
    # )"""

    """
      (
        ((?P<hour>[012]?[0-9]):(?P<minute>[0-5]\d)\s*(?P<am>am|pm)(?![a-zA-Z]))
          |
        ((?P<hour_2>[012]?[0-9]):(?P<minute_2>[0-5]\d)(:(?P<seconds>[0-5]\d))?)
          |
        ((?P<hour_3>[012]?[0-9])\s*(?P<am_1>am|pm|o'?clock)(?![a-zA-Z]))
      )"""
    ]
    self.compiled_regexp = re.compile("|".join(self.patterns), re.I | re.X | re.U)

  def process(self, text, placeholder):
    # Workaround for date pattern matching trailing whitespaces. Strip them before substituting
    for match in re.finditer(self.compiled_regexp, text):
      text = text.replace(match.group().strip(), placeholder)
    return text


  def do_replace(self, text, replace_value):
    if re.search(self.compiled_regexp, text):
      text = text.replace(re.search(self.compiled_regexp, text).group().strip(), replace_value, 1)
    return text

  def get_value(self, text):
    return re.search(self.compiled_regexp, text).group().strip()

class MeasurementUnit(RegExp):
  def __init__(self, lc):
    self.number = Number(lc)
    self.lc = lc
    self.units = [self._get_unit_name(u, f, lc) for u in self._get_unit_types() for f in ['long', 'short', 'narrow']]
    # Sort patterns alphabetically and by length
    self.units = sorted([re.escape(u) for u in self.units if u], key=lambda item: (-len(item), item))

    #self.regexp = (".NUMBER.\s?(" + "|".join(self.units) + ")\\b")
    self.regexp = r'(' + self.number.get_pattern() +"\s?(" + "|".join(self.units) + ")\\b"')'
    #self.regexp = (".NUMBER.\s?(" + "|".join(self.units) + ")\\b(?![a-zA-Z])")
    self.compiled_regexp = re.compile(self.regexp, re.I | re.U)
    logging.debug(self.regexp)

  def process(self, text, placeholder):
    # Workaround for date pattern matching trailing whitespaces. Strip them before substituting
    for match in re.finditer(self.compiled_regexp, text):
      text = text.replace(match.group().strip(), placeholder) # match.group(1).strip()
    return text

  def do_replace(self, text, replace_value):
    if re.search(self.compiled_regexp, text):
      text = text.replace(re.search(self.compiled_regexp, text).group().strip(), replace_value, 1) #.group(1).strip()
    return text

  def get_value(self, text):
    return re.search(self.compiled_regexp, text).group().strip()#group(1).strip()

  def _get_unit_types(self):
    # TODO: read from http://unicode.org/repos/cldr/tags/latest/common/validity/unit.xml
    return ['acceleration-g-force','acceleration-meter-per-second-squared','angle-arc-minute','angle-arc-second','angle-degree','angle-radian','angle-revolution','area-acre','area-hectare','area-square-centimeter','area-square-foot','area-square-inch','area-square-kilometer','area-square-meter','area-square-mile','area-square-yard','concentr-karat','concentr-milligram-per-deciliter','concentr-millimole-per-liter','concentr-part-per-million','consumption-liter-per-100kilometers','consumption-liter-per-kilometer','consumption-mile-per-gallon','consumption-mile-per-gallon-imperial','digital-bit','digital-byte','digital-gigabit','digital-gigabyte','digital-kilobit','digital-kilobyte','digital-megabit','digital-megabyte','digital-terabit','digital-terabyte','duration-century','duration-day','duration-day-person','duration-hour','duration-microsecond','duration-millisecond','duration-minute','duration-month','duration-month-person','duration-nanosecond','duration-second','duration-week','duration-week-person','duration-year','duration-year-person','electric-ampere','electric-milliampere','electric-ohm','electric-volt','energy-calorie','energy-foodcalorie','energy-joule','energy-kilocalorie','energy-kilojoule','energy-kilowatt-hour','frequency-gigahertz','frequency-hertz','frequency-kilohertz','frequency-megahertz','length-astronomical-unit','length-centimeter','length-decimeter','length-fathom','length-foot','length-furlong','length-inch','length-kilometer','length-light-year','length-meter','length-micrometer','length-mile','length-mile-scandinavian','length-millimeter','length-nanometer','length-nautical-mile','length-parsec','length-picometer','length-yard','light-lux','mass-carat','mass-gram','mass-kilogram','mass-metric-ton','mass-microgram','mass-milligram','mass-ounce','mass-ounce-troy','mass-pound','mass-stone','mass-ton','power-gigawatt','power-horsepower','power-kilowatt','power-megawatt','power-milliwatt','power-watt','pressure-hectopascal','pressure-inch-hg','pressure-millibar','pressure-millimeter-of-mercury','pressure-pound-per-square-inch','speed-kilometer-per-hour','speed-knot','speed-meter-per-second','speed-mile-per-hour','temperature-celsius','temperature-fahrenheit','temperature-generic','temperature-kelvin','volume-acre-foot','volume-bushel','volume-centiliter','volume-cubic-centimeter','volume-cubic-foot','volume-cubic-inch','volume-cubic-kilometer','volume-cubic-meter','volume-cubic-mile','volume-cubic-yard','volume-cup','volume-cup-metric','volume-deciliter','volume-fluid-ounce','volume-gallon','volume-gallon-imperial','volume-hectoliter','volume-liter','volume-megaliter','volume-milliliter','volume-pint','volume-pint-metric','volume-quart','volume-tablespoon','volume-teaspoon']

  def _get_unit_name(self, unit, utype, lc):
    try:
      return get_unit_name(unit, utype, lc)
    except:
      return None

class Formula(RegExp):
  def __init__(self, lc):
    self.number = Number(lc)
    super(Formula, self).__init__(
      #r'([+\-]?(.NUMBER.|[()A-Za-z]+)\s*([+\-/*=])\s*)+(.NUMBER.|[()A-Za-z]+)'
      r'([+\-]?('+re.escape(self.number.get_pattern())+'|[()A-Za-z]+)\s*([+\-/*=])\s*)+('+re.escape(self.number.get_pattern())+'|[()A-Za-z]+)'
    )

  def process(self, text, placeholder):
    text = super(Formula, self).process(text, placeholder)
    # Unify consecutive formulas which failed to fully match by regexp
    return re.sub("(\|FORMULA\|){2,}", "|FORMULA|", text)

class Acronym(RegExp):
  def __init__(self):
    super(Acronym, self).__init__(
      # TODO: handle ampersand
      #r'([A-Z]{2,}|[A-Z\.\-]{4,})'
      r'(?:(?<=\.|\s)[A-Za-z]\.){2,}' #--> http://stackoverflow.com/questions/17779771/finding-acronyms-using-regex-in-python
    )
    self.compiled_regexp = re.compile(self.regexp, re.U) # case-sensitive

class Bullet(RegExp):
  def __init__(self, lc):
    self.number = Number(lc)
    super(Bullet, self).__init__(
      #r'(((\b[a-k])|(.NUMBER.))[.\)])' # limiting the list to 10 bullets for now
      r'(((\b[a-k])|('+self.number.get_pattern()+'))[.\)])'
    )


if __name__ == "__main__":
  logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

  tmre = dict([(lc, TMRegExpPreprocessor(lc)) for lc in ['en_US', 'es_ES']])
  tests = {
    'en_US' : ["I have 2512 dollars",
           "There are 3,200.35 euros",
           "2nd degree",
           "Please transfer 5,700 euros to ale@blalal.com",
           "Send me an email to alex@blabla.com or to ale@bla.co",
           "I was born on 18/08/1976 and graduated from school on 05-25-93, later moved to another country on October 1st, 1996",
           "My meeting was at 18:00 or 6 pm and was moved to 7pm",
           "Go to http://pangeanic.com",
           "Install at the angle of 6° and verify the installation",
           "Going for 100 kilometers with speed of 25km/hr, drinking 5 liters of water. It took 4 hours",
           "The calculation is 3+2= 5 and another one is 194.20 / 23*75 and another is V*(25-C) ",
           "DARPA announced new research results and submitted them to IEEC for review",
           "Company H&M acquired H.M.O in December 2015",
            "a) Asia, b) Africa, c) Europe(Russia)",
            "1) Asia, 2) Africa, 3) Europe(Russia)"],

  'es_ES': ["Instale el 6º casquillo del engranaje en el eje primario con sus agujeros de lubricación alineados."]
  }

  for lc,tests in tests.items():
    for t in tests:
      logging.info("Input: {}, output: {}".format(t, tmre[lc].process(t)))

