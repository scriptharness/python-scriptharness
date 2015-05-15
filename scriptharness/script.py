#!/usr/bin/env python
"""Modular actions.

Attributes:
  STRINGS (dict): strings for actions.  In the future these may be in a
    function to allow for localization.
  STATUSES (dict): constants to use for action statuses
"""
from __future__ import print_function
import argparse
from copy import deepcopy
import logging
import os
from scriptharness import ScriptHarnessError, ScriptHarnessFatal


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

class Action(object):
    default_config = {
        "enabled": False,
        "args": [],
        "kwargs": {},
        "exception": ScriptHarnessError,
    }
    def __init__(self, name, script, enabled=False, config=None):
        self.name = name
        self.enabled = enabled
        self.script = script
        self.return_value = STATUSES['notrun']
        self.status = STATUSES['notrun']
        self.config = deepcopy(self.default_config)
        for key, value in STRINGS['action'].items():
            self.config[key] = value
        self.config['logger_name'] = "scriptharness.script.%s" % self.name
        self.config["function"] = globals().get(self.name)
#        for timing in ('preflight', 'postflight', 'postfatal'):
#            functions = []
#            func_name = '%s_%s' % (timing, self.name)
#            if globals().get(func_name):
#                functions.append(globals()[func_name])
#            self.config['%s_functions' % timing] = functions
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
        return logging.getLogger(self.config['logger_name'])

#    def preflight(self):
#        if hasattr(self.config['preflight_functions'], '__iter__'):
#            functions = self.config['preflight_functions']
#        else:
#            functions = [self.config['preflight_functions']
#        for func in functions:
#            if callable(func):
#                func()
#            elif func is not None:
#                raise ScriptHarnessException(
#                    "%s preflight function is not callable!" % self.name,
#                    func
#                )
#
#    def postflight(self):
#        if hasattr(self.config['postflight_functions'], '__iter__'):
#            functions = self.config['postflight_functions']
#        else:
#            functions = [self.config['postflight_functions']
#        for func in functions:
#            if callable(func):
#                func()
#            elif func is not None:
#                raise ScriptHarnessException(
#                    "%s postflight function is not callable!" % self.name,
#                    func
#                )
#
#    def postfatal(self):
#        if hasattr(self.config['postflight_functions'], '__iter__'):
#            functions = self.config['postflight_functions']
#        else:
#            functions = [self.config['postflight_functions']
#        for func in functions:
#            if callable(func):
#                func()
#            elif func is not None:
#                log = self.get_logger()
#                log.critical(
#                    "%s postfatal function is not callable!" % self.name,
#                    func
#                )

    def run(self):
        logger = self.get_logger()
#        self.preflight()
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
#        self.postflight()

# TODO manager like logging
    # get_script(name=?), get_config(name=?)
# TODO preflight, postflight, postfatal in action manager (_listeners?)
# TODO action dependencies

def get_action_parser(actions, **kwargs):
    all_actions = []
    default_actions = []
    parser = argparse.ArgumentParser(add_help=False, **kwargs)
    for action in actions:
        all_actions.append(action.name)
        if action.enabled:
            default_actions.append(action.name)
        parser.add_argument(
            # TODO
        )
    return parser

def get_config_parser(**kwargs):
    parser = argparse.ArgumentParser(add_help=False, **kwargs)
    # TODO required config files
    # TODO optional config files
    return parser

def get_parser(parents=None, initial_config=None, **kwargs):
    parents = parents or []
    parser = argparse.ArgumentParser(parents=parents, **kwargs)
    # TODO populate
    assert initial_config
    return parser


class Script(object):
    # TODO setitem config throws if config
    def __init__(self, all_actions=None, *args, **kwargs):
        default_config = {
            "logger_name": LOGGER_NAME,
        }
        self.actions = self.get_actions(all_actions)
        (parsed_args, parser) = self.parse_args(*args, **kwargs)
        self.config = self.build_config(parsed_args, parser)
        # TODO toggle actions on/off
        # TODO set self.config
        # TODO dump config
        # TODO dump actions
        # TODO strictness allows for ReadOnlyDict
        #      (add ReadOnlyDict pre_config_lock/lock support)

    def get_actions(self, all_actions):
        action_list = []
        for action_name, value in all_actions:
            if isinstance(value, Action):
                action = value
            else:
                action = Action(
                    self, action_name, config={
                        "enabled": value,
                    },
                )
            action_list.append(action)
        return tuple(action_list)

    def parse_args(self, parser=None, initial_config=None, *args):
        if parser is None:
            action_parser = get_action_parser(self.actions)
            config_parser = get_config_parser()
            parser = get_parser(parents=[action_parser, config_parser],
                                initial_config=initial_config)
        args = parser.parse_args(args)  # parse_known_args()?
        return (args, parser)

    def build_config(self, parsed_args, parser):
        # TODO parsed_args_defaults - config files - commandline args
        # differentiate argparse defaults from cmdln set? - parser.get_default(arg)
        pass

    def run(self):
        pass

# Quick n dirty tests
if __name__ == '__main__':
    SCRIPT = Script(all_actions={
        "clobber": False,
        "pull": False,
        "build": True,
        "package": True,
        "upload": False,
        "notify": False,
    })
