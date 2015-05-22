#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/actions.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import scriptharness.actions as actions
from scriptharness.exceptions import ScriptHarnessException, \
    ScriptHarnessError, ScriptHarnessFatal
import six
import unittest

if six.PY3:
    BUILTIN = 'builtins'
else:
    BUILTIN = '__builtin__'


# Helper functions {{{1
def action_func(_):
    """Return 50"""
    return 50

def raise_error(_):
    """raise ScriptHarnessError"""
    raise ScriptHarnessError("error!")

def raise_fatal(_):
    """raise ScriptHarnessFatal"""
    raise ScriptHarnessFatal("fatal!")


# TestAction {{{1
class TestFunctionByName(unittest.TestCase):
    """Test get_function_by_name()
    """


# TestAction {{{1
class TestAction(unittest.TestCase):
    """Test Action()
    """
    def test_missing_func(self):
        """Action should raise if no function
        """
        self.assertRaises(
            ScriptHarnessException, actions.Action, name="missing_function"
        )
        # Test the sys.modules['__main__'] chunk with an uncallable func
        self.assertRaises(
            ScriptHarnessException, actions.Action, name="__name__"
        )

    def test_specify_func(self):
        """Action should raise if function is not callable
        """
        obj = []
        self.assertRaises(
            ScriptHarnessException, actions.Action, name="foo", function=obj
        )
        actions.Action("foo", function=self.test_specify_func)

    def test_run(self):
        """Test a successful Action.run()
        """
        action = actions.Action("name", function=action_func)
        self.assertEqual(action.run({}), actions.SUCCESS)
        self.assertEqual(action.history['return_value'], 50)

    def test_error(self):
        """Test Action.run() ScriptHarnessError
        """
        action = actions.Action("name", function=raise_error)
        self.assertEqual(action.run({}), actions.ERROR)
        self.assertEqual(action.history['status'], actions.ERROR)

    def test_fatal(self):
        """Test Action.run() ScriptHarnessFatal
        """
        action = actions.Action("name", function=raise_fatal)
        self.assertRaises(ScriptHarnessFatal, action.run, {})
        self.assertEqual(action.history['status'], actions.FATAL)
