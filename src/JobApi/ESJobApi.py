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
import datetime
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q
from JobApi.JobApiC import JobApi
from TMDbApi.TMUtils import TMUtils


class ESJobApi(JobApi):
  DOC_TYPE = 'job'
  INDEX = 'jobs'

  def __init__(self, **kwargs):
    self.es = Elasticsearch(kwargs = kwargs)
    if not self.es.indices.exists(index=self.INDEX):
      self.es.indices.create(index=self.INDEX, body=self._index_template())
    self.es.indices.put_template(name='job_template', body=self._index_template())

  def init_job(self, job_id=None, username=None, type='default', **kwargs):
    doc = {
           'id': job_id,
           'type': type,
           'username': username,
           'status': 'pending',
           'submit_time': TMUtils.date2str(datetime.datetime.now())
           }
    if not job_id: job_id = self._allocate_id()
    # Put params into the doc
    doc['params'] = kwargs
    self.update_job(job_id, doc)
    return id

  def get_status(self, job_id):
    return self.get_job(job_id)['status']

  def set_status(self, job_id, status):
    doc = self.get_job(job_id)
    doc['status'] = status
    self.update_job(job_id, doc)

  def get_field(self, job_id, field):
    return self.get_job(job_id).get(field)

  def set_field(self, job_id, field, value):
    doc = self.get_job(job_id)
    doc[field] = value
    self.update_job(job_id, doc)

  def finalize(self, job_id, status='finished'):
    doc = self.get_job(job_id)
    doc['end_time'] = TMUtils.date2str(datetime.datetime.now())
    doc['status'] = status
    self.update_job(job_id, doc)

  def get_job(self, job_id):
    doc = self.es.get(index=self.INDEX, doc_type=self.DOC_TYPE, id=job_id)
    if not doc:
      raise Exception(message="Job {} doesn't exist".format(job_id))
    return doc['_source']

  def update_job(self, job_id, doc):
    self.es.index(index=self.INDEX, id=job_id, doc_type=self.DOC_TYPE, body=doc)

  def scan_jobs(self, limit=10, username_filter=None):
    search = Search(using=self.es, index=self.INDEX).sort('-submit_time')[:limit]

    # TODO: First query - currently running jobs, second one - other jobs
    # q = Q('match', status='running')
    #for query in [q, ~q]:
    #  jobs = search.query(query).execute()
    jobs = search.execute()
    for hit in jobs:
      if username_filter and username_filter != hit["username"]:
        continue
      yield hit

  def _index_template(self):
    template = {
      "template" : self.INDEX,
      "mappings": {
        self.DOC_TYPE: {
          "properties": {
            "submit_time": {
              "type": "date",
              "format": "basic_date_time_no_millis"
            },
            "end_time": {
              "type": "date",
              "format": "basic_date_time_no_millis"
            },
          }
        }
      }
    }
    return template
