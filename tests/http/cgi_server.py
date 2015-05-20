#!/usr/bin/env python

import os
from six.moves.CGIHTTPServer import CGIHTTPRequestHandler
from six.moves.BaseHTTPServer import HTTPServer
import sys

def start_webserver(port=8001):
    path = os.path.dirname(__file__)
    os.chdir(path)
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, CGIHTTPRequestHandler)
    httpd.serve_forever()

start_webserver()
