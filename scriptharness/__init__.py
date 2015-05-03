#!/usr/bin/env python
"""Script harness.

Attributes:
  __version__ (tuple): semver version - three integers and an optional string.
  __version_string__ (str): semver version in string format.
"""
from __future__ import print_function
import sys


# scriptharness exceptions {{{1
class ScriptHarnessBaseException(Exception):
    """
    All scriptharness exceptions should inherit this exception.
    """


class ScriptHarnessException(ScriptHarnessBaseException):
    """
    There is a problem in how scriptharness is being called.
    This is a message for the developer.
    """


class ScriptHarnessFailure(ScriptHarnessBaseException):
    """
    Scriptharness has detected a failure in the running process.
    This exception should result in program termination.
    """


# get_version_string {{{1
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
            'Version tuple is non-semver-compliant {0} length!'.format(version_len)
        )
    return version_string
# 1}}}


# Semantic versioning 2.0.0  http://semver.org/
__version__ = (0, 1, 0, 'alpha')
__version_string__ = get_version_string(__version__)
