# -*- mode: python; coding: utf-8 -*-

import re
import arrow

class Syslog(object):
    syslog_re = re.compile(r'\A<(?P<priority>\d{1,3})>(?P<message>.*)\Z',
                           re.MULTILINE, re.DOTALL, re.IGNORECASE)
    
    facility_labels = ['kernel',
                       'user-level',
                       'mail',
                       'daemon',
                       'security/authorization',
                       'syslogd',
                       'line printer',
                       'network news',
                       'uucp',
                       'clock',
                       'security/authorization',
                       'ftp',
                       'ntp',
                       'log audit',
                       'log alert',
                       'clock',
                       'local0',
                       'local1',
                       'local2',
                       'local3',
                       'local4',
                       'local5',
                       'local6',
                       'local7']

    severity_labels = ['emergency',
                       'alert',
                       'critical',
                       'error',
                       'warning',
                       'notice',
                       'informational',
                       'debug']

    def convert_priority(self, priority):
        if isinstance(priority, basestring):
            priority = int(priority)

        severity = priority & 0x7
        facility = priority >> 3

        result = {}
        result.update(self.convert_severity(severity))
        result.update(self.convert_facility(facility))

        return result

    def convert_severity(self, severity):
        if isinstance(severity, basestring):
            severity = int(severity)

        return {'syslog_severity_code': severity,
                'syslog_severity': self.severity_labels[severity]}

    def convert_facility(self, facility):
        if isinstance(facility, basestring):
            facility = int(facility)

        return {'syslog_facility_code': facility,
                'syslog_facility': self.facility_labels[facility]}

    def parse_message(self, message):
        result = {}
        
        match = self.syslog_re.match(message)
        if match:
            result.update(self.convert_priority(match.group('priority')))
            result['message'] = match.message()

        return result

class SyslogDatagramProtocol(DatagramProtocol, Syslog):
    noisy = False

    def __init__(self, reactor, log, queue):
        self.reactor = reactor
        self.log = log
        self.queue = queue
        
    def startProtocol(self):
        pass

    def datagramReceived(self, datagram, address):
        now = arrow.now().format(timestamp_format)
        result = self.parse_message(datagram)
        result['timestamp'] = now
        result['binary_message'] = datagram.encode('base64')

        if ':' in address.host:
            result['received_from'] = '[{}]:{}'.format(address.host,
                                                       address.port)
        else:
            result['received_from'] = '{}:{}'.format(address.host,
                                                     address.port)
        result['remote_host'] = address.host
        result['remote_port'] = address.port
        
        self.queue.put(result)
    
class SyslogStreamProtocol(LineReceiver, Syslog):
    noisy = False
    delimiter = '\n'

    def __init__(self, reactor, log, queue):
        self.reactor = reactor
        self.log = log

    def connectionMade(self):
        log.msg('connection made')

        host = self.transport.getHost()
        self.syslog_address = host.host
        self.syslog_port = host.port

        peer = self.transport.getPeer()
        self.remote_address = peer.host
        self.remote_port = peer.port
        if ':' in peer.host:
            self.received_from = '[{}]:{}'.format(peer.host, peer.port)
        else:
            self.received_from = '{}:{}'.format(peer.host, peer.port)

    def connectionLost(self, reason):
        #log.err(reason)
        log.msg('connection lost')

    def lineReceived(self, line):
        now = arrow.now().format(es_timestamp_format)
        message = Message(timestamp = now,
                          sequence = self.sequence,
                          received_at = now,
                          host = self.remote_address,
                          remote_address = self.remote_address,
                          remote_port = self.remote_port,
                          syslog_host = self.syslog_host,
                          syslog_address = self.syslog_address,
                          syslog_protocol = 'tcp',
                          syslog_port = self.syslog_port,
                          tags = ['syslog'],
                          message = line.decode('utf-8', errors='replace'),
                          binary_message = line.encode('base64'))
        self.input_queue.put(message)
        self.sequence += 1
        
class SyslogDatagram(object):
    def __init__(self, reactor, log, port):
        self.reactor = reactor
        self.log = log
        self.port = port

        self.reactor.callWhenRunning(self.start)

    def self.start(self):
        self.prototocl = SyslogDatagramProtocol(self.reactor, self.log)
        self.reactor.listenUDP(self.port, self.protocol)
        
