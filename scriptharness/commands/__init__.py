#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Commands, largely through subprocess.

Not wrapping subprocess.call() or subprocess.check_call() because they don't
support using subprocess.PIPE for stdout/stderr; redirecting stdout and stderr
assumes synchronous behavior.

This is starting very small, but there are plans to add equivalents to
run_command() and get_output_from_command() from mozharness shortly.

Attributes:
  STRINGS (dict): Strings for logging.
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import logging
import os
import subprocess

LOGGER_NAME = "scriptharness.commands"
STRINGS = {
    "check_output": {
        "pre_msg":
            "Running subprocess.check_output() with %(args)s %(kwargs)s",
    },
}


def makedirs(path):
    """os.makedirs() wrapper.

    Args:
      path (str): path to the directory
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.info("Creating directory %s", path)
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info("Done.")
    else:
        logger.info("Already exists.")

def make_parent_dir(path):
    """Create the parent of path if it doesn't exist.

    Args:
      path (str): path to the file.
    """
    dirname = os.path.dirname(path)
    if dirname:
        makedirs(dirname)

def check_output(command, logger_name="scriptharness.commands.check_output",
                 log_level=logging.INFO, log_output=True, **kwargs):
    """Wrap subprocess.check_output with logging

    Args:
      **kwargs: sent to `subprocess.check_output()`
    """
    logger = logging.getLogger(logger_name)
    logger.log(log_level, STRINGS['check_output']['pre_msg'],
               {'args': (), 'kwargs': kwargs})
    output = subprocess.check_output(command, **kwargs)
    if log_output:
        logger = logging.getLogger(logger_name)
        logger.info("Output:")
        for line in output.splitlines():
            logger.log(log_level, " %s", line)
    return output
