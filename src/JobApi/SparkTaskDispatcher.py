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
import io
import os
import sys
import tempfile
from Config.Config import G_CONFIG
from JobApi.ESJobApi import ESJobApi


spark_config = G_CONFIG.config['spark']
task_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'tasks')
src_root_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..')

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

# Create zip file of all (python) sources to be passed to Spark task
def create_source_zip():
  zip_file = os.path.join(tempfile.gettempdir(), 'elastictm.zip')
  cmd = 'cd {}; zip -r {} *'.format(src_root_path, zip_file)
  logger.info("Zipping source with the command: {}".format(cmd))
  os.system(cmd)
  return zip_file

class SparkTaskDispatcher:
  src_zip_file = create_source_zip()
  def __init__(self):
    self.job_api = ESJobApi()

  def run_old(self, job_id, pyscript):
    master_path = spark_config['master_path']
    cmd = "export PYSPARK_PYTHON={}; cd {}; {}/bin/spark-submit --master {} {}/{}.py {} --py-files {}"\
                    .format(sys.executable, src_root_path, spark_config['path'], master_path, task_path, pyscript, job_id, self.src_zip_file)
    logger.info("Dispatching Spark task: {}".format(cmd))
    exit_code = os.system(cmd + "> /dev/null 2>&1")
    if exit_code:
      status = 'failed'
    else:
      status = 'succeded'
    logger.info("Dispatching Spark status: {}, exit code: {}".format(status, exit_code))
    self.job_api.set_status(job_id, status)

  def run(self, job_id, pyscript):
    from subprocess import Popen, PIPE

    master_path = spark_config['master_path']
    cmd = "{}/bin/spark-submit".format(spark_config['path'])
    env = dict(os.environ, PYSPARK_PYTHON=sys.executable)
    params = "--master {} {}/{}.py {} --py-files {}".format(master_path, task_path, pyscript, job_id, self.src_zip_file)
    logger.info("Dispatching Spark task: export PYSPARK_PYTHON={}; cd {}; {} {}".format(sys.executable, src_root_path, cmd, params))
    logger.info("ENV: {}".format(env))
    p = Popen("{} {}".format(cmd, params).split(), stdout=PIPE, stderr=PIPE, env=env, cwd=src_root_path)
    for line in io.TextIOWrapper(p.stdout, encoding="utf-8"):
      logger.info(line)
    p.wait()
    exit_code = p.returncode
    if exit_code:
      status = 'failed'
    else:
      status = 'succeded'
    logger.info("Spark status: {}, exit code: {}".format(status, exit_code))
    
    self.job_api.set_status(job_id, status)

if __name__ == "__main__":
    import sys
    G_CONFIG.config_logging()
    std = SparkTaskDispatcher()
    std.run(sys.argv[1], "Delete")
