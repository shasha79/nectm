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



class Translator:

  def translate(self, text, to_lang, from_lang=None):
    if isinstance(text,str):
      ttext_list = self.translate_batch([text])
      if ttext_list and len(ttext_list) > 0: return ttext_list[0]
      return None
    # list or tuple
    if isinstance(text,(list,tuple)):
      return self.translate_batch(text, to_lang, from_lang)
    raise "Can't translate object: {}".format(text)

  def translate_batch(self, text_list, to_lang, from_lang=None):
    raise "Child class has to implement the method"