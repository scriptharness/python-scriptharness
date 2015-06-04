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
from scriptharness.exceptions import ScriptHarnessException
from scriptharness.os import make_parent_dir
from scriptharness.unicode import to_unicode
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


# ErrorList {{{1
class ErrorList(list):
    """Error lists, to describe how to parse output.  In object form for
    better validation.

    An example error_list::

        [
            {
                "regex": re.compile("^Error: not actually an error!"),
                level=-1
            }, {
                "regex": re.compile("^Error:"),
                "level": logging.ERROR,
                "pre_context_lines": 5,
                "post_context_lines": 5
            }, {
                "substr": "Obscure error #94382",
                "explanation":
                    "This is a fatal program error."
                "exception": ScriptHarnessFatal
            }
        ]

    Any output line that matches the first regex will be ignored (discarded),
    because level is negative.  Because the list is matched in order, the
    more specific regex is placed before the more general 2nd regex.  If the
    order were reversed, the more specific regex would never match anything.
    The second regex sets the level to logging.ERROR for this line, and 5
    lines above and 5 lines below this message.

    Attributes:
      strict (bool): If True, be more strict about well-formed error_lists.
      pre_context_lines (int): The max number of lines the error_list defines
        in pre_context_lines.
      post_context_lines (int): The max number of lines the error_list defines
        in post_context_lines.
      error_list (list of dicts): The error list.
    """
    def __init__(self, error_list, strict=True):
        self.strict = strict
        (self.pre_context_lines, self.post_context_lines) = \
            self.validate_error_list(error_list)
        super(ErrorList, self).__init__(error_list)

    @staticmethod
    def check_context_lines(context_lines, orig_context_lines, name, messages):
        """Verifies and returns the larger int of context_lines and
        orig_context_lines.

        Args:
          context_lines (value): The value of pre_context_lines or
            post_context_lines to validate.

          orig_context_lines (int): The previous max int sent to
            check_context_lines

          name (str): The name of the field (pre_context_lines or
            post_context_lines)

          messages (list): The list of error messages so far.

        Returns:
          int: If context_lines is a non-int or negative, an error is appended
            to messages and we return orig_context_lines.  Otherwise, we return
            the max of context_lines or orig_context_lines.
        """
        if not isinstance(context_lines, int) or context_lines < 0:
            messages.append(
                "%s %s must be a positive int!" %
                (name, six.text_type(context_lines))
            )
            return orig_context_lines
        return max(context_lines, orig_context_lines)

    @staticmethod
    def exactly_one(key1, key2, error_check, messages):
        """Make sure one, and only one, of key1 and key2 are in error_check.
        If that's not the case, append an error message in messages.

        Args:
          key1 (str): Dictionary key.

          key2 (str): Dictionary key.

          error_check (dict): a single item of error_list.

          messages (list): the list of error messages so far.

        Returns:
          Bool: True if there is exactly one of the two keys in error_check.
        """
        status = True
        error_check_str = six.text_type(error_check)
        if key1 not in error_check and key2 not in error_check:
            messages.append(
                "%s must contain '%s' or '%s'!" % (error_check_str, key1, key2)
            )
            status = False
        elif key1 in error_check and key2 in error_check:
            messages.append(
                "%s has both '%s' and '%s'!" % (error_check_str, key1, key2)
            )
            status = False
        return status

    @staticmethod
    def verify_unicode(key, error_check, messages):
        """If key is in error_check, it must be of type six.text_type.
        If not, append an error message to messages.

        Args:
          key (str): a dict key
          error_check (dict): a single item of error_list
          messages (list): The error messages so far
        """
        if key in error_check and not \
                isinstance(error_check[key], six.text_type):
            messages.append(
                "%s %s is not of type %s!" % (error_check, key, six.text_type)
            )

    def check_ignore(self, ignore, name, error_check, messages):
        """If the level of an error_check is negative, it will be ignored.
        There is currently no pre_context_lines or post_context_lines support
        for ignored lines.  When self.strict is True, append an error to
        messages.

        Args:
          ignore (bool): True when 'level' is in error_check and negative.
          name (str): The name of the key (pre_context_lines,
            post_context_lines)
          error_check (dict): A single item of error_list
          messages (list): The error messages so far.
        """
        if ignore and self.strict:
            messages.append(
                "%s '%s' will be ignored because 'level' < 0." %
                (error_check, name)
            )

    def validate_error_list(self, error_list):
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
            ignore = False
            error_check_str = six.text_type(error_check)
            if not isinstance(error_check, dict):
                messages.append("%s is not a dict!" % error_check_str)
                continue
            self.exactly_one('level', 'exception', error_check, messages)
            if 'level' in error_check:
                if not isinstance(error_check['level'], int):
                    messages.append(
                        "%s level must be an int!" % error_check_str
                    )
                elif error_check['level'] < 0:
                    ignore = True
            elif 'exception' in error_check and (not \
                    isinstance(error_check['exception'], type) or not \
                    issubclass(error_check['exception'], Exception)):
                messages.append(
                    "%s exception must be a subclass of Exception!" %
                    error_check_str
                )
            self.exactly_one('substr', 'regex', error_check, messages)
            self.verify_unicode('substr', error_check, messages)
            if 'regex' in error_check and not \
                    isinstance(error_check['regex'], re_compile_class):
                messages.append(
                    "%s regex needs to be re.compile'd!" % error_check_str
                )
            if 'pre_context_lines' in error_check:
                pre_context_lines = self.check_context_lines(
                    error_check['pre_context_lines'], pre_context_lines,
                    "pre_context_lines", messages
                )
                self.check_ignore(ignore, 'pre_context_lines', error_check,
                                  messages)
            if 'post_context_lines' in error_check:
                post_context_lines = self.check_context_lines(
                    error_check['post_context_lines'], post_context_lines,
                    "post_context_lines", messages
                )
                self.check_ignore(ignore, 'post_context_lines', error_check,
                                  messages)
            self.verify_unicode('explanation', error_check, messages)
        if messages:
            raise ScriptHarnessException(messages)
        return (pre_context_lines, post_context_lines)


# OutputBuffer {{{1
class OutputBuffer(object):
    """Buffer output for context lines: essentially, an error_check can set
    the level of X lines in the past or Y lines in the future.  If multiple
    error_checks set the level for a line, currently the higher level wins.

    For instance, if a ``make: *** [all] Error 2`` sets the level to
    logging.ERROR for 10 pre_context_lines, we'll need to buffer at least 10
    lines in case we hit that error.  If a second error_check sets the level
    to logging.WARNING 5 lines above the ``make: *** [all] Error 2``, the ERROR
    wins out, and that line is still marked as an ERROR.

    This restricts the buffer size to pre_context_lines.  In years past
    I've also ordered Visual Studio output by thread, and set the error all the
    way up until we match some other pattern, so the buffer had to grow to an
    arbitrary size.  Those could be represented by separate classes/subclasses
    if needed.
    """
    def __init__(self, logger, pre_context_lines, post_context_lines):
        self.logger = logger
        self.pre_context_lines = pre_context_lines
        self.post_context_lines = post_context_lines
        # level, line, time
        self.buffer = []
        self.post_levels = []

    def update_buffer_levels(self, level, pre_context_lines):
        """Set the level for each buffer line to level if it's higher than
        the existing level.

        Args:
          level (int):  The logging level to set the lines to

          pre_context_lines (int): The number of lines to affect.  Since these
            are relative to the current line, these will be counted backwards
            from the end of the buffer.
        """
        start = max(len(self.buffer) - pre_context_lines, 0)
        for position, buf in enumerate(self.buffer):
            if position < start:
                continue
            self.buffer[position]['level'] = max(buf['level'], level)

    def pop_buffer(self, num=1):
        """Pop num lines from the front of the buffer and log them at the
        level set for each line.

        Args:
          num (int): The number of lines to pop and log.
        """
        for _ in range(0, num):
            self.logger.log(
                self.buffer[0]['level'], self.buffer[0]['line'],
                *self.buffer[0]['args']
            )
            self.buffer.pop(0)

    def dump_buffer(self):
        """Write all the buffered log lines to the log.
        """
        self.pop_buffer(num=len(self.buffer))

    def add_line(self, level, line, *args, **kwargs):
        """Add a line to the buffer.

        Args:
          level (int): the logging level for the line.

          line (str): the line to log

          pre_context_lines (int, optional): the number of lines before this
            one to set to log level `level`.  This defaults to 0.

          post_context_lines (int, optional): the number of lines after this
            one to set to log level `level`.  This defaults to 0.
        """
        current_level = level
        pre_context_lines = kwargs.get('pre_context_lines')
        post_context_lines = kwargs.get('post_context_lines')
        if self.post_context_lines:
            if self.post_levels:
                current_level = max(current_level, self.post_levels.pop(0))
            if post_context_lines:
                for position, post_level in enumerate(self.post_levels):
                    if position >= post_context_lines:
                        break
                    self.post_levels[position] = max(post_level, level)
                length = len(self.post_levels)
                if length < post_context_lines:
                    for _ in range(length, post_context_lines):
                        self.post_levels.append(level)
        if self.pre_context_lines:
            if pre_context_lines and self.buffer:
                self.update_buffer_levels(level, pre_context_lines)
            self.buffer.append({
                'level': current_level, 'line': line, 'args': args,
                'time': time.time()
            })
            num_pop = max(len(self.buffer) - self.pre_context_lines, 0)
            if num_pop > 0:
                self.pop_buffer(num=num_pop)
        else:
            self.logger.log(current_level, line, *args)


# OutputParser {{{1
class OutputParser(object):
    """Helper object to parse command output.
    """

    def __init__(self, error_list, logger=None, **kwargs):
        """Initialization method for the OutputParser class

        Args:
          error_list (list of dicts): list of errors to look for.

          logger (logging.Logger, optional): logger to use.

          **kwargs: These are ignored, and are here so we can subclass
            ParsedCommand.
        """
        if kwargs:  # silence pylint
            pass
        self.logger = logger or logging.getLogger(LOGGER_NAME)
        self.error_list = error_list
        self.history = {}
        self.history['num_errors'] = 0
        self.history['num_warnings'] = 0
        self.history['worst_level'] = 0
        self.context_buffer = None
        if error_list.pre_context_lines or error_list.post_context_lines:
            self.context_buffer = OutputBuffer(
                logger, error_list.pre_context_lines,
                error_list.post_context_lines
            )

    def add_buffer(self, level, messages, error_check=None, *args):
        """Add the line to self.context_buffer if it exists, otherwise log it.

        Args:
          level (int): logging level to log the line at

          line (str): line to log

          error_check (dict, optional): the error_check in error_list that
            first matched line, if applicable.  Defaults to None.
        """
        error_check = error_check or {}
        for line in messages.split('\n'):
            if self.context_buffer:
                self.context_buffer.add_line(
                    level, line, error_check.get('pre_context_lines', 0),
                    error_check.get('post_context_lines', 0),
                    *args
                )
            else:
                self.logger.log(level, line, *args)
        if level > logging.WARNING:
            self.history['num_errors'] += 1
        elif level > logging.INFO:
            self.history['num_warnings'] += 1
        self.history['worst_level'] = max(self.history['worst_level'],
                                          level)

    def add_line(self, line, *args):
        """parse a line and check if it matches one in `error_list`,
        if so then log it.

        Args:
          line (str): a line of output to parse.
          *args: Optional args to format the line with.
        """
        line = to_unicode(line.rstrip())
        for error_check in self.error_list:
            match = False
            if 'substr' in error_check:
                if error_check['substr'] in line:
                    match = True
            elif error_check['regex'].search(line):
                match = True
            if match:
                messages = [' {}'.format(line % args)]
                if error_check.get('explanation'):
                    messages.append(' %s' % error_check['explanation'])
                if error_check.get('exception'):
                    if self.context_buffer:
                        self.context_buffer.dump_buffer()
                    raise error_check['exception'](messages)
                level = error_check['level']
                if level >= 0:  # ignore negative levels
                    self.add_buffer(level, '\n'.join(messages), error_check)
                break
        else:
            self.add_buffer(logging.INFO, ' %s' % line, *args)
