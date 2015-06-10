# -*- mode: python; coding: utf-8 -*-

from zope.interface import implements

from twisted.internet import defer
from twisted.internet import protocol
from twisted.web.iweb import IBodyProducer
from twisted.web.client import ResponseDone
from twisted.logger import Logger

class StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return defer.succeed(None)

    def pauseProducing(self):
        pass

    def resumeProducing(self):
        pass

    def stopProducing(self):
        pass

class GatherAndLog(protocol.Protocol):
    log = Logger()

    def __init__(self, finished = None, watchdog = None):
        self.buffer = ''
        self.finished = finished
        self.watchdog = watchdog

    def dataReceived(self, data):
        if self.watchdog is not None:
            self.watchdog.update()

        self.buffer += data

    def connectionLost(self, reason):
        if self.watchdog is not None:
            self.watchdog.update()

        if not isinstance(reason.value, ResponseDone):
            self.log.debug(reason)

        self.log.debug(self.buffer)

        if self.finished is not None:
            self.finished.callback(self.buffer)

class Gather(protocol.Protocol):
    log = Logger()

    def __init__(self, finished = None, watchdog = None):
        self.buffer = ''
        self.finished = finished
        self.watchdog = watchdog

    def dataReceived(self, data):
        if self.watchdog is not None:
            self.watchdog.update()

        self.buffer += data

    def connectionLost(self, reason):
        if self.watchdog is not None:
            self.watchdog.update()

        if not isinstance(reason.value, ResponseDone):
            self.log.debug(reason)

        if self.finished is not None:
            self.finished.callback(self.buffer)
