/*
 * Copyright (c) 2020 Pangeanic SL.
 *
 * This file is part of NEC TM
 * (see https://github.com/shasha79/nectm).
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */


function ElasticTm(url, version=1) {
    this.url = url + '/api/v' + version;
}

ElasticTm.prototype._call_api = function(api, type, data, extra_params={}) {
    var params = {
        url: this.url + api,
        dataType : 'json',
        data: data,
        type: type,
        beforeSend : function(xhr) {
            //xhr.setRequestHeader("Accept", "application/json");
            //xhr.setRequestHeader("Content-Type", "application/json");
            xhr.setRequestHeader("Authorization", "JWT " + window.token);
        },
        error : function(XMLHttpRequest, textStatus, errorThrown) {
            console.log(errorThrown);
        },
        success: function(data) {
            console.log(data);
            return data;
        }
    };
    // Add any extra params coming from the caller
    jQuery.extend(params, extra_params);
    console.log("Calling " + params["url"]);

    return $.ajax(params);
}

ElasticTm.prototype._join_params = function(params) {
    var out = new Array();

    for (key in params) {
        arr = params[key];
        if(!Array.isArray(params[key])) {
            arr = [params[key]];
        }

        for (key1 in arr) {
            var value = ( arr[key1] == "on") ? "true" : ( arr[key1] == "off" ? "false" : arr[key1]);
            out.push(key + '=' + encodeURIComponent(value));
        }
    }
    out = out.join('&');
    return out
}

// Validate saved token
ElasticTm.prototype.token = function(extra_params={}) {
    // Actual call
    return this._call_api('/token', 'GET', "",
                           extra_params);
}


ElasticTm.prototype.login = function(username, password) {
    window.token = null;

    return $.ajax({
        url: this.url + "/auth",
        type: 'POST',
        dataType : 'json',
        data: JSON.stringify({ username : username, password : password }),
        beforeSend : function(xhr) {
            xhr.setRequestHeader("Accept", "application/json");
            xhr.setRequestHeader("Content-Type", "application/json");
        },
        error : function(XMLHttpRequest, textStatus, errorThrown) {
            console.log(errorThrown);
            alert('Failed to connect to: ' + this.url);
        },
        success: function(data) {
            console.log(data);
            window.token = data['access_token'];
        }
    });
}

ElasticTm.prototype.import = function(file, domains, extra_params={}) {
//ElasticTm.prototype.import = function(formData) {
    var formData = new FormData();
    formData.append('file', file);
    domains_str = "tag=" + domains.join("&tag=")
    // Actual call
    params = { processData: false,  // tell jQuery not to process the data
                contentType: false,  // tell jQuery not to set contentType),
                };
    jQuery.extend(params, extra_params);
    return this._call_api('/tm/import?' + domains_str,
                           'PUT',
                           formData,
                           params);
}

ElasticTm.prototype.export = function(slang, tlang, filters, extra_params={}) {
    lang_params = "slang=" + slang + "&tlang=" + tlang;

    // Filter params
    out = this._join_params(filters)
    if (out) { out = '&' + out; } // prepend '&'

    return this._call_api('/tm/export?' + lang_params + out, 'POST', "", extra_params);

}

ElasticTm.prototype.export_list = function(extra_params={}) {
    return this._call_api('/tm/export/file', 'GET', "", extra_params);
}


ElasticTm.prototype.export_delete = function(export_id, extra_params={}) {
    return this._call_api('/tm/export/file/'+ export_id, 'DELETE', "", extra_params);
}



ElasticTm.prototype.export_download = function(export_id, filename, extra_params={}, onready=null) {
    // Using FileSaver. js - limited to the file of size +/- 500M.
    // TODO: implement using StreamSaver.js for bigger files
    var xhr = new XMLHttpRequest();
    xhr.open('GET', this.url + '/tm/export/file/' + export_id, true);

    xhr.responseType = "blob";
    xhr.withCredentials = true;
    xhr.setRequestHeader('Authorization', 'JWT '+ window.token);

    xhr.onreadystatechange = function (){
        if (xhr.readyState === 4) {
            var blob = xhr.response;
            saveAs(blob, filename);
            if(onready) { onready();}
        }
    };
    xhr.send();

/* Not working Jquery/AJAX version - leave here for future reference
    return this._call_api('/tm/export?' + lang_params,
                'GET', [],
                {   dataType: 'text',
                    processData: false,
                    headers: {
                           'Content-Type': 'application/octet-stream',
                    },
                    success : function(data, status, headers, config) {
                        console.log(headers.getAllResponseHeaders());
                        var res = headers.getResponseHeader('Content-Disposition').split('=');
                        var fileName = res[1];
                        console.log(fileName);
                       // var file = new File([data], source_lang + "_" + target_lang + "_tmx.zip", {type: "text/plain;charset=utf-8"});
                        var file = new Blob([headers.response], {type: 'application/octet-stream'});
                        saveAs(file, fileName);
                }});
*/

}

ElasticTm.prototype.query = function(q, slang, tlang, options, filters, extra_params={}) {
    basic_params = "q=" + q + "&slang=" + slang + "&tlang=" + tlang;

    // Filter params
    out = this._join_params(options)
    if (out) { out = '&' + out; } // prepend '&'
    out1 = this._join_params(filters)
    if (out1) { out1 = '&' + out1;}
    return this._call_api('/tm' + '?' + basic_params + out + out1, 'GET', "", extra_params);
}


ElasticTm.prototype.delete = function(slang, tlang, filters, extra_params={}) {
    lang_params = "slang=" + slang + "&tlang=" + tlang;

    // Filter params
    out = this._join_params(filters)
    if (out) { out = '&' + out; } // prepend '&'

    return this._call_api('/tm?' + lang_params + out, 'DELETE', "", extra_params);
}


ElasticTm.prototype.maintain = function(slang, tlang, action, filters, extra_params={}) {
    lang_params = "slang=" + slang + "&tlang=" + tlang;

    // Filter params
    out = this._join_params(filters)
    if (out) { out = '&' + out; } // prepend '&'

    return this._call_api('/tm/' + action + '?' + lang_params + out, 'POST', "", extra_params);
}


ElasticTm.prototype.generate = function(slang, tlang, plang, domain, force=false, extra_params={}) {
    // Actual call
    params = "slang=" + slang + "&tlang=" + tlang + "&plang=" + plang + "&tag=" + domain + "&force=" + force;
    return this._call_api('/tm/generate?' + params, 'PUT', "",
                           extra_params);
}


ElasticTm.prototype.job = function(job_id, extra_params={}) {
    // Actual call
    return this._call_api('/jobs/' + job_id, 'GET', "",
                           extra_params);
}


ElasticTm.prototype.stats = function(extra_params={}) {

    params = {    processData: false,  // tell jQuery not to process the data
                contentType: false,  // tell jQuery not to set contentType)
    };
    // Actual call
    jQuery.extend(params, extra_params);

    return this._call_api('/tm/stats', 'GET', "", extra_params);
}

ElasticTm.prototype.stats_usage = function(extra_params={}) {

    params = {    processData: false,  // tell jQuery not to process the data
                contentType: false,  // tell jQuery not to set contentType)
    };
    // Actual call
    jQuery.extend(params, extra_params);

    return this._call_api('/tm/stats/usage', 'GET', "", extra_params);
}


ElasticTm.prototype.users = function(username="") {
    username = username ? "/" + username : username;
    return this._call_api('/users' + username, 'GET', "");
}

ElasticTm.prototype.set_user = function(user_json, extra_params={}) {
    if(!user_json['password']) {
        delete user_json['password'];
    }
    params = new Array();
    param_names = ["role", "is_active", "password", "token_expires"]
    for (var i = 0; i < param_names.length; i++) {
        key = param_names[i]
        if (key in user_json) {
            params[key] = user_json[key];
        }
    }
    params_str = this._join_params(params);
    return this._call_api('/users/' + user_json['username'] + '?' + params_str , 'POST', "", extra_params);
}

ElasticTm.prototype.delete_user = function(username, extra_params={}) {
    return this._call_api('/users/' + username, 'DELETE', "", extra_params);

}

ElasticTm.prototype.set_user_scope = function(scope_json, extra_params={}) {
    params_str = this._join_params(scope_json);
    return this._call_api('/users/' + scope_json['username'] + '/scopes?' + params_str , 'POST', "", extra_params);
}

ElasticTm.prototype.delete_user_scope = function(username, scope_id, extra_params={}) {
    return this._call_api('/users/' + username + '/scopes?id=' + scope_id , 'DELETE', "", extra_params);
}



ElasticTm.prototype.jobs = function(job_id="", limit=100) {
    job_id = job_id ? "/" + job_id : job_id;
    return this._call_api('/jobs' + job_id + "?limit=" + limit, 'GET', "");
}

ElasticTm.prototype.kill_job = function(job_id, extra_params={}) {
    return this._call_api('/jobs/' + job_id, 'DELETE', "", extra_params);
}


// Tags interface
ElasticTm.prototype.tags = function(extra_params={}) {
    // Actual call
    return this._call_api('/tags', 'GET', "",
                           extra_params);
}

ElasticTm.prototype.get_tag = function(tag_id, extra_params={}) {
    // Actual call
    return this._call_api('/tags/' + tag_id, 'GET', "",
                           extra_params);
}

ElasticTm.prototype.set_tag = function(tag, extra_params={}) {
    // Actual call
    return this._call_api('/tags/' + tag["id"] + "?type=" + tag["type"] + "&name=" + tag["name"], 'POST', "",
                           extra_params);
}

ElasticTm.prototype.delete_tag = function(tag_id, extra_params={}) {
    // Actual call
    return this._call_api('/tags/' + tag_id, 'DELETE', "",
                           extra_params);
}
