#!/usr/bin/env python
"""Modular actions.

Attributes:
  LOGGER_NAME (str): logging.Logger name to use
  STRINGS (dict): strings for actions.  In the future these may be in a
    function to allow for localization.
  STATUSES (dict): constants to use for action statuses
  VALID_LISTENER_TIMING (tuple): valid timing for Script.add_listener()
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import argparse
from copy import deepcopy
import logging
import os
from scriptharness import ScriptHarnessError, ScriptHarnessException, ScriptHarnessFatal
from scriptharness.structures import iterate_pairs, LoggingDict, ReadOnlyDict
import sys


LOGGER_NAME = "scriptharness.script"
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
    'notrun': -1,
    'success': 0,
    'error': 1,
    'fatal': 10,
}
VALID_LISTENER_TIMING = (
    "pre_run",
    "post_run",
    "pre_action",
    "post_action",
    "post_fatal",
)

# Action {{{1
class Action(object):
    """Action object.

    Attributes:
      default_config (dict): the default configuration to use
      name (str): action name for logging
      enabled (bool): skip if not enabled
      return_value (variable): set to None or the return value of the function
      status (int): one of STATUSES
      config (dict): the configuration of the action

    # TODO action dependencies?
    """
    default_config = {
        "args": [],
        "kwargs": {},
        "exception": ScriptHarnessError,
    }

    def __init__(self, name, enabled=False, config=None):
        self.name = name
        self.enabled = enabled
        self.return_value = None
        self.status = STATUSES['notrun']
        self.config = deepcopy(self.default_config)
        for key, value in STRINGS['action'].items():
            self.config[key] = value
        self.config['logger_name'] = "scriptharness.script.%s" % self.name
        self.config["function"] = globals().get(self.name)  # TODO s,-,_
        config = config or {}
        messages = []
        for key, value in config.items():
            if key not in self.config:
                messages.append("Illegal key %s!" % key)
                continue
            self.config[key] = value
        if messages:
            raise ScriptHarnessError(os.linesep.join(messages))
        self.config.update(config)

    def get_logger(self):
        """Shortcut method with subclassing in mind.
        """
        return logging.getLogger(self.config['logger_name'])

    def run(self):
        """Run the action.
        """
        logger = self.get_logger()
        try:
            self.return_value = self.config['function'](
                *self.config['args'], **self.config['kwargs']
            )
        except self.config['exception'] as exc_info:
            self.status = STATUSES['error']
            logger.error(self.config['error_message'], {"name": self.name})
        except ScriptHarnessFatal as exc_info:
            self.status = STATUSES['fatal']
            logger.critical(self.config['fatal_message'], {
                "name": self.name,
                "exc_info": exc_info,
            })
            raise
        else:
            self.status = STATUSES['success']
            logger.info(self.config['success_message'], {"name": self.name})
        return self.status


# Helper functions {{{1
def get_action_parser(all_actions):
    """Create an action option parser from the action list.

    Actions to run are specified as the argparse.REMAINDER options.

    Args:
      all_actions (list): a list of all possible Action objects for the script
      **kwargs: additional kwargs for ArgumentParser

    Returns:
      ArgumentParser with action options
    """
    parser = argparse.ArgumentParser(add_help=False)
    message = []
    for name, enabled in iterate_pairs(all_actions):
        string = "  "
        if enabled:
            string = "* "
        string += name
        message.append(string)
    def list_actions():
        """Helper function to list all actions (enabled shown with a '*')"""
        print(os.linesep.join(message))
        sys.exit(0)
    parser.add_argument(
        "--list-actions", action='store_const', const=list_actions,
        help="List all actions (default prepended with '*') and exit."
    )
    parser.add_argument(
        "--actions", nargs='+', choices=all_actions.keys(), metavar="ACTION",
        help="Specify the actions to run."
    )
    return parser

def get_config_parser():
    """Create a config option parser.

    Args:
      kwargs: additional kwargs for ArgumentParser

    Returns:
      ArgumentParser with config options
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        '--config-file', '--cfg', '-c', action='append', dest='config_files',
        metavar="CONFIG_FILE", help="Specify required config files/urls"
    )
    # TODO optional config files
    return parser


def get_parser(all_actions=None, parents=None, initial_config=None, **kwargs):
    """Create a script option parser.

    Args:
      parents (list, optional): ArgumentParsers to set as parents of the parser
      initial_config (dict, optional): a config to use to override defaults of
        the parser, or to set non-commandline config options, as appropriate
      **kwargs: additional kwargs for ArgumentParser

    Returns:
      ArgumentParser with config options
    """
    if parents is None:
        parents = []
        if all_actions:
            parents.append(get_action_parser(all_actions))
        parents.append(get_config_parser())
    parser = argparse.ArgumentParser(parents=parents, **kwargs)
    # TODO populate
    #assert initial_config
    return parser


def parse_args(parser, initial_config=None, cmdln_args=None):
    """Build the parser and parse the commandline args.

    Args:
      parser (ArgumentParser): specify the parser to use
      initial_config (dict): specify a script-level config to set defaults
        post-parser defaults, but pre-config files and commandline args
      cmdln_args (optional): override the commandline args with these

    Returns:
      tuple(ArgumentParser, parsed_args, unknown_args)
    """
    cmdln_args = cmdln_args or []
    parsed_args, unknown_args = parser.parse_known_args(*cmdln_args)
    if hasattr(parsed_args, 'list_actions') and \
            callable(parsed_args.list_actions):
        parsed_args.list_actions()
    return (parser, parsed_args, unknown_args)


def get_actions(all_actions, parsed_args):
    """Build a tuple of Action objects for the script.

    The simple

    Args:
      all_actions (object): ordered mapping of action_name:enabled bool,
        as accepted by iterate_pairs()
      parsed_args, unknown_args (Namespace): from argparse
        parse_known_args()

    Returns:
      action tuple
    """
    # TODO raise if unknown action
    action_list = []
    for action_name, value in all_actions.items():
        if isinstance(value, Action):
            action = value
        else:
            action = Action(action_name, enabled=value)
        action_list.append(action)
    return tuple(action_list)


# Script {{{1
class Script(object):
    """This maintains the context of the config + actions.

    In general there is a single Script object per run, but the intent is to
    allow for parallel processing by instantiating multiple Script objects when
    it makes sense.

    Attributes:
      config (LoggingDict or ReadOnlyDict): the config for the script
      strict (bool): In strict mode, warnings are fatal; config is read-only.
      actions (tuple): Action objects to run.
      listeners (dict): callbacks for run()

    # TODO setitem config throws if config
    """
    def __init__(self, actions, parser, strict=False, cmdln_args=None):
        """Script.__init__

        Args:
          actions (object): tuple of Action objects.
          parser (ArgumentParser): parser to use
          cmdln_args (tuple, optional): override the commandline args
          **kwargs: sent to ArgumentParser() in parse_args()
        """
        self.strict = strict
        self.actions = actions
        self.listeners = {}
        for timing in VALID_LISTENER_TIMING:
            self.listeners.setdefault(timing, [])
        self.build_config(parser, initial_config=kwargs.get('initial_config'))
        # TODO enable/disable actions based on parsed_args
        # TODO dump config
        # TODO dump actions

    def pre_config_lock(self):
        """Called before locking self.config, when we use a ReadOnlyDict.

        Here for subclassing.
        """
        pass

    def build_config(self, parser, initial_config=None):
        """Create self.config from the parsed args.
        """
        config = {}  # build it from the various files + options
        (parsed_args, unknown_args) = parser.parse_args()
        # TODO parsed_args_defaults - config files - commandline args
        # differentiate argparse defaults from cmdln set? - parser.get_default(arg)
        if self.strict:
            if unknown_args:
                raise ScriptHarnessFatal(
                    "Unknown arguments passed to script!", unknown_args
                )
            self.config = ReadOnlyDict(config)
            self.pre_config_lock()
            self.config.lock()
        else:
            self.config = self.get_logging_dict(config)

    @staticmethod
    def get_logging_dict(config):
        """Here for subclassing.
        """
        return LoggingDict(config, logger_name=LOGGER_NAME)

    def add_listener(self, listener, timing, action_names=None):
        """Add a callback for specific script timing.

        For pre_ and post_run, run at the beginning and end of the script,
        respectively.

        For pre_ and post_action, run at the beginning and end of actions,
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

    def run(self):
        """Run all enabled actions.
        """
        # TODO listeners
        # TODO run actions with try/except for postfatal
        pass
