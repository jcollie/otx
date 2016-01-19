# -*- mode: python; coding: utf-8 -*-

import json
from twisted.logger import Logger

log = Logger()
    
def parse_log_message(message):
    try:
        kibana = json.loads(message)

        return ['kibana'], {'kibana': kibana}
    except ValueError:
        return [], {}
