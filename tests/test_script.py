#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/script.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import argparse
import mock
import scriptharness.actions as actions
from scriptharness.config import get_parser
from scriptharness.exceptions import ScriptHarnessException, \
    ScriptHarnessError, ScriptHarnessFatal
import scriptharness.script as script
import six
import unittest

if six.PY3:
    BUILTIN = 'builtins'
else:
    BUILTIN = '__builtin__'


# TestScript {{{1
class TestScript(unittest.TestCase):
    """Test Script()
    """
    timings = None

    def timing(self, name, *args):
        """helper function for get_action()"""
        self.timings.append(name)

    def get_action(self, name, enabled=True):
        """Helper function to generate Action()s for Script"""
        def func(_):
            """Test function"""
            self.timing(name)
        return actions.Action(name, function=func, enabled=enabled)

    def get_script(self, parser=None, cmdln_args=None, initial_config=None):
        """Create a Script for testing
        """
        actions = [
            self.get_action("one"),
            self.get_action("two"),
            self.get_action("three", enabled=False),
            self.get_action("four"),
        ]
        parser = parser or get_parser(actions)
        cmdln_args = cmdln_args or []
        kwargs = {}
        if initial_config is not None:
            kwargs['initial_config'] = initial_config
        return script.Script(actions, parser, cmdln_args=cmdln_args, **kwargs)

    def setUp(self):
        """Clear statuses before every test"""
        self.timings = []

    def test_bad_actions(self):
        """Script() should throw with a bad action list
        """
        self.assertRaises(
            ScriptHarnessException,
            script.Script, ['one', 'two'], None
        )

    def test_run(self):
        """Try a basic run()
        """
        scr = self.get_script()
        scr.run()
        self.assertEqual(self.timings, ["one", "two", "four"])

    def test_change_config(self):
        """Changing Script.config should raise
        """
        scr = self.get_script(initial_config={'a': 1})
        def func():
            """Test function"""
            scr.config = {}
        self.assertRaises(ScriptHarnessException, func)

    def test_enable_actions(self):
        """Enable/disable actions from the command line
        """
        scr = self.get_script(cmdln_args="--actions one three".split())
        scr.run()
        self.assertEqual(self.timings, ["one", "three"])
