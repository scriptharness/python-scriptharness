#!/usr/bin/env python
"""Serve the test files for requests testing
"""

import os
from six.moves.CGIHTTPServer import CGIHTTPRequestHandler
from six.moves.BaseHTTPServer import HTTPServer

def start_webserver(port=8001):
    """Start the webserver.

    Args:
      port (int): The port to attach to
    """
    path = os.path.dirname(__file__)
    os.chdir(path)
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, CGIHTTPRequestHandler)
    httpd.serve_forever()

start_webserver()
