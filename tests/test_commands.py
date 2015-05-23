#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/commands/__init__.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import mock
import os
import scriptharness.commands as commands
import shutil
import subprocess
import sys
import unittest
from . import LoggerReplacement

TEST_JSON = os.path.join(os.path.dirname(__file__), 'http', 'test_config.json')
TEST_DIR = "this_dir_should_not_exist"


def cleanup():
    """Cleanliness"""
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)

class TestCommands(unittest.TestCase):
    """Test the commands
    """
    def setUp(self):
        """Cleanliness"""
        assert self  # silence pylint
        cleanup()

    def tearDown(self):
        """Cleanliness"""
        assert self  # silence pylint
        cleanup()

    @mock.patch('scriptharness.commands.logging')
    def test_makedirs(self, mock_logging):
        """test_commands | make_parent_dir()
        """
        logger = LoggerReplacement()
        mock_logging.getLogger.return_value = logger
        self.assertFalse(os.path.exists(TEST_DIR))
        commands.make_parent_dir(os.path.join(TEST_DIR, "foo", "bar"))
        self.assertTrue(os.path.isdir(os.path.join(TEST_DIR, "foo")))
        messages = logger.all_messages[:]
        # This should be noop; verifying by no change in all_messages
        commands.make_parent_dir(TEST_DIR)
        self.assertEqual(messages, logger.all_messages)
        # This should also be noop.  Boo hardcoded string.
        commands.makedirs(TEST_DIR)
        self.assertEqual(logger.all_messages[-1][1], "Already exists.")

    @mock.patch('scriptharness.commands.logging')
    def test_check_output(self, mock_logging):
        """test_commands | check_output()
        """
        logger = LoggerReplacement()
        mock_logging.getLogger.return_value = logger
        command = [sys.executable, "-mjson.tool", TEST_JSON]
        output = commands.check_output(command)
        self.assertEqual(
            logger.all_messages[0][1],
            commands.STRINGS["check_output"]["pre_msg"]
        )
        output2 = subprocess.check_output(command)
        self.assertEqual(output, output2)

    @mock.patch('scriptharness.commands.logging')
    def test_check_output_nolog(self, mock_logging):
        """test_commands | check_output() with no logging
        """
        logger = LoggerReplacement()
        mock_logging.getLogger.return_value = logger
        command = [sys.executable, "-mjson.tool", TEST_JSON]
        commands.check_output(command, log_output=False)
        self.assertEqual(
            logger.all_messages[0][1],
            commands.STRINGS["check_output"]["pre_msg"]
        )
        self.assertEqual(len(logger.all_messages), 1)
