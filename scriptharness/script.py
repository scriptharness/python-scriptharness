#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Modular actions.

Attributes:
  LOGGER_NAME (str): logging.Logger name to use
  VALID_LISTENER_TIMING (tuple): valid timing for Script.add_listener()
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import codecs
import logging
import pprint
from scriptharness.actions import Action, STRINGS
import scriptharness.config as shconfig
from scriptharness.exceptions import ScriptHarnessException, ScriptHarnessFatal
from scriptharness.structures import iterate_pairs, LoggingDict
import sys
import time
try:
    import simplejson as json
    assert json
except ImportError:
    import json


LOGGER_NAME = "scriptharness.script"
VALID_LISTENER_TIMING = (
    "pre_run",
    "post_run",
    "pre_action",
    "post_action",
    "post_fatal",
)


def save_config(config, path):
    """Save the configuration file to path as json.

    Args:
      config (dict): The config to save
      path (str): The path to write the config to
    """
    with codecs.open(path, 'w', encoding='utf-8') as filehandle:
        filehandle.write(json.dumps(config, sort_keys=True, indent=4))

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
      logger (logging.Logger): the logger for the script
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
        self.logger = self.get_logger()
        self.start_message()
        self.save_config()

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
        self.dict_to_config(config)
        self.enable_actions(parsed_args)
        if parsed_args.__dict__.get("dump_config"):
            logger = self.get_logger()
            logger.info("Dumping config:")
            self.save_config()
            sys.exit(0)

    def save_config(self):
        """Save config to disk.
        """
        logger = self.get_logger()
        logger.info(pprint.pformat(self.config, indent=4))
        save_config(self.config, "localconfig.json")

    def dict_to_config(self, config):
        """Here for subclassing.
        """
        self.config = LoggingDict(
            config, logger_name=config.get('logger_name', LOGGER_NAME)
        )
        self.config.recursively_set_parent(name="config")

    def enable_actions(self, parsed_args):
        """If parsed_args has 'actions' set, use those as the enabled actions.

        Args:
          parsed_args (argparse Namespace)
        """
        if hasattr(parsed_args, 'actions') and parsed_args.actions is not None:
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
        for name_var in ('__qualname__', '__name__'):
            if hasattr(listener, name_var):
                listener_name = getattr(listener, name_var)
                break
        else:
            raise ScriptHarnessException("Listener has no __name__!", listener)
        if timing not in VALID_LISTENER_TIMING:
            raise ScriptHarnessException(
                "Invalid timing for add_listener!", listener_name,
                timing, action_names
            )
        if action_names and ('action' not in timing and 'fatal' not in timing):
            raise ScriptHarnessException(
                "Only specify action_names for pre/post action or "
                "post_fatal timing!",
                listener_name, timing, action_names
            )
        logger = self.get_logger()
        logger.debug("Adding listener to script: %s %s %s.",
                     listener_name, timing, action_names)
        self.listeners[timing].append((listener, action_names))

    def run_action(self, action):
        """Run a specific action.

        Args:
          action (Action object).
        """
        repl_dict = {
            'name': action.name
        }
        logger = self.get_logger()
        if not action.enabled:
            logger.info(STRINGS['action']['skip_message'], repl_dict)
            return
        for listener, actions in iterate_pairs(self.listeners['pre_action']):
            if actions and action.name not in actions:
                continue
            listener()
        logger.info(STRINGS['action']['run_message'], repl_dict)
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
            listener()

    def get_logger(self):
        """Get a logger to log messages.

        This is not strictly needed, as python's logging module will
        keep track of these loggers.

        However, if we support structured logging as well as python logging,
        get_logger() may return one or the other depending on config.

        This method may end up moving to the scriptharness module, and tracked
        in ScriptManager.

        Returns:
          logging.Logger object.
        """
        if not hasattr(self, 'logger') or not self.logger:
            self.logger = logging.getLogger(
                self.config.get('logger_name', LOGGER_NAME)
            )
        return self.logger

    def start_message(self):
        """Log a message at the end of __init__()

        Split out for subclassing; the string may end up moving elsewhere
        for localizability.
        """
        logger = self.get_logger()
        logger.info("Starting at %s." % time.strftime('%Y-%m-%d %H:%M %Z'))

    def end_message(self):
        """Log a message at the end of run()

        Split out for subclassing; the string may end up moving elsewhere
        for localizability.
        """
        logger = self.get_logger()
        logger.info("Done.")

    def run(self):
        """Run all enabled actions.
        """
        for listener, _ in iterate_pairs(self.listeners['pre_run']):
            listener()
        for action in self.actions:
            self.run_action(action)
        for listener, _ in iterate_pairs(self.listeners['post_run']):
            listener()
        self.end_message()
