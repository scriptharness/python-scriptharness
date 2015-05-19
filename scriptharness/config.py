#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Allow for flexible configuration.

Attributes:
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
#import argparse
import requests
import six.moves.urllib as urllib
try:
    import simplejson as json
except ImportError:
    import json

from scriptharness import ScriptHarnessException


# parse_config_file {{{1
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
        path = download_url(path, mode='w')
    try:
        with open(path) as filehandle:
            config = dict(json.load(filehandle))
    except IOError as exc_info:
        raise ScriptHarnessException(
            "Can't open path %s!" % path, exc_info
        )
    except ValueError:
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
    return parsed.scheme is not ""


def download_url(url, path=None, mode='wb'):
    """Download a url to a path

    Args:
      url (str): the url to download
      path (str, optional): the path to write to

    Raises:
      ScriptHarnessException on error
    """
    if path is None:
        path = get_filename_from_url(url)
    try:
        session = requests.Session()
        session.mount(url, requests.adapters.HTTPAdapter(max_retries=5))
        response = session.get(url, timeout=30, stream=True)
        with open(path, mode) as filehandle:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    filehandle.write(chunk)
                    filehandle.flush()
        return
    except requests.exceptions.Timeout as exc_info:
        raise ScriptHarnessException("Time out accessing %s" % url,
                                     exc_info)
    except requests.exceptions.RequestException as exc_info:
        raise ScriptHarnessException("Error downloading from url %s" % url,
                                     exc_info)
    except IOError as exc_info:
        raise ScriptHarnessException(
            "Error writing downloaded contents to path %s" % path,
            exc_info
        )
    return path


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
    resources = []
    initial_config = initial_config or {}
    for key, value in parsed_args.__dict__.items():
        if parser.get_default(key) == value:
            config[key] = value
        else:
            cmdln_config = value
    config.update(initial_config)
    for obj in cmdln_config, config:
        if 'config_files' in obj:
            resources = obj['config_files']
            break
    for resource in resources:
        config.update(parse_config_file(resource))
    if cmdln_config:
        config.update(cmdln_config)
    return config
