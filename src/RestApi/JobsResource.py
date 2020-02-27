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
from flask_restful import Resource, abort
from flask_restful.reqparse import RequestParser
from celery import task
from flask_jwt import current_identity, jwt_required

from Auth import admin_permission, user_permission, PermissionChecker
from RestApi.Models import Users
from JobApi.ESJobApi import ESJobApi
from JobApi.SparkTaskDispatcher import SparkTaskDispatcher

class JobsResource(Resource):
  decorators = [jwt_required()]

  def __init__(self):
    self.job_api = ESJobApi()

  """
   @api {get} /jobs/id Query job details (start time, status, end time etc.). If no job id specified, all jobs are returned
   @apiVersion 1.0.0
   @apiName GetJob
   @apiGroup Jobs
   @apiUse Header
   @apiPermission admin

   @apiParam {Integer} [limit] Limit number of output jobs. Default is 10

   @apiSuccess {Json} job_details Job details
   @apiError {String} 401 Job doesn't exist

  """
  # TODO: accept limit as a parameter
  #@user_permission.require(http_exception=403)
  #@admin_permission.require(http_exception=403)
  def get(self, job_id=None):
    args = self._get_reqparse()
    jobs = []
    username_filter = current_identity.username if current_identity.role != Users.ADMIN else None
    if job_id:
      try:
        job = self.job_api.get_job(job_id)
        if username_filter and username_filter != job["username"]:
            abort(403, mesage="No permission to view status of job {}".format(job_id))
        jobs.append(job)
      except:
        abort(401, mesage="Job {} doesn't exist".format(job_id))
    else:
      for job in self.job_api.scan_jobs(args.limit, username_filter):
        jobs.append(job.to_dict())
    return {"jobs" : jobs}

  def _get_reqparse(self):
    parser = RequestParser()
    parser.add_argument(name='limit', type=int, default=10,
                        help="Limit output to this number of jobs")
    return parser.parse_args()

  """
   @api {delete} /jobs/:id Cancel job execution
   @apiVersion 1.0.0
   @apiName CancelJob
   @apiGroup Jobs
   @apiUse Header
   @apiPermission admin

   @apiSuccess {String} message Success message
   @apiError {String} 401 Job doesn't exist

  """
  @admin_permission.require(http_exception=403)
  def delete(self, job_id):
    # Setup a job using Celery & ES
    task = self.kill_task.apply_async([job_id])
    return {"job_id": task.id, "message": "Job submitted successfully"}

  @task(bind=True)
  def kill_task(self, job_id):
    SparkTaskDispatcher().run(job_id, 'KillTask')
    return {'status': 'Task completed!'}
