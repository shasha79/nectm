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
from pyspark import SparkContext, StorageLevel
import sys, os
import logging
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))

from JobApi.ESJobApi import ESJobApi
from TMDbApi.TMDbApi import TMDbApi
from Config.Config import G_CONFIG


class Task:
  def __init__(self, job_id):
    self.job_api = ESJobApi()
    self.job_id = job_id
    self.job = self.job_api.get_job(job_id)
    self.job_api.set_status(job_id, 'running')

#  def __del__(self):
#    self.job_api.finalize(self.job_id)
  def finalize(self):
    self.job_api.finalize(self.job_id)

  def get_rdd(self):
    # init access to ES DB
    db = TMDbApi()
    return self._get_rdd(db, db.scan(self.get_langs(), self.job['params']['filter']))

  def get_rdd_generate(self):
    # init access to ES DB
    db = TMDbApi()
    params = self.job['params']
    #return self._get_rdd(db, db.generate(self.get_langs(), params['plang'], params['domain']))

    return self._get_rdd(db, db.ml_index.scan_pivot(params['plang'], self.get_langs()))

  def _get_rdd(self, db, scan_fun):
    sc = SparkContext()
    # set job group
    sc.setJobGroup(self.job_id, self.job['type'])
    # Calculate number of partitions based on number of segments
    count = db.count_scan(self.get_langs(), self.job['params'].get('filter'))
    num_partitions = self.calc_num_parititions(count)
    logging.warning("Scan size: {}, number of partitions: {}".format(count, num_partitions))    # Create RDD by parallelizing segments
    rdd = sc.parallelize(scan_fun, num_partitions)
    rdd.persist(StorageLevel.DISK_ONLY)
    return rdd

  def get_langs(self):
    return (self.job['params']['slang'], self.job['params']['tlang'])

  def set_status(self, status):
    self.job_api.set_status(self.job_id, status)

  def calc_num_parititions(self, db_size):
    return int(db_size/G_CONFIG.config['spark']['segments_per_task']) + 1 # avoid zero

  # Save segments in DB (parallelized, thus should be static)
  @staticmethod
  def save_segments(seg_iter):
    TMDbApi().add_segments(seg_iter)

  @staticmethod
  def delete_segments(task, langs, filter, duplicates_only):
    db = TMDbApi()
    count = db.count_scan(task.get_langs(), filter)
    logging.info("Delete scan size: {}".format(count))
    db.delete(langs, filter, duplicates_only)

  @staticmethod
  def maintain_segments(task, langs, filter):
    db = TMDbApi()
    db.add_segments(task(0, db.scan(langs, filter)))