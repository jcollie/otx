# -*- mode: python; coding: utf-8 -*-

named_re_1 = re.compile(r'\Aqueries: (?P<severity>critical|error|warning|notice|info|debug \d+|dynamic): client (?P<source_address>.*)#(?P<source_port>\d+) \((?P<name>.*)\): query: (?P=name) (?P<class>IN) (?P<type>.*) (?P<recursion_desired>[+-])?(?P<signed>S)?(?P<edns>E)?(?P<tcp>T)?(?P<dnssec_ok>D)?(?P<checking_disabled>C)? \((?P<destination_address>.*)\)\Z', re.DOTALL | re.MULTILINE | re.IGNORECASE)

def parse_log_message(message):
    dns_query = {}
    
    match = named_re_1.match(message)
    if match:
        #message['tags'].append('dns_query')
        for k, v in match.groupdict().items():
            if k == 'source_port':
                v = int(v)
            if k == 'recursion_desired':
                if v == '+':
                    v = True
                if v == '-':
                    v = False
            if k == 'signed':
                if v == 'S':
                    v = True
                else:
                    v = False
            if k == 'edns':
                if v == 'E':
                    v = True
                else:
                    v = False
            if k == 'tcp':
                if v == 'T':
                    v = True
                else:
                    v = False
            if k == 'dnssec_ok':
                if v == 'D':
                    v = True
                else:
                    v = True
            if k == 'checking_disabled':
                if v == 'C':
                    v = True
                else:
                    v = False
            if v is not None:
                dns_query[k] = v
    return ['dns_query'], {'dns_query': dns_query}
