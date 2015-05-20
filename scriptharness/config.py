#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Allow for flexible configuration.

Attributes:
  LOGGER_NAME (str): logging.getLogger name
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import argparse
import logging
import os
import requests
import six
import six.moves.urllib as urllib
import sys
try:
    import simplejson as json
except ImportError:
    import json

from scriptharness import ScriptHarnessException
from scriptharness.structures import iterate_pairs


LOGGER_NAME = "scriptharness.config"


# parse_config_file() {{{1
def parse_config_file(path):
    """Read a config file and return a dictionary.

    For now, only support json.

    Args:
      path (str): path or url to config file.

    Returns:
      config (dict)

    Raises:
      ScriptHarnessException on error
    """
    if is_url(path):
        path = download_url(path)
    # py3 may throw FileNotFoundError or IOError; both inherit OSError.
    # py2 throws IOError, which doesn't inherit OSError.
    if six.PY3:
        exception = OSError
    else:
        exception = IOError
    try:
        with open(path) as filehandle:
            config = dict(json.load(filehandle))
    except exception as exc_info:
        raise ScriptHarnessException(
            "Can't open path %s!" % path, exc_info
        )
    except ValueError as exc_info:
        raise ScriptHarnessException(
            "Can't parse json in %s!" % path, exc_info
        )
    return config


def get_filename_from_url(url):
    """Determine the filename of a file from its url.

    Args:
      url (str): the url to parse

    Returns:
      name (str): the name of the file
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.path != '':
        return parsed.path.rstrip('/').rsplit('/', 1)[-1]
    else:
        return parsed.netloc


def is_url(resource):
    """Is it a url?

    Args:
      resource (str): possible url

    Returns:
      bool
    """
    parsed = urllib.parse.urlparse(resource)
    if parsed.scheme:
        return True
    return False


def download_url(url, path=None, timeout=None, mode='wb'):
    """Download a url to a path

    Args:
      url (str): the url to download
      path (str, optional): the path to write to
      timeout (float, optional): how long to wait before timing out
      mode (str, optional): the mode to open the file with

    Raises:
      ScriptHarnessException on error
    """
    if path is None:
        path = get_filename_from_url(url)
    if timeout is None:
        timeout = 10
    try:
        session = requests.Session()
        session.mount(url, requests.adapters.HTTPAdapter(max_retries=5))
        response = session.get(url, timeout=timeout, stream=True)
        with open(path, mode) as filehandle:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    filehandle.write(chunk)
                    filehandle.flush()
        return path
    except requests.exceptions.RequestException as exc_info:
        raise ScriptHarnessException("Error downloading from url %s" % url,
                                     exc_info)
    except IOError as exc_info:
        raise ScriptHarnessException(
            "Error writing downloaded contents to path %s" % path,
            exc_info
        )


# get_parser() {{{1
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
    parser.add_argument(
        '--opt-config-file', '--opt-cfg', action='append',
        dest='opt_config_files', metavar="CONFIG_FILE",
        help="Specify optional config files/urls"
    )
    return parser


def get_parser(all_actions=None, parents=None, **kwargs):
    """Create a script option parser.

    Args:
      parents (list, optional): ArgumentParsers to set as parents of the parser
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
    return parser


def parse_args(parser, cmdln_args=None):
    """Build the parser and parse the commandline args.

    Args:
      parser (ArgumentParser): specify the parser to use
      cmdln_args (optional): override the commandline args with these

    Returns:
      tuple(ArgumentParser, parsed_args)
    """
    cmdln_args = cmdln_args or []
    parsed_args = parser.parse_args(*cmdln_args)
    if hasattr(parsed_args, 'list_actions') and \
            callable(parsed_args.list_actions):
        parsed_args.list_actions()
    return (parser, parsed_args)


# build_config {{{1
def build_config(parser, parsed_args, initial_config=None):
    """Build a configuration dict from the parser and initial config.

    The configuration is built in this order::

      * parser defaults
      * initial_config
      * parsed_args.config_files, in order
      * non-default parser args (cmdln_args)

    So the commandline args can override everything else, as long as there are
    options to do so (commandline args will need to be a subset of the parser
    args).  The final configuration file can override everything but the
    commandline args, and its config isn't restricted as a subset of the
    parser options.

    Args:
      parser (ArgumentParser): the parser used to parse_args()
      parsed_args (argparse Namespace): the results of parse_args()
      initial_config (dict, optional): initial configuration to set before
        commandline args
    """
    config = {}
    cmdln_config = {}
    resources = {}
    initial_config = initial_config or {}
    logger = logging.getLogger(LOGGER_NAME)
    for key, value in parsed_args.__dict__.items():
        if parser.get_default(key) == value:
            config[key] = value
        else:
            cmdln_config = value
    config.update(initial_config)
    for obj in cmdln_config, config:
        if 'config_files' in obj:
            resources['config_files'].setdefault(obj['config_files'])
        if 'opt_config_files' in obj:
            resources['opt_config_files'].setdefault(obj['opt_config_files'])
    for resource in resources.get('config_files', []):
        config.update(parse_config_file(resource))
    for resource in resources.get('opt_config_files', []):
        try:
            config.update(parse_config_file(resource))
        except ScriptHarnessException:
            logger.info("Can't read optional config file %s; skipping.",
                        resource)
    if cmdln_config:
        config.update(cmdln_config)
    return config
