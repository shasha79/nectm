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
from flask_restful import Resource, abort, inputs

from Auth import user_permission, PermissionChecker

class TokenResource(Resource):
  decorators = [PermissionChecker(user_permission)]
  """
  @api {get} /token Dummy endpoint, needed to quickly validate token
  @apiVersion 1.0.0
  @apiName Get
  @apiGroup Login
  @apiUse Header
  @apiPermission user


  """
  def get(self):
      return {'token': 'valid'}
