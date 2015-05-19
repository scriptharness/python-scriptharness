#!/usr/bin/env python
"""Modular actions.

Attributes:
  LOGGER_NAME (str): logging.Logger name to use
  STRINGS (dict): strings for actions.  In the future these may be in a
    function to allow for localization.
  STATUSES (dict): constants to use for action statuses
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import argparse
from copy import deepcopy
import logging
import os
from scriptharness import ScriptHarnessError, ScriptHarnessFatal
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

def parse_args(all_actions=None, parser=None, initial_config=None,
               cmdln_args=None, **kwargs):
    """Build the parser and parse the commandline args.

    Args:
      parser (ArgumentParser, optional): specify the parser to use
      initial_config (dict): specify a script-level config to set defaults
        post-parser defaults, but pre-config files and commandline args
      cmdln_args (optional): override the commandline args with these

    Returns:
      tuple(ArgumentParser, parsed_args, unknown_args)
    """
    if parser is None:
        parser = get_parser(all_actions=all_actions,
                            initial_config=initial_config, **kwargs)
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

    # TODO setitem config throws if config
    # TODO preflight, postflight, postfatal listeners
    """
    def __init__(self, actions, strict=False, cmdln_args=None, **kwargs):
        """Script.__init__

        Args:
          actions (object): tuple of Action objects.
          cmdln_args (tuple, optional): override the commandline args
          **kwargs: sent to ArgumentParser() in parse_args()
        """
        self.strict = strict
        (parser, parsed_args, unknown_args) = parse_args(
            all_actions=all_actions, cmdln_args=cmdln_args, **kwargs
        )
        if self.strict and unknown_args:
            raise ScriptHarnessFatal(
                "Unknown arguments passed to script!", unknown_args
            )
        self.config = self.build_config(parser, parsed_args, unknown_args)
        self.actions = actions
        # TODO enable/disable actions based on parsed_args
        # TODO dump config
        # TODO dump actions

    def build_config(self, parser, parsed_args, unknown_args):
        """Create self.config from the parsed args.
        """
        # TODO parsed_args_defaults - config files - commandline args
        # differentiate argparse defaults from cmdln set? - parser.get_default(arg)
        self.config = (parser, parsed_args, unknown_args)

    def run(self):
        """Run all enabled actions.
        """
        pass
