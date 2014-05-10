# -*- mode: python; coding: utf-8 -*-

import time

class Watchdog(object):
    def __init__(self, reactor, log):
        self.reactor = reactor
        self.log = log
        self.last_activity = time.time()
        self.shutdown_delayed_call = self.reactor.callLater(300.0,
                                                            self.shutdown)

    def update(self):
        now = time.time()
        self.last_activity = now
        self.shutdown_delayed_call.reset(300.0)

    def shutdown(self):
        self.log.warning('watchdog shutting things down')
        self.reactor.stop()
