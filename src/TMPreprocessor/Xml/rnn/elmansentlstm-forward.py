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

import load
from elmansentlstm import model
from accuracy import conlleval
from tools import shuffle, minibatch, contextwin

'''
modified by Liangyou Li @ 25 July 2016
'''

if __name__ == '__main__':

    s = {'verbose':1,
         'win':7, # number of words in the context window
         'nhidden':100, # number of hidden units
         'seed':345,
         'emb_dimension':100, # dimension of word embedding
         'nepochs':100}

    folder = os.path.basename(__file__).split('.')[0]
    if not os.path.exists(folder): os.mkdir(folder)

    # load the dataset
    train_set, valid_set, test_set, dic = load.postagfold('data/alltag.bio.pkl')
    idx2label = dict((k,v) for v,k in dic['labels2idx'].iteritems())
    idx2word  = dict((k,v) for v,k in dic['words2idx'].iteritems())

    train_lex, train_y, train_slex, train_sy = train_set
    valid_lex, valid_y, valid_slex, valid_sy = valid_set
    test_lex,  test_y, test_slex, test_sy  = test_set

    vocsize = len(dic['words2idx'])
    nclasses = len(dic['labels2idx'])
    nsentences = len(train_lex)

    # instanciate the model
    numpy.random.seed(s['seed'])
    random.seed(s['seed'])
    rnn = model(    nh = s['nhidden'],
                    nc = nclasses,
                    ne = vocsize,
                    de = s['emb_dimension'],
                    cs = s['win'] )
    
    # train
    best_f1 = -numpy.inf
    for e in xrange(s['nepochs']):
        # shuffle
        shuffle([train_lex, train_y, train_slex, train_sy], s['seed'])
        tic = time.time()
        for i in xrange(nsentences):
            cwords = contextwin(train_lex[i], s['win'])
            labels = train_y[i]
            src = train_slex[i]
            srcy = train_sy[i]
            
            rnn.train(cwords, labels, src,srcy)

            if s['verbose'] and ((i == nsentences-1) or i % 100 == 0):
                print '[learning] epoch %i >> %i / %i '%(e, i+1, nsentences),'completed in %.2f (sec) ' %(time.time()-tic)
                sys.stdout.flush()
            
            if i > 0 and ((i == nsentences-1) or i % 500 == 0):
            
                # evaluation // back into the real world : idx -> words
                predictions_test = [ map(lambda x: idx2label[x], \
                                     rnn.classify(numpy.asarray(contextwin(x, s['win'])).astype('int32'), src, srcy))\
                                     for x, src, srcy in zip(test_lex, test_slex, test_sy) ]
                groundtruth_test = [ map(lambda x: idx2label[x], y) for y in test_y ]
                words_test = [ map(lambda x: idx2word[x], w) for w in test_lex]

                predictions_valid = [ map(lambda x: idx2label[x], \
                                     rnn.classify(numpy.asarray(contextwin(x, s['win'])).astype('int32'), src, srcy))\
                                     for x, src, srcy in zip(valid_lex, valid_slex, valid_sy) ]
                groundtruth_valid = [ map(lambda x: idx2label[x], y) for y in valid_y ]
                words_valid = [ map(lambda x: idx2word[x], w) for w in valid_lex]

                # evaluation // compute the accuracy using conlleval.pl
                res_test  = conlleval(predictions_test, groundtruth_test, words_test, folder + '/current.test.txt')
                res_valid = conlleval(predictions_valid, groundtruth_valid, words_valid, folder + '/current.valid.txt')
                
                # save new model if a better score is obtained
                if res_valid['f1'] > best_f1:
                    rnn.save(folder)
                    best_f1 = res_valid['f1']
                    if s['verbose']:
                        print 'NEW BEST: epoch', e, 'valid F1', res_valid['f1'], 'best test F1', res_test['f1'], ' '*20
                        sys.stdout.flush()
                    s['vf1'], s['vp'], s['vr'] = res_valid['f1'], res_valid['p'], res_valid['r']
                    s['tf1'], s['tp'], s['tr'] = res_test['f1'],  res_test['p'],  res_test['r']
                    s['be'] = e
                    subprocess.call(['mv', folder + '/current.test.txt', folder + '/best.test.txt'])
                    subprocess.call(['mv', folder + '/current.valid.txt', folder + '/best.valid.txt'])
                else:
                    print 'epoch', e, 'valid F1', res_valid['f1'], 'best test F1', res_test['f1'], ' '*20
                    sys.stdout.flush()

    print 'BEST RESULT: epoch', e, 'valid F1', s['vf1'], 'best test F1', s['tf1'], 'with the model', folder

