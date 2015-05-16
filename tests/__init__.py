#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Common attributes, classes, and functions for test suites.

Attributes:
  UNICODE_STRINGS (list): a list of strings to test unicode functionality
  LOGGER_NAME (str): the logger name to use for tests
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals


UNICODE_STRINGS = [
    'ascii',
    '日本語',
    '한국말',
    'हिन्दी',
    'العَرَبِيةُ',
    'ру́сский язы́к',
    'ខេមរភាសា',
]
LOGGER_NAME = "scriptharness.nosetests"


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

    def silence_pylint(self):
        """pylint complains about too few public methods"""
        pass
