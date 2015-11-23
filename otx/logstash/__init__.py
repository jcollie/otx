# -*- mode: python; coding: utf-8 -*-

import arrow
import json

es_timestamp_format = 'YYYY-MM-DDTHH:mm:ss.SSSZZ'

class InnerMessage(dict):
    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def dumps(self):
        return json.dumps(self)

    boolean_conversions = {'false': False,
                           'no': False,
                           'off': False,
                           '0': False,
                           '': False,
                           0: False,
                           0.0: False}

    def convert_boolean(self, key):
        if self.__contains__(key):
            value = self.__getitem__(key).lower()
            if value in self.boolean_conversions:
                self.__setitem__(key, self.boolean_conversions[value])
            else:
                self.__setitem__(key, True)

class Message(dict):
    @classmethod
    def loads(klass, data, prefix = None):
        message = klass()
        data = json.loads(data)
        if prefix is not None:
            data = {prefix: InnerMessage(data)}
        message.update(data)
        return message

    def __init__(self, *args, **kwargs):
        dict.__setitem__(self, '@version', 1)

        if 'timestamp' in kwargs:
            dict.__setitem__(self, '@timestamp', kwargs.pop('timestamp'))
        else:
            dict.__setitem__(self, '@timestamp', arrow.now().format(es_timestamp_format))

        if 'tags' in kwargs:
            dict.__setitem__(self, 'tags', kwargs.pop('tags'))
        else:
            dict.__setitem__(self, 'tags', [])

        self.update(*args, **kwargs)

    def dumps(self):
        return json.dumps(self)

    boolean_conversions = {'false': False,
                           'no': False,
                           'off': False,
                           '0': False,
                           '': False,
                           0: False,
                           0.0: False}

    def convert_boolean(self, key):
        if self.__contains__(key):
            value = self.__getitem__(key).lower()
            if value in self.boolean_conversions:
                self.__setitem__(key, self.boolean_conversions[value])
            else:
                self.__setitem__(key, True)
