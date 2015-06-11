#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The goals of `modular actions` are:
 * faster development feedback loops, and
 * different workflows for different usage requirements.

Attributes:
  LOGGER_NAME (str): logging.Logger name to use
  STRINGS (dict): strings for actions.  In the future these may be in a
    function to allow for localization.
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
from copy import deepcopy
import logging
from scriptharness.exceptions import ScriptHarnessError, \
    ScriptHarnessException, ScriptHarnessFatal
from scriptharness.status import SUCCESS, ERROR, FATAL
import sys
import time


LOGGER_NAME = "scriptharness.actions"
STRINGS = {
    "action": {
        "run_message": "%(action_msg_prefix)sRunning action %(name)s",
        "skip_message": "%(action_msg_prefix)sSkipping action %(name)s",
        "error_message": "%(action_msg_prefix)sAction %(name)s error!",
        "fatal_message":
            "%(action_msg_prefix)sFatal %(name)s exception: %(exc_info)s",
        "success_message":
            "%(action_msg_prefix)sAction %(name)s: finished successfully",
        "action_msg_prefix": "### ",
    }
}

def get_function_by_name(function_name):
    """If function isn't passed to Action, find the function with the same name

    This searches in sys.modules['__main__'] and globals() for the function.

    Args:
      function_name (str): The name of the function to find.

    Returns:
      function: the function found.

    Raises:
      scriptharness.exceptions.ScriptHarnesException: if the function is
        not found or not callable.
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
    """Basic Action object.

    Attributes:
      name (str): This is the action name, for logging.

      enabled (bool): Enabled actions will run.  Disabled actions will log
        the skip_message and not run.

      strings (dict): Strings for action-specific log messages.

      logger_name (str): The logger name for logging calls inside this object.

      function (function): This is the function to call in run_function().

      history (dict): History of the action (return_value, status, start_time,
        end_time).
    """
    def __init__(self, name, action_groups=None, function=None, enabled=True):
        r"""Create the Action object.

        Args:
          name (str): Action name, for logging.

          action_groups (list): a list of action group names that this
            Action belongs to.  If scriptharness_volatile_action_group is
            specified in config (usually via \--action-group), all actions
            belonging to that action group will be enabled by default, and all
            others disabled by default.

          function (Optional[function]).  This is the function or method
            to run in run_function().  If not specified, use
            get_function_by_name() to find the function that matches the
            action name.  If not found, raise.

          enabled (Optional[bool]): Whether the action is enabled by default.
            This may be toggled by commandline options or configuration later.

        Raises:
          scriptharness.exceptions.ScriptHarnessException: when the function
            is not found or not callable.
        """
        self.name = name
        self.enabled = enabled
        self.strings = deepcopy(STRINGS['action'])
        self.logger_name = "scriptharness.actions.%s" % self.name
        self.action_groups = action_groups or []
        self.history = {}
        if function is None:
            self.function = get_function_by_name(self.name.replace('-', '_'))
        else:
            self.function = function
        if not callable(self.function):
            raise ScriptHarnessException(
                "No callable function for action %s!" % name
            )

    def run_function(self, context):
        """Run self.function.  Called from run() for subclassing purposes.

        This sets self.history['return_value'] for posterity.

        Args:
          context (Context): the context from the calling Script
            (passed from run()).
        """
        self.history['return_value'] = self.function(context)

    def run(self, context):
        """Run the action.

        This sets self.history timestamps and status.

        Args:
          context (Context): the context from the calling Script.

        Returns:
          status (int): one of SUCCESS, ERROR, or FATAL.

        Raises:
          scriptharness.exceptions.ScriptHarnessFatal: when the function
            raises ScriptHarnessFatal, run() re-raises.
        """
        self.history['start_time'] = time.time()
        logger = logging.getLogger(self.logger_name)
        repl_dict = {
            "name": self.name,
            "action_msg_prefix": self.strings['action_msg_prefix'],
        }
        try:
            self.run_function(context)
        except ScriptHarnessError as exc_info:
            self.history['status'] = ERROR
            logger.error(self.strings['error_message'], repl_dict)
        except ScriptHarnessFatal as exc_info:
            repl_dict['exc_info'] = exc_info
            self.history['status'] = FATAL
            logger.critical(self.strings['fatal_message'], repl_dict)
            raise
        else:
            self.history['status'] = SUCCESS
            logger.info(self.strings['success_message'], repl_dict)
        self.history['end_time'] = time.time()
        return self.history['status']
