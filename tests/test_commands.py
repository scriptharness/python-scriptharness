#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/commands/__init__.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import mock
import os
import pprint
import scriptharness.commands as commands
import scriptharness.status as status
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

def get_command(command=None, **kwargs):
    if command is None:
        command = [
            sys.executable, "-c",
            'from __future__ import print_function; print("hello")'
        ]
    return commands.Command(command, **kwargs)

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


# TestDetectErrors {{{1
class TestDetectErrors(unittest.TestCase):
    """Test detect_errors()
    """
    def test_success(self):
        """test_commands | detect_errors() success
        """
        command = get_command()
        command.history['return_value'] = 0
        self.assertEqual(commands.detect_errors(command), status.SUCCESS)

    def test_failure(self):
        """test_commands | detect_errors() failure
        """
        command = get_command()
        for value in (1, None):
            command.history['return_value'] = value
            self.assertEqual(commands.detect_errors(command), status.ERROR)

# TestCommand {{{1
class TestCommand(unittest.TestCase):
    """Test Command()
    """
    @mock.patch('scriptharness.commands.logging')
    def test_simple_command(self, mock_logging):
        """test_commands | simple Command.run()
        """
        logger = LoggerReplacement()
        mock_logging.getLogger.return_value = logger
        command = get_command()
        command.run()
        self.assertEqual(logger.all_messages[-1][2][0], "hello")

    @mock.patch('scriptharness.commands.logging')
    def test_log_env(self, mock_logging):
        """test_commands | Command.log_env()
        """
        logger = LoggerReplacement()
        mock_logging.getLogger.return_value = logger
        command = get_command()
        env = {"foo": "bar"}
        command.log_env(env)
        self.assertEqual(
            logger.all_messages[0][1], commands.STRINGS['command']['env'],
        )
        self.assertEqual(
            logger.all_messages[0][2][0]["env"], pprint.pformat(env)
        )
