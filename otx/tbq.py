# -*- mode: python; coding: utf-8 -*-

from twisted.internet import defer

class TokenBucketQueue(object):
    def __init__(self, reactor, token_rate, bucket_size, token_cost = 1.0, start_paused = False):
        self.reactor = reactor
        self.token_rate = token_rate
        self.bucket_size = bucket_size
        self.token_cost = token_cost
        self.paused = start_paused
        self.tokens = 0.0
        self.waiting = []
        self.pending = []
        self.delayed_call = None

        if not self.paused:
            self.delayed_call = self.reactor.callLater(0.0, self._add)

    def pause(self):
        if self.delayed_call is not None and self.delayed_call.active():
            self.delayed_call.cancel()
        self.delayed_call = None
        self.paused = True

    def resume(self):
        self.paused = False
        if self.delayed_call is None or not self.delayed_call.active():
            self.delayed_call = self.reactor.callLater(0.0, self._add)

    def _add(self):
        if self.paused:
            return

        self.reactor.callLater(self.token_rate, self._add)

        self.tokens += 1.0
        if self.tokens > self.bucket_size:
            self.tokens = self.bucket_size

        while self.tokens >= self.token_cost and self.waiting and self.pending:
            self.tokens -= self.token_cost
            self.waiting.pop(0).callback(self.pending.pop(0))

    def _cancel(self, d):
        self.waiting.remove(d)

    def get(self):
        if not self.paused and self.tokens >= self.token_cost and self.pending:
            self.tokens -= self.token_cost
            return defer.succeed(self.pending.pop(0))

        d = defer.Deferred(canceller = self._cancel)
        self.waiting.append(d)
        return d

    def put(self, obj):
        if not self.paused and self.tokens >= self.token_cost and self.waiting:
            self.tokens -= self.token_cost
            self.waiting.pop(0).callback(obj)
            return

        self.pending.append(obj)
