#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Modular actions.

Attributes:
  LOGGER_NAME (str): logging.Logger name to use
  LISTENER_PHASES (tuple): valid phases for Script.add_listener()
  ALL_PHASES (tuple): valid phases for build_context()
  PRE_RUN (str): the pre-run phase constant
  POST_RUN (str): the post-run phase constant
  PRE_ACTION (str): the pre-action phase constant
  POST_ACTION (str): the post-action phase constant
  RUN_ACTION (str): the run-action phase constant
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import codecs
import collections
import json
import logging
import os
import pprint
from scriptharness.actions import Action
from scriptharness.commands import make_parent_dir
import scriptharness.config as shconfig
from scriptharness.exceptions import ScriptHarnessException, ScriptHarnessFatal
from scriptharness.structures import iterate_pairs, LoggingDict, ReadOnlyDict
import sys
import time


LOGGER_NAME = "scriptharness.script"
PRE_RUN = "pre_run"
POST_RUN = "post_run"
PRE_ACTION = "pre_action"
POST_ACTION = "post_action"
RUN_ACTION = "run_action"
POST_FATAL = "post_fatal"
LISTENER_PHASES = (PRE_RUN, POST_RUN, PRE_ACTION, POST_ACTION, POST_FATAL)
ALL_PHASES = tuple(list(LISTENER_PHASES) + [RUN_ACTION])

Context = collections.namedtuple(
    'Context', ['script', 'config', 'logger', 'action', 'phase', 'script_name']
)


# Helper functions {{{1
def save_config(config, path):
    """Save the configuration file to path as json.

    Args:
      config (dict): The config to save
      path (str): The path to write the config to
    """
    make_parent_dir(path)
    # log rotation would be nice.
    with codecs.open(path, 'w', encoding='utf-8') as filehandle:
        filehandle.write(json.dumps(config, sort_keys=True, indent=4))

def build_context(script, phase, action=None):
    """Build context for functions called by Actions.

    Args:
      script (Script): the calling script
      phase (str): the current script phase
      action (Action, optional): The active Action.
    """
    if phase not in ALL_PHASES:
        raise ScriptHarnessException(
            "Invalid phase %s in build_context!" % phase
        )
    return Context(
        script=script, config=script.config, logger=script.get_logger(),
        action=action, phase=phase, script_name=script.name
    )

# Script {{{1
class Script(object):
    """This maintains the context of the config + actions.

    In general there is a single Script object per run, but the intent is to
    allow for parallel processing by instantiating multiple Script objects when
    it makes sense.

    Attributes:
      config (LoggingDict): the config for the script
      actions (tuple): Action objects to run.
      name (string): The name of the script
      listeners (dict): callbacks for run()
      logger (logging.Logger): the logger for the script
    """
    config = None

    def __init__(self, actions, parser, name='root', **kwargs):
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
        self.name = name
        self.listeners = {}
        for phase in LISTENER_PHASES:
            self.listeners.setdefault(phase, [])
        self.build_config(parser, **kwargs)
        self.logger = self.get_logger()
        self.start_message()
        self.save_config()

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
        if parsed_args.__dict__.get("scriptharness_volatile_dump_config"):
            logger = self.get_logger()
            logger.info("Dumping config:")
            self.save_config()
            sys.exit(0)

    def save_config(self):
        """Save config to disk.
        """
        logger = self.get_logger()
        for line in pprint.pformat(self.config).splitlines():
            logger.info(line)
        save_config(
            self.config,
            os.path.join(
                self.config['scriptharness_artifact_dir'], "localconfig.json"
            )
        )

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
        if hasattr(parsed_args, 'scriptharness_volatile_actions') and \
                parsed_args.scriptharness_volatile_actions is not None:
            for action in self.actions:
                if action.name in parsed_args.scriptharness_volatile_actions:
                    action.enabled = True
                else:
                    action.enabled = False

    def add_listener(self, listener, phase, action_names=None):
        """Add a callback for a specific script phase.

        For pre and post_run, run at the beginning and end of the script,
        respectively.

        For pre and post_action, run at the beginning and end of actions,
        respectively.  If action_names are specified, only run before/after
        those action(s).

        Args:
          listener (function): Function to call at the right time.
          phase (str): When to run the function.  Choices in LISTENER_PHASES
          action_names (iterable): for pre/post action phase listeners,
            only run before/after these action(s).
        """
        for name_var in ('__qualname__', '__name__'):
            if hasattr(listener, name_var):
                listener_name = getattr(listener, name_var)
                break
        else:
            raise ScriptHarnessException("Listener has no __name__!", listener)
        if phase not in LISTENER_PHASES:
            raise ScriptHarnessException(
                "Invalid phase for add_listener!", listener_name,
                phase, action_names
            )
        if action_names and ('action' not in phase and 'fatal' not in phase):
            raise ScriptHarnessException(
                "Only specify action_names for pre/post action or "
                "post_fatal phase!",
                listener_name, phase, action_names
            )
        logger = self.get_logger()
        logger.debug("Adding listener to script: %s %s %s.",
                     listener_name, phase, action_names)
        self.listeners[phase].append((listener, action_names))

    def run_action(self, action):
        """Run a specific action.

        Args:
          action (Action object).
        """
        repl_dict = {
            'name': action.name,
            'action_msg_prefix': action.strings['action_msg_prefix'],
        }
        logger = self.get_logger()
        if not action.enabled:
            logger.info(action.strings['skip_message'], repl_dict)
            return
        context = build_context(self, PRE_ACTION, action=action)
        for listener, actions in iterate_pairs(self.listeners[PRE_ACTION]):
            if actions and action.name not in actions:
                continue
            listener(context)
        logger.info(action.strings['run_message'], repl_dict)
        try:
            context = build_context(self, RUN_ACTION, action=action)
            action.run(context)
        except ScriptHarnessFatal:
            context = build_context(self, POST_FATAL, action=action)
            for listener, actions in \
                    iterate_pairs(self.listeners['post_fatal']):
                if actions and action.name not in actions:
                    continue
                listener(context)
            raise
        context = build_context(self, POST_ACTION, action=action)
        for listener, actions in iterate_pairs(self.listeners['post_action']):
            if actions and action.name not in actions:
                continue
            listener(context)

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
        # Maybe self.logger should be an @property?
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
        logger.info("Starting at %s.", time.strftime('%Y-%m-%d %H:%M %Z'))

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
        context = build_context(self, PRE_RUN)
        for listener, _ in iterate_pairs(self.listeners[PRE_RUN]):
            listener(context)
        for action in self.actions:
            self.run_action(action)
        context = build_context(self, POST_RUN)
        for listener, _ in iterate_pairs(self.listeners[POST_RUN]):
            listener(context)
        self.end_message()


class StrictScript(Script):
    """A subclass of Script that uses a ReadOnlyDict for config, and locks
    its attributes.

    Attributes:
      _lock (bool): Similar to the ReadOnlyDict _lock.  Once set,
        __setattr__ will raise if any attributes are changed/set.
    """
    def __init__(self, *args, **kwargs):
        super(StrictScript, self).__init__(*args, **kwargs)
        self._lock = False

    def __setattr__(self, name, *args):
        if hasattr(self, '_lock') and self._lock:
            # Re-locking a locked StrictScript is ok; everything else is
            # verboten.
            if name != '_lock' or not args[0]:
                raise ScriptHarnessException(
                    "Not allowed to modify a locked StrictScript!"
                )
        return super(StrictScript, self).__setattr__(name, *args)

    def pre_config_lock(self):
        """Stub method for subclassing.
        """
        assert self

    def dict_to_config(self, config):
        """Set self.config to a ReadOnlyDict and lock.
        """
        self.config = ReadOnlyDict(config)
        self.pre_config_lock()
        self.config.lock()

    def run(self):
        self._lock = True
        super(StrictScript, self).run()
