#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/commands/__init__.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
from contextlib import contextmanager
import logging
import mock
import os
import pprint
import scriptharness.commands as commands
from scriptharness.errorlists import ErrorList
from scriptharness.exceptions import ScriptHarnessError, \
    ScriptHarnessException, ScriptHarnessFatal, ScriptHarnessTimeout
import scriptharness.log as log
import scriptharness.status as status
from scriptharness.unicode import to_unicode
import shutil
import six
import subprocess
import sys
import time
import unittest
from . import LoggerReplacement

TEST_JSON = os.path.join(os.path.dirname(__file__), 'http', 'test_config.json')
TEST_DIR = "this_dir_should_not_exist"
TEST_COMMAND = [
    sys.executable, "-c",
    'from __future__ import print_function; print("hello");'
]


# Helper functions {{{1
def cleanup():
    """Cleanliness"""
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)


def get_command(command=None, **kwargs):
    """Create a Command for testing
    """
    if command is None:
        command = TEST_COMMAND
    kwargs.setdefault('logger', LoggerReplacement())
    return commands.Command(command, **kwargs)


def get_parsed_command(command=None, **kwargs):
    """Create a ParsedCommand for testing
    """
    if command is None:
        command = TEST_COMMAND
    kwargs.setdefault('logger', LoggerReplacement())
    return commands.ParsedCommand(command, **kwargs)


@contextmanager
def get_output(command=None, **kwargs):
    """Create an Output for testing
    """
    if command is None:
        command = TEST_COMMAND
    kwargs.setdefault('logger', LoggerReplacement())
    cmd = commands.Output(command, **kwargs)
    try:
        yield cmd
    finally:
        cmd.cleanup()


def get_timeout_cmdlns():
    """Create a list of commandline commands to run to test timeouts.
    """
    cmdlns = [
        [sys.executable, "-c", "import time;time.sleep(300);"],
        [sys.executable, "-c",
         "from __future__ import print_function; import time;"
         "print('foo', end=' ');"
         "time.sleep(300);"],
    ]
    return cmdlns


# TestFunctions {{{1
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


# TestDetectParsedErrors {{{1
class TestDetectParsedErrors(unittest.TestCase):
    """Test detect_parsed_errors()
    """
    def test_success(self):
        """test_commands | detect_parsed_errors() success
        """
        error_list = ErrorList([])
        command = get_parsed_command(error_list=error_list)
        command.parser.history['num_errors'] = 0
        self.assertEqual(commands.detect_parsed_errors(command),
                         status.SUCCESS)

    def test_failure(self):
        """test_commands | detect_parsed_errors() failure
        """
        error_list = ErrorList([])
        command = get_parsed_command(error_list=error_list)
        for value in (1, 20):
            command.parser.history['num_errors'] = value
            self.assertEqual(commands.detect_parsed_errors(command),
                             status.ERROR)


# TestCommand {{{1
class TestCommand(unittest.TestCase):
    """Test Command()
    """
    def setUp(self):
        """Cleanliness"""
        assert self  # silence pylint
        cleanup()

    def tearDown(self):
        """Cleanliness"""
        assert self  # silence pylint
        cleanup()

    def test_simple_command(self):
        """test_commands | simple Command.run()
        """
        command = get_command()
        command.run()
        pprint.pprint(command.logger.all_messages)
        self.assertEqual(command.logger.all_messages[-1][2][0], "hello")

    def test_log_env(self):
        """test_commands | Command.log_env()
        """
        env = {"foo": "bar"}
        command = get_command(
            env=env,
        )
        command.log_env(env)
        command.run()
        env_line = "'foo': 'bar'"
        if os.name != 'nt' and six.PY2:
            env_line = "u'foo': u'bar'"
        count = 0
        for line in command.logger.all_messages:
            if line[1] == commands.STRINGS['command']['env']:
                print(line)
                self.assertTrue(env_line in line[2][0]["env"])
                count += 1
        self.assertEqual(count, 2)

    def test_bad_cwd(self):
        """test_commands | Command bad cwd
        """
        command = get_command(cwd=TEST_DIR)
        self.assertRaises(ScriptHarnessException, command.run)

    def test_good_cwd(self):
        """test_commands | Command good cwd
        """
        os.makedirs(TEST_DIR)
        command = get_command(cwd=TEST_DIR)
        command.log_start()
        self.assertEqual(
            command.logger.all_messages[0][1],
            command.strings["start_with_cwd"],
        )

    def test_output_timeout(self):
        """test_commands | Command output_timeout
        """
        for cmdln in get_timeout_cmdlns():
            now = time.time()
            command = get_command(command=cmdln, output_timeout=.5)
            print(cmdln)
            self.assertRaises(ScriptHarnessTimeout, command.run)
            self.assertTrue(now + 1 > time.time())

    def test_timeout(self):
        """test_commands | Command timeout
        """
        for cmdln in get_timeout_cmdlns():
            now = time.time()
            command = get_command(command=cmdln, timeout=.5)
            print(cmdln)
            self.assertRaises(ScriptHarnessTimeout, command.run)
            self.assertTrue(now + 1 > time.time())

    def test_command_error(self):
        """test_commands | Command.run() with error
        """
        command = get_command(
            command=[sys.executable, "-c", 'import sys; sys.exit(1)']
        )
        self.assertRaises(ScriptHarnessError, command.run)

    @mock.patch('scriptharness.commands.os')
    def test_fix_env(self, mock_os):
        """test_commands | Command.fix_env()
        """
        mock_os.name = 'nt'
        mock_os.environ = {u'SystemRoot': u'FakeSystemRoot'}
        command = get_command()
        env = {u'foo': u'bar', b'x': b'y'}
        if six.PY3:
            expected_env = {u'foo': u'bar', b'x': b'y',
                            u'SystemRoot': u'FakeSystemRoot'}
        else:
            expected_env = {b'foo': b'bar', b'x': b'y',
                            b'SystemRoot': b'FakeSystemRoot'}
        self.assertEqual(command.fix_env(env), expected_env)


# TestRun {{{1
class TestRun(unittest.TestCase):
    """test commands.run()
    """
    @mock.patch('scriptharness.commands.multiprocessing')
    def test_error(self, mock_multiprocessing):
        """test_commands | run() error
        """
        def raise_error(*args, **kwargs):
            """raise ScriptHarnessError"""
            if args or kwargs:  # silence pylint
                pass
            raise ScriptHarnessError("foo")
        mock_multiprocessing.Process = raise_error
        self.assertRaises(
            ScriptHarnessFatal, commands.run,
            "echo", halt_on_failure=True
        )

    @mock.patch('scriptharness.commands.multiprocessing')
    def test_timeout(self, mock_multiprocessing):
        """test_commands | run() timeout
        """
        def raise_error(*args, **kwargs):
            """raise ScriptHarnessTimeout"""
            if args or kwargs:  # silence pylint
                pass
            raise ScriptHarnessTimeout("foo")
        mock_multiprocessing.Process = raise_error
        self.assertRaises(
            ScriptHarnessFatal, commands.run,
            "echo", halt_on_failure=True
        )

    @mock.patch('scriptharness.commands.multiprocessing')
    def test_no_halt(self, mock_multiprocessing):
        """test_commands | run() halt_on_error=False
        """
        def raise_error(*args, **kwargs):
            """raise ScriptHarnessTimeout"""
            if args or kwargs:  # silence pylint
                pass
            raise ScriptHarnessTimeout("foo")
        mock_multiprocessing.Process = raise_error
        cmd = commands.run("echo", halt_on_failure=False)
        self.assertEqual(cmd.history['status'], status.TIMEOUT)


# TestParsedCommand {{{1
class TestParsedCommand(unittest.TestCase):
    """ParsedCommand()
    """
    def test_parser_kwarg(self):
        """test_commands | ParsedCommand() parser kwarg
        """
        error_list = ErrorList([
            {'substr': 'ell', 'level': logging.WARNING}
        ])
        logger = LoggerReplacement()
        parser = log.OutputParser(error_list, logger=logger)
        cmd = get_parsed_command(parser=parser)
        cmd.run()
        self.assertEqual(parser.history['num_warnings'], 1)
        pprint.pprint(logger.all_messages)
        self.assertEqual(
            logger.all_messages,
            [(logging.WARNING, ' hello', ())]
        )

    def test_bad_errorlist(self):
        """test_commands | ParsedCommand bad error_list
        """
        for error_list in (None, {'substr': 'asdf', 'level': logging.ERROR}):
            self.assertRaises(
                ScriptHarnessException, get_parsed_command,
                error_list
            )

    def test_parse(self):
        """test_commands | parse()
        """
        error_list = ErrorList([
            {'substr': 'ell', 'level': logging.WARNING}
        ])
        logger = LoggerReplacement()
        parser = log.OutputParser(error_list, logger=logger)
        cmd = commands.parse(TEST_COMMAND, parser=parser)
        self.assertTrue(isinstance(cmd, commands.ParsedCommand))
        self.assertEqual(parser.history['num_warnings'], 1)
        pprint.pprint(logger.all_messages)
        self.assertEqual(
            logger.all_messages,
            [(logging.WARNING, ' hello', ())]
        )


# Output {{{1
class TestOutput(unittest.TestCase):
    """Test Output()
    """
    def test_env_output(self):
        """test_commands | Output run env
        """
        cmd = [
            sys.executable, "-c",
            'from __future__ import print_function;import os;'
            'print(os.environ["foo"]);'
        ]
        with get_output(command=cmd, env={'foo': 'bar'}) as command:
            command.run()
            with open(command.stdout.name) as filehandle:
                output = filehandle.read()
            self.assertEqual(to_unicode(output).rstrip(), "bar")
            self.assertEqual(os.path.getsize(command.stderr.name), 0)
            # This will result in cleanup() being called twice;
            # idempotence test
            command.cleanup()

    def test_output_timeout(self):
        """test_commands | Output output_timeout
        """
        for cmdln in get_timeout_cmdlns():
            now = time.time()
            with get_output(command=cmdln, output_timeout=.5) as command:
                print(cmdln)
                self.assertRaises(ScriptHarnessTimeout, command.run)
                self.assertTrue(now + 1 > time.time())

    def test_timeout(self):
        """test_commands | Output timeout
        """
        for cmdln in get_timeout_cmdlns():
            now = time.time()
            with get_output(command=cmdln, timeout=.5) as command:
                print(cmdln)
                self.assertRaises(ScriptHarnessTimeout, command.run)
                self.assertTrue(now + 1 > time.time())

    def test_get_output_exception(self):
        """test_commands | Output.get_output() exception
        """
        with get_output() as command:
            self.assertRaises(
                ScriptHarnessException, command.get_output,
                handle_name="foo"
            )

    def test_get_output_binary(self):
        """test_commands | Output.get_output()
        """
        with get_output() as command:
            command.run()
            self.assertEqual(command.get_output(), "hello")
            self.assertEqual(
                to_unicode(command.get_output(text=False)).rstrip(),
                "hello"
            )

    def test_nonexistent_command(self):
        """test_commands | Output nonexistent command
        """
        with get_output(command=["this_command_should_not_exist"]) as command:
            self.assertRaises(ScriptHarnessError, command.run)


# TestGetOutput {{{1
class TestGetOutput(unittest.TestCase):
    """test commands.get_output() and get_text_output()

    The ScriptHarnessFatal tests are testing get_text_output() because
    it's trickier to test the contextmanager method directly.
    """
    @mock.patch('scriptharness.commands.subprocess')
    def test_error(self, mock_subprocess):
        """test_commands | get_text_output() error
        """
        def raise_error(*args, **kwargs):
            """raise ScriptHarnessError"""
            if args or kwargs:  # silence pylint
                pass
            raise ScriptHarnessError("foo")
        mock_subprocess.Popen = raise_error
        self.assertRaises(
            ScriptHarnessFatal, commands.get_text_output,
            "echo", halt_on_failure=True
        )

    @mock.patch('scriptharness.commands.subprocess')
    def test_timeout(self, mock_subprocess):
        """test_commands | get_text_output() timeout
        """
        def raise_error(*args, **kwargs):
            """raise ScriptHarnessTimeout"""
            if args or kwargs:  # silence pylint
                pass
            raise ScriptHarnessTimeout("foo")
        mock_subprocess.Popen = raise_error
        self.assertRaises(
            ScriptHarnessFatal, commands.get_text_output,
            "echo", halt_on_failure=True
        )

    @mock.patch('scriptharness.commands.subprocess')
    def test_no_halt(self, mock_subprocess):
        """test_commands | get_output() halt_on_error=False
        """
        def raise_error(*args, **kwargs):
            """raise ScriptHarnessTimeout"""
            if args or kwargs:  # silence pylint
                pass
            raise ScriptHarnessTimeout("foo")
        mock_subprocess.Popen = raise_error
        with commands.get_output("echo", halt_on_failure=False) as cmd:
            self.assertEqual(cmd.history['status'], status.TIMEOUT)

    def test_get_text_output(self):
        """test_commands | get_text_output()
        """
        output = commands.get_text_output(TEST_COMMAND)
        self.assertEqual(output, "hello")
