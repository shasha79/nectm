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
PR.registerLangHandler(PR.createSimpleLexer([["pln",/^[\t-\r ]+/,null,"\t\n\u000b\u000c\r "],["str",/^"(?:[^\n\f\r"\\]|\\[\S\s])*(?:"|$)/,null,'"'],["lit",/^[a-z]\w*/],["lit",/^'(?:[^\n\f\r'\\]|\\[^&])+'?/,null,"'"],["lit",/^\?[^\t\n ({]+/,null,"?"],["lit",/^(?:0o[0-7]+|0x[\da-f]+|\d+(?:\.\d+)?(?:e[+-]?\d+)?)/i,null,"0123456789"]],[["com",/^%[^\n]*/],["kwd",/^(?:module|attributes|do|let|in|letrec|apply|call|primop|case|of|end|when|fun|try|catch|receive|after|char|integer|float,atom,string,var)\b/],
["kwd",/^-[_a-z]+/],["typ",/^[A-Z_]\w*/],["pun",/^[,.;]/]]),["erlang","erl"]);
