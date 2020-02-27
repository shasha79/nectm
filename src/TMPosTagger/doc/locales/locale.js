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
define([
    './locales/de.js',
    './locales/nl.js',
    './locales/zh.js'
], function() {
    var locales = {};
    for(index in arguments) {
        for(property in arguments[index]) {
            locales[property] = arguments[index][property];
        }
    }

    var language = ((navigator.language) ? navigator.language : navigator.userLanguage).substr(0, 2).toLowerCase();
    if( ! locales['en'])
        locales['en'] = {};
    if( ! locales[language])
        language = 'en';

    var locale = locales[language];

    var __ = function(text) {
        var index = locale[text];
        if(index === undefined) return text;
        return index;
    };

    return {
        __     : __,
        locales: locales,
        locale : locale
    };
});
