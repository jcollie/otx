# -*- mode: python; coding: utf-8 -*-

import arrow
import ujson

es_timestamp_format = 'YYYY-MM-DDTHH:mm:ss.SSSZZ'

class Message(dict):
    @classmethod
    def loads(klass, json, prefix = None):
        message = klass()
        data = ujson.loads(json)
        if prefix is not None:
            data = {prefix: data}
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
        return ujson.dumps(self)

    boolean_conversions = {'true': True,
                           'yes': True,
                           'false': False,
                           'no': False}

    def convert_boolean(self, key):
        if self.__contains__(key):
            value = self.__getitem__(key).lower()
            if value in self.boolean_conversions:
                self.__setitem__(key, self.boolean_conversions[value])
