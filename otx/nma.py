# -*- mode: python; coding: utf-8 -*-

from __future__ import absolute_import

from twisted.web.client import Agent
from twisted.web.client import _HTTP11ClientFactory
from twisted.web.client import HTTPConnectionPool
from twisted.web.http_headers import Headers

from twisted.internet import defer

class QuietHTTP11ClientFactory(_HTTP11ClientFactory):
    noisy = False

import urllib

from .tbq import TokenBucketQueue
from .utils import StringProducer
from .utils import GatherAndLog

class NMA(object):
    def __init__(self, reactor, log, application, watchdog = None):
        self.reactor = reactor
        self.log = log
        self.application = application
        self.watchdog = watchdog

        self.pool = HTTPConnectionPool(self.reactor, persistent = True)
        self.pool.maxPersistentPerHost = 1
        self.pool._factory = QuietHTTP11ClientFactory
        self.agent = Agent(self.reactor, pool = self.pool)

        self.tbq = TokenBucketQueue(self.reactor, 1.0, 2.0)
        self.reactor.callWhenRunning(self._getRequest)

    def _getRequest(self):
        d = self.tbq.get()
        d.addCallback(self._sendRequest)

    def _sendRequest(self, result):
        self.reactor.callLater(0.0, self._getRequest)
        if self.watchdog is not None:
            self.watchdog.update()
        finished, data = result
        body = urllib.urlencode(data)
        d = self.agent.request('POST',
                               'https://www.notifymyandroid.com/publicapi/notify',
                               Headers({'User-Agent': [self.application],
                                        'Content-Type': ['application/x-www-form-urlencoded']}),
                               StringProducer(body))
        d.addCallback(self._processResponse, finished)
        d.addErrback(self.log.errback)

    def _processResponse(self, response, finished):
        self.log.msg('NotifyMyAndroid notification resulted in response code {}'.format(response.code))
        response.deliverBody(GatherAndLog(self.log, finished = finished, watchdog = self.watchdog))

    def sendNotifications(self, apikeys, event, description, priority = 0):
        self.log.debug('Sending NotifyMyAndroid notifications')

        if not apikeys:
            self.log.debug('No NotifyMyAndroid API keys to send to!')
            return defer.suceed(None)

        finished = defer.Deferred()

        data = {'apikey': ','.join(apikeys),
                'application': self.application.encode('utf-8'),
                'event': event.encode('utf-8'),
                'description': description.encode('utf-8'),
                'priority': priority}

        self.tbq.put((finished, data))

        return finished
