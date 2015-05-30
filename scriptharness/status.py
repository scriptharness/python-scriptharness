#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Statuses for Commands and Actions.

Attributes:
  SUCCESS (int): Constant for Action or Command.history['status']
  ERROR (int): Constant for Action or Command.history['status']
  FATAL (int): Constant for Action or Command.history['status']
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals


# We'll most likely need more of these later.
# I'm wondering how be best to be programmatic about it.
# The history dict may become a class.
SUCCESS = 0
ERROR = 1
FATAL = -1
