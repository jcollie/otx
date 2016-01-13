# -*- mode: python; coding: utf-8 -*-

import re
from twisted.logger import Logger

log = Logger()

exim_id_re = re.compile(r'\A(?P<id>[A-Za-z0-9]{6}-[A-Za-z0-9]{6}-[A-Za-z0-9]{2})\s*(?P<rest>.*)\Z', re.DOTALL | re.MULTILINE)

exim_sender_re = re.compile(r'\A<= (?P<sender>[^ ]+) ', re.DOTALL | re.MULTILINE)
exim_recipient_re = re.compile(r'\A(?:=>|\*\*) (?P<recipient>[^ ]+)(?: <(?P<recipient_original>[^ ]+)>)?', re.DOTALL | re.MULTILINE)

exim_confirmation_re = re.compile(r'(?:C="(?P<confirmation>[^"]+)")', re.DOTALL | re.MULTILINE)
exim_remote_host_re = re.compile(r'H=(?:(?<!\()(?P<remote_hostname>[^ ()]+)(?!\)) )?(?:\((?P<remote_heloname>[^ ]+)\) )?\[(?P<remote_address>[^ ]+)\]', re.DOTALL | re.MULTILINE)
exim_i_re = re.compile(r'(?:I=\[(?P<local_address>[^ ]+)\](?::(?P<local_port>\d+))?)', re.DOTALL | re.MULTILINE)
exim_message_id_re = re.compile(r'(?:id=(?P<message_id>[^ ]+))', re.DOTALL | re.MULTILINE)
exim_p_re = re.compile(r'(?:P=(?P<protocol>[^ ]+))', re.DOTALL | re.MULTILINE)
exim_reference_re = re.compile(r'(?:R=(?P<reference>[A-Za-z0-9]{6}-[A-Za-z0-9]{6}-[A-Za-z0-9]{2}))', re.DOTALL | re.MULTILINE)
exim_router_re = re.compile(r'(?:R=(?P<router>[^ ]+))', re.DOTALL | re.MULTILINE)
exim_size_re = re.compile(r'(?:S=(?P<size>\d+))', re.DOTALL | re.MULTILINE)
exim_transport_re = re.compile(r'(?:T=(?P<transport>[^ ]+))', re.DOTALL | re.MULTILINE)
exim_u_re = re.compile(r'(?:U=(?P<user>[^ ]+))', re.DOTALL | re.MULTILINE)
exim_x_re = re.compile(r'(?:X=(?P<tls>[^ ]+))', re.DOTALL | re.MULTILINE)
exim_cv_re = re.compile(r'(?:CV=(?P<certificate_verified>[^ ]+))', re.DOTALL | re.MULTILINE)
exim_smtp_error_re = re.compile(r'(?:: SMTP error from remote mail server after (?P<smtp_command>.*): host (?P<remote_hostname>[^ ]+) \[(?P<remote_address>[^ ]+)\]: (?P<smtp_error>\d{3}.*))\Z', re.DOTALL | re.MULTILINE)
exim_rte_error_re = re.compile(r': retry timeout exceeded\Z', re.DOTALL | re.MULTILINE)
exim_unroutable_error_re = re.compile(r': Unrouteable address\Z', re.DOTALL | re.MULTILINE)
exim_no_smtp_error_re = re.compile(r': an MX or SRV record indicated no SMTP service\Z', re.DOTALL | re.MULTILINE)
exim_no_mx_error_re = re.compile(r': all relevant MX records point to non-existent hosts\Z', re.DOTALL | re.MULTILINE)
exim_reverse_re = re.compile(r'\Ano host name found for IP address (?P<remote_address>[^ ]+)\Z', re.DOTALL | re.MULTILINE)
    
def parse_log_message(message):
    exim = {}
    match = exim_id_re.match(message)
    if not match:
        exim['unparsed'] = 1

        match = exim_reverse_re.match(message)
        if match:
            exim['unparsed'] = 0
            exim['remote_address'] = match.group('remote_address')

        return ['exim'], {'exim': exim}

    exim['id'] = match.group('id')
    message = match.group('rest')

    if message.startswith('<='):
        exim['flags'] = '<='
        exim['category'] = 'received'
        exim['unparsed'] = 0

        for regex in [exim_sender_re, exim_reference_re, exim_remote_host_re, exim_size_re, exim_i_re, exim_x_re, exim_p_re, exim_u_re, exim_message_id_re]:
            match = regex.search(message)
            if match:
                for key, value in match.groupdict().items():
                    if value is not None:
                        exim[key] = value
                message = message[:match.start()] + message[match.end():]

        if message.strip():
            log.debug('something not parsed: {message:}', message = message)
            exim['unparsed'] = 1

    elif message.startswith('=>'):
        exim['flags'] = '=>'
        exim['category'] = 'delivery_successful'
        exim['unparsed'] = 0

        for regex in [exim_recipient_re, exim_confirmation_re, exim_router_re, exim_transport_re, exim_message_id_re, exim_remote_host_re, exim_x_re, exim_cv_re]:
            match = regex.search(message)
            if match:
                for key, value in match.groupdict().items():
                    if value is not None:
                        exim[key] = value
                message = message[:match.start()] + message[match.end():]

        if message.strip():
            log.debug('something not parsed: {message:}', message = message)
            exim['unparsed'] = 1

    elif message.startswith('->'):
        exim['flags'] = '->'
        exim['category'] = 'delivery_successful'
        exim['unparsed'] = 1

    elif message.startswith('>>'):
        exim['flags'] = '>>'
        exim['category'] = 'delivery_successful'
        exim['unparsed'] = 1

    elif message.startswith('*>'):
        exim['flags'] = '*>'
        exim['category'] = 'delivery_unsuccessful'
        exim['unparsed'] = 1

    elif message.startswith('**'):
        exim['flags'] = '**'
        exim['category'] = 'delivery_unsuccessful'
        exim['unparsed'] = 0

        match = exim_smtp_error_re.search(message)
        if match:
            for key, value in match.groupdict().items():
                if value is not None:
                    exim[key] = value
            if 'smtp_error' in exim:
                exim['smtp_error'] = exim['smtp_error'].replace('\\n', '\n')
            message = message[:match.start()] + message[match.end():]

        match = exim_rte_error_re.search(message)
        if match:
            exim['error'] = 'retry timeout exceeded'
            message = message[:match.start()] + message[match.end():]

        match = exim_unroutable_error_re.search(message)
        if match:
            exim['error'] = 'unroutable address'
            message = message[:match.start()] + message[match.end():]

        match = exim_no_smtp_error_re.search(message)
        if match:
            exim['error'] = 'an MX or SRV record indicated no SMTP service'
            message = message[:match.start()] + message[match.end():]

        match = exim_no_mx_error_re.search(message)
        if match:
            exim['error'] = 'all relevant MX records point to non-existent hosts'
            message = message[:match.start()] + message[match.end():]

        for regex in [exim_recipient_re, exim_router_re, exim_transport_re, exim_x_re]:
            match = regex.search(message)
            if match:
                for key, value in match.groupdict().items():
                    if value is not None:
                        exim[key] = value
                message = message[:match.start()] + message[match.end():]

        if message.strip():
            log.debug('something not parsed: {message:}', message = message)
            exim['unparsed'] = 1

    elif message.startswith('=='):
        exim['flags'] = '=='
        exim['category'] = 'delivery_delayed'
        exim['unparsed'] = 1

    else:

        exim['category'] = 'other'
        exim['unparsed'] = 1

    return ['exim'], {'exim': exim}
