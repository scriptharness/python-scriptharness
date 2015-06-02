#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/process.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import psutil
import scriptharness.process as process
import six
import unittest


def find_unused_pid():
    for num in range(1000, 10000):
        if not psutil.pid_exists(num):
            return num
    return None

# TestProcess {{{1
class TestProcess(unittest.TestCase):
    """Test process.
    """
    def test_kill_nonexistent_pid(self):
        pid = find_unused_pid()
        self.assertRaises(psutil.NoSuchProcess, process.kill_proc_tree, pid,
                          include_parent=True)
