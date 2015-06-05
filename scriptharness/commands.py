#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Commands, largely through subprocess.

Attributes:
  LOGGER_NAME (str): default logging.Logger name.
  STRINGS (dict): Strings for logging.
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
from contextlib import contextmanager
from copy import deepcopy
import logging
import multiprocessing
import os
import six
import pprint
from scriptharness.exceptions import ScriptHarnessError, \
    ScriptHarnessException, ScriptHarnessFatal, ScriptHarnessTimeout
from scriptharness.log import OutputParser, ErrorList
import scriptharness.process
import scriptharness.status
from scriptharness.unicode import to_unicode
import subprocess
import tempfile


# Constants {{{1
LOGGER_NAME = "scriptharness.commands"
STRINGS = {
    "check_output": {
        "pre_msg":
            "Running subprocess.check_output() with %(args)s %(kwargs)s",
    },
    "command": {
        "cwd_doesn't_exist":
            "Can't run command %(command)s in non-existent directory %(cwd)s!",
        "start_with_cwd": "Running command: %(command)s in %(cwd)s",
        "start_without_cwd": "Running command: %(command)s",
        "copy_paste": "Copy/paste: %(command)s",
        "output_timeout":
            "Command %(command)s timed out after %(output_timeout)d "
            "seconds without output.",
        "timeout":
            "Command %(command)s timed out after %(run_time)d seconds.",
        "error": "Command %(command)s failed.",
        "env": "Using env: %(env)s",
        "kill_hung_process": "Killing process that's still here",
    },
    "output": {
        "cwd_doesn't_exist":
            "Can't get output from command %(command)s in non-existent "
            "directory %(cwd)s!",
        "start_with_cwd": "Getting output from command: %(command)s in "
                          "%(cwd)s",
        "start_without_cwd": "Getting output from command: %(command)s",
        "copy_paste": "Copy/paste: %(command)s",
        "output_timeout":
            "Command %(command)s timed out after %(output_timeout)d "
            "seconds without output.",
        "timeout":
            "Command %(command)s timed out after %(run_time)d seconds.",
        "error": "Command %(command)s failed.",
        "env": "Using env: %(env)s",
        "kill_hung_process": "Killing process that's still here",
        "temp_files": "Temporary files: stdout %(stdout)s; stderr %(stderr)s",
    },
}


# Helper functions {{{1
def check_output(command, logger_name="scriptharness.commands.check_output",
                 level=logging.INFO, log_output=True, **kwargs):
    """Wrap subprocess.check_output with logging

    Args:
      command (str or list): The command to run.
      logger_name (str, optional): the logger name to log with.
      level (int, optional): the logging level to log with.  Defaults to
        logging.INFO
      log_output (bool, optional): When true, log the output of the command.
        Defaults to True.
      **kwargs: sent to `subprocess.check_output()`
    """
    logger = logging.getLogger(logger_name)
    logger.log(level, STRINGS['check_output']['pre_msg'],
               {'args': (), 'kwargs': kwargs})
    output = subprocess.check_output(command, **kwargs)
    if log_output:
        logger = logging.getLogger(logger_name)
        logger.info("Output:")
        for line in output.splitlines():
            logger.log(level, " %s", line)
    return output


def detect_errors(command):
    """ Very basic detect_errors_cb for Command.

    This looks in the command.history for return_value.  If this is set
    to 0 or other null value other than None, the command is successful.
    Otherwise it's unsuccessful.

    Args:
      command (Command obj):
    """
    status = scriptharness.status.SUCCESS
    return_value = command.history.get('return_value')
    if return_value is None or return_value:
        status = scriptharness.status.ERROR
    return status


# Command {{{1
class Command(object):
    """Basic command: run and log output.  Stdout and stderr are interleaved
    depending on the timing of the message.  Because we're logging output,
    we're expecting text/non-binary output only.  For binary output, use the
    scriptharness.commands.Output object.

    Attributes:
      command (list or string): The command to send to subprocess.Popen

      logger (logging.Logger): logger to log with.

      detect_error_cb (function): this function determines whether the
        command was successful.

      history (dict): This dictionary holds the timestamps and status of
        the command.

      kwargs (dict): These kwargs will be passed to subprocess.Popen, except
        for the optional 'output_timeout' and 'timeout', which are processed by
        Command.  `output_timeout` is how long a command can run without
        outputting anything to the screen/log.  `timeout` is how long the
        command can run, total.

      strings (dict): Strings to log.
    """
    def __init__(self, command, logger=None, detect_error_cb=None, **kwargs):
        self.command = command
        self.logger = logger or logging.getLogger(LOGGER_NAME)
        self.detect_error_cb = detect_error_cb or detect_errors
        if not hasattr(self, 'history'):
            self.history = {}
        self.kwargs = kwargs or {}
        self.strings = deepcopy(STRINGS['command'])
        self.process = None

    def log_env(self, env):
        """Log environment variables.  Here for subclassing.

        Args:
          env (dict): the environment we'll be passing to subprocess.Popen.
        """
        env = self.fix_env(env)
        self.logger.info(self.strings['env'], {'env': pprint.pformat(env)})

    @staticmethod
    def fix_env(env):
        """Windows environments are fiddly.

        Args:
          env (dict): the environment we'll be passing to subprocess.Popen.
        """
        if os.name == 'nt':
            env.setdefault("SystemRoot", os.environ["SystemRoot"])
            if six.PY2:
                new_env = {}
                # Win Py2 unhappy with unicode env vars
                for key, value in env.items():
                    if isinstance(key, six.text_type):
                        key = six.binary_type(key)
                    if isinstance(value, six.text_type):
                        value = six.binary_type(value)
                    new_env[key] = value
                env = new_env
        return env

    def log_start(self):
        """Log the start of the command, also checking for the existence of
        cwd if defined.

        Raises:
          scriptharness.exceptions.ScriptHarnessException: if cwd is defined
            and doesn't exist.
        """
        if 'cwd' in self.kwargs:
            if not os.path.isdir(self.kwargs['cwd']):
                raise ScriptHarnessException(
                    self.strings["cwd_doesn't_exist"] % \
                    {'cwd': self.kwargs['cwd'], 'command': self.command}
                )
            self.logger.info(
                self.strings["start_with_cwd"],
                {'cwd': self.kwargs['cwd'], 'command': self.command}
            )
        else:
            self.logger.info(
                self.strings["start_without_cwd"], {'command': self.command}
            )
        if isinstance(self.command, (list, tuple)):
            self.logger.info(
                self.strings["copy_paste"],
                {'command': subprocess.list2cmdline(self.command)}
            )
        if 'env' in self.kwargs:
            # https://mail.python.org/pipermail/python-dev/2011-December/114740.html
            self.log_env(self.kwargs['env'])

    def add_line(self, line):
        """Log the output.  Here for subclassing.

        Args:
          line (str): a line of output
        """
        self.logger.info(" %s", to_unicode(line.rstrip()))

    def finish_process(self):
        """Here for subclassing.
        """
        if self.history['status'] != scriptharness.status.SUCCESS:
            raise ScriptHarnessError(
                self.strings["error"] % {'command': self.command,}
            )

    def run(self):
        """Run the command.

        Raises:
          scriptharness.exceptions.ScriptHarnessError on error
        """
        if 'env' in self.kwargs:
            self.kwargs['env'] = self.fix_env(self.kwargs['env'])
        self.log_start()
        output_timeout = self.kwargs.get('output_timeout', None)
        if 'output_timeout' in self.kwargs:
            del self.kwargs['output_timeout']
        max_timeout = self.kwargs.get('timeout', None)
        if 'timeout' in self.kwargs:
            del self.kwargs['timeout']
        if isinstance(self.command, (list, tuple)):
            self.kwargs.setdefault('shell', False)
        else:
            self.kwargs.setdefault('shell', True)
        queue = multiprocessing.Queue()
        runner = multiprocessing.Process(
            target=scriptharness.process.command_subprocess,
            args=(queue, self.command),
            kwargs=self.kwargs,
        )
        runner.start()
        self.history['return_value'] = scriptharness.process.watch_command(
            self.logger, queue, runner, self.add_line,
            output_timeout=output_timeout, max_timeout=max_timeout
        )
        self.history['status'] = self.detect_error_cb(self)
        self.finish_process()


# ParsedCommand {{{1
class ParsedCommand(OutputParser, Command):
    """Parse each line of output for errors.
    """
    def __init__(self, command, error_list, **kwargs):
        if not isinstance(error_list, ErrorList):
            raise ScriptHarnessException(
                "error_list must be an ErrorList!",
                error_list
            )
        OutputParser.__init__(self, error_list)
        Command.__init__(self, command, **kwargs)

# Output {{{1
class Output(Command):
    """Run the command and capture stdout and stderr to separate files.
    The output can be binary or text.

    Attributes:
      strings (dict): Strings to log.
      stdout (NamedTemporaryFile): file to log stdout to
      stderr (NamedTemporaryFile): file to log stderr to
      + all of the attributes in scriptharness.commands.Command
    """
    def __init__(self, *args, **kwargs):
        super(Output, self).__init__(*args, **kwargs)
        self.strings = deepcopy(STRINGS['output'])
        self.stdout = tempfile.NamedTemporaryFile(delete=False)
        self.stderr = tempfile.NamedTemporaryFile(delete=False)
        self.logger.debug(
            self.strings['temp_files'], {
                'stdout': self.stdout,
                'stderr': self.stderr,
            },
        )

    def run(self):
        if 'env' in self.kwargs:
            self.kwargs['env'] = self.fix_env(self.kwargs['env'])
        self.log_start()
        output_timeout = self.kwargs.get('output_timeout', None)
        if 'output_timeout' in self.kwargs:
            del self.kwargs['output_timeout']
        max_timeout = self.kwargs.get('timeout', None)
        if 'timeout' in self.kwargs:
            del self.kwargs['timeout']
        if isinstance(self.command, (list, tuple)):
            self.kwargs.setdefault('shell', False)
        else:
            self.kwargs.setdefault('shell', True)
        runner = multiprocessing.Process(
            target=scriptharness.process.output_subprocess,
            args=(self.stdout, self.stderr, self.command),
            kwargs=self.kwargs,
        )
        runner.start()
        self.history['return_value'] = scriptharness.process.watch_output(
            self.logger, runner, self.stdout, self.stderr,
            output_timeout=output_timeout, max_timeout=max_timeout
        )
        self.history['status'] = self.detect_error_cb(self)
        self.finish_process()

    def cleanup(self, level=logging.INFO):
        """Clean up stdout and stderr temp files.
        """
        if os.path.exists(self.stdout.name):
            self.logger.log(level, "Cleaning up stdout %s", self.stdout.name)
            os.remove(self.stdout.name)
        if os.path.exists(self.stderr.name):
            self.logger.log(level, "Cleaning up stderr %s", self.stderr.name)
            os.remove(self.stderr.name)


# run {{{1
def run(command, halt_on_failure=False, **kwargs):
    """Shortcut for running a Command.

    Not entirely sure if this should also catch ScriptHarnessFatal, as those
    are explicitly trying to kill the script.

    Args:
      command (list or str): Command line to run.
      **kwargs: kwargs for subprocess.Popen.

    Returns:
      command exit code (int)

    Raises:
      scriptharness.exceptions.ScriptHarnessFatal: on fatal error
    """
    message = ""
    try:
        cmd = Command(command, **kwargs)
        cmd.run()
        return cmd
    except ScriptHarnessError as exc_info:
        message = "error: %s" % exc_info
        status = scriptharness.status.ERROR
    except ScriptHarnessTimeout as exc_info:
        message = "timeout: %s" % exc_info
        status = scriptharness.status.TIMEOUT
    if halt_on_failure and message:
        raise ScriptHarnessFatal("Fatal %s" % message)
    else:
        cmd.history.setdefault('status', status)
        return cmd


def get_text_output(command, level=logging.INFO, **kwargs):
    """Run command and return the raw stdout from that command.
    Because we log the output, we're assuming the output is text.

    Args:
      command (list or str): command for subprocess.Popen
      level (int): logging level
      **kwargs: kwargs to send to scriptharness.commands.Output

    Returns:
      output (text): the raw stdout from the command.  Most likely the
        consumer will want to pass this through
        scriptharness.unicode.to_unicode().
    """
    cmd = Output(command, **kwargs)
    # TODO catch exceptions
    cmd.run()
    with open(cmd.stdout.name) as filehandle:
        output = filehandle.read()
    cmd.logger.log(level, "Got output:")
    for line in output.splitlines():
        cmd.logger.log(level, " {}".format(to_unicode(line).rstrip()))
    cmd.cleanup(level=level)
    # TODO to_unicode output?
    # TODO yield line-by-line with contextmanager?
    return output


@contextmanager
def get_output(command, **kwargs):
    """Run command and return the Output cmd object.
    The stdout and stderr file paths can be retrieved through cmd.stdout and
    cmd.stderr, respectively.

    The output is not logged, and is written as byte data, so this can work
    for both binary or text.  If text, get_text_output is preferred for full
    logging, unless the output is either sensitive in nature or so verbose
    that logging it would be more harmful than useful.  Also, if text,
    most likely the consumer will want to pass the output through
    scriptharness.unicode.to_unicode().

    Args:
      command (list or str): the command to use in subprocess.Popen
      **kwargs: kwargs to send to scriptharness.commands.Output

    Yields:
      cmd (scriptharness.commands.Output)
    """
    cmd = Output(command, **kwargs)
    # TODO catch exceptions
    cmd.run()
    try:
        yield cmd
    finally:
        cmd.cleanup()
