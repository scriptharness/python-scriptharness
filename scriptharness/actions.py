#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Modular actions.

Attributes:
  LOGGER_NAME (str): logging.Logger name to use
  STRINGS (dict): strings for actions.  In the future these may be in a
    function to allow for localization.
  SUCCESS (int): Constant for Action.history['status']
  ERROR (int): Constant for Action.history['status']
  FATAL (int): Constant from Action.history['status']
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
from copy import deepcopy
import logging
from scriptharness.exceptions import ScriptHarnessError, \
    ScriptHarnessException, ScriptHarnessFatal
import sys
import time


LOGGER_NAME = "scriptharness.actions"
STRINGS = {
    "action": {
        "run_message": "Running action %(name)s",
        "skip_message": "Skipping action %(name)s",
        "error_message": "Action %(name)s error!",
        "fatal_message": "Fatal %(name)s exception: %(exc_info)s",
        "success_message": "Action %(name)s: finished successfully",
    }
}
SUCCESS = 0
ERROR = 1
FATAL = -1

def get_function_by_name(function_name):
    """If function isn't passed to Action, find the function with the same name
    """
    if hasattr(sys.modules['__main__'], function_name):
        function = getattr(sys.modules['__main__'], function_name)
    elif globals().get(function_name):
        function = globals()[function_name]
    else:
        raise ScriptHarnessException("Can't find function %s!" % function_name)
    if callable(function):
        return function
    else:
        raise ScriptHarnessException('%s is not callable!' % function_name)

# Action {{{1
class Action(object):
    """Action object.

    Attributes:
      name (str): action name for logging
      enabled (bool): skip if not enabled
      strings (dict): strings for log messages
      logger_name (str): logger name
      function (function): function to call
      history (dict): history of the action (return_value, status, timestamps)
    """

    def __init__(self, name, function=None, enabled=False):
        self.name = name
        self.enabled = enabled
        self.strings = deepcopy(STRINGS['action'])
        self.logger_name = "scriptharness.script.%s" % self.name
        self.history = {'timestamps': {}}
        self.function = function or get_function_by_name(
            self.name.replace('-', '_')
        )
        if not callable(self.function):
            raise ScriptHarnessException(
                "No callable function for action %s!" % name
            )

    def run_function(self, config):
        """Run self.function.  Called from run() for subclassing purposes.

        Args:
          config (data structure): the config from the calling Script
            (passed from run()).
        """
        self.history['return_value'] = self.function(config)

    def run(self, config):
        """Run the action.

        Args:
          config (data structure): the config from the calling Script.
        """
        self.history['timestamps']['start_time'] = time.time()
        logger = logging.getLogger(self.logger_name)
        try:
            self.run_function(config)
        except ScriptHarnessError as exc_info:
            self.history['status'] = ERROR
            logger.error(self.strings['error_message'], {"name": self.name})
        except ScriptHarnessFatal as exc_info:
            self.history['status'] = FATAL
            logger.critical(self.strings['fatal_message'], {
                "name": self.name,
                "exc_info": exc_info,
            })
            raise
        else:
            self.history['status'] = SUCCESS
            logger.info(self.strings['success_message'], {"name": self.name})
        self.history['timestamps']['end_time'] = time.time()
        return self.history['status']
