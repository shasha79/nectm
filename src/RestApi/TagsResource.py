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
from flask_restful.reqparse import RequestParser

from flask_jwt import current_identity

from RestApi.Models import Tags, CRUD
from Auth import admin_permission, user_permission, PermissionChecker, UserScopeChecker
from TMPreprocessor.TMRegExpPreprocessor import TMRegExpPreprocessor

class TagsResource(Resource):
  decorators = [PermissionChecker(user_permission)]
  regex_pp = TMRegExpPreprocessor()

  """
  @api {get} /tags/<tag_id> List available tags or get specific tag details
  @apiVersion 1.0.0
  @apiName Get
  @apiGroup Tags
  @apiUse Header
  @apiPermission user

  @apiParam {String} [tag]
  
  @apiError {String} 404 Tag doesn't exist
  @apiError {String} 403 Insufficient permissions
  
  """
  def get(self, tag_id=None):
    tags = []
    if tag_id:
      tag = Tags.query.get(tag_id)
      if tag:
        tags =  [tag.to_dict()]
      else:
        abort(404, mesage="Tag {} doesn't exist".format(tag_id))
    else:
        tags = [tag.to_dict() for tag in Tags.query.all()]
    # Filter scopes according to permissions
    tags = UserScopeChecker.filter_domains(tags, key_fn=lambda t: t["id"])
    if tag_id:
      if not tags:
        abort(404, mesage="Tag {} doesn't exist".format(tag_id))
      return tags[0]
    # List of all users
    return {'tags': tags}


  """
  @api {post} /tags/:id Update tag
  @apiVersion 1.0.0
  @apiName Post
  @apiGroup Tags
  @apiUse Header
  @apiPermission admin

  @apiParam {String} id
  @apiParam {String} name
  @apiParam {String} type

  @apiError {String} 403 Insufficient permissions

  """
  @admin_permission.require(http_exception=403)
  def post(self, tag_id):
    args = self._reqparse()
    tag = Tags.query.get(tag_id)

    try:
      if tag:
        tag.update(**args)
        CRUD.update()
      else:
        tag = Tags(tag_id, **args)
        CRUD.add(tag)
    except Exception as e:
      abort(500, message=str(e))
    return {"message" : "Tag {} added/updated successfully".format(tag_id)}

  def _reqparse(self):
      parser = RequestParser(bundle_errors=True)
      parser.add_argument(name='name', help="Tag name")
      parser.add_argument(name='type', help="Tag type")

      return parser.parse_args()


  """
  @api {delete} /tags/:id Delete tag
  @apiVersion 1.0.0
  @apiName Delete
  @apiGroup Tags
  @apiUse Header
  @apiPermission admin

  @apiParam {String} tag

  @apiError {String} 403 Insufficient permissions
  @apiError {String} 404 Tag doesn't exist

  """
  @admin_permission.require(http_exception=403)
  def delete(self, tag_id):
    tag = Tags.query.get(tag_id)
    if tag:
      try:
        CRUD.delete(tag)
      except Exception as e:
        abort(500, message=str(e))
    else:
      abort(404, mesage="Tag {} doesn't exist".format(tag_id))
    return {"message" : "Tag {} deleted successfully".format(tag_id)}
