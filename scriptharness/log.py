#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Allow for full logging.

Attributes:
  DEFAULT_DATEFMT (str): default logging date format
  DEFAULT_FMT (str): default logging format
  DEFAULT_LEVEL (int): default logging level
  LOGGING_DEFAULTS (dict): provide defaults for logging.basicConfig().
"""

from __future__ import absolute_import, division, print_function, \
                       unicode_literals
from copy import deepcopy
import logging
import os
import six

from scriptharness.exceptions import ScriptHarnessException


DEFAULT_DATEFMT = '%H:%M:%S'
DEFAULT_FMT = '%(asctime)s %(levelname)8s - %(message)s'
DEFAULT_LEVEL = logging.INFO


# UnicodeFormatter {{{1
class UnicodeFormatter(logging.Formatter):
    """Subclass logging.Formatter to not barf on unicode strings in py2.

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
      file_level (int, optional): the level to log to the file.  If this is
        None, don't create a file handler.  Default DEFAULT_LEVEL
      console_level (int, optional): the level to log to the console.  If this
        is None, don't create a console handler.  Default DEFAULT_LEVEL

    Returns:
        logger (Logger object).  This is also easily retrievable via
            logging.getLogger(logger_name).
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    get_file_handler(path, logger=logger, mode=mode, level=level,
                     formatter=formatter)
    get_console_handler(logger=logger, level=level, formatter=formatter)
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
    """Wrapper decorator object for logging and error detection.

    Attributes:
      default_config (dict): contains the config defaults that can be
      overridden via __init__ **kwargs.  Changing default_config directly
      may carry over to other decorated LogMethod functions!
    """
    default_config = {
        'level': logging.INFO,
        'error_level': logging.ERROR,
        'logger_name': '{func_name}',
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
        # pylint: disable=anomalous-backslash-in-string
        """Wrap the function call as a decorator.

        When there are decorator arguments, \_\_call\_\_ is only called once, at
        decorator time.  \*args and \*\*kwargs only show up when func is called,
        so we need to create and return a wrapping function.

        Args:
          func (function): this is the decorated function.
          *args: the function's \*args
          **kwargs: the function's \*\*kwargs
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
            'func_name': self.func.__name__,
            'args': self.args,
            'kwargs': self.kwargs,
        }

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
