# Copyright (c) 2016, NVIDIA CORPORATION. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#  * Neither the name of NVIDIA CORPORATION nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from threading import Thread
import numpy as np

from Config import Config


class ThreadTrainer(Thread):
    def __init__(self, server, id):
        super(ThreadTrainer, self).__init__()
        self.setDaemon(True)

        self.id = id
        self.server = server
        self.exit_flag = False

    @staticmethod
    def dynamic_pad(x, r, a):
      size = int(Config.TIME_MAX) # required size
      z = np.zeros((size-len(x),) + x.shape[1:])
      x = np.append(x, z, axis=0)
      z = np.zeros((size-len(r),) + r.shape[1:])
      r = np.append(r, z, axis=0)
      z = np.zeros((size-len(a),) + a.shape[1:])
      a = np.append(a, z, axis=0)
      assert len(x) == size 
      return x, r, a

    def run(self):
        while not self.exit_flag:
            batch_size = 0
            c__ = []; h__ = []   # lstm hidden states
            while batch_size <= Config.TRAINING_MIN_BATCH_SIZE:
                x_, r_, a_, lstm_ = self.server.training_q.get()

                # when using LSTMs, the recurrence is over the TIME_MAX length
                # trajectory from each agent. Use padding for trajectories of 
                # length < TIME_MAX
                if Config.NUM_LSTMS and x_.shape[0] != int(Config.TIME_MAX):
                  x_, r_, a_ = ThreadTrainer.dynamic_pad(x_, r_, a_)

                if batch_size == 0:
                    x__ = x_; r__ = r_; a__ = a_ 

                    if len(lstm_):
                      c__ = []; h__ = []
                      for i in range(Config.NUM_LSTMS):
                        c__.append(lstm_[i]['c'])
                        h__.append(lstm_[i]['h'])

                else:
                    x__ = np.concatenate((x__, x_))
                    r__ = np.concatenate((r__, r_))
                    a__ = np.concatenate((a__, a_))

                    if len(lstm_):
                      for i in range(Config.NUM_LSTMS):
                        c__[i] = np.concatenate((c__[i], lstm_[i]['c']))
                        h__[i] = np.concatenate((h__[i], lstm_[i]['h']))

                batch_size += x_.shape[0]
            
            if Config.TRAIN_MODELS:
                self.server.train_model(x__, r__, a__, c__, h__, self.id)
