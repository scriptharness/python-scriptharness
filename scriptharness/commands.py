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
from scriptharness.errorlists import ErrorList
from scriptharness.exceptions import ScriptHarnessError, \
    ScriptHarnessException, ScriptHarnessFatal, ScriptHarnessTimeout
from scriptharness.log import OutputParser
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

      logger_name (Optional[str]): the logger name to log with.

      level (Optional[int]): the logging level to log with.  Defaults to
        logging.INFO

      log_output (Optional[bool]): When true, log the output of the command.
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
    """Very basic detect_errors_cb for Command.

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


def detect_parsed_errors(command):
    """Very basic detect_errors_cb for ParsedCommand.

    This looks in the command.history for num_errors.  If this is set
    to 0, the command is successful.  Otherwise it's unsuccessful.

    Args:
      command (Command obj):
    """
    status = scriptharness.status.SUCCESS
    if command.parser.history.get('num_errors'):
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
        self.history = {}
        self.kwargs = kwargs or {}
        self.strings = deepcopy(STRINGS['command'])

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
        queue = multiprocessing.Queue()  # pylint: disable=no-member
        runner = multiprocessing.Process(  # pylint: disable=not-callable
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
        return self.history['status']


# ParsedCommand {{{1
class ParsedCommand(Command):
    """Parse each line of output for errors.

    This class could have easily subclassed both OutputParser and Command;
    that may have been slightly cleaner.  However, people have subclassed
    OutputParser in mozharness for various purposes; keeping the two objects
    separate may encourage that behavior.
    """
    def __init__(self, command, error_list=None, parser=None, **kwargs):
        if not parser:
            if not isinstance(error_list, ErrorList):
                raise ScriptHarnessException(
                    "error_list must be an ErrorList!",
                    error_list
                )
            parser = OutputParser(error_list)
        self.parser = parser
        kwargs.setdefault("detect_error_cb", detect_parsed_errors)
        Command.__init__(self, command, **kwargs)

    def add_line(self, line):
        """Send the line to the parser.

        Args:
          line (str): a line of output
        """
        self.parser.add_line(line)


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
        keywargs = {'delete': False}
        if six.PY2:
            keywargs['bufsize'] = 0
        else:
            keywargs['buffering'] = 0
        self.stdout = tempfile.NamedTemporaryFile(**keywargs)
        self.stderr = tempfile.NamedTemporaryFile(**keywargs)
        self.logger.debug(
            self.strings['temp_files'], {
                'stdout': self.stdout,
                'stderr': self.stderr,
            },
        )

    def finish_process(self):
        """Close the filehandles.
        """
        self.stderr.close()
        self.stdout.close()
        super(Output, self).finish_process()

    def run(self):
        """Output.run()
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
        self.kwargs['stdout'] = self.stdout.file
        self.kwargs['stderr'] = self.stderr.file
        try:
            process = subprocess.Popen(self.command, **self.kwargs)
        except OSError as exc_info:
            raise ScriptHarnessError(
                "Can't run command!", self.command, exc_info
            )
        self.history['return_value'] = scriptharness.process.watch_output(
            self.logger, process, self.stdout, self.stderr,
            output_timeout=output_timeout, max_timeout=max_timeout
        )
        self.history['status'] = self.detect_error_cb(self)
        self.finish_process()
        return self.history['status']

    def get_output(self, handle_name="stdout", text=True):
        """Get output from file.  This reads the output into memory, so
        this is not appropriate for large amounts of output.

        Args:
          handle_name (Optional["stdout" or "stderr"]): the handle to read
            from.  Defaults to "stdout"

          text (Optional[bool]): whether the output is text.  If so, run
            output through to_unicode() and rstrip().  Defaults to True.
        """
        if handle_name not in ("stdout", "stderr"):
            raise ScriptHarnessException("Bad handle for get_output: %s" %
                                         handle_name)
        handle = getattr(self, handle_name)
        with open(handle.name) as filehandle:
            contents = filehandle.read()
        if text:
            contents = to_unicode(contents).rstrip()
        return contents

    def cleanup(self):
        """Best effort cleanup of stdout and stderr temp files.
        """
        for handle in self.stdout, self.stderr:
            try:
                handle.close()
                os.remove(handle.name)
            except Exception:  # pylint: disable=broad-except
                # Broad exception especially for windows nosetests
                pass


# run {{{1
def run(command, cmd_class=Command, halt_on_failure=False, *args, **kwargs):
    """Shortcut for running a Command.

    Not entirely sure if this should also catch ScriptHarnessFatal, as those
    are explicitly trying to kill the script.

    Args:
      command (list or str): Command line to run.

      cmd_class (Optional[Command subclass]): the class to instantiate.
        Defaults to scriptharness.commands.Command.

      halt_on_failure (Optional[bool]): raise ScriptHarnessFatal on error
        if True.  Default: False

      **kwargs: kwargs for subprocess.Popen.

    Returns:
      command exit code (int)

    Raises:
      scriptharness.exceptions.ScriptHarnessFatal: on fatal error
    """
    message = ""
    try:
        cmd = cmd_class(command, *args, **kwargs)
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


# parse {{{1
def parse(command, **kwargs):
    """Shortcut for running a ParsedCommand.

    Not entirely sure if this should also catch ScriptHarnessFatal, as those
    are explicitly trying to kill the script.

    Args:
      command (list or str): Command line to run.

      **kwargs: kwargs for run/ParsedCommand.

    Returns:
      command exit code (int)

    Raises:
      scriptharness.exceptions.ScriptHarnessFatal: on fatal error
    """
    return run(command, cmd_class=ParsedCommand, **kwargs)


# get_output {{{1
@contextmanager
def get_output(command, halt_on_failure=False, **kwargs):
    """Run command and yield the Output cmd object.
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

      halt_on_failure (Optional[bool]): raise ScriptHarnessFatal on error
        if True.  Default: False

      **kwargs: kwargs to send to scriptharness.commands.Output

    Yields:
      cmd (scriptharness.commands.Output)

    Raises:
      scriptharness.exceptions.ScriptHarnessFatal: when halt_on_failure is
        True and we hit an error or timeout.
    """
    cmd = Output(command, **kwargs)
    status = scriptharness.status.SUCCESS
    message = None
    try:
        cmd.run()
    except ScriptHarnessError as exc_info:
        message = "error: %s" % exc_info
        status = scriptharness.status.ERROR
    except ScriptHarnessTimeout as exc_info:
        message = "timeout: %s" % exc_info
        status = scriptharness.status.TIMEOUT
    if halt_on_failure and message:
        raise ScriptHarnessFatal("Fatal %s" % message)
    else:
        cmd.history.setdefault("status", status)
    try:
        yield cmd
    finally:
        cmd.cleanup()

# get_text_output {{{1
def get_text_output(command, level=logging.INFO, **kwargs):
    """Run command and return the raw stdout from that command.
    Because we log the output, we're assuming the output is text.

    Args:
      command (list or str): command for subprocess.Popen

      level (int): logging level

      **kwargs: kwargs to send to scriptharness.commands.Output

    Returns:
      output (text): the stdout from the command.
    """
    cmd = Output(command, **kwargs)
    with get_output(command, **kwargs) as cmd:
        output = cmd.get_output()
        cmd.logger.log(level, "Got output:")
        for line in output.splitlines():
            cmd.logger.log(level, " {}".format(line.rstrip()))
    return output
