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
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter

class TMAlignSentences():

  def __init__(self):
    pass

  #Create a matrix with the similarity among source and target sentence
  def matrix_str_cosine(self, source, target):
    s_matrix = np.zeros(shape=(len(source),len(target)), dtype=float)

    for row in range(0,len(source)):
      for col in range(0,len(target)):
        s_matrix[row, col] = self.string_cosine(source[row],target[col])
    return s_matrix


  def string_cosine(self, a, b):

    # count word occurrences
    a_vals = Counter(a.split())
    b_vals = Counter(b.split())

    # convert to word-vectors
    words = list(a_vals.keys() | b_vals.keys())
    a_vect = [a_vals.get(word, 0) for word in words]
    b_vect = [b_vals.get(word, 0) for word in words]

    # find cosine
    len_a = sum(av * av for av in a_vect) ** 0.5
    len_b = sum(bv * bv for bv in b_vect) ** 0.5
    dot = sum(av * bv for av, bv in zip(a_vect, b_vect))
    cosine = dot / (len_a * len_b)

    return cosine

  # Return a list with align between the sentences or empty if not align
  def align_process(self, sourceV, targetV):

    align_value = []
    for s in range(0,len(sourceV)): # All the sentences source and target
      s_segments = sourceV[s]#List of feature for each segment
      t_segments = targetV[s]

      if (s_segments!=[] and t_segments!=[]) and (len(s_segments)==len(t_segments)):

        # Superficial similarity
        source_array = np.array([(s_segment[0:2]) for s_segment in s_segments])
        target_array = np.array([(t_segment[0:2]) for t_segment in t_segments])

        superficial_cosine = cosine_similarity(source_array, target_array)

        # Linguistic Similarity --> content pattern posTagtargetV
        source_array = np.array([(s_segment[2]) for s_segment in s_segments], dtype=str)
        target_array = np.array([(t_segment[2]) for t_segment in t_segments], dtype=str)

        pos_pattern_cosine = self.matrix_str_cosine(source_array, target_array)

        #Linguistic Similarity --> stopwords pattern posTag
        source_array = np.array([(s_segment[3]) for s_segment in s_segments], dtype=str)
        target_array = np.array([(t_segment[3]) for t_segment in t_segments], dtype=str)

        stop_word_cosine = self.matrix_str_cosine(source_array, target_array)
        similarity_values = superficial_cosine + pos_pattern_cosine + stop_word_cosine

        align_value.append(np.argmax(similarity_values, axis=1)) #--> Load a list with the index of target align
      else:
        align_value.append([])

    return align_value
