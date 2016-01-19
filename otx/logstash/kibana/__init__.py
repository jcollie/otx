# -*- mode: python; coding: utf-8 -*-

import json
from twisted.logger import Logger

log = Logger()
    
def parse_log_message(message):
    if message.get('systemd', {}).get('_SYSTEMD_UNIT', None) != 'kibana.service':
        return [], {}

    try:
        kibana = json.loads(message.get('message', 'null'))

        return ['kibana'], {'kibana': kibana}
    except ValueError:
        return [], {}
