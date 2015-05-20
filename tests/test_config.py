#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/config.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
from contextlib import contextmanager
import os
import requests
import scriptharness.config as shconfig
import subprocess
import sys
import time
import unittest


TEST_FILE = '_test_config_file'
TEST_FILE2 = '_test_config_file2'

def nuke_test_files():
    """Cleanup helper function"""
    for path in TEST_FILE, TEST_FILE2:
        if os.path.exists(path):
            os.remove(path)

@contextmanager
def start_webserver():
    """Start a webserver for local requests testing
    """
    port = 8001  # TODO get free port
    max_wait = 5
    wait = 0
    interval = .02
    host = "http://localhost:%s" % str(port)
    dir_path = os.path.join(os.path.dirname(__file__), 'http')
    file_path = os.path.join(dir_path, 'cgi_server.py')
    proc = subprocess.Popen([sys.executable, file_path],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while wait < max_wait:
        try:
            response = requests.get(host)
            if response.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(interval)
        wait += interval
    try:
        yield (dir_path, host)
    finally:
        proc.terminate()

# TestUrlFunctions {{{1
class TestUrlFunctionss(unittest.TestCase):
    """Test url functions
    """
    def setUp(self):
        assert self  # silence pylint
        nuke_test_files()

    def tearDown(self):
        assert self  # silence pylint
        nuke_test_files()

    def test_basic_url_filename(self):
        """Filename from a basic url"""
        url = "http://example.com/bar/baz"
        self.assertEqual(shconfig.get_filename_from_url(url), "baz")

    def test_no_path(self):
        """Filename from a url without a path"""
        url = "https://example.com"
        self.assertEqual(shconfig.get_filename_from_url(url), "example.com")

    def test_is_url(self):
        """Verify is_url(real_url)"""
        for url in ("http://example.com", "https://example.com/foo/bar",
                    "file:///home/example/.bashrc"):
            self.assertTrue(shconfig.is_url(url))

    def test_is_not_url(self):
        """Verify not is_url(real_url)"""
        for url in ("example.com", "/usr/local/bin/python"):
            print(url)
            self.assertFalse(shconfig.is_url(url))

    def test_successful_download_url(self):
        """Download a file from a local webserver.
        """
        with start_webserver() as (path, host):
            with open(os.path.join(path, "test_config.json")) as filehandle:
                orig_contents = filehandle.read()
            shconfig.download_url("%s/test_config.json" % host)
        with open("test_config.json") as filehandle:
            contents = filehandle.read()
        os.remove("test_config.json")
        self.assertEqual(contents, orig_contents)
