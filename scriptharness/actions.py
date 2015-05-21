#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Modular actions.

Attributes:
  LOGGER_NAME (str): logging.Logger name to use
  STRINGS (dict): strings for actions.  In the future these may be in a
    function to allow for localization.
  STATUSES (dict): constants to use for action statuses
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
from copy import deepcopy
import logging
from scriptharness.exceptions import ScriptHarnessError, \
    ScriptHarnessException, ScriptHarnessFatal
from scriptharness.structures import iterate_pairs
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
STATUSES = {
    'success': 0,
    'error': 1,
    'fatal': -1,
}


# Helper functions {{{1
def get_actions(all_actions):
    """Build a tuple of Action objects for the script.

    Args:
      all_actions (data structure): ordered mapping of action_name:enabled
        bool, as accepted by iterate_pairs()

    Returns:
      tuple of Action objects
    """
    action_list = []
    for action_name, value in iterate_pairs(all_actions):
        action = Action(action_name, enabled=value)
        action_list.append(action)
    return tuple(action_list)

def get_actions_from_lists(all_actions, default_actions=None):
    """Helper method to generate the ordered mapping for get_actions().

    Args:
      all_actions (list): ordered list of all action names
      default_actions (list, optional): actions that are enabled by default

    Returns:
      tuple of Action objects
    """
    if default_actions is None:
        default_actions = all_actions[:]
    elif not set(default_actions).issubset(set(all_actions)):
        raise ScriptHarnessException(
            "default_actions not a subset of all_actions!",
            default_actions, all_actions
        )
    action_list = []
    for action in all_actions:
        if action in default_actions:
            action_list.append((action, True))
        else:
            action_list.append((action, False))
    return get_actions(action_list)


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
        self.function = function or \
                        globals().get(self.name.replace('-', '_'))
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
            self.history['status'] = STATUSES['error']
            logger.error(self.strings['error_message'], {"name": self.name})
        except ScriptHarnessFatal as exc_info:
            self.history['status'] = STATUSES['fatal']
            logger.critical(self.strings['fatal_message'], {
                "name": self.name,
                "exc_info": exc_info,
            })
            raise
        else:
            self.history['status'] = STATUSES['success']
            logger.info(self.strings['success_message'], {"name": self.name})
        self.history['timestamps']['end_time'] = time.time()
        return self.history['status']
