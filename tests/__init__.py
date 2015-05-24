#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Common attributes, classes, and functions for test suites.

Attributes:
  UNICODE_BYTES (list): a list of strings to test unicode functionality,
    in byte format.  Originally there was only UNICODE_STRINGS, but
    this got mangled on git clone on Windows.

  UNICODE_STRINGS (list): a list of strings to test unicode functionality

  LOGGER_NAME (str): the logger name to use for tests

  TEST_ACTIONS (tuple): action_name:enabled pairs to test with
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
from contextlib import contextmanager
import logging
import os
import sys


UNICODE_BYTES = [
    b'ascii',
    b'\xe6\x97\xa5\xe6\x9c\xac\xe8\xaa\x9e',
    b'\xed\x95\x9c\xea\xb5\xad\xeb\xa7\x90',
    b'\xe0\xa4\xb9\xe0\xa4\xbf\xe0\xa4\xa8\xe0\xa5\x8d\xe0\xa4\xa6\xe0\xa5\x80',
    b'\xd8\xa7\xd9\x84\xd8\xb9\xd9\x8e\xd8\xb1\xd9\x8e\xd8\xa8\xd9\x90\xd9\x8a\xd8\xa9\xd9\x8f',
    b'\xd1\x80\xd1\x83\xcc\x81\xd1\x81\xd1\x81\xd0\xba\xd0\xb8\xd0\xb9 \xd1\x8f\xd0\xb7\xd1\x8b\xcc\x81\xd0\xba',
    b'\xe1\x9e\x81\xe1\x9f\x81\xe1\x9e\x98\xe1\x9e\x9a\xe1\x9e\x97\xe1\x9e\xb6\xe1\x9e\x9f\xe1\x9e\xb6',
]
UNICODE_STRINGS = [string.decode() for string in UNICODE_BYTES]
LOGGER_NAME = "scriptharness.nosetests"
TEST_ACTIONS = (
    ("clobber", False),
    ("pull", True),
    ("build", True),
    ("package", True),
    ("upload", False),
    ("notify", False),
)


class LoggerReplacement(object):
    """A replacement logging.Logger to more easily test

    Attributes:
      all_messages (list): a list of all messages sent to log()
      level_messages (dict): a list of all messages sent to log(), sorted
        by level.
      simple (bool): append message strings to all_messages if True.
        When False, log (level, msg, args)
    """
    def __init__(self, simple=False):
        super(LoggerReplacement, self).__init__()
        self.all_messages = []
        self.level_messages = {}
        self.simple = simple

    def log(self, level, msg, *args):
        """Keep track of all calls to logger.log()

        self.all_messages gets a list of all (level, msg, *args).
        self.level_messages is a dict, with level keys; the values are lists
        containing tuples of (msg, args) per log() call.
        """
        if self.simple:
            if args:
                msg = msg % args[0]
            self.all_messages.append(msg)
        else:
            self.all_messages.append((level, msg, args))
        self.level_messages.setdefault(level, [])
        self.level_messages[level].append((msg, args))

    def debug(self, *args):
        """debug() wrapper"""
        self.log(logging.DEBUG, *args)

    def info(self, *args):
        """info() wrapper"""
        self.log(logging.INFO, *args)

    def warning(self, *args):
        """warning() wrapper"""
        self.log(logging.WARNING, *args)

    def error(self, *args):
        """error() wrapper"""
        self.log(logging.ERROR, *args)

    def critical(self, *args):
        """critical() wrapper"""
        self.log(logging.CRITICAL, *args)


# http://stackoverflow.com/questions/4675728/redirect-stdout-to-a-file-in-python
@contextmanager
def stdstar_redirected(path):
    """Open path and redirect stdout+stderr to it.

    Args:
      path (str): A file path to use to log stdout+stderr
    """
    stdout = sys.stdout
    stderr = sys.stderr
    with os.fdopen(os.dup(1), 'wb') as copied_out, \
            os.fdopen(os.dup(2), 'wb') as copied_err:
        stdout.flush()
        stderr.flush()
        with open(path, 'wb') as to_file:
            os.dup2(to_file.fileno(), 1)
            os.dup2(to_file.fileno(), 2)
        try:
            yield stdout
        finally:
            stdout.flush()
            stderr.flush()
            os.dup2(copied_out.fileno(), 1)  # $ exec >&copied
            os.dup2(copied_err.fileno(), 2)  # $ exec >&copied
