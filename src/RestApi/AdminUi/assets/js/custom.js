


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


(function ($) {
    "use strict";
    var mainApp = {

        main_fun: function () {

            /*====================================
              LOAD APPROPRIATE MENU BAR
           ======================================*/
            $(window).bind("load resize", function () {
                if ($(this).width() < 768) {
                    $('div.sidebar-collapse').addClass('collapse')
                } else {
                    $('div.sidebar-collapse').removeClass('collapse')
                }
            });

            function fill_users_table() {
                $("#spinner_users").show();
                var data = window.users["users"];
                var tbl_data = [];
                for (var i = 0, len = data.length; i < len; i++) {
                    var udata= jQuery.extend({}, data[i]); // shallow clone

                    udata["delete"] =   '<a href="javascript:void(0);" onclick="edit_user(\'' + udata["username"] + '\');"><i class="fa fa-edit"></i></a>' +
                                       '&nbsp;<a href="javascript:void(0);" onclick="delete_user(\'' + udata["username"] + '\');"><i class="fa fa-ban danger"></i></a>'
                    udata["password"] = "****";
                    // Replace scopes with its IDs
                    var scopes = "";
                    for (var j = 0, slen = udata["scopes"].length; j < slen; j++) {
                        var scope_id = udata["scopes"][j]["id"];
                        scopes = scopes + '&nbsp;<a href="javascript:void(0);" onclick="edit_user_scope(\'' + udata["username"] + '\',' + scope_id + ');">' + scope_id + '</a>';
                    }
                    scopes = scopes + '&nbsp;<a href="javascript:void(0);" onclick="edit_user_scope(\'' + udata["username"] + '\');"><i class="fa fa-plus"></i></a>';
                    udata["scopes"] = scopes;
                    udata["created"] = dateFormatter(udata["created"]);
                    tbl_data.push(udata);
                }

                $("#users_table").on('editable-save.bs.table', function(e, col_name, row_data){
                       window.changed_users.push(row_data);
                       $('#save_users_btn').removeAttr('disabled');
                });
                $("#users_table").on('post-body.bs.table',function(data) {
                    $("#spinner_users").hide();
                });
                $("#users_table").bootstrapTable('load', tbl_data);
            }

            function fill_usage_table(mt="all") {
                var data = window.stats_usage;
                var tbl_data = [];
                $.each( data, function( user, user_stats ) {
                    var udata={};
                    $.each( user_stats, function( month, value ) {
                        var mt_defined = typeof(value.mt) != "undefined";
                        if(mt == "mt_false"  ) {
                           udata[month] = mt_defined ? value.mt[0] : undefined;
                        } else if (mt == "mt_true" && mt_defined) {
                           udata[month] = mt_defined ? value.mt[1] : undefined;
                        } else {
                           udata[month] = value["count"];
                        }
                    });
                    udata["username"] = user;
                    if(mt == "mt_false") {
                        udata["total"] = user_stats["mt"][0];
                    } else if (mt == "mt_true") {
                       udata["total"] = user_stats["mt"][1];
                    } else {
                       udata["total"] = user_stats["count"];
                    }

                    tbl_data.push(udata);
                });

                $("#stats_usage_table").bootstrapTable('load', tbl_data);
            }

            function fill_tags_table() {
                var data = window.tags;
                var tbl_data = [];
                window.tagnames = [];
                window.taggroups = {};
                data["tags"].map(function( tag ) {
                    var utag= jQuery.extend({}, tag); // shallow clone
                    utag["id"] = '<a href="javascript:void(0);" onclick="edit_tag(\'' + tag["id"] + '\');">' + tag["id"] + '</a>'
                    tbl_data.push(utag);
                    window.tagnames.push(tag["name"]);
                    if (! (tag["type"] in window.taggroups)) { window.taggroups[tag["type"]] = []}
                    window.taggroups[tag["type"]].push(tag);
                });
                window.tagnames = window.tagnames.sort()
                $("#tags_table").bootstrapTable('load', tbl_data);
                // Update all tags fields
                $("select[id$=_filter_tag],[id=domain_tags],[id=scope_tags]").each(function(index) {
                    //var select = this;
                    $(this).multiselect('destroy');
                    //select.options.length = 0;
                    //$.each(window.tagnames, function(id, tagname) {
                    //  select.append(new Option(tagname, tagname));
                    //});
                    var optgroups = [];
                    $.each(window.taggroups, function(taggroup, taglist) {
                        optgroups.push({label: taggroup, children:[]});
                        $.each(taglist, function(id, tag) {
                            optgroups[optgroups.length-1].children.push({label: tag["name"], value: tag["id"]});
                        });
                        optgroups[optgroups.length-1].children.sort((a,b) => (a.value > b.value) ? 1 : ((b.value > a.value) ? -1 : 0));
                    });


                    $(this).multiselect('dataprovider', optgroups);
                /*    $(this).tagsinput({
                        typeahead: {
                            source: tagnames
                        },
                        freeInput: false
                    });
                    $(this).tagsinput('refresh');
                */
                });

            }

            $(document).on('change', 'input:radio[id^="mt_"]', function (event) {
                 fill_usage_table(event.target.value);
            });

            function fill_export_table() {
                var data = window.export.files;
                var tbl_data = [];
                for (var i = 0, len = data.length; i < len; i++) {
                    var udata= jQuery.extend({}, data[i]); // shallow clone

                    udata["delete"] =   '<a href="javascript:void(0);" onclick="export_delete(\'' + udata["id"] + '\');"><i class="fa fa-ban danger"></i></a>'
                    udata["filename"] = '&nbsp;<a href="javascript:void(0);" onclick="export_file(\'' + udata["id"] + '\',\'' + udata["filename"] +'\');">' + udata["filename"] + '</a>';
                    udata["export_time"] = dateFormatter(udata["export_time"]);
                    udata["size"] = (udata["size"]*1e-6).toFixed(1) + " M";
                    tbl_data.push(udata);
                }
                $("#export_table").bootstrapTable('load', tbl_data);

            }


            function fill_jobs_table() {
                $("#spinner_jobs").show();
                var data = window.jobs["jobs"];
                var tbl_data = [];
                for (var i = 0, len = data.length; i < len; i++) {
                    var udata = data[i];
                    udata["delete"] = '<a href="javascript:void(0);" onclick="kill_job(\'' + udata["id"] + '\');"><i class="fa fa-ban danger"></i></a>'
                    udata["params_str"] = JSON.stringify(udata["params"]);
                    udata["params"] = '<a href="javascript:void(0);" onclick="job_params(\'' + udata["id"] + '\');"><i class="fa fa-info-circle"></i></a>'

                    tbl_data.push(udata);
                }
                $("#jobs_table").on('post-body.bs.table',function(data) {
                    $("#spinner_jobs").hide();
                });
                $("#jobs_table").bootstrapTable('load', tbl_data);
            }

            function try_login() {
                window.token = window.localStorage.getItem("token");
                return window.g_elastic_tm.token(
                    {error: function(data) {
                       // Open login modal
                       $("input#luser").val(window.localStorage.getItem("username"));
                       $("input#lpassword").val(window.localStorage.getItem("password"));
                       $('#login_modal').modal('show');
                    },
                    success: function(data) {
                        return window.g_elastic_tm.users()
                        .then(function(response) {
                            window.user = response;
                            return init();
                        });
                    }
                });
            }


            function login(username, password) {
                return window.g_elastic_tm.login(username,password)
                    .then(function(response) {
                        return window.g_elastic_tm.users(username)
                    })
                    .then(function(response) {
                        window.user = response;
                        window.localStorage.setItem("token", window.token);
                        return init();
                    });
            }

            function init () {
                if (window.user.role == "user") {
                    return init_user();
                } else {
                    return init_admin();
                }

            }

            function init_admin () {
               $("#spinner").show();

               return window.g_elastic_tm.stats()
                .then(function(data) {
                    window.stats = data;
                    return window.g_elastic_tm.stats_usage()
                })
                .then(function(data) {
                    window.stats_usage = data;
                    return window.g_elastic_tm.jobs()
                })
                .then(function(data) {
                    window.jobs = data;
                    return window.g_elastic_tm.users()
                })
                .then(function(data) {
                    window.users = data;
                    window.changed_users = [];
                    return window.g_elastic_tm.tags()
                })
                .then(function(data) {
                    window.tags = data;
                    window.tag_ids2names = tag_ids2names_fun(window.tags["tags"]);
                    return window.g_elastic_tm.export_list()
                })
                .then(function(data) {
                    window.export = data;
                    fill_users_table();
                    fill_jobs_table();
                    fill_usage_table();
                    fill_tags_table();
                    fill_export_table();
                    fill_languages();
                    $('#status').hide();
                    $("#spinner").hide();
                });
            }

            function init_user () {
               $("#spinner").show();

                return window.g_elastic_tm.tags()
                .then(function(data) {
                    window.tags = data;
                    window.tag_ids2names = tag_ids2names_fun(window.tags["tags"]);
                    fill_tags_table();
                    return window.g_elastic_tm.export_list()
                })
                .then(function(data) {
                    window.export = data;
                    fill_export_table();
                    return window.g_elastic_tm.stats()
                })
                .then(function(data) {
                    window.stats = data;
                    for (let li of ["generate", "delete", "maintain", "tags", "users_vertical", "jobs_vertical"]) {
                        $("#" + li + "_tab").hide();
                    }
                    fill_languages();
                    $('#status').hide();
                    $("#spinner").hide();
                });
            }


            // Global ElasticTM API
            window.g_elastic_tm = new ElasticTm(window.location.protocol + '//' + window.location.host);

            // Try logging with saved token. If failed, open login window
            try_login();

            // Initialize jquery validation plugin
            $("#upload-file-form").validate();
            // Initialize bootstrap-select (custom options list)
            $('.selectpicker').selectpicker();
            // Put default EN-ES pair to all language selections
            $("select[id$=_source_lang]").selectpicker('val', 'EN');
            $("select[id$=_target_lang]").selectpicker('val', 'ES');
            // Initialize datepicker fields
            $('.datepicker').datepicker({
                // format: 'DD/MM/YYYY' doesn't work for some reason
            });



            $( "#file_field" ).change(function() {
                $('#import_progressbar').removeClass('progress-bar-success')
                $('#import_progressbar').css('width', '0%');
                if ($( "#file_field" ).val() && $( "#domain_tags" ).val()) {
                    $('#import_btn').removeAttr('disabled');
                }
            });

            $( "#domain_tags" ).change(function() {
                if ($( "#file_field" ).val() && $( "#domain_tags" ).val()) {
                    $('#import_btn').removeAttr('disabled');
                }
            });

            var ajax_job_params = {
                complete: function() {$("#spinner").hide();},
                success: function(data) {
                       console.log(data);
                       $('#status').addClass('alert-success')
                       $('#status').show();
                       $("#status_text").html('Job <a href="#" class="alert-link">' + data["job_id"] + "</a> has been submitted successfully")
                       $("#status").fadeTo(5000, 500).slideUp(500, function(){
                            $("#status").slideUp(500);
                        });

                       window.g_elastic_tm.job(data["job_id"],
                        {success: function(jdata) {console.log(jdata);}});
                        // TODO: show job id/status with the link to job details page/pop-up
                },
                error: function(XMLHttpRequest, textStatus, errorThrown) {
                       $('#status').addClass('alert-danger');
                       $('#status').show();
                       $("#status_text").text(textStatus + " - " + errorThrown);

                }
            }


            $( "#import_btn" ).click(function() {
                $("#upload-file-form").valid(); // TODO: not working for some reason
                $("#spinner").show();
/*                if (!validate_tag_combination($("#domain_tags"))) {
                    $("#spinner").hide();
                    bootbox.alert("You should select at least one private or public tag in addition to unspecified tag(s)")
                } else {
                    window.g_elastic_tm.import($('input[type=file]')[0].files[0],
                                               $("#domain_tags").val(),
                                               ajax_job_params)
                }
*/
                validate_tag_combination($("#domain_tags").val()).then(function (result) {
                    $("#spinner").hide();
                    if (!result) {
                        bootbox.alert("You should select at least one private or public tag in addition to unspecified tag(s)")
                    } else {
                        window.g_elastic_tm.import($('input[type=file]')[0].files[0],
                                                   $("#domain_tags").val(),
                                                   ajax_job_params)
                    }
               })

            });

            $( "#export_btn" ).click(function() {
                $("#spinner").show();
                var filters = get_filters('export');

                validate_tag_combination($("#export_filter_tag").val()).then(function (result) {
                    $("#spinner").hide();
                    if (!result) {
                        bootbox.alert("You should select at least one private or public tag in addition to unspecified tag(s)")
                    } else {
                        window.g_elastic_tm.export($( "#export_source_lang" ).val(), $( "#export_target_lang" ).val(), filters,
                                            ajax_job_params);
                        reset_filters('export');
                    }
                });
            });

            $( "#generate_btn" ).click(function() {
                $("#spinner").show();
                var pivot_lang = $( "#gen_pivot_lang" ).val();
                if (pivot_lang == 'Automatic') {pivot_lang = ''; }
                window.g_elastic_tm.generate($( "#gen_source_lang" ).val(),
                                             $( "#gen_target_lang" ).val(),
                                             pivot_lang,
                                             $("#gen_domain_tags").val().split(","),
                                             $("#gen_force")[0].checked,
                                             ajax_job_params)
            });

            $( "#delete_btn" ).click(function() {
                $("#spinner").show();
                var filters = get_filters('delete');
                window.g_elastic_tm.delete( $("#delete_source_lang" ).val(), $( "#delete_target_lang" ).val(), filters, ajax_job_params);
                reset_filters('delete');
            });


            $( "#maintain_btn" ).click(function() {
                $("#spinner").show();
                var filters = get_filters('maintain');
                window.g_elastic_tm.maintain( $("#maintain_source_lang" ).val(), $( "#maintain_target_lang" ).val(), $( "#maintain_action" ).val(), filters, ajax_job_params);
                reset_filters('maintain');
            });


            $("#stats_tab").click(function() {
                var data = window.stats;
                var tbl_data = [];
                var tbl_domain_data = [];
                var tbl_file_name_data = [];
                var domain2langs = new Array();
                var fn2langs = new Array();
                Object.keys(data["lang_pairs"]).forEach(function(lang_pair, value) {
                    var langs = lang_pair.split('_');
                    var tbl_row_data = {slang: langs[0], tlang: langs[1]};
                    Object.keys(data["lang_pairs"][lang_pair]).forEach(function(key1, value1) {
                        if (key1 == "count") {
                            tbl_row_data[key1] = data["lang_pairs"][lang_pair][key1];
                        }
                        if (key1 == "tag") {
                            tbl_row_data[key1] = new Array();
                            for (var tag_id in data["lang_pairs"][lang_pair][key1]) {
                                var count = data["lang_pairs"][lang_pair][key1][tag_id];
                                var tag_name = window.tag_ids2names[tag_id];
                                tbl_row_data[key1].push(tag_name +"," + count);
                                if (! (item in domain2langs)) { domain2langs[tag_name] = []; }
                                domain2langs[tag_name].push(lang_pair +"," + count);
                            };
                            //tbl_row_data[key1] = Object.values(data["lang_pairs"][key][key1]);
                        }
                        if (key1 == "file_name") {
                            for (var item in data["lang_pairs"][lang_pair][key1]) {
                                var count = data["lang_pairs"][lang_pair][key1][item];
                                if (! (item in fn2langs)) { fn2langs[item] = []; }
                                fn2langs[item].push(lang_pair +"," + count);
                            };
                            //tbl_row_data[key1] = Object.values(data["lang_pairs"][key][key1]);
                        }
                    });
                    tbl_data.push(tbl_row_data)

                 });
                if ("tag" in data) {
                    Object.keys(data["tag"]).forEach(function(key, value) {
                        var tag_name = window.tag_ids2names[key];
                        var tbl_row_data = {domain: tag_name, count: data["tag"][key], lang_pairs: domain2langs[tag_name]}
                        tbl_domain_data.push(tbl_row_data)
                     });
                 }
                if ("file_name" in data) {
                    Object.keys(data["file_name"]).forEach(function(key, value) {
                        var tbl_row_data = {file_name: key, count: data["file_name"][key], lang_pairs: fn2langs[key]}
                        tbl_file_name_data.push(tbl_row_data)
                     });
                }

                $("#stats_table").bootstrapTable('load', tbl_data);
                $("#stats_domain_table").bootstrapTable('load', tbl_domain_data);
                $("#stats_file_name_table").bootstrapTable('load', tbl_file_name_data);
                $("*[data-role='tagsinput'").tagsinput('refresh');

                $("#spinner").hide();
            });

            window.ajax_user_params = {
                complete: function() {$("#spinner").hide();},
                success: function(data) {
                       console.log(data);
                       $("#spinner_users").hide();

                       $('#status').addClass('alert-success')
                       $('#status').show();
                       window.g_elastic_tm.users().then(function(data) {
                           window.users = data;
                           fill_users_table();
                       });
                       $("#status_text").html("User(s) saved successfully");
                       $("#status").fadeTo(2000, 500).slideUp(500, function(){
                            $("#status").slideUp(500);
                        });

                },
                error: function(XMLHttpRequest, textStatus, errorThrown) {
                       $("#spinner_users").hide();
                       $('#status').addClass('alert-danger');
                       $('#status').show();
                       $("#status_text").text(textStatus + " - " + errorThrown);

                }
            }

            window.ajax_tags_params = {
                complete: function() {$("#spinner").hide();},
                success: function(data) {
                       console.log(data);
                       $("#spinner").hide();

                       $('#status').addClass('alert-success')
                       $('#status').show();
                       window.g_elastic_tm.tags().then(function(data) {
                           window.tags = data;
                           window.tag_ids2names = tag_ids2names_fun(window.tags["tags"]);
                           fill_tags_table();
                       });
                       $("#status_text").html("Tag(s) saved successfully");
                       $("#status").fadeTo(2000, 500).slideUp(500, function(){
                            $("#status").slideUp(500);
                        });

                },
                error: function(XMLHttpRequest, textStatus, errorThrown) {
                       $("#spinner").hide();
                       $('#status').addClass('alert-danger');
                       $('#status').show();
                       $("#status_text").text(textStatus + " - " + errorThrown);

                }
            }

            window.ajax_export_params = {
                complete: function() {$("#spinner").hide();},
                success: function(data) {
                       console.log(data);
                       $("#spinner").hide();

                       $('#status').addClass('alert-success')
                       $('#status').show();
                       window.g_elastic_tm.export_list().then(function(data) {
                           window.export = data;
                           fill_export_table();
                       });
                       $("#status_text").html("Export deleted successfully");
                       $("#status").fadeTo(2000, 500).slideUp(500, function(){
                            $("#status").slideUp(500);
                        });

                },
                error: function(XMLHttpRequest, textStatus, errorThrown) {
                       $("#spinner").hide();
                       $('#status').addClass('alert-danger');
                       $('#status').show();
                       $("#status_text").text(textStatus + " - " + errorThrown);

                }
            }





            $( "#save_users_btn" ).click(function() {
                $("#spinner_users").show();
                // TODO: implement and use multiple update method
                for (var i = 0, len = window.changed_users.length; i < len; i++) {
                    var user = window.changed_users[i];
                    window.g_elastic_tm.set_user(user, window.ajax_user_params);
                }
                window.changed_users = [];
                $('#save_users_btn').attr('disabled','disabled');
                $("#spinner_users").hide();

            });

            $( "#save_user_btn" ).click(function() {
                $("#spinner_users").show();
                var user = { username: $('input#user').val(),
                             role : $('select#role').val(),
                             password: $('input#password').val(),
                             is_active: $('input#is_active').is(':checked'),
                             token_expires: $('input#token_expires').is(':checked')
                }
                window.g_elastic_tm.set_user(user, window.ajax_user_params);
                $("#spinner_users").hide();
                $('#user_modal').modal('hide');


            });
            $( "#save_tag_btn" ).click(function() {
                $("#spinner").show();
                var tag = { id: $('input#tag_id').val(),
                            name: $('input#tag_name').val(),
                             type : $('select#type').val()
                          }
                window.g_elastic_tm.set_tag(tag, window.ajax_tags_params)
                    .then(function(data) {
                       return window.g_elastic_tm.tags()
                    })
                    .then(function(data) {
                       window.tags = data;
                       fill_tags_table();
                    });
                $("#spinner").hide();
                $('#tag_modal').modal('hide');
                // Refresh tags
                window.g_elastic_tm.tags().then(function(data) {
                   window.tags = data;
                   fill_tags_table();
                });


            });

            $( "#delete_tag_btn" ).click(function() {
                bootbox.confirm("Are you sure you want to delete tag " + $('input#tag').val() + "?",
                            function(result) {
                    if (result) {
                        $('#tag_modal').modal('hide');
                        window.g_elastic_tm.delete_tag($('input#tag_id').val(), window.ajax_tags_params);
                    }
                })
            });



            $( "#new_users_btn" ).click(function() {
                edit_user();
            });

            $( "#new_tag_btn" ).click(function() {
                edit_tag();
            });


            $( "#save_scope_btn" ).click(function() {

                var scope = { username: $('input#scope_username').val(),
                              lang_pairs : $('input#lang_pairs').val(),
                              tags : $('select#scope_tags').val().join(','),
                              usage_limit : $('input#usage_limit').val(),
                              start_date : $('input#start_date').val(),
                              end_date : $('input#end_date').val(),
                              can_update: $('input#can_update').is(':checked'),
                              can_import: $('input#can_import').is(':checked'),
                              can_export: $('input#can_export').is(':checked'),
                              }

                var scope_id = $('input#scope_id').val();
                if (scope_id != 'auto') {
                    scope['id'] = scope_id;
                }
                console.log(scope);
                window.g_elastic_tm.set_user_scope(scope, window.ajax_user_params);

            });

            $( "#delete_scope_btn" ).click(function() {
                bootbox.confirm("Are you sure you want to delete scope " + $('input#scope_id').val() + "?",
                            function(result) {
                    if (result) {
                        $('#scope_modal').modal('hide');
                        $('#user_modal').modal('hide');
                        window.g_elastic_tm.delete_user_scope($('input#scope_username').val(), $('input#scope_id').val(), window.ajax_user_params);
                    }
                })
            });

            var ajax_query_params = {
                complete: function() {$("#spinner").hide();},
                success: function(data) {
                       console.log(data);
                       $('#status').addClass('alert-success')
                       $('#status').show();
                       $("#status_text").html('Query succeeded with <b>' + data["results"].length + '</b> result(s)')
                       $("#status").fadeTo(5000, 500).slideUp(500, function(){
                            $("#status").slideUp(500);
                        });
                        var query_results = "";
                        $.each(data["results"], function(index, value) {
                            if (!value.mt) {
                                var match = value.match;
                                var cl = "success";
                                if (match < 70) {
                                    cl = "warning";
                                }
                            } else {
                                var match = "MT";
                                var cl = "info";
                            }
                            var tag_names = []
                            for (var tag_id of value.tag) { tag_names.push(window.tag_ids2names[tag_id]); }
                            var result = '<tr><td class="' + cl + '">' + match +
                                            "</td><td>" + value.tu.source_text +
                                            "</td><td>" + value.tu.target_text +
                                            "</td><td>" + tag_names +
                                            "</td><td>" + value.username +
                                            "</td><td>" + value.file_name +
                                            "</td><td>" + dateFormatter(value.update_date) + "</td></tr>";
                            query_results += result;
                        });
                        $("#query_results_table > tbody").html(query_results)

                },
                error: function(XMLHttpRequest, textStatus, errorThrown) {
                       $('#status').addClass('alert-danger');
                       $('#status').show();
                       $("#status_text").text(textStatus + " - " + errorThrown);

                }
            }


            $( "#query_btn" ).click(function() {
                $("#spinner").show();
                var options = {}

                $( "input[id^='query_options'][type='text']" ).each(function(index) {
                    var text = $(this).val();
                    if (text) {
                        options[$(this)[0].name] = text;
                    }
                });
                $( "input[id^='query_options'][type='checkbox']" ).each(function(index) {
                    options[$(this)[0].name] = $(this).is(':checked');
                });

                var filters = get_filters('query');
                window.g_elastic_tm.query( $("#input_query").val(), $("#query_source_lang" ).val(), $( "#query_target_lang" ).val(), options, filters, ajax_query_params);
            });



            $( "#login_btn" ).click(function() {
                var username = $('input#luser').val();
                var password = $('input#lpassword').val();
                var remember_me = $('input#remember_me').is(':checked');

                login(username, password).then(function() {
                    // Update local storage accordingly
                    window.localStorage.setItem("username", remember_me ? username : "");
                    window.localStorage.setItem("password", remember_me ? password : "");
                    $('#login_modal').modal('hide');
                })
            });


            // Main tabs switiching handlers
            $('a[href="#tm"]').click(function(){
                $("#users_row").hide();
                $("#jobs_row").hide();
                $("#tm_row").show();

                $("#title").text("Translation Memory");

                $("#tm_li").addClass("active-link");
                $("#jobs_li").removeClass("active-link");
                $("#users_li").removeClass("active-link");
            });

            $('a[href="#users"]').click(function(){
                $("#jobs_row").hide();
                $("#tm_row").hide();
                $("#users_row").show();
                $("#title").text("Users");

                $("#users_li").addClass("active-link");
                $("#jobs_li").removeClass("active-link");
                $("#tm_li").removeClass("active-link");
            });

            $('a[href="#jobs"]').click(function(){
                $("#tm_row").hide();
                $("#users_row").hide();
                $("#jobs_row").show();
                $("#title").text("Jobs");

                $("#jobs_li").addClass("active-link");
                $("#tm_li").removeClass("active-link");
                $("#users_li").removeClass("active-link");

            });

             // Logout handling
            $('a[href="#logout"]').click(function(){
                window.token = "";
                window.localStorage.setItem("token", "");
                try_login();
            });

             // Refresh handling
            $('a[href="#refresh"]').click(function(){
                init().then(function() {
                    $("#stats_tab").trigger("click");
                    fill_languages();
                });
            });


        },

        initialization: function () {
            mainApp.main_fun();

        }
    }
    // Initializing ///

    $(document).ready(function () {
        mainApp.main_fun();
    });


}(jQuery));

function flagFormatter(value) {
    lang = value.toUpperCase();
    code = value.toLowerCase()
    // TODO: add more language to country mappings
    var lang2country = { AR : 'eg',
                         EN : 'gb',
                         CS : 'cz',
                         DA : 'dk',
                         EL : 'gr',
                         ZH : 'cn',
                         GA : 'ie',
                         SV : 'se',
                         SL : 'si',
                         ET : 'ee',
                         JA : 'jp',
                         FA : 'ir',
                         HE : 'il',
                         KO : 'kr',
                         EU:  'es-eu',
                         CA:  'es-ca',
                         NB:  'no',
                         UK: 'ua',
                         SR: 'rs',
                         KK: 'kz',
                         SQ: 'al'}
    if (lang in lang2country) { code = lang2country[lang]; }
    return '<span class="flag-icon flag-icon-' + code + '"></span>&nbsp;' + lang;
}

function dateFormatter(utcDate) {
    // TODO: make time zone configurable
    return moment(utcDate, "YYYYMMDDTHHmmssZ").tz('Europe/Madrid').format('DD/MM/YYYY H:mm:ss')
}

function dateFormatterTableFun(utcDate, row, index, field) {
    // TODO: make time zone configurable
    return dateFormatter(utcDate);
}


function stringListFormatter(stringList) {
   var html = '';
   var countList = [];
   if (stringList == undefined) {stringList = [];}
   stringList.forEach(function(key, value) {
        //html += '<span class="badge">' + key1 + '</span>'
        stringSplit = key.split(',');
        countList.push({value : stringSplit[0], count: parseInt(stringSplit[1])});
   });
   countList.sort(function(a,b) {return b.count-a.count;} );

   countList.forEach(function(countMap, value) {
     html += '<span class="badge">' + countMap.value +'<span class="badge" style="background-color:#337ab7;"><small >' + countMap.count + '</small></span></span>'
   });

   return html;
}

function delete_user(username) {
    bootbox.confirm("Are you sure you want to delete user: " + username + "?",
                    function(result) {
        if (result) {
            window.g_elastic_tm.delete_user(username, window.ajax_user_params);
        }
    })
}

function edit_user(username) {
    var user = null;
    var is_new = false;
    if (username != '' && username != null) {
        var users = window.users["users"];
        for (var i = 0, len = users.length; i < len; i++) {
            if (users[i]["username"] == username) {
                user = users[i];
                break;
            }
        }
    } else {
        // New user
        user = { username: 'user' + Math.floor(Math.random()*1000),
                 role: 'user',
                 is_active: true,
                 token_expires: true,
                }
        is_new = true;
    }
    $('input#user').val(user["username"]);
    $('select#role').val(user["role"]);
    $('input#password').val(""); //
    $('input#is_active').prop("checked", user["is_active"]);
    $('input#token_expires').prop("checked", user["token_expires"]);


    // Fill scopes
    if (!is_new) {
        $('div#scopes_group').show();
        var scopes = "";
        if (user["scopes"]) {
            for (var j = 0, slen = user["scopes"].length; j < slen; j++) {
                var scope_id = user["scopes"][j]["id"];
                scopes = scopes + '&nbsp;<a href="javascript:void(0);" onclick="edit_user_scope(\'' + user["username"] + '\',' + scope_id + ');">' + scope_id + '</a>';
            }
        }
        scopes = scopes + '&nbsp;<a href="javascript:void(0);" onclick="edit_user_scope(\'' + user["username"] + '\');"><i class="fa fa-plus"></i></a>';
        $('div#scopes').html(scopes); //
    } else {
        $('div#scopes_group').hide();
    }


    $('#user_modal').modal('show');
}

function edit_user_scope(username, scope_id) {
    $('#scope_tags').multiselect('deselectAll', false);

    var user = null;
    // Find user by username
    if (username != '' && username != null) {
        var users = window.users["users"];
        for (var i = 0, len = users.length; i < len; i++) {
            if (users[i]["username"] == username) {
                user = users[i];
                break;
            }
        }
    }

    if (scope_id != '' && scope_id != null) {
        for (var i = 0, len = user.scopes.length; i < len; i++) {
            if (user.scopes[i]["id"] == scope_id) {
                scope = user.scopes[i];
                $('#delete_scope_btn').prop('disabled',false);
                break;
            }
        }
    } else {
        scope = {id: "auto",
                can_update: false,
                can_import: false,
                can_export: false,
                usage_limit: 0};
        $('#delete_scope_btn').prop('disabled',true);
    }
    $('input#scope_username').val(username);
    $('input#scope_id').val(scope["id"]);
    // Field scope fields
    var fields = ["start_date", "end_date", "usage_limit", "usage_count"];
    for (var i = 0, len = fields.length; i < len; i++) {
        $('input#' + fields[i]).val(scope[fields[i]]);
    }
    // Fill tag-based fields
    var fields = ["lang_pairs"];
    for (var i = 0, len = fields.length; i < len; i++) {
        $('input#' + fields[i]).tagsinput('removeAll');
        var val = scope[fields[i]];
        if (val) {
            var values = val.split(',');

            for (var j = 0, vlen = values.length; j < vlen; j++) {
                $('input#' + fields[i]).tagsinput('add', values[j]);
            }
        }
    }
    // Fill tags
    if (scope["tags"]) {
        $('#scope_tags').multiselect('select', scope["tags"].split(','));
    } else {
        $('#scope_tags').multiselect('deselectAll', false);
        $('#scope_tags').multiselect('updateButtonText');
    }
    for(let option of ['can_update', 'can_import', 'can_export']) {
        $('input#'+option).prop("checked", scope[option]);
    }
    $('#scope_modal').modal('show');
}

function edit_tag(tag_id) {
    var user = null;
    var is_new = false;
    var readonly = true;
    if (tag_id != '' && tag_id != null) {
        var tags = window.tags["tags"];
        for (var i = 0, len = tags.length; i < len; i++) {
            if (tags[i]["id"] == tag_id) {
                tag = tags[i];
                break;
            }
        }
    } else {
        // New tag
        tag = { id: 'tag' + Math.floor(Math.random()*1000),
                name: 'unnamed',
                type: 'unspecified'
              }
        is_new = true;
        readonly = false;
    }
    $('input#tag_id').val(tag["id"]);
    $('input#tag_id').prop('readonly', readonly);
    $('input#tag_name').val(tag["name"]);
    $('select#type').val(tag["type"]);

    $('#tag_modal').modal('show');
}

function tag_ids2names_fun(tags) {
    var ids2names = new Array();
    for (var i = 0, len = tags.length; i < len; i++) {
        ids2names[tags[i]["id"]] = tags[i]["name"];
    }
    return ids2names;
}


function job_params(job_id) {
    var data = window.jobs["jobs"];
    for (var i = 0, len = data.length; i < len; i++) {
        var udata = data[i];
        if (udata["id"] == job_id) {
           $('div#job_params').html(udata["params_str"]);
           $('#job_params_modal').modal('show');
           break;
        }
    }
}

function get_filters(prefix) {
    var filters = {};
    $( "*[id^='" + prefix +"_filter']" ).each(function(index) {
        var value;
        if($(this)[0].type == 'checkbox') {
            value = $(this)[0].checked;
        } else {
            value = $(this).val();
        }
        if (value) {
            filters[$(this)[0].name] = value;
        }
    });
    return filters;
}

function reset_filters(prefix) {
    var filters = {};
    var pattern = "*[id^='" + prefix +"_filter']";
    // Clear values of all input fields
    $( pattern ).val(null);
    // Special handling for tags input
    $( pattern + "[data-role='tagsinput']" ).tagsinput('removeAll');
    // Special handling for multiselect input for tags
    $("*[id^='" + prefix +"_filter_tag']").multiselect("deselectAll", false).multiselect('updateButtonText');

}

function kill_job(job) {
    bootbox.confirm("Are you sure you want to kill job: " + job + "?",
                    function(result) {
        if (result) {
            window.g_elastic_tm.kill_job(job);
        }
    })
}

function fill_languages() {
    $('.selectpicker').selectpicker('destroy');
    for (type of ["source", "target"]) {
        var dropdown = "select[id$=_" + type + "_lang]";
        $( dropdown ).addClass("selectpicker");
        $( dropdown ).each(function(index) {
            var select = this;
            //select.selectpicker('destroy');
            select.options.length = 0;
            var langs = Array();
            Object.keys(window.stats.lang_pairs).forEach(function(lang_pair, value) {
                var lang_pair_arr = lang_pair.split('_');
                var index = type == "source" ? 0 : 1;
                langs[lang_pair_arr[index]] = 1;

            });

            for (var key in langs) {
                var option = new Option("", key);
                option.dataset.content = flagFormatter(key);
                select.append(option);
            }
            //select.selectpicker();
            //select.addClass("selectpicker");
        });
    }
    $('.selectpicker').selectpicker();
}

function export_file(export_id, filename) {
    window.g_elastic_tm.export_download(export_id, filename, {});
}

function export_delete(export_id) {
    bootbox.confirm("Are you sure you want to delete export: " + export_id + "?",
                    function(result) {
        if (result) {
            window.g_elastic_tm.export_delete(export_id, window.ajax_export_params);
        }
    })
}
/*
function validate_tag_combination(tag_ids) {
    let has_specified_tags = false;
    for (tag_id of tag_ids) {
        let res = await window.g_elastic_tm.get_tag(next_tag_id);
        if (res) {
            has_specified_tags = true;
            break;
        }
    }
    return has_specified_tags;
}
*/

function validate_tag_combination(tag_ids) {
    let has_specified_tags = false;
    return tag_ids.reduce( async (prev_promise, next_tag_id) => {
        await prev_promise;
        return window.g_elastic_tm.get_tag(next_tag_id).then(function(tag_data) {
           if (tag_data["type"] !== "unspecified") {
               has_specified_tags = true;
           }
           return has_specified_tags;
        })
    }, Promise.resolve());
}


$(function(){
    $("[data-hide]").on("click", function(){
        $("." + $(this).attr("data-hide")).hide();
        /*
         * The snippet above will hide all elements with the class specified in data-hide,
         * i.e: data-hide="alert" will hide all elements with the alert property.
         *
         * Xeon06 provided an alternative solution:
         * $(this).closest("." + $(this).attr("data-hide")).hide();
         * Use this if are using multiple alerts with the same class since it will only find the closest element
         *
         * (From jquery doc: For each element in the set, get the first element that matches the selector by
         * testing the element itself and traversing up through its ancestors in the DOM tree.)
        */
    });
});
