#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/actions.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import mock
import scriptharness.actions as actions
from scriptharness.exceptions import ScriptHarnessException, \
    ScriptHarnessError, ScriptHarnessFatal
import six
import unittest
from . import TEST_ACTIONS

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


# TestHelperFunctions {{{1
class TestHelperFunctions(unittest.TestCase):
    """Test the helper functions.
    """
    def compare_actions(self, action_tuple):
        """Helper method: compare action_tuple against TEST_ACTIONS
        """
        for position, action in enumerate(action_tuple):
            self.assertEqual(
                (action.name, action.enabled),
                TEST_ACTIONS[position]
            )

    @staticmethod
    def fake_action_func(mock_globals):
        """Set up a fake function for Action()s so they don't throw
        """
        def func():
            """Test function so Action() doesn't throw"""
            pass
        get_mock = mock.MagicMock()
        get_mock.get.return_value = func
        mock_globals.return_value = get_mock

    @mock.patch('%s.globals' % BUILTIN)
    def test_get_actions(self, mock_globals):
        """Test get_actions()
        """
        self.fake_action_func(mock_globals)
        action_tuple = actions.get_actions(TEST_ACTIONS)
        self.compare_actions(action_tuple)

    @mock.patch('%s.globals' % BUILTIN)
    def test_all_enabled(self, mock_globals):
        """Test get_actions_from_lists() all enabled
        """
        self.fake_action_func(mock_globals)
        action_tuple = actions.get_actions_from_lists(
            ["one", "two", "three", "four", "five", "six", "seven"]
        )
        for action in action_tuple:
            self.assertTrue(action.enabled)

    @mock.patch('%s.globals' % BUILTIN)
    def test_bad_default_actions(self, mock_globals):
        """Test get_actions_from_lists() with bad default_actions
        """
        self.fake_action_func(mock_globals)
        all_actions = ["one", "two", "three"]
        default_actions = ["two", "three", "four"]
        self.assertRaises(
            ScriptHarnessException,
            actions.get_actions_from_lists,
            all_actions, default_actions=default_actions
        )

    @mock.patch('%s.globals' % BUILTIN)
    def test_actions_from_list(self, mock_globals):
        """Test get_actions_from_lists() with default_actions
        """
        self.fake_action_func(mock_globals)
        all_actions = []
        default_actions = []
        for name, enabled in TEST_ACTIONS:
            all_actions.append(name)
            if enabled:
                default_actions.append(name)
        action_tuple = actions.get_actions_from_lists(
            all_actions, default_actions=default_actions
        )
        self.compare_actions(action_tuple)


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

    def test_run(self):
        """Test a successful Action.run()
        """
        action = actions.Action("name", function=action_func)
        self.assertEqual(action.run({}), actions.STATUSES['success'])
        self.assertEqual(action.history['return_value'], 50)

    def test_error(self):
        """Test Action.run() ScriptHarnessError
        """
        action = actions.Action("name", function=raise_error)
        self.assertEqual(action.run({}), actions.STATUSES['error'])
        self.assertEqual(action.history['status'], actions.STATUSES['error'])

    def test_fatal(self):
        """Test Action.run() ScriptHarnessFatal
        """
        action = actions.Action("name", function=raise_fatal)
        self.assertRaises(ScriptHarnessFatal, action.run, {})
        self.assertEqual(action.history['status'], actions.STATUSES['fatal'])
