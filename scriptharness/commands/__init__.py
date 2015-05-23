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
from scriptharness.log import LogMethod
import subprocess

STRINGS = {
    "check_output": {
        "pre_msg":
            "Running subprocess.check_output() with %(args)s %(kwargs)s",
    },
}


# Wrap subprocess {{{1
@LogMethod(**STRINGS["check_output"])
def check_output(command, logger_name="scriptharness.commands.check_output",
                 log_level=logging.INFO, **kwargs):
    """Wrap subprocess.check_output with logging

    Args:
      **kwargs: sent to `subprocess.check_output()`
    """
    output = subprocess.check_output(command, **kwargs)
    if logger_name:
        logger = logging.getLogger(logger_name)
        logger.info("Output:")
        for line in output.splitlines():
            logger.log(log_level, " %s", line)
    return output
