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
import numpy
import time
import sys
import subprocess
import os
import random

import cPickle

from elmansentlstm import model
from tools import contextwin

'''
created by Liangyou Li @ 25 July 2016
'''

if __name__ == '__main__':

    s = {'verbose':1,
         'win':7, # number of words in the context window
         'nhidden':100, # number of hidden units
         'seed':345,
         'emb_dimension':100, # dimension of word embedding
         'nepochs':100}

    folder = 'alltag-model'
    if not os.path.exists(folder): sys.exit()

    # load the dict
    print 'load dict ...'
    _, _, _, dic = cPickle.load(open('data/alltag.bio.pkl','rb'))
    label2idx = dic['labels2idx']
    word2idx  = dic['words2idx']
    idx2label = dict((k,v) for v,k in dic['labels2idx'].iteritems())
    idx2word  = dict((k,v) for v,k in dic['words2idx'].iteritems())
    
    vocsize = len(dic['words2idx'])
    nclasses = len(dic['labels2idx'])
    
    print 'load model'
    rnn = model(    nh = s['nhidden'],
                    nc = nclasses,
                    ne = vocsize,
                    de = s['emb_dimension'],
                    cs = s['win'] )
    rnn.load(folder)
    
    print 'test ...'
    test_lex = ['NOUN', 'X', 'NOUN', 'NOUN', 'NOUN']
    test_lex = [ word2idx[w] for w in test_lex]
    test_slex = ['NOUN', 'NOUN', 'CONJ', 'NOUN', 'NOUN', 'NOUN']
    test_slex = [ word2idx[w] for w in test_slex]
    test_sy = ['O', 'O', 'O', 'B-T', 'I-T', 'I-T']
    test_sy = [ label2idx[w] for w in test_sy]
    
    # evaluation
    predictions_test = [ map(lambda x: idx2label[x], \
                         rnn.classify(numpy.asarray(contextwin(test_lex, s['win'])).astype('int32'), test_slex, test_sy)) ]
    print predictions_test

                

