# -*- mode: python; coding: utf-8 -*-

import pkg_resources

from twisted.internet import defer
from twisted.internet import endpoints
from twisted.internet import protocol
from twisted.logger import Logger

import txamqp.protocol
import txamqp.client 
import txamqp.content
import txamqp.spec

class Factory(protocol.ClientFactory):
    log = Logger()
    noisy = False

    def __init__(self, vhost, spec):
        self.vhost = vhost
        self.spec = spec

    def startFactory(self):
        pass

    def stopFactory(self):
        pass

    def buildProtocol(self, addr):
        return txamqp.protocol.AMQClient(delegate = txamqp.client.TwistedDelegate(),
                                         vhost = self.vhost,
                                         spec = self.spec)

class Client(object):
    log = Logger()
    
    NON_PERSISTENT = 1
    PERSISTENT = 2
    Content = txamqp.content.Content

    def __init__(self, reactor, hostname, port = 5672, ssl = False, crt = None, vhost = '/', username = 'guest', password = 'guest'):
        self.reactor = reactor

        spec = pkg_resources.resource_string(__name__, 'amqp0-9-1.stripped.xml')
        self.spec = txamqp.spec.loadString(spec)

        self.factory = Factory(vhost = vhost, spec = self.spec)

        self.credentials = {'LOGIN': username,
                            'PASSWORD': password}

        self.ssl = ssl
        self.crt = crt
        self.hostname = hostname
        self.port = port

        self.setup_never_finished = self.reactor.callLater(60.0, self.setupNeverFinished)
        self.reactor.callWhenRunning(self.start)

    def start(self):
        self.log.debug('connecting to AMQP broker {h:}:{p:}', h = self.hostname, p = self.port)
        if self.ssl:
            endpoint = 'ssl:host={}:port={}'.format(self.hostname, self.port)
            if self.crt is not None:
                endpoint += ':certKey={}:privateKey={}'.format(self.crt, self.crt)
        else:
            endpoint = 'tcp:host={}:port={}'.format(self.hostname, self.port)
        self.log.debug('connecting to {e:}', e = endpoint)
        self.endpoint = endpoints.clientFromString(self.reactor, endpoint)
        d = self.endpoint.connect(self.factory)
        d.addCallback(self.gotConnection)
        #d.addErrback(self.errConnection)
        
    def gotConnection(self, connection):
        self.log.debug('got connection, logging in')
        self.connection = connection
        d = self.connection.start(self.credentials)
        d.addCallback(self.connectionStarted)

    def connectionStarted(self, _):
        self.log.debug('connection started')
        d = self.connection.channel(1)
        d.addCallback(self.gotChannel)

    def gotChannel(self, channel):
        self.log.debug('got channel, opening')
        self.channel = channel
        d = self.channel.channel_open()
        d.addCallback(self.channelOpened)

    def channelOpened(self, _):
        self.log.debug('channel opened')
        self.reactor.callLater(0.0, self.getReturnMessage)
        self.setup_never_finished.cancel()
        self.setupFinished()

    def getReturnMessage(self):
        d = self.connection.basic_return_queue.get()
        d.addCallback(self.gotReturnMessage)

    def gotReturnMessage(self, message):
        self.reactor.callLater(0.0, self.getReturnMessage)
        self.log.error(`message`)
