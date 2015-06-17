# -*- mode: python; coding: utf-8 -*-

import os
import socket

from twisted.internet import protocol
from twisted.internet import defer
from twisted.logger import Logger

class NotifyProtocol(protocol.ConnectedDatagramProtocol):
    log = Logger()

    def __init__(self, reactor):
        self.reactor = reactor
        self.when_connected = defer.Deferred()
        self.state = 'connecting'

    def startProtocol(self):
        self.state = 'connected'
        self.when_connected.callback(None)

    def stopProtocol(self):
        self.state = 'closed'

    def connectionFailed(self, failure):
        self.state = 'failed'
        if self.log is not None:
            self.log.debug('NOTIFY FAILED!: {}'.format(`failure`))

        self.when_connected.errback(failure)

    def datagramReceived(self, data):
        if self.log is not None:
            self.log.debug('Received data from notify socket: {}'.format(`data`))

class Notify(object):
    log = Logger()

    def __init__(self, reactor):
        self.reactor = reactor
        self.notify_socket_address = None
        self.notify_socket = None
        self.connection_attempts = 0

        if 'NOTIFY_SOCKET' in os.environ:
            self.notify_socket_address = os.environ['NOTIFY_SOCKET']
            if self.notify_socket_address.startswith('@'):
                self.notify_socket_address = '\0' + self.notify_socket_address[1:]

            self.connect()

    def connect(self, data = None):
        self.connection_attempts += 1

        if self.connection_attempts >= 10:
            if self.log is not None:
                self.log.error('Too many notification socket connection attempts: {}'.format(self.connection_attempts))
            return

        if self.notify_socket_address is None:
            if self.log is not None:
                self.log.error('No notification socket address!')
            return

        self.notify_socket = NotifyProtocol(self.reactor, self.log)

        self.notify_socket.when_connected.addCallback(self.when_connected_cb, data)

        self.reactor.connectUNIXDatagram(self.notify_socket_address, self.notify_socket)

    def when_connected_cb(self, result, data):
        self.connection_attempts = 0

        if data is not None:
            self.notify(data)

        return result

    def notify(self, data):
        if self.notify_socket_address is None:
            return

        elif self.notify_socket is None:
            self.connect(data)

        elif self.notify_socket.state == 'connected':
            try:
                self.notify_socket.transport.write(data)
            except socket.error as e:
                if self.log is not None:
                    self.log.err(e)
                self.connect(data)

        elif self.notify_socket.state == 'connecting':
            self.notify_socket.when_connected.addCallback(self.when_connected_cb, data)

        else:
            if self.log is not None:
                self.log.warning('Unable to send message because socket is in state: {}'.format(self.notify_socket.state))
            self.connect(data)

notifier = None

def startNotifier(reactor):
    global notifier
    if notifier is None:
        notifier = Notify(reactor)
    return notifier
