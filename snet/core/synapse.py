# !/usr/bin/env python3
# -*- coding: utf-8 -*-

# @Filename: synapse
# @Date: 2019-04-17-14-58
# @Author: Nuullll (Yilong Guo)
# @Email: vfirst218@gmail.com


import torch


class AbstractSynapse(object):
    """
    Abstract class for synapse.
    """

    def __init__(self, pre_layer, post_layer, weights, net):
        """
        :param pre_layer:   <Layer>
        :param post_layer:  <Layer>
        :param weights:     <torch.Tensor>
        :param net:         <Network>
        """

        self.pre_layer = pre_layer
        self.post_layer = post_layer

        # weights related
        self.weights = weights
        self.w_min = 0.
        self.w_max = 1.

        self.network = net

        # recording
        self._last_pre_spike_time = -torch.ones(self.pre_layer.size)    # -1 means never fired before
        self._last_post_spike_time = -torch.ones(self.post_layer.size)

        # static mode
        self.static = False

    def forward(self):
        """
        Fetches output of `pre_layer` and computes results as input of `post_layer`.
        """
        pre = self.pre_layer.o

        self.post_layer.i = torch.matmul(pre, self.weights)

    def _clamp(self):
        self.weights.clamp_(min=self.w_min, max=self.w_max)

    @property
    def time(self):
        return self.network.time

    def update_on_pre_spikes(self):
        """
        Updates weights when new pre-spikes come.
        """
        raise NotImplementedError("update_on_pre_spikes() is not implemented.")

    def update_on_post_spikes(self):
        """
        Updates weights when new post-spikes come.
        :return:
        """
        raise NotImplementedError("update_on_post_spikes() is not implemented.")

    def plot_weight_map(self):
        """
        Plots weight map.
        """
        # TODO: plot weight map.
        pass


class ExponentialSTDPSynapse(AbstractSynapse):
    """
    Learning rule: exponential STDP
    """

    def __init__(self, *args, **kwargs):
        super(ExponentialSTDPSynapse, self).__init__(*args, **kwargs)

        # TODO: parse learning rate options.

    def update_on_pre_spikes(self):
        if self.static:
            return

        # record new pre-spikes
        self._last_pre_spike_time[self.pre_layer.firing_mask] = self.time

        # mask
        post_active = self._last_post_spike_time >= 0
        active = torch.ger(self.pre_layer.firing_mask, post_active)  # new pre-spikes and fired post-spikes

        # calculate timing difference (where new pre-spikes timing is now)
        dt = (self._last_pre_spike_time.repeat(self.post_layer.size, 1).t() -
              self._last_post_spike_time.repeat(self.pre_layer.size, 1))

        window_mask = (dt <= 2 * self.tau_m)
        active &= window_mask

        # weights decrease, because pre-spikes come after post-spikes
        dw = self.learn_rate_m * (self.weights[active] - self.w_min) * torch.exp(-dt / self.tau_m)
        self.weights[active] -= dw
        self._clamp()

    def update_on_post_spikes(self):
        if self.static:
            return

        # record new post-spikes
        self._last_post_spike_time[self.post_layer.firing_mask] = self.time

        # mask
        pre_active = self._last_pre_spike_time >= 0
        active = torch.ger(pre_active, self.post_layer.firing_mask)     # fired pre-spikes and new post-spikes

        # calculate timing difference (where new post-spikes timing is now)
        dt = (self._last_post_spike_time.repeat(self.pre_layer.size, 1) -
              self._last_pre_spike_time.repeat(self.post_layer.size, 1).t())

        window_mask = (dt <= 2 * self.tau_p)
        active &= window_mask

        # weights decrease, because pre-spikes come after post-spikes
        dw = self.learn_rate_p * (self.w_max - self.weights[active]) * torch.exp(-dt / self.tau_p)
        self.weights[active] += dw
        self._clamp()
