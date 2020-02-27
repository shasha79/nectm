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


class TMQueryParams:
  def __init__(self,qlist, qinfo ,source_lang, target_lang, pipe, out ,limit, domains=None, min_match=75, concordance=False, aut_trans=False, exact_length=False):
    self.qlist = qlist
    self.qinfo = qinfo
    self.source_lang = source_lang
    self.target_lang = target_lang
    self.pipe = pipe
    self.out = out
    self.limit = limit
    self.domains = domains
    self.min_match = min_match
    self.concordance = concordance
    self.aut_trans = aut_trans
    self.exact_length = exact_length