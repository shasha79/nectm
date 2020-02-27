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
"""
  @api {INFO} /Settings Settings -- Change & Update ActivaTM code
  @apiName Update
  @apiVersion 0.1.0
  @apiGroup Settings
  @apiPermission admin

  @apiExample {curl} Example & Notes

  * See several git code => https://trello.com/b/qvYlSdKT/git-commands

  Clone via ssh the repository git => clone ssh://lianet@192.168.100.103:26/var/git/expert

  Update repository change => git push

  1- cd /opt/elasticTM
  2- sudo su -- su alexander
  3- update local code =>	git pull
  4- restart the service =>	service uwsgi restart
"""

"""
  @api {INFO} /Settings Check -- Check ActivaTM files
  @apiName Check
  @apiVersion 0.1.0
  @apiGroup Settings
  @apiPermission admin

  @apiExample {curl} Example & Notes

  # Log files => /var/log/elastictm

"""

"""
  @api {INFO} /Settings Query -- Query Elasticsearch
  @apiName Query
  @apiVersion 0.1.0
  @apiGroup Settings
  @apiPermission admin

  @apiExample {curl} Example & Notes

  # List elasticsearch index => curl 'localhost:9200/_cat/indices?v'
  # List all documents of specific index => http://localhost:9200/tm_es/_search?pretty=true&q=*:*
  # Delete an index => curl -X DELETE 'http://localhost:9200/map_en_es/'
  # Query an specific text => curl -XPOST 'localhost:9200/tm_en/_search?pretty' -d '{"query":{"match":{"text":"It is also possible to send an email to client_service@repair.net."}}}'

"""
class Settings():

  def __int__(self):

    g = 0