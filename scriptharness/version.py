#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Scriptharness version.

Attributes:
  __version__ (tuple): semver version - three integers and an optional string.
  __version_string__ (str): semver version in string format.
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
from scriptharness.exceptions import ScriptHarnessException


def get_version_string(version):
    """Translate a version tuple into a string.

    Specify the __version__ as a tuple for more precise comparisons, and
    translate it to __version_string__ for when that's needed.

    This function exists primarily for easier unit testing.

    Args:
      version (tuple): three ints and an optional string.

    Returns:
      version_string (str): the tuple translated into a string per semver.org
    """
    version_len = len(version)
    if version_len == 3:
        version_string = '%d.%d.%d' % version
    elif version_len == 4:
        version_string = '%d.%d.%d-%s' % version
    else:
        raise ScriptHarnessException(
            'Version tuple is non-semver-compliant {} length!'.format(version_len)
        )
    return version_string


# Semantic versioning 2.0.0  http://semver.org/
__version__ = (0, 1, 0, 'alpha')
__version_string__ = get_version_string(__version__)
