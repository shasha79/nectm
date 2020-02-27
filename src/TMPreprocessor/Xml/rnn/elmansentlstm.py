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
import theano
import numpy
import os

from theano import tensor as T
from collections import OrderedDict

'''
modified by Liangyou Li @ 25 July 2016
'''


class LSTM(object):
    
    '''
    nh :: dimension of the hidden layer
    de :: dimension of the word embeddings
    x  :: input sentence in two-dimension: sent_len * de
    '''
    
    def __init__(self, nh, de, x, suffix):
        
        # parameters
        self.wifoc = theano.shared(0.2*numpy.random.uniform(-1.0, 1.0,\
                    (de, 4*nh)).astype(theano.config.floatX))
        self.uifoc = theano.shared(0.2*numpy.random.uniform(-1.0, 1.0,\
                    (nh, 4*nh)).astype(theano.config.floatX))
        self.bifoc = theano.shared(numpy.zeros(4*nh).astype(theano.config.floatX))
        self.h0 = theano.shared(numpy.zeros(nh,).astype(theano.config.floatX))
        self.c0 = theano.shared(numpy.zeros(nh,).astype(theano.config.floatX))
         
        # bundle
        self.params = [ self.wifoc, self.uifoc, self.bifoc, self.h0, self.c0 ]
        self.names = ['wifoc_'+suffix, 'uifoc_'+suffix, 'bifoc_'+suffix, 'h0_'+suffix, 'c0_'+suffix]
        

        def _slice(data, index, size):
            return data[index*size:(index+1)*size]
    
        # rnn step   
        def recurrence(precomp_x_t, h_tm1, c_tm1):
            # i f o c
            precomp = precomp_x_t + T.dot(h_tm1, self.uifoc)
            
            # input gate
            it = T.nnet.sigmoid(_slice(precomp, 0, nh))
            ctt = T.tanh(_slice(precomp, 3, nh))
            # forget gate
            ft = T.nnet.sigmoid(_slice(precomp, 1, nh))
            
            # new memory cell
            ct = it*ctt + ft*c_tm1
            
            #output gate
            ot = T.nnet.sigmoid(_slice(precomp, 2, nh))
            
            # new hidden state, a vector
            ht = ot * T.tanh(ct)
            
            return [ht, ct]
        
        # precomputation for speed-up
        precomp_x = T.dot(x, self.wifoc) + self.bifoc
        
        '''
        theano.scan read a sentence word by word
        call the function recurrence to:
            process each word
            return values
        '''
        [h_sent, c_sent] , _ = theano.scan(fn=recurrence,\
                sequences=[precomp_x], outputs_info=[self.h0, self.c0])
        
        # new sentence representation in two dimension: sent_len * nh
        self.hidden = h_sent.reshape((x.shape[0], nh))



class model(object):
    
    def __init__(self, nh, nc, ne, de, cs):
        '''
        nh :: dimension of the hidden layer
        nc :: number of classes
        ne :: number of word embeddings in the vocabulary
        de :: dimension of the word embeddings
        cs :: word window context size 
        '''
        
        nctxt = 2*nh
        
        # parameters of the model
        self.emb = theano.shared(0.2 * numpy.random.uniform(-1.0, 1.0,\
                   (ne+1, de)).astype(theano.config.floatX)) # add one for PADDING at the end
        self.W   = theano.shared(0.2 * numpy.random.uniform(-1.0, 1.0,\
                   (nh, nc)).astype(theano.config.floatX))
        self.b   = theano.shared(numpy.zeros(nc, dtype=theano.config.floatX))
        
        self.wifoc = theano.shared(0.2*numpy.random.uniform(-1.0, 1.0,\
                    (de*cs, 4*nh)).astype(theano.config.floatX))
        self.uifoc = theano.shared(0.2*numpy.random.uniform(-1.0, 1.0,\
                    (nh, 4*nh)).astype(theano.config.floatX))
        self.bifoc = theano.shared(numpy.zeros(4*nh).astype(theano.config.floatX))
        self.h0 = theano.shared(numpy.zeros(nh,).astype(theano.config.floatX))
        self.c0 = theano.shared(numpy.zeros(nh,).astype(theano.config.floatX))
        self.Watt  = theano.shared(0.2*numpy.random.uniform(-1.0, 1.0,\
                    (de*cs, nctxt)).astype(theano.config.floatX))
        self.batt = theano.shared(numpy.zeros(nctxt).astype(theano.config.floatX))
        
        # parameters of source context
        self.emb_ctxt = theano.shared(0.2 * numpy.random.uniform(-1.0, 1.0,\
                        (ne, de)).astype(theano.config.floatX)) # add one for PADDING at the end
        self.h2c = theano.shared(0.2 * numpy.random.uniform(-0.1, 0.1,\
                    (nh,nctxt)).astype(theano.config.floatX))
        self.Wctxt = theano.shared(0.2 * numpy.random.uniform(-0.1, 0.1,\
                    (nctxt,1)).astype(theano.config.floatX))
        self.bctxt   = theano.shared(numpy.zeros((1,), dtype=theano.config.floatX))
        self.Wcv = theano.shared(0.2 * numpy.random.uniform(-0.1, 0.1,\
                    (nctxt,4*nh)).astype(theano.config.floatX))
        self.c2c = theano.shared(0.2 * numpy.random.uniform(-0.1, 0.1,\
                    (nctxt,nctxt)).astype(theano.config.floatX))
        
        # vector representation of labels
        s = [ [1,0,0],
              [0,1,0],
              [0,0,1]
            ]
        self.emb_label = theano.shared(numpy.array(s, dtype=theano.config.floatX))
        
        '''
        z: source sentence, a vector
        zy: source sentence label, a vector
        '''
        z = T.ivector()
        zy = T.ivector()
        
        '''
        ctxt: source, a matrix: sent_len * (de + nc)
        ctxt_rev: reversed source, a matrix: sent_len * (de + nc)
        
        word representation and label representation are concatenated
        '''
        
        ctxt = T.concatenate([self.emb_ctxt[z], self.emb_label[zy]], axis=1)
        ctxt_rev = T.concatenate([self.emb_ctxt[z[::-1]], self.emb_label[zy[::-1]]], axis=1)
        
        '''
        forward and backward LSTM to compute representation of each source word
        '''
        self.lstmfwd = LSTM(nh, de+nc, ctxt, "fwd")
        self.lstmbwd = LSTM(nh, de+nc, ctxt_rev, "bwd")
        
        '''
        concatenate the two LSTM to get a full representation of each source word
        '''
        self.context = T.concatenate([self.lstmfwd.hidden, self.lstmbwd.hidden[::-1]], axis=1)

        # bundle parameters which will be tuned
        self.params = [ self.emb, self.W, self.b, self.wifoc, self.uifoc, self.bifoc, self.h0, self.c0, self.Watt, self.batt ]\
                        + [self.emb_ctxt, self.h2c, self.Wctxt, self.bctxt, self.Wcv, self.c2c] \
                        + self.lstmfwd.params + self.lstmbwd.params
        self.names  = ['embeddings', 'W', 'b', 'Wifoc', 'Uifoc', 'bifoc', 'h0', 'c0', 'Watt', 'batt']\
                        + ['embeddings_src', 'h2c', 'Wctxt', 'bctxt', 'Wcv', 'Wc2c'] \
                        + self.lstmfwd.names + self.lstmbwd.names
        '''
        target sentence
        each target word is accompanied with context words, see the finction contextwin in tools.py
        '''
        idxs = T.imatrix() 
        x = self.emb[idxs].reshape((idxs.shape[0], de*cs))
        # target labels
        y    = T.ivector('y') # label
        
        def _slice(data, index, size):
            return data[index*size:(index+1)*size]
        
        '''
        target recurrent neural network, LSTM
        use attention to source sentence
        '''
        def recurrence(attx_t, precomp_x_t, h_tm1, c_tm1, ctxt_tm1):
            
            '''
            attention model
            a distribution over source words
            '''
            pre_ctxt = T.dot(h_tm1, self.h2c) + attx_t + T.dot(ctxt_tm1, self.c2c)
            ctxt = self.context + pre_ctxt[None,:] 
            ctxt = T.tanh(ctxt)
            alpha = T.dot(ctxt, self.Wctxt) + self.bctxt#.repeat(ctxt.shape[0],axis=0)
            alpha = T.exp(alpha.reshape((alpha.shape[0],)))
            alpha = alpha / T.sum(alpha)
            
            '''
            weighted sum of source words
            '''
            cv = (self.context * alpha[:,None]).sum(axis=0) # 2h
            
            
            precomp = precomp_x_t + T.dot(h_tm1, self.uifoc) + T.dot(cv, self.Wcv)
            
            # LSTM gates
            it = T.nnet.sigmoid(_slice(precomp, 0, nh))
            ctt = T.tanh(_slice(precomp, 3, nh))
            ft = T.nnet.sigmoid(_slice(precomp, 1, nh))
            
            c_t = it*ctt + ft*c_tm1
            
            ot = T.nnet.sigmoid(_slice(precomp, 2, nh))
            
            # new hidden
            h_t = ot * T.tanh(c_t)
            
            # softmax to calculate a distribution over labels
            s_t = T.nnet.softmax(T.dot(h_t, self.W) + self.b)
            return [h_t, c_t, cv, s_t]
        
        # precomputation to speed-up
        precomp_x = T.dot(x, self.wifoc) + self.bifoc
        att_x = T.dot(x, self.Watt) + self.batt
        ctxt_init = T.mean(self.context, axis=0)
        
        # theano.scan over target sentence word by word
        [h, _, _, s], _ = theano.scan(fn=recurrence, \
            sequences=[att_x, precomp_x], outputs_info=[self.h0, self.c0, ctxt_init, None], \
            n_steps=x.shape[0])
        
        '''
        label probabilities of each target word
        '''
        p_y_given_x_sentence = s[:,0,:]
        # take the one with the largest probability
        y_pred = T.argmax(p_y_given_x_sentence, axis=1)

        # cost and gradients
        lr = T.scalar('lr')
        nll = T.mean(-T.log(p_y_given_x_sentence[T.arange(y.shape[0]), y]))
        gradients = T.grad( nll, self.params )
        
        '''
        gradient clipping to prevent huge updates
        '''
        max_dw = 5.
        new_dw = T.sum([(gparam**2).sum() for gparam in gradients])
        new_dw = T.sqrt(new_dw)
        gradients = [gparam*T.min([max_dw, new_dw])/new_dw for gparam in gradients]
        
        
        ####### adadelta, adaptive updates of parameters
        # create variables to store intermediate updates
        parameters = self.params
        rho = 0.95
        eps = 1e-6
        gradients_sq = [ theano.shared(numpy.zeros(p.get_value().shape).astype(theano.config.floatX)) for p in parameters ]
        deltas_sq = [ theano.shared(numpy.zeros(p.get_value().shape).astype(theano.config.floatX)) for p in parameters ]
     
        # calculates the new "average" delta for the next iteration
        gradients_sq_new = [ rho*g_sq + (1-rho)*(g**2) for g_sq,g in zip(gradients_sq,gradients) ]
     
        # calculates the step in direction. The square root is an approximation to getting the RMS for the average value
        deltas = [ (T.sqrt(d_sq+eps)/T.sqrt(g_sq+eps))*grad for d_sq,g_sq,grad in zip(deltas_sq,gradients_sq_new,gradients) ]
     
        # calculates the new "average" deltas for the next step.
        deltas_sq_new = [ rho*d_sq + (1-rho)*(d**2) for d_sq,d in zip(deltas_sq,deltas) ]
     
        # Prepare it as a list f
        gradient_sq_updates = list(zip(gradients_sq,gradients_sq_new))
        deltas_sq_updates = list(zip(deltas_sq,deltas_sq_new))
        parameters_updates = [ (p,p - d) for p,d in zip(parameters,deltas) ]
        updates = gradient_sq_updates + deltas_sq_updates + parameters_updates
        ##### end adadelta
        
        # theano functions
        self.classify = theano.function(inputs=[idxs, z, zy], outputs=y_pred)

        self.train = theano.function( inputs  = [idxs, y, z, zy],
                                      outputs = nll,
                                      updates = updates )
        
        # not used
        self.normalize = theano.function( inputs = [],
                         updates = [(self.emb,
                         self.emb/T.sqrt((self.emb**2).sum(axis=1)).dimshuffle(0,'x')),\
                         (self.emb_ctxt,
                         self.emb_ctxt/T.sqrt((self.emb_ctxt**2).sum(axis=1)).dimshuffle(0,'x'))])
    
    '''
    save model to a given folder
    '''
    def save(self, folder):   
        for param, name in zip(self.params, self.names):
            numpy.save(os.path.join(folder, name + '.npy'), param.get_value())
    '''
    load model from a given folder
    '''
    def load(self, folder):   
        for param, name in zip(self.params, self.names):
            param.set_value(numpy.load(os.path.join(folder, name + '.npy')))
