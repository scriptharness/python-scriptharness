#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Commands, largely through subprocess.

"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
from scriptharness.log import LogMethod
import subprocess

STRINGS = {
    "call": {
        "pre_msg":
            "Running subprocess.call() with %(args)s %(kwargs)s",
    },
    "check_call": {
        "pre_msg":
            "Running subprocess.check_call() with %(args)s %(kwargs)s",
    },
    "check_output": {
        "pre_msg":
            "Running subprocess.check_output() with %(args)s %(kwargs)s",
    },
}


# Wrap subprocess {{{1
@LogMethod(**STRINGS["call"])
def call(*args, **kwargs):
    """Wrap subprocess.call with logging"""
    return subprocess.call(*args, **kwargs)

@LogMethod(**STRINGS["check_call"])
def check_call(*args, **kwargs):
    """Wrap subprocess.check_call with logging"""
    return subprocess.check_call(*args, **kwargs)

@LogMethod(**STRINGS["check_output"])
def check_output(*args, **kwargs):
    """Wrap subprocess.check_output with logging"""
    return subprocess.check_output(*args, **kwargs)
