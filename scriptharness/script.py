#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Modular actions.

Attributes:
  LOGGER_NAME (str): logging.Logger name to use
  VALID_LISTENER_TIMING (tuple): valid timing for Script.add_listener()
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import logging
from scriptharness.actions import Action, STRINGS
import scriptharness.config as shconfig
from scriptharness.exceptions import ScriptHarnessException, ScriptHarnessFatal
from scriptharness.structures import iterate_pairs, LoggingDict


LOGGER_NAME = "scriptharness.script"
VALID_LISTENER_TIMING = (
    "pre_run",
    "post_run",
    "pre_action",
    "post_action",
    "post_fatal",
)

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


# Script {{{1
class Script(object):
    """This maintains the context of the config + actions.

    In general there is a single Script object per run, but the intent is to
    allow for parallel processing by instantiating multiple Script objects when
    it makes sense.

    Attributes:
      config (LoggingDict): the config for the script
      strict (bool): In strict mode, warnings are fatal; config is read-only.
      actions (tuple): Action objects to run.
      listeners (dict): callbacks for run()
    """
    config = None

    def __init__(self, actions, parser, **kwargs):
        """Script.__init__

        Args:
          actions (tuple): Action objects to run.
          parser (ArgumentParser): parser to use
        """
        for action in actions:
            if not isinstance(action, Action):
                raise ScriptHarnessException(
                    "Script action is not an instance of Action!", action
                )
        self.actions = actions
        self.listeners = {}
        for timing in VALID_LISTENER_TIMING:
            self.listeners.setdefault(timing, [])
        self.build_config(parser, **kwargs)
        # TODO dump config
        # TODO dump actions

    def __setattr__(self, name, *args):
        if name == 'config' and self.config:
            raise ScriptHarnessException(
                "Changing script config after config is already set!"
            )
        return super(Script, self).__setattr__(name, *args)

    def build_config(self, parser, cmdln_args=None, initial_config=None):
        """Create self.config from the parsed args.

        Args:
          parser (ArgumentParser): parser to use
          cmdln_args (tuple, optional): override the commandline args
          initial_config (dict, optional): initial config dict to apply

        Returns:
          parsed_args from parse_args()
        """
        parsed_args = shconfig.parse_args(parser, cmdln_args)
        config = shconfig.build_config(parser, parsed_args, initial_config)
        self.config = self.dict_to_config(config)
        self.enable_actions(parsed_args)

    @staticmethod
    def dict_to_config(config):
        """Here for subclassing.
        """
        return LoggingDict(config, logger_name=LOGGER_NAME)

    def enable_actions(self, parsed_args):
        """If parsed_args has 'actions' set, use those as the enabled actions.

        Args:
          parsed_args (argparse Namespace)
        """
        if hasattr(parsed_args, 'actions'):
            for action in self.actions:
                if action.name in parsed_args.actions:
                    action.enabled = True
                else:
                    action.enabled = False

    def add_listener(self, listener, timing, action_names=None):
        """Add a callback for specific script timing.

        For pre and post_run, run at the beginning and end of the script,
        respectively.

        For pre and post_action, run at the beginning and end of actions,
        respectively.  If action_names are specified, only run before/after
        those action(s).

        Args:
          listener (function): Function to call at the right time.
          timing (str): When to run the function.  Choices in
            VALID_LISTENER_TIMING.
          action_names (iterable): for pre/post action timing listeners,
            only run before/after these action(s).
        """
        if timing not in VALID_LISTENER_TIMING:
            raise ScriptHarnessException(
                "Invalid timing for add_listener!", listener.__qualname__,
                timing, action_names
            )
        if action_names and 'action' not in timing:
            raise ScriptHarnessException(
                "Only specify action_names for pre/post action timing!",
                listener.__qualname__, timing, action_names
            )
        logger = logging.getLogger(LOGGER_NAME)
        logger.debug("Adding listener to script: %s %s %s.",
                     listener.__qualname__, timing, action_names)
        self.listeners[timing].append((listener, action_names))

    def run_action(self, action):
        """Run a specific action.

        Args:
          action (Action object).
        """
        logger = logging.getLogger(LOGGER_NAME)
        if not action.enabled:
            logger.info(STRINGS['actions']['skip_message'])
            return
        for listener, actions in iterate_pairs(self.listeners['pre_action']):
            if actions and action.name not in actions:
                continue
            listener()
        logger.info(STRINGS['actions']['run_message'])
        try:
            action.run(self.config)
        except ScriptHarnessFatal:
            for listener, actions in \
                    iterate_pairs(self.listeners['post_fatal']):
                if actions and action.name not in actions:
                    continue
                listener()
            raise
        for listener, actions in iterate_pairs(self.listeners['post_action']):
            if actions and action.name not in actions:
                continue

    def run(self):
        """Run all enabled actions.
        """
        # TODO some sort of log msg
        for listener, _ in iterate_pairs(self.listeners['pre_run']):
            listener()
        for action in self.actions:
            self.run_action(action)
        for listener, _ in iterate_pairs(self.listeners['post_run']):
            listener()
