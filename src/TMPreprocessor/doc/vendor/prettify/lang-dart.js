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
PR.registerLangHandler(PR.createSimpleLexer([["pln",/^[\t\n\r \xa0]+/,null,"\t\n\r \u00a0"]],[["com",/^#!.*/],["kwd",/^\b(?:import|library|part of|part|as|show|hide)\b/i],["com",/^\/\/.*/],["com",/^\/\*[^*]*\*+(?:[^*/][^*]*\*+)*\//],["kwd",/^\b(?:class|interface)\b/i],["kwd",/^\b(?:assert|break|case|catch|continue|default|do|else|finally|for|if|in|is|new|return|super|switch|this|throw|try|while)\b/i],["kwd",/^\b(?:abstract|const|extends|factory|final|get|implements|native|operator|set|static|typedef|var)\b/i],
["typ",/^\b(?:bool|double|dynamic|int|num|object|string|void)\b/i],["kwd",/^\b(?:false|null|true)\b/i],["str",/^r?'''[\S\s]*?[^\\]'''/],["str",/^r?"""[\S\s]*?[^\\]"""/],["str",/^r?'('|[^\n\f\r]*?[^\\]')/],["str",/^r?"("|[^\n\f\r]*?[^\\]")/],["pln",/^[$_a-z]\w*/i],["pun",/^[!%&*+/:<-?^|~-]/],["lit",/^\b0x[\da-f]+/i],["lit",/^\b\d+(?:\.\d*)?(?:e[+-]?\d+)?/i],["lit",/^\b\.\d+(?:e[+-]?\d+)?/i],["pun",/^[(),.;[\]{}]/]]),
["dart"]);
