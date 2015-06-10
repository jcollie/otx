# -*- mode: python; coding: utf-8 -*-

import pkg_resources

from twisted.internet import defer
from twisted.internet import endpoints
from twisted.internet import protocol

import txamqp.protocol
import txamqp.client 
import txamqp.content
import txamqp.spec

class Factory(protocol.ClientFactory):
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
    NON_PERSISTENT = 1
    PERSISTENT = 2
    Content = txamqp.content.Content

    def __init__(self, reactor, log, hostname, port = 5672, ssl = False, vhost = '/', username = 'guest', password = 'guest'):
        self.reactor = reactor
        self.log = log

        spec = pkg_resources.resource_string(__name__, 'amqp0-9-1.stripped.xml')
        self.spec = txamqp.spec.loadString(spec)

        self.factory = Factory(vhost = vhost, spec = self.spec)

        self.credentials = {'LOGIN': username,
                            'PASSWORD': password}

        self.ssl = ssl
        self.hostname = hostname
        self.port = port

        #self.setup_never_finished = self.reactor.callLater(300.0, self.setupNeverFinished)
        self.reactor.callWhenRunning(self.start)

    def start(self):
        self.log.debug('connecting to AMQP broker {}:{}'.format(self.hostname, self.port))
        if self.ssl:
            self.endpoint = endpoints.clientFromString(self.reactor, 'ssl:host={}:port={}'.format(self.hostname, self.port))
        else:
            self.endpoint = endpoints.clientFromString(self.reactor, 'tcp:host={}:port={}'.format(self.hostname, self.port))
        d = self.endpoint.connect(self.factory)
        d.addCallback(self.gotConnection)
        d.addErrback(self.log.errback)
        
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
        self.setupFinished()

    def getReturnMessage(self):
        d = self.connection.basic_return_queue.get()
        d.addCallback(self.gotReturnMessage)

    def gotReturnMessage(self, message):
        self.reactor.callLater(0.0, self.getReturnMessage)
        self.log.error(`message`)