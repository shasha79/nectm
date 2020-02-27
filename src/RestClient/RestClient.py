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
import sys
import os
import requests
import logging
import time
import json
from timeit import default_timer as timer
from requests_toolbelt import MultipartEncoder


class RestClient:

  def __init__(self, username=None, password=None, host='http://localhost', port=5000, version='1'):
    self.username = username
    self.password = password
    self.set_url(host, port, version)
    self.token = None

  def set_url(self, host, port, version):
    self.base_url = "{}:{}/api/v{}".format(host, port, version)

  def query(self, query, slang, tlang, out='json', strip_tags=False, min_match=75, limit=10, operation_match='regex,tags', concordance=False, aut_trans=False, domain=None, tag=None, smeta=None,tmeta=None): # split isn't default ,split
    params = {'slang': slang, 'tlang': tlang, 'out': out, 'q': query,
              'strip_tags': strip_tags, 'min_match': min_match, 'limit': limit,
              'operation_match': operation_match,
              'concordance': concordance,
              'smeta': smeta, 'tmeta': tmeta,
              'aut_trans': aut_trans,
              'tag' : tag if tag else domain} # backward compatibility
    print("PARAMS: {}".format(params))
    response = self._call_api('/tm', 'get', params=params)
    if out == 'json':
      return response.json()
    # Moses format
    return response.content.decode('utf-8')

  def query_batch(self, queries, slang, tlang, out='json', strip_tags=False, min_match=75, limit=10, operation_match = 'regex,tags,posTag', aut_trans=False, domain=None, split_pattern=None): ## split isn't default ,split
    # Represent params as a list of tuple to allow multiple values for 'q' parameter
    params = [('slang', slang), ('tlang', tlang), ('out', out),
              ('strip_tags', strip_tags), ('min_match', min_match),
              ('limit', limit), ('operation_match', operation_match),
              ('aut_trans', aut_trans),
              ('tag', domain),
              ('split_pattern', split_pattern)]
    params += [('q', q) for q in queries]
    print("PARAMS: {}".format(params))
    response = self._call_api('/tm/query_batch', 'post', jsond=params, headers={'Content-Type': 'application/json'})
    if out == 'json':
      return response.json()
    # Moses format
    return response.content.decode('utf-8')



  def add_tu(self, stext, ttext, slang, tlang, domain, file_name='', smeta=None,tmeta=None):
    response = self._call_api('/tm', 'post', params={'stext': stext,
                                                     'ttext': ttext,
                                                     'slang': slang,
                                                     'tlang': tlang,
                                                     'tag': [domain],
                                                     'file_name':file_name,
                                                     'smeta': smeta,
                                                     'tmeta': tmeta})
    return response.json()

  def import_tm(self, tmx_file, domain, lang_pairs=[]):
    m = MultipartEncoder(fields={'file': (os.path.basename(tmx_file), open(tmx_file, 'rb'), 'text/plain')})
    headers = {'Content-Type': m.content_type}
    response = self._call_api('/tm/import', 'put', params={'tag': domain, 'lang_pair': lang_pairs}, data=m, headers=headers)
    return JobMonitor(self, response.json())()

  def export_tm(self, slang, tlang, squery=None, tquery=None, duplicates_only=False, filters={}):
    # Prepare params dict
    params = {'slang': slang, 'tlang': tlang}
    if squery: params['squery'] = squery
    if tquery: params['tquery'] = tquery
    if duplicates_only: params['duplicates_only'] = True
    params.update(filters)
    # Actual call
    response = self._call_api('/tm/export', 'post', params=params)
    return JobMonitor(self, response.json())()

  def generate_tm(self, slang, tlang, plang, domain=[], force=False):
    response = self._call_api('/tm/generate', 'put', params={'slang': slang, 'tlang': tlang, 'plang': plang, 'tag': domain, 'force': force})
    return JobMonitor(self, response.json())()


  def delete_tm(self, slang, tlang, duplicates_only, filters={}):
    params = {'slang': slang, 'tlang': tlang}
    params.update(filters)
    if duplicates_only: params['duplicates_only'] = True

    response = self._call_api('/tm', 'delete', params=params)
    return JobMonitor(self, response.json())()

  def pos(self, slang, tlang, universal=False, filters={}):
    params = {'slang': slang, 'tlang': tlang, 'universal': universal}
    params.update(filters)
    response = self._call_api('/tm/pos', 'put',params=params)
    return JobMonitor(self, response.json())()

  def maintain(self, slang, tlang, filters={}):
    params = {'slang': slang, 'tlang': tlang}
    params.update(filters)
    response = self._call_api('/tm/maintain', 'post',params=params)
    return JobMonitor(self, response.json())()

  def clean(self, slang, tlang, filters={}):
    params = {'slang': slang, 'tlang': tlang}
    params.update(filters)
    response = self._call_api('/tm/clean', 'post',params=params)
    return JobMonitor(self, response.json())()

  def stats(self):
    response = self._call_api('/tm/stats', 'get')
    return response.json()

  def get_user(self, username):
    api_path = '/users'
    if username:
      api_path += '/{}'.format(username)
    response = self._call_api(api_path, 'get')
    return response.json()

  def set_user(self, username, **kwargs):
    response = self._call_api('/users/{}'.format(username), 'post',params=kwargs)
    return response.json()

  def delete_user(self, username):
    response = self._call_api('/users/{}'.format(username), 'delete')
    return response.json()


  def get_tag(self, tagname):
    api_path = '/tags'
    if tagname:
      api_path += '/{}'.format(tagname)
    response = self._call_api(api_path, 'get')
    return response.json()

  def set_tag(self, tagname, **kwargs):
    response = self._call_api('/tags/{}'.format(tagname), 'post',params=kwargs)
    return response.json()

  def delete_tag(self, tagname, **kwargs):
    response = self._call_api('/tags/{}'.format(tagname), 'delete', params=kwargs)
    return response.json()

  def set_user_scope(self, username, **kwargs):
    response = self._call_api('/users/{}/scopes'.format(username), 'post',params=kwargs)
    return response.json()

  def delete_scope(self, username, scope, **kwargs):
    response = self._call_api('/users/{}/scopes/{}'.format(username, scope), 'delete', params=kwargs)
    return response.json()

  def get_job(self, job_id, **kwargs):
    response = self._call_api('/jobs/{}'.format(job_id), 'get', params=kwargs)
    return response.json()

  def kill_job(self, job_id, **kwargs):
    response = self._call_api('/jobs/{}'.format(job_id), 'delete', params=kwargs)
    return response.json()

  def get_settings(self, **kwargs):
    response = self._call_api('/settings', 'get', params=kwargs)
    return response.json()

  def set_settings(self, **kwargs):
    response = self._call_api('/settings', 'put', params=kwargs)
    return response.json()


  # --- Helper methods ------

  def _call_api(self, suffix, method='get', params={}, data={}, headers={}, files={}, stream=False):
    # Imitating do-while: first, try to call method with JWT authentication. If failed, try authorizing with the credentials
    # and call it again. If failed again -> raise an exception
    logging.debug("Api: {}, method: {}, Params: ".format(suffix, method, params))
    t_start = timer()

    for i in range(0,2):
      response = None
      if self.token:
        logging.info("JWT Token: {}".format(self.token))
        headers.update({'Authorization': 'JWT {}'.format(self.token)})
        response = getattr(requests, method)(self._get_url(suffix), params=params, data=data, headers=headers, files=files, stream=stream, verify=False)
      logging.debug("------ {}, response: {}".format(i, response))
      #if response != None: logging.debug("Request: {}".format(response.request.__dict__))
      # If token expired, authorize again and repeat
      if response == None or response.status_code == 401:
        if i: response.raise_for_status() # we are here for the second time, something is wrong with authorization,
                                          # raise an exception
        self._auth() # get token
      elif not response.ok:
        # Some other problem has occured - raise an exception
        try:
          logging.error("Server returned error message: {}".format(response.json()))
        except:
          pass # if response is not json
        response.raise_for_status()
      else:
        # success
        t_end = timer()
        logging.debug("Execution time: {}".format(t_end-t_start))
        return response

  def _auth(self):
    auth_response = requests.post(self._get_url('/auth'),
                                  data=json.dumps({'username': self.username, 'password': self.password}),
                                  headers={"content-type": "application/json"},
                                  verify=False)
    # TODO: cache token for future requests
    if auth_response.ok:
      self.token = auth_response.json()['access_token']
      logging.debug("Authorized user {} successfully".format(self.username))
      return True
    auth_response.raise_for_status()

  def _get_url(self, suffix):
    if suffix[0] != '/': suffix = '/' + suffix
    return self.base_url + suffix

class JobMonitor:
  def __init__(self, client, job_json):
    self.client = client
    print(job_json)
    self.job_id = job_json['job_id']
    self.end_statuses = {'finished', 'failed', 'succeded', 'killed'}

  def __call__(self, *args, **kwargs):
    status_json = self.client.get_job(self.job_id)
    print("STATUS: {}".format(status_json))
    job_status = status_json['jobs'][0]['status']
    logging.info('Monitoring job: {}'.format(self.job_id))
    logging.info('Job status: {}'.format(job_status))
    while not job_status in self.end_statuses: # failed? killed?
      time.sleep(5)
      status_json = self.client.get_job(self.job_id)
      print(status_json)
      job_status = status_json['jobs'][0]['status']
      logging.info('Job status: {}'.format(job_status))
    return status_json

if __name__ == "__main__":
  logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO, stream=sys.stderr)
  logging.getLogger("requests").setLevel(logging.WARNING)
  logging.getLogger("urllib3").setLevel(logging.WARNING)
  import json, pprint
  from CommandLine import CommandLine
  cl = CommandLine()
  client = RestClient("admin", "admin")
  out = cl(client)
  if isinstance(out, dict):
    pprint.pprint(json.dumps(out, indent=4))
  else:
    for o in out:
      pprint.pprint(o)
