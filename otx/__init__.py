# -*- mode: python; coding: utf-8 -*-

from __future__ import absolute_import

def setup(appname):
    from twisted.internet import reactor

    from .log import startLogging
    log = startLogging(reactor, appname=appname)

    from .notify import startNotifier
    notifier = startNotifier(reactor, log)

    return reactor, log, notifier
