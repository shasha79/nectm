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
from nltk.tree import ParentedTree

def output(sentS, sentT, startS, endS, startT, endT):
    
    s = list(sentS)
    t = list(sentT)
    
    for i in range(0, startS):
        s[i] = s[i] + "/O"
    for i in range(startS, endS+1):
        if i == startS:
            s[i] = s[i] + "/B-T"
        else:
            s[i] = s[i] + "/I-T"
    for i in range(endS+1, len(sentS)):
        s[i] = s[i] + "/O"
    
    for i in range(0, startT):
        t[i] = t[i] + "/O"
    for i in range(startT, endT+1):
        if i == startT:
            t[i] = t[i] + "/B-T"
        else:
            t[i] = t[i] + "/I-T"
    for i in range(endT+1, len(sentT)):
        t[i] = t[i] + "/O"
    print " ".join(s) + " ||| " + " ".join(t)

for line in sys.stdin.readlines():
    source, target = line.split(" ||| ")
    #source = "<T> " + source + " </T>"
    #target = "<T> " + target + " </T>"
    
    stree = ParentedTree.fromstring(source)
    ttree = ParentedTree.fromstring(target)
    
    s_sent = stree.leaves()
    t_sent = ttree.leaves();
    
    sleaves_pos = stree.treepositions('leaves')
    tleaves_pos = ttree.treepositions('leaves')
    
    for skid in stree.subtrees():
        if skid.label() == "T":
            continue
        s_num = len(skid.leaves())
        if s_num == 0:
            continue
        
        skid_pos = skid.treeposition()
        startS = sleaves_pos.index(skid_pos + skid.leaf_treeposition(0))
        endS = sleaves_pos.index(skid_pos + skid.leaf_treeposition(s_num-1))
        
        found = False
        for tkid in ttree.subtrees(lambda t: t.label() == skid.label()):
            assert not found
            found = True
            
            t_num = len(tkid.leaves())
            if t_num == 0:
                continue
        
            tkid_pos = tkid.treeposition()
            startT = tleaves_pos.index(tkid_pos + tkid.leaf_treeposition(0))
            endT = tleaves_pos.index(tkid_pos + tkid.leaf_treeposition(t_num-1))
            
            output(s_sent, t_sent, startS, endS, startT, endT)
            
        if not found:
            output(s_sent, t_sent, startS, endS, len(t_sent), len(t_sent)-1)
    
    #break
