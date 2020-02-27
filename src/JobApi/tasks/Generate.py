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
import sys, os, datetime
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))

from pyspark import SparkContext, StorageLevel

from JobApi.tasks.Task import Task
from TMDbApi.TMDbApi import TMDbApi

class GenerateTask(Task):
  BATCH_SIZE = 100

  def __init__(self, task):
    self.langs = task.get_langs()
    self.plang = task.job['params']['plang']
    self.domains = task.job['params']['domain']


  def __call__(self, index, segments_iter):
    db = TMDbApi()

    batch_mget = []
    for pivot_id in segments_iter:
      batch_mget += [(pivot_id, self.plang, lang) for lang in self.langs]
      # Reached batch limit - generate segments
      if len(batch_mget) >= self.BATCH_SIZE:
        for segment in db._generate_batch(batch_mget, self.domains):
           yield segment
        batch_mget = []
    # Generate segments for remaining incomplete batch
    for segment in db._generate_batch(batch_mget, self.domains):
       yield segment

  def run_sequential(self):
    params = self.job['params']
    # init access to ES DB
    db = TMDbApi()
    Task.save_segments(db.generate((params['slang'],params['tlang']), params['plang'], params['domain']))


if __name__ == "__main__":
  from Config.Config import G_CONFIG
  G_CONFIG.config_logging()

  task = Task(sys.argv[1])
  #task.get_rdd_generate().mapPartitionsWithIndex(GenerateTask(task)).foreachPartition(Task.save_segments)
  rdd = task.get_rdd_generate().mapPartitionsWithIndex(GenerateTask(task))
  Task.save_segments(rdd.toLocalIterator()) # save partitions sequentially as we have already bulk parallelization in save_segments()

  #task.run_sequential()
  task.finalize()


