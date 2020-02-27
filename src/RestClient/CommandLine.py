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
import logging
import argparse
import dateutil

# ---------- Command line API ---------------
class Command:
  def __init__(self, client):
    self.client = client
    self.args = self._parse_args()
    self.client.set_url(self.args.host, self.args.port, '1')
    if self.args.login: self.client.username = self.args.login
    if self.args.pwd: self.client.password = self.args.pwd

  def _parse_args(self):
    parser = argparse.ArgumentParser()
    self.subparsers = parser.add_subparsers()
    subparser = self._subparse_args()
    self._add_common_args(subparser)
    return parser.parse_args()

  def _add_common_args(self, parser):
    parser.add_argument('--host', type=str, default="http://localhost", help="API host URL")
    parser.add_argument('--port', type=int, default=5000, help="API host port")
    parser.add_argument('--login', type=str, help="API login")
    parser.add_argument('--pwd', type=str, help="API password")

  def _common_args(self):
    return ['host', 'port', 'login', 'pwd']

  def _add_filter_args(self, parser):
    for arg in ['file_name', 'organization', 'tag', 'industry', 'language', 'type']:
      parser.add_argument('--filter_'+arg, type=str, help="Filter by "+arg)

    for arg in ['tm_change_date', 'tm_creation_date', 'insert_date', 'update_date', 'check_date']:
      for t in ['from', 'to']:
        parser.add_argument('--filter_{}.{}'.format(arg, t), type=self._str2date, help="Filter {} {}".format(t, arg))

    for arg in ['dirty_score']:
      for t in ['from', 'to']:
        parser.add_argument('--filter_{}.{}'.format(arg, t), type=int, help="Filter {} {}".format(t, arg))

  def _args2filters(self, args):
    filters = {}
    for k,v in vars(args).items():
      prefix = 'filter_'
      if k.startswith(prefix):
        filters[k.replace(prefix, '')] = v
    return filters

  def _str2date(self, s):
    try:
      dt = dateutil.parser.parse(s)
    except ValueError as e:
      raise argparse.ArgumentTypeError("Can't parse {} as a date/time: {}".format(dt, e))
    return dt

class QueryCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('query', help="Search translation memory segments")
    parser.add_argument('-q', '--query', type=str, help="Query string", required=True)
    parser.add_argument('-sl', '--slang', type=str, help="Source language", required=True)
    parser.add_argument('-tl', '--tlang', type=str, help="Target language", required=True)
    parser.add_argument('-o', '--out', type=str, help="Output format", choices=['json', 'moses'], default='json')
    parser.add_argument('-st', '--strip_tags',action='store_true', help="Strip XML tags")
    parser.add_argument('-cc', '--concordance',action='store_true', help="Concordance search mode. Valid for single query mode only")
    parser.add_argument('-mt', '--aut_trans', action='store_true', help="Apply machine translation if match less than a threshold")
    parser.add_argument('-mm', '--min_match',type=int, help="Minimal match for segments", default=75)
    parser.add_argument('-l', '--limit',type=int, help="Limit output to this number of segments", default=10)
    parser.add_argument('-b', '--batch',type=int, help="Batch size", default=1)
    parser.add_argument('-om', '--operation_match', type=str, help="Regex, Tags, PosTag and Split", default='regex,tags') # split isn't default ,split
    parser.add_argument('-tg', '--tag', type=str, help="Prefer given tag(s), penalize others", action='append')
    parser.add_argument('-sp', '--split_pattern', type=str, help="Split queries by this pattern")

    return parser

  def __call__(self):

    if self.args.query == '-':
      queries = sys.stdin # read from stdin
    else:
      queries = [self.args.query] # one query
    i = 0
    q_batch = []

    for query in queries:
      logging.debug("Query length: {}".format(len(query.split())))
      q_batch.append(query.strip())
      print("TAGS: {}".format(self.args.tag))
      if len(q_batch) >= self.args.batch:
        if self.args.batch == 1:
          yield self.client.query(q_batch[0], self.args.slang, self.args.tlang, self.args.out, self.args.strip_tags, self.args.min_match, self.args.limit, self.args.operation_match, self.args.concordance, self.args.aut_trans, self.args.tag)
        else:
          yield self.client.query_batch(q_batch, self.args.slang, self.args.tlang, self.args.out, self.args.strip_tags, self.args.min_match, self.args.limit, self.args.operation_match, self.args.aut_trans, self.args.tag, self.args.split_pattern)
        q_batch.clear()
    # Query remaining batch
    if q_batch:
      yield self.client.query_batch(q_batch, self.args.slang, self.args.tlang, self.args.out, self.args.strip_tags,
                               self.args.min_match, self.args.limit, self.args.operation_match, self.args.aut_trans , self.args.tag, self.args.split_pattern)


class AddCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('add', help="Add new translation unit")
    parser.add_argument('-st', '--stext', type=str, help="Source text", required=True)
    parser.add_argument('-tt', '--ttext', type=str, help="Target text", required=True)
    parser.add_argument('-sl', '--slang', type=str, help="Source language", required=True)
    parser.add_argument('-tl', '--tlang', type=str, help="Target language", required=True)
    parser.add_argument('-sm', '--smeta', type=str, help="Source metadata (valid JSON)", required=False)
    parser.add_argument('-tm', '--tmeta', type=str, help="Target language (valid JSON)", required=False)
    parser.add_argument('-t', '--tag', type=str, help="Tag", required=True)
    parser.add_argument('-f', '--file_name', type=str, help="File name")

    #self._add_filter_args(parser)
    return parser

  def __call__(self):
    return self.client.add_tu(self.args.stext, self.args.ttext, self.args.slang, self.args.tlang, self.args.tag, self.args.file_name, self.args.smeta, self.args.tmeta)


class ImportCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('import', help="Import translation memory segments from (zipped) TMX file")
    parser.add_argument('-f', '--file', type=str, help="TMX file to import. May be zipped archive with multiple TMX files in it", required=True)
    parser.add_argument('-d', '--domain', type=str, help="File domain", required=True)
    parser.add_argument('-lp', '--lang_pair', type=str, nargs='+', help="Language pair to import (language codes separated with underscore, e.g. en_es)", )
    return parser

  def __call__(self):
    return self.client.import_tm(self.args.file, self.args.domain, self.args.lang_pair)

class ExportCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('export', help="Export translation memory segments to (zipped) TMX file")
    parser.add_argument('-sl', '--slang', type=str, help="Source language", required=True)
    parser.add_argument('-tl', '--tlang', type=str, help="Target language", required=True)
    parser.add_argument('-sq', '--squery', type=str, help="Filter source segments by this query. May include regexp")
    parser.add_argument('-q', '--tquery', type=str, help="Filter target segments by this query. May include regexp")
    parser.add_argument('-do', '--duplicates_only', type=bool, help="Duplicate segments only", default=False)
    self._add_filter_args(parser)
    return parser

  def __call__(self):
    return self.client.export_tm(self.args.slang, self.args.tlang, self.args.squery, self.args.tquery, self.args.duplicates_only, self._args2filters(self.args))

class GenerateCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('generate', help="Generate translation memory segments using pivot language")
    parser.add_argument('-sl', '--slang', type=str, help="Source language", required=True)
    parser.add_argument('-tl', '--tlang', type=str, help="Target language", required=True)
    parser.add_argument('-pl', '--plang', type=str, help="Pivot language")
    parser.add_argument('-t', '--tag', type=str, help="Generate segments for given tags only", nargs='+')
    parser.add_argument('-f', '--force', action='store_true', help="Use Universal POS tags")

    return parser

  def __call__(self):
    return self.client.generate_tm(self.args.slang, self.args.tlang, self.args.plang, self.args.domain, self.args.force)


class DeleteCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('delete', help="Delete translation memory segments from DB")
    parser.add_argument('-sl', '--slang', type=str, help="Source language", required=True)
    parser.add_argument('-tl', '--tlang', type=str, help="Target language", required=True)
    parser.add_argument('-sq', '--squery', type=str, help="Filter source segments by this query. May include regexp")
    parser.add_argument('-q', '--tquery', type=str, help="Filter target segments by this query. May include regexp")
    parser.add_argument('-do', '--duplicates_only', type=bool, help="Duplicate segments only", default=False)

    self._add_filter_args(parser)
    return parser

  def __call__(self):
    return self.client.delete_tm(self.args.slang, self.args.tlang, self.args.duplicates_only, self._args2filters(self.args))#self.args.squery, self.args.tquery,


class PosCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('pos', help="Tag segments with POS")
    parser.add_argument('-sl', '--slang', type=str, help="Source language", required=True)
    parser.add_argument('-tl', '--tlang', type=str, help="Target language", required=True)
    parser.add_argument('-u', '--universal', action='store_true', help="Use Universal POS tags")

    self._add_filter_args(parser)
    return parser

  def __call__(self):
    return self.client.pos(self.args.slang, self.args.tlang, self.args.universal, self._args2filters(self.args))


class MaintainCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('maintain', help="Run various maintenance tasks (cleaning, POS tagging, etc.)")
    parser.add_argument('-sl', '--slang', type=str, help="Source language", required=True)
    parser.add_argument('-tl', '--tlang', type=str, help="Target language", required=True)

    self._add_filter_args(parser)
    return parser

  def __call__(self):
    return self.client.maintain(self.args.slang, self.args.tlang, self._args2filters(self.args))

class CleanCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('clean', help="Apply cleaning rules")
    parser.add_argument('-sl', '--slang', type=str, help="Source language", required=True)
    parser.add_argument('-tl', '--tlang', type=str, help="Target language", required=True)

    self._add_filter_args(parser)
    return parser

  def __call__(self):
    return self.client.clean(self.args.slang, self.args.tlang, self._args2filters(self.args))


class StatsCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('stats', help="Get various statistics")
    return parser

  def __call__(self):
    return self.client.stats()

class GetUserCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('get_user', help="Get user details")
    parser.add_argument('-u', '--username', type=str, help="Username")

    return parser

  def __call__(self):
    return self.client.get_user(self.args.username)

class SetUserCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('set_user', help="Add/update user details")
    parser.add_argument('-u', '--username', type=str, help="Username", required=True)
    parser.add_argument('-p', '--password', type=str, help="Password")
    parser.add_argument('-r', '--role', type=str, help="User role", choices=['admin', 'user'])
    parser.add_argument('-a', '--active', type=bool, help="Activate/deactivate user", default=True)
    return parser

  def __call__(self):
    args = vars(self.args)
    for arg in self._common_args(): del args[arg]
    return self.client.set_user(**args)

class SetUserScopeCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('set_user_scope', help="Add/update user scope details")
    parser.add_argument('-u', '--user', type=str, help="Username")
    parser.add_argument('-i', '--id', type=int, help="Scope id")
    parser.add_argument('-lp', '--lang_pairs', type=str, help="Comma-separate list of language pairs included in this scope (may contain wildcard: *,?)")
    parser.add_argument('-t', '--tags', type=str, help="Comma-separate list of tags included in this scope (may contain wildcards: *,?)")
    parser.add_argument('-ul', '--usage_limit', type=int, help="Limit usage (number of queries) in this scope")

    parser.add_argument('-sd', '--start_date', type=str,
                        help="Scope is valid from this date)")
    parser.add_argument('-ed', '--end_date', type=str,
                        help="Scope is valid until this date)")

    return parser

  def __call__(self):
    args = vars(self.args)
    for arg in self._common_args(): del args[arg]
    return self.client.set_user_scope(args['user'], **args)


class DeleteUserScopeCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('delete_scope', help="Delete user scope")
    parser.add_argument('-u', '--user', type=str, help="Username", required=True)
    parser.add_argument('-i', '--id', type=str, help="Scop id", required=True)

    return parser

  def __call__(self):
    return self.client.delete_tag(self.args.tag)


class GetJobCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('get_job', help="Get job details")
    parser.add_argument('-i', '--job_id', type=str, help="Job id", required=True)

    return parser

  def __call__(self):
    return self.client.get_job(self.args.job_id)

class KillJobCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('kill_job', help="Kill given job")
    parser.add_argument('-i', '--job_id', type=str, help="Job id", required=True)

    return parser

  def __call__(self):
    return self.client.kill_job(self.args.job_id)


class GetSettingsCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('get_settings', help="Get user settings")
    return parser

  def __call__(self):
    return self.client.get_settings()

class SetSettingsCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('set_settings', help="Get user settings")
    parser.add_argument('-re', '--regex', type=str, help="List (separated by comma) of regular expression shortnames to apply", required=True)

    return parser

  def __call__(self):
    return self.client.set_settings(regex=self.args.regex)


class GetTagCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('get_tag', help="Get tag details")
    parser.add_argument('-t', '--tag', type=str, help="Tagname")

    return parser

  def __call__(self):
    return self.client.get_tag(self.args.tag)

class SetTagCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('set_tag', help="Add/update tag details")
    parser.add_argument('-t', '--tag', type=str, help="Tagname", required=True)
    parser.add_argument('--type', type=str, help="Type", choices=['unspecified', 'private', 'public'], required=True)
    return parser

  def __call__(self):
    args = vars(self.args)
    for arg in self._common_args(): del args[arg]
    return self.client.set_tag(**args)

class DeleteTagCommand(Command):
  def _subparse_args(self):
    parser = self.subparsers.add_parser('delete_tag', help="Delete tag")
    parser.add_argument('-t', '--tag', type=str, help="Tagname", required=True)

    return parser

  def __call__(self):
    return self.client.delete_tag(self.args.tag)



class CommandLine:
  cmds = {'query': QueryCommand,
          'add': AddCommand,
          'import' : ImportCommand,
          'export' : ExportCommand,
          'generate': GenerateCommand,
          'delete': DeleteCommand,
          'pos': PosCommand,
          'maintain' : MaintainCommand,
          'clean': CleanCommand,
          'stats': StatsCommand,
          'get_user': GetUserCommand,
          'set_user': SetUserCommand,
          'set_user_scope': SetUserScopeCommand,
          'delete_user_scope': DeleteUserScopeCommand,
          'get_job' : GetJobCommand,
          'kill_job': KillJobCommand,
          'get_settings': GetSettingsCommand,
          'set_settings': SetSettingsCommand,
          'get_tag': GetTagCommand,
          'delete_tag': DeleteTagCommand,
          'set_tag': SetTagCommand}

  def __init__(self):
    if len(sys.argv) < 2:
      logging.error("Usage: {} {} <arguments>".format(sys.argv[0], '|'.join(self.cmds.keys())))
      exit(1)
    self.cmd = sys.argv[1]
    if not self.cmd in self.cmds:
      logging.error("Unknown command: {}. List of known commands: {}".format(self.cmd, '|'.join(self.cmds.keys())))
      exit(1)

  def __call__(self, client):
    cmd = self.cmds[self.cmd](client)
    return cmd()
