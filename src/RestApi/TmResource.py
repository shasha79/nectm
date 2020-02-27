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
from flask import Response, request
from flask_restful import Resource, abort, inputs
from flask_restful.reqparse import RequestParser
import werkzeug
import os
import dateutil.parser
import tempfile
import re
import datetime
import json
import logging

from celery import task

from TMDbApi.TMDbApi import TMDbApi
from TMDbApi.TMUtils import TMUtils
from TMDbApi.TMTranslationUnit import TMTranslationUnit
from TMDbApi.TMQueryParams import TMQueryParams

from TMPreprocessor.Xml.XmlUtils import XmlUtils

from TMX.TMXParser import TMXParser

from TMDbApi.TMDbQuery import TMDbQuery

from JobApi.ESJobApi import ESJobApi
from JobApi.SparkTaskDispatcher import SparkTaskDispatcher


from TMDbApi.TMExport import TMExport
from TMOutputer.TMOutputerMoses import TMOutputerMoses
from TMDbApi.TMQueryLogger import TMQueryLogger

from Auth import admin_permission, user_permission, PermissionChecker, UserScopeChecker
from RestApi.Models import Users, Tags

from flask_jwt import current_identity

# Search/update/delete segments
class TmResource(Resource):
  decorators = [PermissionChecker(user_permission)]

  db = TMDbApi('elasticsearch')
  job_api = ESJobApi()
  qlogger = TMQueryLogger()

  """
  @apiDefine FilterParams
  @apiParam {String} [file_name] Filter segments by filename(s).
  @apiParam {String} [organization] Filter segments by organization(s).
  @apiParam {String} [tag] Filter segments by tag(s).
  @apiParam {String} [industry] Filter segments by industry(s).
  @apiParam {String} [language] Filter segments by language(s).
  @apiParam {String} [type] Filter segments by type(s).
  @apiParam {String} [username] Filter segments by creator's username.

  @apiParam {Date} [tm_change_date] Filter segments by TM change date (.from and .to limits).
  @apiParam {Date} [tm_creation_date] Filter segments by TM creation date (.from and .to limits).
  @apiParam {Date} [insert_date] Filter segments by date of insertion into DB (.from and .to limits).
  @apiParam {Date} [update_date] Filter segments by date of update in DB  (.from and .to limits).
  @apiParam {Date} [check_date] Filter segments by script check (.from and .to limits).
  @apiParam {Integer} [dirty_score] Filter segments by clean score (.from and .to limits).

  @apiParamExample {json} FilterExample
                                          {
                                          "tm_change_date.from" : "20160414",
                                          "tm_change_date.to" :"20160822",
                                          "check_date.to": "20160530" }

  """
  """
  @apiDefine Header
  @apiHeader {String} token Token returned by auth endpoint.
  @apiError {String} 401 Unathorized
  @apiError {String} 403 Insufficient permissions
  """
  """
  @apiDefine ExportDeleteCommonParams
  @apiParam {String} slang Source language.
  @apiParam {String} tlang Target language.
  @apiParam {String} [squery] Filter source segments by this query. Supports regular expressions.
  @apiParam {String} [tquery] Filter target segments by this query. Supports regular expressions.
  @apiParam {Number} [limit] Limit number of exported segments.
  @apiParam {Boolean} [duplicates_only] Return duplicate segments only (duplicates = having the same source text)
  """

  # Querying segment translation into the target language
  """
   @api {get} /tm Search translation memory segments
   @apiVersion 1.0.0
   @apiName Query
   @apiGroup TranslationMemory
   @apiUse Header
   @apiPermission user

   @apiParam {String} q String to query
   @apiParam {String} slang Source language.
   @apiParam {String} tlang Target language.
   @apiParam {String='json','moses'} [out='json'] Output format.
   @apiParam {Number} [limit=10] Limit output to this number of segments (for json). For Moses, only one segment is output
   @apiParam {Number} [min_match=75] Return only match above or equal to given threshold (0-100)
   @apiParam {Boolean} [strip_tags=false] Strip all XML tags from the query
   @apiParam {Boolean} [concordance=false] Concordance search mode
   @apiParam {Boolean} [aut_trans=True] Apply machine translation if match score is less than a threshold
   @apiParam {String} [tag] Prefer given tag(s). Penalize segments from other tags
   @apiParam {String} smeta Source metadata (JSON).
   @apiParam {String} tmeta Target metadata (JSON).
   @apiParam {String='regex,tags,posTag,split' or 'None'} [operation_match='regex,tags,posTag,split'] Operation to match. If None only editdistace is calculated

   @apiSuccess {String/Json} Translation units matching the query
   @apiExample {curl} Example usage:
    curl -G "http://127.0.0.1:5000/api/v1/tm?q=English+skills"
    -X GET
    -H 'Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE0NjQ2MTU0NDUsImlkZW50aXR5IjoxLCJleHAiOjE0NjQ3MDE4NDUsIm5iZiI6MTQ2NDYxNTQ0NX0.j_p4a-NUG-6zu3Zh4_d1d0C5fkiTy-eJcVyyT1z2IfU'

  """
  def get(self):
    args = self._get_reqparse().parse_args()
    sl = self._detect_lang(args)
    if not sl: return {"message": "Couldn't detect source language. Provide it via 'slang' parameter"}
    # Check user scope
    if not UserScopeChecker.check((sl, args.tlang), args.tag):
      abort(403, message="No valid user permission scope found for given language pair, tag and operation")

    # Do the query
    out = self._query([args.q], args)
    if out: out = out[0] # only one query

    # Moses format output - either translation or original query
    if args.out == 'moses':
      return Response(out, mimetype='text/xml; charset=utf-8')
    return Response(json.dumps(out, ensure_ascii=False), mimetype='application/json; charset=utf-8')

  def _query(self, qlist, args, penalty=0):
    if args.strip_tags:
      qlist = [XmlUtils.strip_tags(q) for q in qlist]
    # Query TM DB
    # TODO: paginate
    moses_out = []
    rlist = []
    if args.operation_match=='None':
      op_match = []
    else: op_match = args.operation_match.split(',')
    # The second argument is an empty list, because the query has not been preprocessed (tokenizer and posTag)
    # exact_query indicate if we want to search on elasticsearch segments with exact length
    tag_ids = args.tag if args.tag else args.domain # backward compatibility fallback
    self._validate_tag_ids(tag_ids, abort_if_not_exists=False)

    qparams = TMQueryParams(qlist,
                            [],
                            args.slang,
                            args.tlang,
                            op_match,
                            args.out,
                            2*args.limit, # make sure we have enought to filter
                            tag_ids,
                            min_match=args.min_match,
                            concordance=args.concordance,
                            aut_trans=args.aut_trans,
                            exact_length=False)

    for _q, results in zip(qlist, self.db.query(qparams)):
      moses_qout = _q.encode('utf-8')
      count = 0
      r = []
      qresults = results[0] if len(results) else []
      for (segment,match) in qresults:
        if segment.domain:
          if Tags.has_public(segment.domain):
            logging.debug("Segment has either empty domain or domain with public access: {} ".format(segment.to_dict_short()))
          elif not UserScopeChecker.check((args.slang, args.tlang), segment.domain):
            logging.debug("Filtered out segment (out of user scope): {}".format(segment.to_dict_short()))
            continue
          filtered_tags = [t["id"] for t in UserScopeChecker.filter_domains(self._tag_ids2dict(segment.domain), key_fn=lambda t:t["id"], allow_unspecified=False)]
          if not filtered_tags or (tag_ids and not set(tag_ids).issubset(set(filtered_tags))):
            logging.debug("Filtered out segment from other domains".format(segment.to_dict_short()))
            continue
        else:
          filtered_tags = [] # Segment's domain is empty -> it is machine translation result, take it in any case
        if args.out == 'moses':
          moses_qout = TMOutputerMoses().output_segment(segment, match)
          break
        # Check perfect match
        if (args.smeta or args.tmeta) and segment.source_metadata == args.smeta and segment.target_metadata == args.tmeta:
          match += 1
          if int(match) > 100:
            r.clear() # Clear all previous results to leave only 101
            count = args.limit # break on finding perfect match

        segment_json = {"tu": segment.to_dict_short(),
                        "match": int(match),
                        "mt": results[1],
                        "update_date": segment.update_date,
                        "username": segment.username,
                        "file_name": segment.file_name,
                        "tag": filtered_tags
        }
        # TODO: hide some fields for user?
        if (current_identity.role != Users.ADMIN):
          pass
        r.append(segment_json)
        count += 1
        if count >= args.limit: break
      moses_out.append(moses_qout)
      rlist.append(r)
    # Apply match penalty
    if penalty:
      for r in rlist: r['match'] -= penalty
    # Log query & its results:
    self.qlogger.log_query(current_identity.id, request.remote_addr, qparams, rlist)

    # Moses format output - either translation or original query
    if args.out == 'moses':
      return moses_out
    if not rlist: rlist = [[] for i in range(0,len(qlist))] # if no results, make sure it will have the same length as qlist
    return [{'query': q, 'results': r} for q,r in zip(qlist, rlist)]


  def _get_reqparse(self):
    parser = RequestParser()
    parser.add_argument(name='q', required=True, help="TM query string is a mandatory option")
    parser.add_argument(name='slang', help="Source language is a desired option", type=self._validate_lang)
    parser.add_argument(name='tlang', required=True, help="Target language is a mandatory option",
                          type=self._validate_lang)
    parser.add_argument(name='smeta', required=False, help="Source metadata (valid JSON)", type=self._validate_json, default={})
    parser.add_argument(name='tmeta', required=False, help="Target metadata (valid JSON)", type=self._validate_json, default={})
    parser.add_argument(name='limit', type=int, default=10,
                          help="Limit output to this number of segments (for JSON output. For Moses, only one segment will be output")
    parser.add_argument(name='duplicates_only', type=inputs.boolean, default=False,
                        help="Duplicate segments only")

    parser.add_argument(name='out', choices=['json', 'moses'], help="Output format", default='json')
    parser.add_argument(name='strip_tags', type=inputs.boolean, default=False,
                          help="Strip all XML tags from the query")
    min_match_default=65
    parser.add_argument(name='min_match',
                          type=int,
                          default=min_match_default,
                          help="Return only match above or equal to given threshold (0-100) Default is {}.".format(min_match_default))
    parser.add_argument(name='operation_match',
                        type=str,
                        default='regex,tags', # split & posTag isn't default posTag,split
                        help="Apply different operation to obtain the match. Default is all (All operation).")
    parser.add_argument(name='concordance', type=inputs.boolean, default=False,
                          help="Concordance search mode")
    parser.add_argument(name='aut_trans', type=inputs.boolean, default=False, help="Apply machine translation if match score is less than a threshold")
    parser.add_argument(name='tag', action='append', help="Prefer given tag(s). Penalize segments from other tags", type=str)
    parser.add_argument(name='domain', action='append', help="DEPRECATED: use 'tag' instead", type=str)
    return parser

  """
   @api {post} /tm Add new translation memory unit
   @apiVersion 1.0.0
   @apiName Add
   @apiGroup TranslationMemory
   @apiUse Header
   @apiPermission user

   @apiParam {String} stext Source segment text.
   @apiParam {String} ttext Target segment text..
   @apiParam {String} slang Source language.
   @apiParam {String} tlang Target language.
   @apiParam {String} smeta Source metadata (JSON).
   @apiParam {String} tmeta Target metadata (JSON).
   @apiParam {String} tag Translation unit tag.
   @apiParam {String} [file_name] File name (or source name)
  """
  def post(self):
    args = self._post_reqparse().parse_args()

    tag_ids = args.tag if args.tag else args.domain # backward compatibility fallback
    if not tag_ids:
      abort(403, message="Tag is required option")
    # Check tag existence
    self._validate_tag_ids(tag_ids)

    if current_identity.role != Users.ADMIN and not Tags.has_specified(tag_ids):
      abort(403, message="Tags should include at least one private or public tag")
    # Check user scope
    if not UserScopeChecker.check((args.slang, args.tlang), tag_ids, is_update=True):
      abort(403, message="No valid user permission scope found for given language pair, tag and operation")


    now_str = TMUtils.date2str(datetime.datetime.now())
    segment = TMTranslationUnit({'source_text': args.stext,
                         'target_text': args.ttext,
                         'source_language': args.slang,
                         'target_language': args.tlang,
                         'source_metadata': args.smeta,
                         'target_metadata': args.tmeta,
                         'domain' : tag_ids,
                         'file_name': args.file_name,
                         'tm_creation_date': now_str,
                         'tm_change_date': now_str,
                         'username': current_identity.id })
    self.db.add_segments([segment]) #add_segment(segment) --> Change this line, because the function add_segment replace tag in TM
    return  {'message': 'Translation unit was added successfully'}


  def _post_reqparse(self):
    parser = RequestParser()
    parser.add_argument(name='stext', required=True, help="Source text is a mandatory option", type=str)
    parser.add_argument(name='ttext', required=True, help="Target text is a mandatory option", type=str)
    parser.add_argument(name='slang', required=True, help="Source language is a mandatory option", type=self._validate_lang)
    parser.add_argument(name='tlang', required=True, help="Target language is a mandatory option", type=self._validate_lang)
    parser.add_argument(name='smeta', required=False, help="Source metadata (valid JSON)", type=self._validate_json)
    parser.add_argument(name='tmeta', required=False, help="Target metadata (valid JSON)", type=self._validate_json)
    # TODO: when domain parameter is removed, make tag to be required parameter
    parser.add_argument(name='tag', required=False, help="Tag or domain name is a mandatory option", action='append')
    parser.add_argument(name='domain', required=False, help="DEPRECATED: use 'tag' instead", type=str)

    parser.add_argument(name='file_name', help="File or source name", type=str, default='')

    # Add filter arguments to the parser
    self._add_filter_args(parser)
    return parser

  def _validate_json(self, json_str):
    if not json_str: return {}
    try:
      return json.loads(json_str)
    except:
      abort(400, message="Invalid JSON: {}".format(json_str))


  def _detect_lang(self, args):
    if not args.slang:
      args.slang = TMUtils.detect_lang(args.q)[0]
    return args.slang

  # Delete
  """
    @api {delete} /tm Delete translation memory segments from DB
    @apiVersion 1.0.0
    @apiName Delete
    @apiGroup TranslationMemory
    @apiUse Header
    @apiPermission admin

    @apiUse ExportDeleteCommonParams
    @apiUse FilterParams

    @apiExample {curl} Example usage:
    curl -G "http://127.0.0.1:5000/api/v1/tm?slang=en&tlang=es&file_name=test.tmx"
    -X DELETE
    -H 'Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE0NjQ2MTU0NDUsImlkZW50aXR5IjoxLCJleHAiOjE0NjQ3MDE4NDUsIm5iZiI6MTQ2NDYxNTQ0NX0.j_p4a-NUG-6zu3Zh4_d1d0C5fkiTy-eJcVyyT1z2IfU'
    """
  @admin_permission.require(http_exception=403)
  def delete(self):
    args = self._common_reqparse().parse_args()
    filters = self._args2filter(args)
    # Setup a job using Celery & ES
    task = self.delete_task.apply_async()
    self.job_api.init_job(job_id=task.id, username=current_identity.id, type='delete', filter=filters, slang=args.slang, tlang=args.tlang, duplicates_only=args.duplicates_only)
    return {"job_id": task.id, "message": "Job submitted successfully"}

  @task(bind=True)
  def delete_task(self):
    SparkTaskDispatcher().run(self.request.id, 'Delete')
    return {'status': 'Task completed!'}

  ############### Helper methods ###################
  def _validate_lang(self, lang):
    if not lang: return lang

    lang = lang.lower()
    try:
      TMUtils.validate_lang(lang)
    except Exception as e:
      print(e)
      abort(400, mesage="Unsupported language".format(lang))
    return lang

  def _common_reqparse(self):
    parser = RequestParser()
    parser.add_argument(name='slang', required=True, help="Source language is a mandatory option", type=self._validate_lang)
    parser.add_argument(name='tlang', required=True, help="Target language is a mandatory option", type=self._validate_lang)
    parser.add_argument(name='squery', help="Get source segments matching this pattern. Can be regular expression")
    parser.add_argument(name='tquery', help="Get target segments matching this pattern. Can be regular expression")

    parser.add_argument(name='limit', type=int, help="Limit operation to this number of segments")
    parser.add_argument(name='duplicates_only', type=inputs.boolean, default=False,
                        help="Duplicate segments only")

    self._add_filter_args(parser)
    return parser

  def _add_filter_args(self, parser):
    for attr in TMDbQuery.str_attrs:
      if attr == "domain": attr = "tag"
      parser.add_argument(name=attr, action='append', help="Filter TM by {} (may have multiple values)".format(attr))
    for attr in TMDbQuery.date_attrs + TMDbQuery.num_attrs:
      parser.add_argument(name=attr + ".from", help="Filter {} - lower limit".format(attr))
      parser.add_argument(name=attr + ".to", help="Filter {} - upper limit".format(attr))

  def _args2filter(self, args):
    filter = dict()
    # Backward compatibility - translate tag into domain
    if hasattr(args, 'tag') and getattr(args, 'tag'):
      self._validate_tag_ids(args.tag)
      filter['domain'] = args.tag

    # Parse string filters
    for attr in TMDbQuery.str_attrs:
      if hasattr(args, attr) and getattr(args, attr):
        filter[attr] = getattr(args, attr)
    # Parse range filters (dates, numbers)
    range_filters = [(attr, 'date') for attr in TMDbQuery.date_attrs]
    range_filters += [(attr, 'num') for attr in TMDbQuery.num_attrs]
    for attr,type in range_filters:
      filter[attr] = dict()
      # Parse from/to limit and convert them to ES-friendly dictionary
      for (n,p) in [('from', 'gte'), ('to', 'lte')]:
        value = getattr(args, attr + '.' + n)
        if not value: continue
        # Convert to range
        if type == 'date':
          fvalue = dateutil.parser.parse(value).strftime(TMDbApi.DATE_FORMAT)
        else:
          # numeric
          fvalue = float(value)
        filter[attr][p] = fvalue

    for attr in ['squery', 'tquery']:
      if hasattr(args, attr) and getattr(args, attr):
        filter[attr] = re.compile(getattr(args, attr), re.U) # TODO: get additional flags
    logging.info("Arguments converted to filter dict: {}".format(filter))
    return filter

  def _validate_tag_ids(self, tag_ids, abort_if_not_exists=True):
    if not tag_ids: return True
    for tag_id in tag_ids:
      tag = Tags.query.get(tag_id)
      if not tag:
        if abort_if_not_exists:
          abort(400, mesage="Tag {} doesn't exist. You should add it first by using POST /tags/<tag>".format(tag_id))
        else:
          return False
    return True


  def _tag_names2ids(self, tagnames, abort_if_not_exists=True):
    tag_ids = []
    if not tagnames: return tag_ids
    for tag_name in tagnames:
      tag = Tags.query.filter_by(name = tag_name).one_or_none()
      if tag:
        tag_ids.append(tag.id)
      elif abort_if_not_exists:
        abort(400, mesage="Tag {} doesn't exist. You should add it first by using POST /tags/<tag>".format(tag_name))
    return tag_ids

  def _tag_ids2names(self, tagids):
    tag_names = []
    if not tagids: return tag_names
    for tag_id in tagids:
      tag = Tags.query.get(tag_id)
      if not tag:
        logging.error("Tag  id {} doesn't exist".format(tag_id))
      else:
        tag_names.append(tag.name)
    return tag_names


  def _tag_ids2dict(self, tagids):
    tags = []
    if not tagids: return tags
    for tag_id in tagids:
      tag = Tags.query.get(tag_id)
      if not tag:
        logging.error("Tag  id {} doesn't exist".format(tag_id))
      else:
        tags.append(tag.to_dict())
    return tags



class TmBatchQueryResource(TmResource):
  decorators = [PermissionChecker(user_permission)]

  # Querying segment translation into the target language
  """
   @api {get} /tm/query_batch Search translation memory segments
   @apiVersion 1.0.0
   @apiName QueryBatch
   @apiGroup TranslationMemory
   @apiUse Header
   @apiPermission user

   @apiParam {String} q String to query (multiple values allowed)
   @apiParam {String} slang Source language.
   @apiParam {String} tlang Target language.
   @apiParam {String} smeta Source metadata (JSON).
   @apiParam {String} tmeta Target metadata (JSON).
   @apiParam {String='json','moses'} [out='json'] Output format.
   @apiParam {Number} [limit=10] Limit output to this number of segments (for json). For Moses, only one segment is output
   @apiParam {Number} [min_match=75] Return only match above or equal to given threshold (0-100)
   @apiParam {Boolean} [strip_tags=false] Strip all XML tags from the query
   @apiParam {Boolean} [concordance=false] Concordance search mode
   @apiParam {Boolean} [aut_trans=True] Applied machine translation if there aren't match
   @apiParam {String} [tag] Prefer given tag(s). Penalize segments from other tags
   @apiParam {String} [split_pattern] Enable splitting of query to multiple queries by using this pattern (see https://docs.python.org/3/library/stdtypes.html#str.split)
   @apiParam {String='regex,tags,posTag,split' or 'None'} [operation_match='regex,tags,posTag,split'] Operation to match. If None only editdistace is calculated

   @apiSuccess {String/Json} Translation units matching the query
  """
  def get(self):
    args = self._get_reqparse().parse_args()
    #filters = self._args2filter(args)
    # Check user scope
    if not UserScopeChecker.check((args.slang, args.tlang), args.tag):
      abort(403, message="No valid user permission scope found for given language pair, tag and operation")

    if args.split_pattern:
      args.q = [item for sublist in args.q for item in sublist.split(args.split_pattern)]

    out_list = self._query(args.q, args)

    # Moses format output - either translation or original query
    if args.out == 'moses':
      return Response(b'\n'.join(out_list), mimetype='text/xml; charset=utf-8')

    return Response(json.dumps(out_list, ensure_ascii=False), mimetype='application/json; charset=utf-8')


  def post(self):
    return self.get()


  def _get_reqparse(self):
    parser = super()._get_reqparse()
    parser.replace_argument(name='q', required=True, action='append', help="TM query string is a mandatory option")
    parser.add_argument(name="split_pattern", default=None)
    return parser

class TmImportResource(TmResource):
  decorators = [PermissionChecker(user_permission)]

  # Import
  """
   @api {put} /tm/import Import translation memory segments from zipped TMX file
   @apiVersion 1.0.0
   @apiName Import
   @apiGroup TranslationMemory
   @apiUse Header
   @apiPermission admin

   @apiParam {File} file Zipped TMX file to import.
   @apiParam {String} tag Tag name of the imported file.
   @apiParam {String} [lang_pair] Language pair to import (for multilingual TMX files). 2-letter language codes join by underscore.
                                  By default, import first pair in each segment

   @apiExample {curl} Example usage:

    curl -G "http://127.0.0.1:5000/api/v1/tm/import?tag=Automotive&lang_pair=en_es"
     -F file=@data/test.zip -X PUT
    -H 'Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE0NjQ2MTU0NDUsImlkZW50aXR5IjoxLCJleHAiOjE0NjQ3MDE4NDUsIm5iZiI6MTQ2NDYxNTQ0NX0.j_p4a-NUG-6zu3Zh4_d1d0C5fkiTy-eJcVyyT1z2IfU'
   """
  def put(self):
    args = self._put_reqparse()
    # Check tag existence
    tag_ids = args.tag
    self._validate_tag_ids(tag_ids)
    if current_identity.role != Users.ADMIN and not Tags.has_specified(tag_ids):
      abort(403, message="Tags should include at least one private or public tag")

    lang_pairs = self._parse_lang_pairs(args.lang_pair)
    if not lang_pairs:
      lang_pairs = TMXParser(args.full_path).language_pairs()

    if not lang_pairs:
      abort(400, message="Failed to detect languages to import")

    # Check user scope
    for lang_pair in lang_pairs:
      if not UserScopeChecker.check(lang_pair, args.tag, is_import=True):
        abort(403, message="No valid user permission scope found for given language pair, tag and operation")

    # Setup a job using Celery & ES
    task = self.import_task.apply_async()
    self.job_api.init_job(job_id=task.id, username=current_identity.id, type='import', file=args.full_path, domain=tag_ids, lang_pairs=lang_pairs)
    return {"job_id": task.id, "message": "Job submitted successfully"}

  @task(bind=True)
  def import_task(self):
    SparkTaskDispatcher().run(self.request.id, 'Import')
    return {'status': 'Task completed!'}

  def _parse_lang_pairs(self, lang_pairs):
    if not lang_pairs: return []
    return [lp.split('_') for lp in lang_pairs]

  def _put_reqparse(self):
    parser = RequestParser()
    parser.add_argument(name='file', required=True, type=werkzeug.FileStorage, location='files')
    parser.add_argument(name='tag', required=True,  action='append', help="Translation memories tag is a mandatory option")
    parser.add_argument(name='lang_pair', action='append', help="Language pair to parse from TMX. May supply multiple pairs \ "
                                               "Each pair is a string of 2-letter language codes joined with underscore",
                        default=[],

                        )

    args =  parser.parse_args()
    # Store file in a local tmp dir
    tmp_dir = tempfile.mkdtemp(prefix='elastictm')
    os.chmod(tmp_dir, 0o755)
    args.full_path = os.path.join(tmp_dir, args.file.filename)
    args.file.save(args.full_path)
    # Validate language pairs
    for lp in args.lang_pair:
      if not re.match('[a-zA-Z]{2}_[a-zA-Z]{2}', lp):
        abort(400, mesage="Language pair format is incorrect: {} The correct format example : en_es".format(lp))

    return args

class TmExportResource(TmResource):
  decorators = [PermissionChecker(user_permission)]

  # Export
  """
  @api {post} /tm/export Export translation memory segments to zipped TMX file(s)
  @apiVersion 1.0.0
  @apiName Export
  @apiGroup TranslationMemory
  @apiUse Header
  @apiPermission admin

  @apiUse ExportDeleteCommonParams
  @apiUse FilterParams

  @apiSuccess {String} task_id ID of export task invoked in the background
 
  @apiExample {curl} Example usage:
   curl -XPOST "http://127.0.0.1:5000/api/v1/tm/export?slang=en&tlang=es&insert_date.from=20120122&tm_creation_date.to=20090915"
   -H 'Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE0NjQ2MTU0NDUsImlkZW50aXR5IjoxLCJleHAiOjE0NjQ3MDE4NDUsIm5iZiI6MTQ2NDYxNTQ0NX0.j_p4a-NUG-6zu3Zh4_d1d0C5fkiTy-eJcVyyT1z2IfU' -X GET
  """


  def post(self):
    # print("USER PERM : {}".format(user_permission.can()))
    args = self._get_reqparse().parse_args()
    filters = self._args2filter(args)
    args.slang = args.slang.lower()
    args.tlang = args.tlang.lower()

    if current_identity.role != Users.ADMIN and not Tags.has_specified(filters.get("domain", [])):
      abort(403, message="Tags should include at least one private or public tag")

    if not UserScopeChecker.check((args.slang, args.tlang), filters.get("domain"), is_export=True):
      abort(403, message="No valid user permission scope found for given language pair, tag and operation")

    # Iterate segment by segment: scan existing segments if language pair exists in DB
    # or otherwise generate segments from the adjacent language pairs on-the-fly ("matrix feature")
    lang_pair = (args.slang, args.tlang)
    if not self.db.has_langs(lang_pair):
      abort(403, mesage="Requested language pair doesn't exist. Try generating using pivot language")

    task = self.export_task.apply_async()
    self.job_api.init_job(job_id=task.id, username=current_identity.id, type='export', filter=filters, slang=args.slang, tlang=args.tlang, limit=args.limit, duplicates_only=args.duplicates_only)
    return {"job_id": task.id, "message": "Job submitted successfully"}

    #
    #
    # # Temporary zip file.
    # fid, tmpfile = tempfile.mkstemp(suffix='.zip')
    # writer = TMXIterWriter(tmpfile, args.slang)
    #
    # # Task id and status (Celery is not involved, just for consistency)
    # task_id = uuid.uuid4()
    # self.job_api.init_job(job_id=task_id, username=current_identity.id, type='export', filter=filters, slang=args.slang, tlang=args.tlang)
    # self.job_api.set_status(task_id, "running")
    #
    # def segment_iter(filters):
    #   i = 0
    #
    #   scan_fun = self.db.scan if not args.duplicates_only else self.db.get_duplicates
    #   seg_iter = scan_fun(lang_pair, filters)
    #   for s in seg_iter:
    #     i += 1
    #     if args.limit and i > args.limit: return
    #     yield s
    #
    # def write_iter():
    #   # Iterate file by file
    #   for fn in file_names:
    #     filters['file_name'] = [fn]
    #     for data in writer.write_iter(segment_iter(filters), fn):
    #       # TODO: in addition, write data to a local file to import it
    #       # at the end of generation
    #       yield data
    #   # Zip footer
    #   for data in writer.write_close():
    #     yield data
    #   # Finalize job
    #   self.job_api.finalize(task_id)
    #
    # # Generate zipped TMX file(s) and send as a response part by part
    # response = Response(write_iter(), mimetype='application/octet-stream')
    # response.headers['Content-Disposition'] = 'attachment; filename={}'.format(tmpfile)
    # os.remove(tmpfile)
    # return response

  @task(bind=True)
  def export_task(self):
    SparkTaskDispatcher().run(self.request.id, 'Export')
    return {'status': 'Task completed!'}

  def _get_reqparse(self):
    return self._common_reqparse()


class TmExportFileResource(TmResource):
  decorators = [PermissionChecker(user_permission)]

  """
  @api {get} /tm/export/file/<export_id> Download exported file or list all available downloads
  @apiVersion 1.0.0
  @apiName ExportFile
  @apiGroup TranslationMemory
  @apiUse Header
  @apiPermission user

  @apiSuccess {File} binary Content of zipped TMX file(s) (if export_id is supplied)
  @apiSuccess {Json} files List of all available exports (if export_id is not supplied)
  @apiExample {curl} Example usage:
   curl -G "http://127.0.0.1:5000/api/v1/tm/export/files/4235-45454-34343-43434"
   -H 'Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE0NjQ2MTU0NDUsImlkZW50aXR5IjoxLCJleHAiOjE0NjQ3MDE4NDUsIm5iZiI6MTQ2NDYxNTQ0NX0.j_p4a-NUG-6zu3Zh4_d1d0C5fkiTy-eJcVyyT1z2IfU' -X GET
  """
  def get(self, export_id=None):
    export = TMExport(current_identity.id)
    # If specific ID was requested -> download it
    if export_id:
      files = export.list(export_id)
      if not len(files): return []
      if len(files) > 1: logging.warning("Export downloading found more than 1 file at {}, picking only the first".format(export_id))
      file_path = os.path.join(files[0]["filepath"], files[0]["filename"])
      response = Response(open(file_path, 'rb'), mimetype='application/octet-stream')
      response.headers['Content-Disposition'] = 'attachment; filename={}'.format(file_path)
      return response
    # Else, return list of available export files
    files = export.list()
    return {"files" : files}


  """
  @api {delete} /tm/export/file/:export_id Delete exported file
  @apiVersion 1.0.0
  @apiName DeleteExportFile
  @apiGroup TranslationMemory
  @apiUse Header
  @apiPermission user

  @apiExample {curl} Example usage:
   curl -XDELETE "http://127.0.0.1:5000/api/v1/tm/export/files/4235-45454-34343-43434"
   -H 'Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE0NjQ2MTU0NDUsImlkZW50aXR5IjoxLCJleHAiOjE0NjQ3MDE4NDUsIm5iZiI6MTQ2NDYxNTQ0NX0.j_p4a-NUG-6zu3Zh4_d1d0C5fkiTy-eJcVyyT1z2IfU' -X GET
  """
  def delete(self, export_id):
    export = TMExport(current_identity.id)
    export.delete(export_id)
    return {"message": "success"}



class TmGenerateResource(TmResource):
  decorators = [PermissionChecker(admin_permission)]

  # Import
  """
   @api {put} /tm/generate Generate translation memory segments from existing pairs using pivot language
   @apiVersion 1.0.0
   @apiName Generate
   @apiGroup TranslationMemory
   @apiUse Header
   @apiPermission admin

   @apiParam {String} slang Source language.
   @apiParam {String} tlang Target language.
   @apiParam {String} [plang] Pivot language. If not provided, ActivaTM will try to identify best pivot language automatically
   @apiParam {String} [tag] Generate segments only for given tag(s)
   @apiParam {Bool} [force=false] Force segment generation even if requested language pair + tag exist in DB

   @apiExample {curl} Example usage:

    curl -G "http://127.0.0.1:5000/api/v1/tm/generate?tag=Automotive&slang=de&tlang=fr&plang=en"
    -X PUT -H 'Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE0NjQ2MTU0NDUsImlkZW50aXR5IjoxLCJleHAiOjE0NjQ3MDE4NDUsIm5iZiI6MTQ2NDYxNTQ0NX0.j_p4a-NUG-6zu3Zh4_d1d0C5fkiTy-eJcVyyT1z2IfU'
   """
  def put(self):
    args = self._put_reqparse()
    args.tag = [d for d in args.tag if d] # filter empty values
    filter = {'domain' : args.tag} if args.tag else {}
    langs = (args.slang, args.tlang)
    if self.db.count_scan(langs, filter=filter) and not args.force:
      abort(403, mesage="Requested language pair and tag already exist. Use force=true argument to force generation")

    # Detect pivot language if not supplied
    if not args.plang:
      args.plang = self.db._find_pivot_lang(langs)
      if not args.plang:
        abort(403, message="Failed to find pivot language for {}".format(langs))

    # Setup a job using Celery & ES
    task = self.generate_task.apply_async()
    self.job_api.init_job(job_id=task.id,
                          username=current_identity.id,
                          type='generate',
                          slang=args.slang,
                          tlang=args.tlang,
                          plang=args.plang,
                          domain=args.tag)
    return {"job_id": task.id, "message": "Job submitted successfully"}

  @task(bind=True)
  def generate_task(self):
    SparkTaskDispatcher().run(self.request.id, 'Generate')
    return {'status': 'Task completed!'}

  def _put_reqparse(self):
    parser = RequestParser()
    parser.add_argument(name='slang', required=True, help="Source language", type=self._validate_lang)
    parser.add_argument(name='tlang', required=True, help="Target language", type=self._validate_lang)
    parser.add_argument(name='plang', help="Pivot language", type=self._validate_lang)
    parser.add_argument(name='tag', action='append', help="Generate segments for given tags only")
    parser.add_argument(name='force', type=bool, help="Force generation even if segments of this language pair + tag already exist", default=False)

    return parser.parse_args()


"""
   @api {post} /tm/pos Tag segments with POS
   @apiVersion 1.0.0
   @apiName PosTagger
   @apiGroup TranslationMemory
   @apiUse Header
   @apiPermission admin

   @apiParam {String} slang Source language.
   @apiParam {String} tlang Target language.
   @apiParam {Boolean} [universal]=False Use Universal POS tags

   @apiUse FilterParams
   @apiUse ExportDeleteCommonParams

   @apiExample {curl} Example usage:

   curl -G "http://127.0.0.1:5000/api/v1/tm/pos?slang=en&tlang=es"
   -X PUT
   -H 'Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZGVudGl0eSI6ImFkbWluIiwiZXhwIjoxNDY2MDAxNzQ2LCJuYmYiOjE0NjU5MTUzNDYsImlhdCI6MTQ2NTkxNTM0Nn0.Z8Dzb_1JUr8CYBLiBVT2_9paMvRNzSs_hL9OgAx0IEQ'
"""

class TmPosTagResource(TmResource):
  decorators = [PermissionChecker(admin_permission)]

  def post(self):
    args = self._put_pos_reqparse()
    filters = self._args2filter(args)
    # Setup a job using Celery & ES
    task = self.pos_tag_task.apply_async()
    self.job_api.init_job(job_id=task.id, username=current_identity.id, type='pos_tag', filter=filters, slang=args.slang, tlang=args.tlang, universal=args.universal)
    return {"job_id": task.id, "message": "Job submitted successfully "}

  def _put_pos_reqparse(self):

    parser = RequestParser()
    parser.add_argument(name='slang', required=True, help="Source language is a mandatory option", type=self._validate_lang)
    parser.add_argument(name='tlang', required=True, help="Target language is a mandatory option", type=self._validate_lang)
    parser.add_argument(name='universal', type=inputs.boolean, default=False, help="Convert all POS tags to Universal POS tags")

    # Add filter arguments to the parser
    self._add_filter_args(parser)
    args = parser.parse_args()
    return args

  @task(bind=True)
  def pos_tag_task(self):
    SparkTaskDispatcher().run(self.request.id, 'PosTag')
    return {'status': 'Task completed!'}


"""
 @api {post} /tm/maintain Perform various maintenance tasks on TM (POS tagging, cleaning, etc.)
 @apiVersion 1.0.0
 @apiName Maintenance
 @apiGroup TranslationMemory
 @apiUse Header
 @apiPermission admin

 @apiParam {String} slang Source language.
 @apiParam {String} tlang Target language.

 @apiUse FilterParams
 @apiUse ExportDeleteCommonParams
 @apiSuccess {String} task_id ID of maintenance task invoked in the background
"""
class TmMaintainResource(TmResource):
  decorators = [PermissionChecker(admin_permission)]

  def post(self):
    args = self._common_reqparse().parse_args()
    filters = self._args2filter(args)
    # Setup a job using Celery & ES
    task = self.maintain_task.apply_async()
    self.job_api.init_job(job_id=task.id, username=current_identity.id, type='maintain', filter=filters, slang=args.slang, tlang=args.tlang)
    return {"job_id": task.id, "message": "Job submitted successfully "}

  @task(bind=True)
  def maintain_task(self):
    SparkTaskDispatcher().run(self.request.id, 'Maintain')
    return {'status': 'Task completed!'}


"""
 @api {post} /tm/clean Apply cleaning rules at given segments
 @apiVersion 1.0.0
 @apiName Clean
 @apiGroup TranslationMemory
 @apiUse Header
 @apiPermission admin

 @apiParam {String} slang Source language.
 @apiParam {String} tlang Target language.

 @apiUse FilterParams
 @apiUse ExportDeleteCommonParams

 @apiSuccess {String} task_id ID of maintenance task invoked in the background
"""
class TmCleanResource(TmResource):
  decorators = [PermissionChecker(admin_permission)]

  def post(self):
    args = self._common_reqparse().parse_args()
    filters = self._args2filter(args)
    # Setup a job using Celery & ES
    task = self.clean_task.apply_async()
    self.job_api.init_job(job_id=task.id, username=current_identity.id, type='clean',  filter=filters, slang=args.slang, tlang=args.tlang)
    return {"job_id": task.id, "message": "Job submitted successfully "}

  @task(bind=True)
  def clean_task(self):
    SparkTaskDispatcher().run(self.request.id, 'Clean')
    return {'status': 'Task completed!'}

"""
 @api {get} /tm/stats Return various statistics & allowed language pairs
 @apiVersion 1.0.0
 @apiName Stats
 @apiGroup TranslationMemory
 @apiUse Header
 @apiPermission user


 @apiSuccess {Json} stats Various stats
"""
class TmStatsResource(TmResource):
  decorators = [PermissionChecker(user_permission)]

  def get(self):
    stats =  self.db.mstats()
    lps = dict()
    # Filter language pairs and domains accordin to valid user scopes
    filter_lp = self._allowed_lang_pairs(stats['lang_pairs'].keys())
    allowed_domains = []
    for lp in filter_lp:
      # Get language pair stats or its reverse counterpart
      stat = stats['lang_pairs'].get(lp)
      if not stat: stat = stats['lang_pairs'][self._reverse_lp(lp)]
      # Filter allowed domains
      tags = self._tag_ids2dict(stat.get('domain', dict()).keys())
      allowed_domains += [t["id"] for t in UserScopeChecker.filter_domains(tags, lp, key_fn=lambda t: t["id"])]
      allowed_domains = list(set(allowed_domains)) # deduplicate
      all_domains = list(stat['domain'].keys())
      for d in all_domains:
        if d not in allowed_domains:
          del stat['domain'][d]
      lps[lp] = stat
    stats['lang_pairs'] = lps
    ##### Rename "domain(s)" to "tag(s)"
    if 'domain' in stats:
       stats["tag"] = stats["domain"]
       del stats["domain"]
       # Remove disallowed domains
       for tag in  list(stats['tag'].keys()):
         if tag not in allowed_domains:
           del stats["tag"][tag]


    for lp, lp_stat in stats['lang_pairs'].items():
      if "domain" in lp_stat:
        lp_stat["tag"] = lp_stat["domain"]
        del lp_stat["domain"]
      # Remove disallowed domains
      for lp_tag in  list(lp_stat['tag'].keys()):
        if lp_tag not in allowed_domains:
          del lp_stat["tag"][lp_tag]

    ##################
    # For regular user, just return language pair and tag stats
    if current_identity.role == 'user':
      stats = {'lang_pairs': stats['lang_pairs'],
               'tag': stats.get('tag',[])}
    return stats

  # Reverse language pair
  def _reverse_lp(self, lp):
    return '_'.join(lp.split('_')[::-1])

  def _allowed_lang_pairs(self, lang_pairs):
    # Append reverse pairs
    all_lp = list(lang_pairs)
    for lp in lang_pairs:
      all_lp.append(self._reverse_lp(lp))
    return UserScopeChecker.filter_lang_pairs(all_lp)


"""
 @api {get} /tm/stats/usage Return various usage statistics
 @apiVersion 1.0.0
 @apiName Stats
 @apiGroup TranslationMemory
 @apiUse Header
 @apiPermission user


 @apiSuccess {Json} stats Various stats
"""
class TmUsageStatsResource(TmResource):
  decorators = [PermissionChecker(user_permission)]

  def get(self):
    stats =  self.qlogger.stats()
    # For regular user, just return language pair stats
    if current_identity.role == 'user':
      stats = {current_identity.username: stats.get(current_identity.username, dict())}
    return stats
