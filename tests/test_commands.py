#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/commands/__init__.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import mock
import os
import scriptharness.commands as commands
import subprocess
import sys
import unittest
from . import LoggerReplacement

TEST_JSON = os.path.join(os.path.dirname(__file__), 'http', 'test_config.json')


class TestSubprocessWrappers(unittest.TestCase):
    """Test the subprocess wrapper functions.
    """
    @mock.patch('scriptharness.commands.logging')
    def test_check_output(self, mock_logging):
        """Test check_output()
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
        """Test check_output() with no logging
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
