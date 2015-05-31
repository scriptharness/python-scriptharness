#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The goal of `full logging` is to be able to debug problems purely through
the log.

Attributes:
  LOGGER_NAME (str): the default name to use for logging.getLogger()
  DEFAULT_DATEFMT (str): default logging date format
  DEFAULT_FMT (str): default logging format
  DEFAULT_LEVEL (int): default logging level
"""

from __future__ import absolute_import, division, print_function, \
                       unicode_literals
from copy import deepcopy
import logging
import os
import re
from scriptharness.commands import make_parent_dir
from scriptharness.exceptions import ScriptHarnessException
import six
import time

LOGGER_NAME = "scriptharness.log"
DEFAULT_DATEFMT = '%H:%M:%S'
DEFAULT_FMT = '%(asctime)s %(levelname)8s - %(message)s'
DEFAULT_LEVEL = logging.INFO


# UnicodeFormatter {{{1
class UnicodeFormatter(logging.Formatter):
    """Subclass logging.Formatter to handle unicode strings in py2.

    Attributes:
      encoding (str): defaults to utf-8.
    """
    encoding = 'utf-8'

    def format(self, record):
        string = super(UnicodeFormatter, self).format(record)
        if six.PY2 and isinstance(string, six.text_type):
            string = string.encode(self.encoding, 'replace')
        return string


# logging helper methods {{{1
def get_formatter(fmt=DEFAULT_FMT, datefmt=DEFAULT_DATEFMT):
    """Create a unicode-friendly formatter to add to logging handlers.

    Args:
      fmt (str, optional): logging message format.
      datefmt (str, optional): date format for the log message.

    Returns:
      UnicodeFormatter to add to a handler - handler.setFormatter(formatter)
    """
    formatter = UnicodeFormatter(fmt=fmt, datefmt=datefmt)
    return formatter


def prepare_simple_logging(path, mode='w', logger_name='', level=DEFAULT_LEVEL,
                           formatter=None):
    """Create a unicode-friendly logger.

    By default it'll create the root logger with a console handler; if passed
    a path it'll also create a file handler.  Both handlers will have a
    unicode-friendly formatter.

    This function is intended to be called a single time.  If called
    a second time, beware creating multiple console handlers or multiple
    file handlers writing to the same file.

    Args:
      path (str, optional): path to the file log.  If this isn't set,
        don't create a file handler.  Default ''
      mode (char, optional): the mode to open the file log.  Default 'w'
      logger_name (str, optional): the name of the logger to use. Default ''
      level (int, optional): the level to log.  Default DEFAULT_LEVEL
      formatter (Formatter, optional): a logging Formatter to use; to handle
        unicode, subclass UnicodeFormatter.

    Returns:
        logger (Logger object).  This is also easily retrievable via
            logging.getLogger(logger_name).
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    get_console_handler(logger=logger, level=level, formatter=formatter)
    get_file_handler(path, logger=logger, mode=mode, level=level,
                     formatter=formatter)
    return logger


def get_file_handler(path, level=logging.INFO, formatter=None,
                     logger=None, mode='w'):
    """Create a file handler to add to a logger.

    Args:
      path (str): the path to the logfile.
      level (int, optional): logging level for the file.
      formatter (logging.Formatter, optional): formatter to use for logs.
      logger (logging logger, optional): logger to add the file handler to.
      mode (str, optional): mode to open the file

    Returns:
      handler (logging.FileHandler):  This can be added to a logger
      via logger.addHandler(handler)
    """
    make_parent_dir(path, level=logging.DEBUG)
    if not formatter:
        formatter = get_formatter()
    handler = logging.FileHandler(path, mode)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    if logger:
        logger.addHandler(handler)
    return handler


def get_console_handler(formatter=None, logger=None, level=logging.INFO):
    """Create a stream handler to add to a logger.

    Args:
      formatter (logging.Formatter, optional): formatter to use for logs.
      logger (logging logger, optional): logger to add the file handler to.
      level (int, optional): logging level for the file.

    Returns:
      logging.StreamHandler handler.  This can be added to a logger
      via logger.addHandler(handler)
    """
    if not formatter:
        formatter = get_formatter()
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(formatter)
    if logger:
        logger.addHandler(handler)
    return handler


# LogMethod decorator {{{1
class LogMethod(object):
    r"""Wrapper decorator object for logging and error detection.
    This is here as a shortcut to wrap functions with basic logging.

    Attributes:

      default_config (dict): contains the config defaults that can be
        overridden via __init__ kwargs.  Changing default_config directly
        may carry over to other decorated LogMethod functions!
    """
    default_config = {
        'level': logging.INFO,
        'error_level': logging.ERROR,
        'logger_name': 'scriptharness.{func_name}',
        'pre_msg': '%(func_name)s arguments were: %(args)s %(kwargs)s',
        'post_success_msg': '%(func_name)s completed.',
        'post_failure_msg': '%(func_name)s failed.',
        'exception': None,
        'detect_error_cb': None,
    }

    def __init__(self, func=None, **kwargs):
        """Set instance attributes from the decorator.

        Usage::

          # with arguments
          @LogMethod(foo='bar')
          def decorated_function(...):
              ...

          # without arguments
          @LogMethod()
          def decorated_function2(...):
              ...

        In the first example, func will be decorated_function, and kwargs
        will be {'foo': 'bar'}.  (Which will raise an exception, because
        'foo' isn't in self.defaults.)

        All of the self.defaults are overrideable via **kwargs or
        subclassing and changing self.defaults.

        func is optional because decorators are called differently when
        they have arguments or not.  As long as the decorator-without-args
        has the empty (), the function will be sent to LogMethod.__call__()

        Args:
          func (function, optional): This is the decorated function.
          **kwargs: Contains any config options to override default_config
        """
        self.func = func
        self.return_value = None
        self.args = None
        self.kwargs = None
        self.repl_dict = {}
        self.detected_errors = False
        self.config = deepcopy(self.default_config)
        messages = []
        for key, value in kwargs.items():
            if key not in self.config:
                messages.append('Unknown key {} in kwargs!'.format(key))
            self.config[key] = value
        if kwargs.get('detect_error_cb') is not None and \
                not callable(kwargs['detect_error_cb']):
            messages.append('detect_error_cb not callable!')
        if messages:
            raise ScriptHarnessException(os.linesep.join(messages))

    def __call__(self, func, *args, **kwargs):
        r"""Wrap the function call as a decorator.

        When there are decorator arguments, __call__ is only called once, at
        decorator time.  args and kwargs only show up when func is called,
        so we need to create and return a wrapping function.

        Args:
          func (function): this is the decorated function.
          *args: the args from the wrapped function call.
          **kwargs: the kwargs from the wrapped function call.
        """
        self.func = func
        def wrapped_func(*args, **kwargs):
            """This function replaces the decorated function.
            """
            self.args = args
            self.kwargs = kwargs
            self.set_repl_dict()
            self.pre_func()
            self.return_value = self.func(*self.args, **self.kwargs)
            self.repl_dict['return_value'] = self.return_value
            if self.config['detect_error_cb'] is not None:
                self.detected_errors = self.config['detect_error_cb'].__call__(self)
            self.post_func()
            return self.return_value
        return wrapped_func

    def set_repl_dict(self):
        """Create a replacement dictionary to format strings.

        The log messages in pre_func() and post_func() require some additional
        info.  Specify that info in the replacement dictionary.

        Currently, set the following::

          func_name: self.func.__name__
          *args: the args passed to self.func()
          **kwargs: the kwargs passed to self.func()

        After running self.func, we'll also set return_value.
        """
        self.repl_dict = {
            'args': self.args,
            'kwargs': self.kwargs,
        }
        for name_var in ('__qualname__', '__name__'):
            if hasattr(self.func, name_var):
                self.repl_dict['func_name'] = getattr(self.func, name_var)

    def pre_func(self):
        """Log the function call before proceeding.

        This method is split out for easier subclassing.
        """
        log = logging.getLogger(
            self.config['logger_name'].format(**self.repl_dict)
        )
        log.log(self.config['level'], self.config['pre_msg'], self.repl_dict)

    def post_func(self):
        """Log the success message until we get an error detection callback.

        This method is split out for easier subclassing.
        """
        log = logging.getLogger(
            self.config['logger_name'].format(**self.repl_dict)
        )
        if self.detected_errors:
            msg = self.config['post_failure_msg']
            level = self.config['error_level']
        else:
            msg = self.config['post_success_msg']
            level = self.config['level']
        log.log(level, msg, self.repl_dict)
        if self.detected_errors and self.config['exception']:
            raise self.config['exception'](
                self.config['post_failure_msg'].format(**self.repl_dict)
            )


# OutputParser and helpers{{{1
def _check_context_lines(context_lines, orig_context_lines, name, messages):
    """
    """
    if not isinstance(context_lines, int) or context_lines < 0:
        messages.append(
            "%s %s must be a positive int!" % (name,
                                               six.text_type(context_lines)))
        return orig_context_lines
    return max(context_lines, orig_context_lines)

def validate_error_list(error_list):
    """Validate an error_list.
    This is going to be a pain to unit test properly.

    Args:
      error_list (list of dicts): an error_list.

    Returns:
      (pre_context_lines, post_context_lines) (tuple of int, int)

    Raises:
      scriptharness.exceptions.ScriptHarnessException: if error_list is not
        well-formed.
    """
    messages = []
    context_lines_re = re.compile(r'^(\d+):(\d+)')
    re_compile_class = context_lines_re.__class__
    pre_context_lines = 0
    post_context_lines = 0
    for error_check in error_list:
        if not isinstance(error_check, dict):
            messages.append("%s is not a dict!" % six.text_type(error_check))
            continue
        if 'level' not in error_check or not \
                isinstance(error_check['level'], int):
            messages.append(
                "%s doesn't contain an int 'level'!" % six.text_type(
                    error_check)
            )
        if 'substr' not in error_check and 'regex' not in error_check:
            messages.append("%s must contain either 'substr' or 'regex'!",
                            six.text_type(error_check))
            continue
        if 'substr' in error_check and not \
                isinstance(error_check['substr'], six.text_type):
            messages.append(
                "substr %s is not of type %s!" % (error_check['substr'],
                                                  six.text_type)
            )
        if 'regex' in error_check and not isinstance(error_check['regex'],
                                                     re_compile_class):
            messages.append(
                "regex %s needs to be re.compile()d!" % error_check['regex']
            )
        if 'regex' in error_check and 'substr' in error_check:
            messages.append(
                "%s has both 'regex' and 'substr'!" % six.text_type(
                    error_check)
            )
        if 'pre_context_lines' in error_check:
            pre_context_lines = _check_context_lines(
                error_check['pre_context_lines'], pre_context_lines,
                "pre_context_lines", messages
            )
        if 'post_context_lines' in error_check:
            post_context_lines = _check_context_lines(
                error_check['post_context_lines'], post_context_lines,
                "post_context_lines", messages
            )
        # add check for explanation
        # TODO fatal support -- exception=ScriptHarnessFatal ?
        # TODO summary support -- Context has a summary object? Script
        # builds a summary?
    if messages:
        raise ScriptHarnessException(messages)
    return (pre_context_lines, post_context_lines)


class OutputBuffer(object):
    """Buffer output for context lines
    """
    def __init__(self, logger, pre_context_lines, post_context_lines):
        self.logger = logger
        self.pre_context_lines = pre_context_lines
        self.post_context_lines = post_context_lines
        # level, line, time
        self.buffer = []
        self.post_levels = []

    def update_buffer_levels(self, level, pre_context_lines):
        start = max(len(self.buffer) - pre_context_lines, 0)
        for position, buf in enumerate(self.buffer, start=start):
            self.buffer[position][0] = max(buf[0], level)

    def pop_buffer(self, num):
        for _ in range(0, num):
            self.logger.log(
                self.buffer[0][0], self.buffer[0][1], *self.buffer[0][2]
            )

    def add_line(self, level, line, pre_context_lines=0, post_context_lines=0):
        current_level = level
        if self.post_context_lines:
            if self.post_levels:
                current_level = self.post_levels.pop()
            if post_context_lines:
                for position, post_level in enumerate(self.post_levels):
                    self.post_levels[position] = max(post_level, level)
                length = len(self.post_levels)
                if length < post_context_lines:
                    for _ in range(length, post_context_lines):
                        self.post_levels.append(level)
        if self.pre_context_lines:
            if pre_context_lines and self.buffer:
                self.update_buffer_levels(level, pre_context_lines)
            self.buffer.append(current_level, line, time.time())
            num_pop = max(len(self.buffer) - self.pre_context_lines, 0)
            if num_pop > 0:
                self.pop_buffer(num_pop)
        else:
            self.logger.log(current_level, line)


class OutputParser(object):
    """Helper object to parse command output.
    """

    def __init__(self, error_list, logger=None):
        """Initialization method for the OutputParser class

        Args:
          error_list (list): list of errors to look for.
            # TODO document what it looks like
          logger (logging.Logger, optional): logger to use.
        """
        self.logger = logger or logging.getLogger(LOGGER_NAME)
        (pre_context_lines, post_context_lines) = \
            validate_error_list(error_list)
        self.error_list = error_list
        if not hasattr(self, 'history'):
            self.history = {}
        self.history['num_errors'] = 0
        self.history['num_warnings'] = 0
        self.history['worst_level'] = 0
        self.context_buffer = None
        if pre_context_lines or post_context_lines:
            self.context_buffer = OutputBuffer(logger, pre_context_lines,
                                               post_context_lines)

    def add_buffer(self, level, line, error_check):
        if self.context_buffer:
            self.context_buffer.add_line(
                level, line, error_check.get('pre_context_lines', 0),
                error_check.get('post_context_lines', 0),
            )
        else:
            self.logger.log(level, line)

    def add_line(self, line, *args):
        """parse a line and check if it matches one in `error_list`,
        if so then log it.

        Args:
          line (str): a line of output to parse.
          *args: Optional args to format the line with.
        """
        for error_check in self.error_list:
            match = False
            if 'substr' in error_check:
                if error_check['substr'] in line:
                    match = True
            else:
                if error_check['regex'].search(line):
                    match = True
            if match:
                level = error_check['level']
                messages = [' {}'.format(line % args)]
                if error_check.get('explanation'):
                    messages.append(' %s' % error_check['explanation'])
                for message in messages:
                    self.add_buffer(level, message, error_check)
                if level > logging.WARNING:
                    self.history['num_errors'] += 1
                elif level > logging.INFO:
                    self.history['num_warnings'] += 1
                self.history['worst_level'] = max(self.history['worst_level'],
                                                  level)
                break
        else:
            self.logger.info(' %s' % line)
