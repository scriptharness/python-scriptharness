#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Allow for flexible configuration.

Attributes:
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
#import argparse
import requests
from six.moves import urllib as urllib
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

    Returns:
      config (dict)

    Raises:
      ScriptHarnessException on error
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
