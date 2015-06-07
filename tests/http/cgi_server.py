#!/usr/bin/env python
"""Serve the test files for requests testing
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals
import os
from six.moves.CGIHTTPServer import CGIHTTPRequestHandler
from six.moves.BaseHTTPServer import HTTPServer

def start_webserver():
    """Start the webserver.
    """
    path = os.path.dirname(__file__)
    os.chdir(path)
    server_address = ("127.0.0.1", 0)
    httpd = HTTPServer(server_address, CGIHTTPRequestHandler)
    print("http://127.0.0.1:%d" % httpd.server_port)
    httpd.serve_forever()

start_webserver()
