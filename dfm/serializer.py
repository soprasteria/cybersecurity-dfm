#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"Data Feed Manager json data custom serializer"

from memory_profiler import profile
import time
import datetime
class CustomSerializer:
    """ Custom JSON Serializer for date and bytes
    """
    def __init__(self,logger):
        self.logger=logger
    def to_json(self,python_object):
        """ convert python object to json
        """
        if isinstance(python_object, time.struct_time):
            #json serialize date cast or ES index fail
            return {'__class__': 'time.asctime',
                    '__value__': time.asctime(python_object)}

        if isinstance(python_object, datetime.datetime):
            #json serialize date with special date parser otherwise ES index fail
            return python_object.strftime('%Y-%m-%dT%H:%M:%SZ')

        raise TypeError(repr(python_object) + ' is not JSON serializable')

    def from_json(self,json_object):
        """ convert json object to python
        """
        if '__class__' in json_object:
            if json_object['__class__'] == 'time.asctime':
                return time.strptime(json_object['__value__'])
            if json_object['__class__'] == 'bytes':
                return bytes(json_object['__value__'])
        return json_object
