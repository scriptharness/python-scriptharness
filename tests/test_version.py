#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/__init__.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import json
import os
import scriptharness.version
import six
import subprocess
import sys
import unittest


TEST_VERSION_JSON = "_test_version.json"
def cleanup():
    """cleanliness"""
    if os.path.exists(TEST_VERSION_JSON):
        os.remove(TEST_VERSION_JSON)

class TestVersionString(unittest.TestCase):
    """Test the various semver version->version string conversions
    """
    def setUp(self):
        """cleanliness"""
        assert self  # silence pylint
        cleanup()

    def tearDown(self):
        """cleanliness"""
        assert self  # silence pylint
        cleanup()

    def test_three_version(self):
        """test_version | 3 digit tuple -> version string
        """
        test_dict = {
            '0.1.0': (0, 1, 0),
            '1.2.3': (1, 2, 3),
            '4.1.5': (4, 1, 5),
        }
        for key, value in test_dict.items():
            self.assertEqual(
                scriptharness.version.get_version_string(value), key
            )

    def test_illegal_three_version(self):
        """test_version | Raise if a 3-len tuple has a non-digit
        """
        self.assertRaises(
            TypeError, scriptharness.version.get_version_string,
            (('one', 'two', 'three'))
        )

    def test_four_version(self):
        """test_version | 3 digit + string tuple -> version string
        """
        self.assertEqual(
            scriptharness.version.get_version_string((0, 1, 0, 'alpha')),
            '0.1.0-alpha'
        )

    def test_illegal_len_version(self):
        """test_version | Raise if len(version) not in (3, 4)
        """
        test_versions = (
            (0, ),
            (0, 1),
            (0, 1, 0, 'alpha', 'beta'),
        )
        for version in test_versions:
            self.assertRaises(
                Exception,
                scriptharness.version.get_version_string, (version, )
            )

    def helper_write_version(self, function, *args, **kwargs):
        """Help test write_version
        """
        parent_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)))
        version_json = os.path.join(parent_dir, 'version.json')
        function(*args, **kwargs)
        self.assertTrue(os.path.exists(version_json))
        self.assertTrue(os.path.exists(TEST_VERSION_JSON))
        with open(version_json) as filehandle:
            contents = json.load(filehandle)
        with open(TEST_VERSION_JSON) as filehandle:
            contents2 = json.load(filehandle)
        self.assertEqual(contents, contents2)

    @unittest.skipIf(
        os.name == 'nt' and six.PY3,
        "OSError: [WinError 6] The handle is invalid"
    )
    def test_run_version_py(self):
        """test_version | run version.py
        """
        if os.name == 'nt':
            command = [sys.executable]
        else:
            command = [
                os.path.join(os.path.dirname(sys.executable), "coverage"),
                "run", "-a", "--branch",
            ]
        parent_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)))
        version_py = os.path.join(parent_dir, 'scriptharness', 'version.py')
        version_json = os.path.join(parent_dir, 'version.json')
        try:
            os.rename(version_json, TEST_VERSION_JSON)
            self.helper_write_version(subprocess.call, command + [version_py])
        finally:
            if os.path.exists(version_json):
                os.remove(version_json)
            os.rename(TEST_VERSION_JSON, version_json)


    def test_write_version(self):
        """test_version | write_version()
        """
        self.helper_write_version(scriptharness.version.write_version,
                                  name='__main__', path=TEST_VERSION_JSON)
        self.helper_write_version(scriptharness.version.write_version,
                                  path=TEST_VERSION_JSON)
