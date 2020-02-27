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
import sys, os, datetime, re, logging
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))
from JobApi.tasks.Task import Task
from TMDbApi.TMExport import TMExport
from Config.Config import G_CONFIG

class ExportTask(Task):
  def __init__(self, job_id):
    super().__init__(job_id)
    self.langs = self.get_langs()
    self.export = TMExport(self.job['username'])

  def run_sequential(self):
    export_file = self.export.export(self.job_id, self.langs, filters=self.job['params']['filter'],
                                     duplicates_only=self.job['params']['duplicates_only'],
                                     limit=self.job['params']['limit'])
    logging.info("Job: {}, export file: {}".format(self.job_id, export_file))
    # Save filename
    self.job_api.set_field(self.job_id, 'export_file', export_file)
    self.job_api.finalize(self.job_id, status="finished:{}".format(export_file))


if __name__ == "__main__":
  G_CONFIG.config_logging()

  task = ExportTask(sys.argv[1])
  # Delete sequentially
  task.run_sequential()
  task.finalize()

