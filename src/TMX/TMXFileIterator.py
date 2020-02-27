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
import os
import logging

# Given directory, return recursively all TMX files
class TMXFileIterator():

  def __init__(self, dir):
    self.dir  = dir
    self.files = []
    self.index = 0
    if not dir:
      return
    # TODO: optimize iteration by calling os.walk() during next() and caching found files
    for root, subdirs, files in os.walk(dir):
      self.files += [os.path.join(root, f) for f in files]
    logging.debug("Files: {}".format(self.files))

  def __iter__(self):
    return self

  def __next__(self):
    if self.index >= len(self.files):
      raise StopIteration
    f = self.files[self.index]
    self.index += 1
    return f
