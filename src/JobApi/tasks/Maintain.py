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
import sys, os, datetime, re
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))
from Config.Config import G_CONFIG
from TMDbApi.TMUtils import TMUtils
from JobApi.tasks.Task import Task
from JobApi.tasks.PosTag import PosTagTask
from JobApi.tasks.Clean import CleanTask


class MaintainTask:
  def __init__(self, task):
    self.langs = task.get_langs()
    self.version = self._calc_version()
    print("Version: {}".format(self.version))

  def __call__(self, index, segments_iter):
    for segment in segments_iter:
      segment.check_date = TMUtils.date2str(datetime.datetime.now())
      segment.check_version = self.version
      yield segment

  # Create version by hashing source codes of task classes and part of config file
  # IMPORTANT: update this function whenever new maintenance tasks are introduced
  def _calc_version(self):
    import inspect, hashlib
    source = b''
    for o in [MaintainTask, PosTagTask, CleanTask]:
      with open(inspect.getsourcefile(o), 'rb') as f:
        source += f.read()
    # Add maintenance part of config file
    source += str(G_CONFIG.config["maintenance"]).encode('utf-8')
    return hashlib.sha1(source).hexdigest()


if __name__ == "__main__":
  G_CONFIG.config_logging()

  task = Task(sys.argv[1])
  # Run (parallel) check and then store each partition in DB
  task.get_rdd().mapPartitionsWithIndex(MaintainTask(task))\
    .mapPartitionsWithIndex(CleanTask(task))\
    .mapPartitionsWithIndex(PosTagTask(task))\
    .foreachPartition(Task.save_segments)
  task.finalize()

