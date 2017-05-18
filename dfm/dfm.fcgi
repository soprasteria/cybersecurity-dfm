#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import sys,os
from flup.server.fcgi import WSGIServer
sys.path.insert(0, '/opt/dfm/dfm')
from server import app

if __name__ == '__main__':
    WSGIServer(app).run()
