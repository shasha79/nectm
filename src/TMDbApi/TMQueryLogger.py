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
from cmreslogging.handlers import CMRESHandler
from Config.Config import G_CONFIG
import logging
from elasticsearch_dsl import MultiSearch, Search
from elasticsearch import Elasticsearch
# Forcing modification of a private field to avoid logging redundant data
CMRESHandler._CMRESHandler__LOGGING_FILTER_FIELDS += ['args', 'exc_info', 'exc_text', 'filename', 'funcName',
                                                                   'levelname',
                                                                   'lineno', 'module',
                                                                   'pathname', 'process', 'processName', 'stack_info',
                                                                   'thread',
                                                                   'threadName',
                                                                   'msg', 'message']


class TMQueryLogger:
  LOGGER_NAME = "TMQueryLogger"
  ES_INDEX_NAME="query_log"

  def __init__(self):
    es_config = G_CONFIG.config['elasticsearch']
    hosts = [{'host': es_config['host'], 'port': es_config['port']}]
    self.handler = CMRESHandler(hosts=hosts,
                           auth_type=CMRESHandler.AuthType.NO_AUTH,
                           es_index_name=self.ES_INDEX_NAME,
                           index_name_frequency=CMRESHandler.IndexNameFrequency.MONTHLY)
    self.es = Elasticsearch(hosts=hosts)
    self.log = logging.getLogger(self.LOGGER_NAME)
    self.log.setLevel(logging.INFO)
    self.log.addHandler(self.handler)
    self.es.indices.put_template(name='qlogger_template', body=self._index_template())
 

  def log_query(self, username, ip, qparams, results):
    for query, result in zip(qparams.qlist, results):
      segment = result[0] if result else {'match': 0, 'mt': False}
      self.log.info("{}".format(query),
                    extra={ 'query': query,
                            'username' : username,
                            'ip': ip,
                            'source': qparams.source_lang,
                            'target': qparams.target_lang,
                            'domain' : qparams.domains,
                            'match': int(segment.get('match')),
                            'mt': segment.get('mt'),
                            'num_results': len(result)
                    })

  # Returns the following dictitionary:
  # {
  #   "admin": {              - username
  #       "count": 190        - total usage
  #        "mt": [
  #               106,         - total usage (non MT)
  #               84           - total usage (MT)
  #        ],
  #       "01/18": {          - month
  #           "count": 16,    - usage per month
  #           "mt": [
  #               16,         - usage per month (non MT)
  #               0           - usage per month (MT)
  #           ]
  #       },
  #  ...
  # }
  def stats(self):
    search = Search(using=self.es, index="{}*".format(self.ES_INDEX_NAME))
    search.aggs.bucket('users', 'terms', field='username', size=99999)\
      .bucket('usage', 'date_histogram', field='timestamp', interval="1M", format="MM/YY") \
      .bucket('mt', 'terms', field='mt', size=99999)
    res = search.execute()
    stats = dict()
    if not hasattr(res, 'aggregations') or not 'users' in res.aggregations: return stats
    for user_bucket in  res.aggregations['users'].buckets:
      user_stats = dict()
      user_stats["count"] = user_bucket["doc_count"]
      user_stats["mt"] = [0, 0]
      for usage in user_bucket["usage"]["buckets"]:
        month = usage["key_as_string"]
        user_stats[month] = {"count" : usage["doc_count"]}
        user_stats[month]["mt"] = [0, 0]
        for mt_bucket in usage["mt"]["buckets"]:
          user_stats[month]["mt"][mt_bucket["key"]] = mt_bucket["doc_count"]
          user_stats["mt"][mt_bucket["key"]] +=  mt_bucket["doc_count"]

        #print(usage)

      stats[user_bucket["key"]] = user_stats
   # return res.to_dict()
    return stats

  def _index_template(self):
     template =  {
       "template": self.ES_INDEX_NAME + "*",
       "mappings" : {
         "python_log": {
           "properties": {
             "username": {
              "type": "keyword"
            }
          }
        }
      } 
     }
     return template


if __name__ == "__main__":
  import json
  tl = TMQueryLogger()
  print(json.dumps(tl.stats()))
