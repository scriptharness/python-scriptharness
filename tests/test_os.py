#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/os.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import mock
import os
import scriptharness.os as sh_os
import shutil
import unittest
from . import LoggerReplacement

TEST_DIR = "this_dir_should_not_exist"


def cleanup():
    """Cleanliness"""
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)

class TestFunctions(unittest.TestCase):
    """Test the command functions
    """
    def setUp(self):
        """Cleanliness"""
        assert self  # silence pylint
        cleanup()

    def tearDown(self):
        """Cleanliness"""
        assert self  # silence pylint
        cleanup()

    @mock.patch('scriptharness.commands.os.logging')
    def test_makedirs(self, mock_logging):
        """test_commands_os | make_parent_dir()
        """
        logger = LoggerReplacement()
        mock_logging.getLogger.return_value = logger
        self.assertFalse(os.path.exists(TEST_DIR))
        sh_os.make_parent_dir(os.path.join(TEST_DIR, "foo", "bar"))
        self.assertTrue(os.path.isdir(os.path.join(TEST_DIR, "foo")))
        messages = logger.all_messages[:]
        # This should be noop; verifying by no change in all_messages
        sh_os.make_parent_dir(TEST_DIR)
        self.assertEqual(messages, logger.all_messages)
        # This should also be noop.  Boo hardcoded string.
        sh_os.makedirs(TEST_DIR)
        self.assertEqual(logger.all_messages[-1][1], "Already exists.")
