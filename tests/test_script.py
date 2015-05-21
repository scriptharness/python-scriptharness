#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/script.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import scriptharness.actions as actions
from scriptharness.config import get_parser
from scriptharness.exceptions import ScriptHarnessException
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
    def get_timing_func(self, name):
        """helper function for listeners and actions"""
        def func(*args):
            """Test function"""
            if args:  # silence pylint
                pass
            self.timings.append(name)
        return func

    def get_action(self, name, enabled=True):
        """Helper function to generate Action()s for Script"""
        return actions.Action(name, function=self.get_timing_func(name),
                              enabled=enabled)

    def get_script(self, parser=None, cmdln_args=None, initial_config=None):
        """Create a Script for testing
        """
        action_list = [
            self.get_action("one"),
            self.get_action("two"),
            self.get_action("three", enabled=False),
            self.get_action("four"),
        ]
        parser = parser or get_parser(action_list)
        cmdln_args = cmdln_args or []
        kwargs = {}
        if initial_config is not None:
            kwargs['initial_config'] = initial_config
        return script.Script(action_list, parser, cmdln_args=cmdln_args,
                             **kwargs)

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

    def test_pre_action_listener(self):
        """Test pre_action listeners
        """
        scr = self.get_script()
        scr.add_listener(
            self.get_timing_func("pre_action1"),
            "pre_action",
        )
        scr.add_listener(
            self.get_timing_func("pre_action2"),
            "pre_action",
            action_names=["two", "three", "five"]
        )
        scr.run()
        self.assertEqual(self.timings, [
            "pre_action1", "one", "pre_action1", "pre_action2", "two",
            "pre_action1", "four"
        ])
