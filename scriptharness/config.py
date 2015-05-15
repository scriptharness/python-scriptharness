#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Allow for flexible configuration.

Attributes:
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import argparse
import requests
try:
    import simplejson as json
except ImportError:
    import json

from scriptharness import ScriptHarnessException


# parse_config_file {{{1
def parse_config_file(file_path):
    """Read a config file and return a dictionary.

    For now, only support json.

    Args:
      file_path (str): path to config file.
    """
    try:
        with open(file_path) as filehandle:
            config = dict(json.load(filehandle))
    except IOError as exc_info:
        raise ScriptHarnessException(
            "Can't open path %s!" % file_path, exc_info
        )
    except ValueError:
        raise ScriptHarnessException(
            "Can't parse json in %s!" % file_path, exc_info
        )
    return config


def download_config_file(url, file_name):
    try:
        session = requests.Session()
        session.mount(url, requests.adapters.HTTPAdapter(max_retries=5))
        response = session.get(url, timeout=30)
        contents = response.text
        with open(file_name, 'w') as filehandle:
            filehandle.write(contents)
        return
    except requests.exceptions.Timeout as exc_info:
        raise ScriptHarnessException("Time out accessing %s" % url,
                                     exc_info)
    except requests.exceptions.RequestException as exc_info:
        raise ScriptHarnessException("Error downloading from url %s" % url,
                                     exc_info)
    except IOError as exc_info:
        raise ScriptHarnessException(
            "Error writing downloaded contents to file %s" % file_name,
            exc_info
        )
>>>>>>> start script + actions + config
