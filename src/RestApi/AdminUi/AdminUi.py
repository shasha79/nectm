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
from flask import render_template, Blueprint
from TMDbApi.TMDbApi import TMDbApi
from TMDbApi.TMDbQuery import TMDbQuery
from _datetime import datetime, timedelta

admin_ui = Blueprint('admin_ui', __name__,
                        template_folder='templates',
                        static_folder='assets',
                        static_url_path='/admin/assets')
tmdb = TMDbApi()


@admin_ui.route('/admin/')
@admin_ui.route('/admin/index.html')
def index():
  users_headers = ['username', 'role', 'is_active', 'scopes', 'created', 'password']

  base = datetime.today()
  month_dates = [(base - timedelta(days=x*30)).strftime("%m/%y") for x in range(0, 11)]
  usage_headers = ['username', 'total'] + month_dates
  tags_headers = ['id', 'name', 'type']
  export_headers = ['id', 'filename', 'size', 'export_time']

  users_editable = [False, True, True, False, False, True]
  jobs_headers = ['type', 'id', 'status', 'username', 'submit_time', 'end_time', 'params']

  tmdb.ml_index.refresh()

  def _map_filter(f):
    if f == "domain": return "tag"
    return f
  str_filters = [_map_filter(sf) for sf in TMDbQuery.list_attrs + ['username'] ]

  return render_template('index.html',
                            langs=sorted(tmdb.ml_index.get_langs()),
                            users_headers=zip(users_headers,users_editable),
                            jobs_headers=jobs_headers,
                            str_filters=str_filters,
                            query_filters=['squery', 'tquery'],
                            date_filters=TMDbQuery.date_attrs,
                            num_filters=TMDbQuery.num_attrs,
                            usage_headers=usage_headers,
                            tags_headers=tags_headers,
                            export_headers=export_headers)

@admin_ui.app_template_global('flag')
def flag(lang):
  lang = lang.upper()
  code = lang.lower()
  # TODO: add more  language  to  country  mappings  var
  lang2country = {'AR': 'eg',
                  'EN': 'gb',
                  'CS': 'cz',
                  'DA': 'dk',
                  'EL': 'gr',
                  'ZH': 'cn',
                  'GA': 'ie',
                  'SV': 'se',
                  'SL': 'si',
                  'ET': 'ee',
                  'JA': 'jp',
                  'FA': 'ir',
                  'HE': 'il',
                  'KO': 'kr',
                  'EU': 'es-eu',
                  'CA': 'es-ca',
                  'NB': 'no',
                  'UK': 'ua',
                  'SR' : 'rs',
                  'KK': 'kz',
                  'SQ': 'al'
                  }
  if (lang in lang2country):
    return lang2country[lang]
  return code


