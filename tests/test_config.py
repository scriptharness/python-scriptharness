#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/config.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import scriptharness.config as shconfig
import unittest


# TestUrlFunctions {{{1
class TestUrlFunctionss(unittest.TestCase):
    """Test url functions
    """
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
