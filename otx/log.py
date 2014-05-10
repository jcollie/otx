#! -*- mode: python; coding: utf-8 -*-

from __future__ import absolute_import

import sys

stdout_write = sys.stdout.write
stdout_flush = sys.stdout.flush
stderr_write = sys.stderr.write
stderr_flush = sys.stderr.flush

from twisted.internet import protocol
from twisted.internet import defer
from twisted.python import util
from twisted.python import failure

import twisted.python.log

import os
import re
import struct
import inspect
import traceback

EMERGENCY, ALERT, CRITICAL, ERROR, WARNING, NOTICE, INFORMATIONAL, DEBUG = range(8)
TRACE = DEBUG
INFO = INFORMATIONAL

class JournalClientProtocol(protocol.ConnectedDatagramProtocol):
    def __init__(self, reactor):
        self.reactor = reactor
        self.running = False

    def startProtocol(self):
        self.running = True

    def stopProtocol(self):
        self.running = False

    def datagramReceived(self, data):
        pass

class JournalMessage(object):
    name_re = re.compile(r'[A-Z0-9][_A-Z0-9]*')
    binary_re = re.compile(r'[^\x20-\x7f]')

    converters = {'PRIORITY': lambda priority: '{:d}'.format(priority),
                  'CODE_LINE': lambda priority: '{:d}'.format(priority)}

    def __init__(self):
        self.data = b''

    def add(self, name, value):
        match = self.name_re.match(name)
        if not match:
            raise RuntimeException('bad name!')

        self.data += bytes(name)

        if name in self.converters:
            value = self.converters[name](value)

        else:
            value = value.encode('utf-8')

        match = self.binary_re.search(value)
        if match:
            self.data += '\n'
            self.data += struct.pack('<Q', len(value))
            self.data += value
            self.data += '\n'

        else:
            self.data += '='
            self.data += value
            self.data += '\n'

class JournalObserver(object):
    def __init__(self, reactor, priority, appname = None):
        self.reactor = reactor
        self.priority = priority
        self.appname = appname

        self.journal = JournalClientProtocol(self.reactor)

        self.reactor.connectUNIXDatagram('/run/systemd/journal/socket',
                                         self.journal)

    def emit(self, event):
        global stdout_write
        global stdout_flush
        global stderr_write
        global stderr_flush

        message = JournalMessage()
        
        if 'MESSAGE_ID' in event and event['MESSAGE_ID'] is not None:
            message.add('MESSAGE_ID', event['MESSAGE_ID'])

        if 'CODE_FILE' in event and event['CODE_FILE'] is not None:
            message.add('CODE_FILE', event['CODE_FILE'])

        if 'CODE_LINE' in event and event['CODE_LINE'] is not None:
            message.add('CODE_LINE', event['CODE_LINE'])

        if 'CODE_FUNC' in event and event['CODE_FUNC'] is not None:
            message.add('CODE_FUNC', event['CODE_FUNC'])

        if 'SYSLOG_IDENTIFIER' not in event and self.appname is not None:
            message.add('SYSLOG_IDENTIFIER', self.appname)

        if event.has_key('PRIORITY'):
            if event['PRIORITY'] is None:
                event['PRIORITY'] = DEBUG

            elif event['PRIORITY'] not in range(8):
                event['PRIORITY'] = DEBUG

        elif event.get('isError'):
            event['PRIORITY'] = ERROR

        else:
            event['PRIORITY'] = DEBUG

        message.add('PRIORITY', event['PRIORITY'])

        text = twisted.python.log.textFromEventDict(event)
        if text is None:
            return

        text = text.rstrip()
        text = text.expandtabs()

        message.add('MESSAGE', text)

        if self.journal.running:
            self.journal.transport.write(message.data)

        if not self.journal.running or 'SHLVL' in os.environ:
            text += '\n'
            text = text.encode('utf-8')
            util.untilConcludes(stderr_write, text)
            util.untilConcludes(stderr_flush)

        if event['PRIORITY'] <= CRITICAL:
            self.reactor.stop()

def introspect(func):
    def _introspect(*args, **kw):
        if ('CODE_FILE' not in kw or
            'CODE_LINE' not in kw or
            'CODE_FUNC' not in kw):
            (kw['CODE_FILE'],
             kw['CODE_LINE'],
             kw['CODE_FUNC']) = inspect.stack()[1][1:4]
        func(*args, **kw)
    return _introspect

class Logger(object):
    def __init__(self, reactor, priority, appname = None):
        self.reactor = reactor
        self.priority = priority

        if appname is None:
            appname = os.path.basename(sys.argv[0])
            if appname == '':
                appname = 'unknown'

        self.appname = appname

        self.observer = JournalObserver(self.reactor, self.priority, self.appname)

        twisted.python.log.msg = self.msg
        twisted.python.log.err = self.err
        #twisted.python.log.startLoggingWithObserver(self.observer.emit,
        #                                            setStdout = 1)

        if twisted.python.log.defaultObserver:
            twisted.python.log.defaultObserver.stop()
            twisted.python.log.defaultObserver = None
        twisted.python.log.addObserver(self.observer.emit)
        sys.stdout = twisted.python.log.logfile
        sys.stderr = twisted.python.log.logerr

    @introspect
    def msg(self, *args, **kw):
        if 'PRIORITY' not in kw:
            kw['PRIORITY'] = DEBUG
        twisted.python.log.theLogPublisher.msg(*args, **kw)

    @introspect
    def err(self, _stuff = None, _why = None, **kw):
        if _stuff is None:
            _stuff = failure.Failure()
        if isinstance(_stuff, failure.Failure):
            self.msg(failure = _stuff, why = _why, isError = 1, **kw)
        elif isinstance(_stuff, Exception):
            self.msg(failure = failure.Failure(_stuff), why = _why, isError = 1, **kw)
        else:
            self.msg(repr(_stuff), why = _why, isError = 1, **kw)
     
    @introspect
    def debug(self, *message, **kw):
        kw['PRIORITY'] = DEBUG
        self.msg(*message, **kw)

    trace = debug

    @introspect
    def informational(self, *message, **kw):
        kw['PRIORITY'] = INFORMATIONAL
        self.msg(*message, **kw)

    info = informational

    @introspect
    def notice(self, *message, **kw):
        kw['PRIORITY'] = NOTICE
        self.msg(*message, **kw)

    @introspect
    def warning(self, *message, **kw):
        kw['PRIORITY'] = WARNING
        self.msg(*message, **kw)

    @introspect
    def error(self, *message, **kw):
        kw['PRIORITY'] = ERROR
        self.msg(*message, **kw)

    @introspect
    def critical(self, *message, **kw):
        kw['PRIORITY'] = CRITICAL
        self.msg(*message, **kw)

    @introspect
    def alert(self, *message, **kw):
        kw['PRIORITY'] = ALERT
        self.msg(*message, **kw)

    @introspect
    def emergency(self, *message, **kw):
        kw['PRIORITY'] = EMERGENCY
        self.msg(*message, **kw)

    @introspect
    def errback(self, failure, *args, **kw):
        if 'PRIORITY' not in kw:
            kw['PRIORITY'] = CRITICAL
        self.err(failure, **kw)

logger = None

def startLogging(reactor, priority = DEBUG, appname = None):
    global logger

    if logger is None:
        logger = Logger(reactor, priority, appname)

    return logger
