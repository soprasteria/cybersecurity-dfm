#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"Data Feed Manager WSGI for Web Server binding"
import sys,os
sys.path.insert(0, '/opt/dfm/dfm')
#os.chdir("/opt/dfm/dfm")
from server import app as application
