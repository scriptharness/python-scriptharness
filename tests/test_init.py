#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/__init__.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import mock
import os
import scriptharness
from scriptharness.exceptions import ScriptHarnessException
import six
from six.moves import reload_module
import unittest
from . import TEST_ACTIONS

if six.PY3:
    BUILTIN = 'builtins'
else:
    BUILTIN = '__builtin__'


# Helper classes {{{1
class FakeAction(object):  # pylint: disable=too-few-public-methods
    """Pretend Action class"""
    def __init__(self, *args, **kwargs):
        pass

class FakeScript(object):
    """Pretend Script class"""
    def __init__(self, *args, **kwargs):
        self.silence_pylint(args, kwargs)
    def add_config(self):
        """add self.config"""
        self.config = {  # pylint: disable=attribute-defined-outside-init
            "fakescript": True
        }
    def silence_pylint(self, *args):
        """silence pylint"""
        if args and self:
            pass


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
        action_tuple = scriptharness.get_actions(TEST_ACTIONS)
        self.compare_actions(action_tuple)

    @mock.patch('%s.globals' % BUILTIN)
    def test_all_enabled(self, mock_globals):
        """Test get_actions_from_list() all enabled
        """
        self.fake_action_func(mock_globals)
        action_tuple = scriptharness.get_actions_from_list(
            ["one", "two", "three", "four", "five", "six", "seven"]
        )
        for action in action_tuple:
            self.assertTrue(action.enabled)

    @mock.patch('%s.globals' % BUILTIN)
    def test_bad_default_actions(self, mock_globals):
        """Test get_actions_from_list() with bad default_actions
        """
        self.fake_action_func(mock_globals)
        all_actions = ["one", "two", "three"]
        default_actions = ["two", "three", "four"]
        self.assertRaises(
            ScriptHarnessException,
            scriptharness.get_actions_from_list,
            all_actions, default_actions=default_actions
        )

    @mock.patch('%s.globals' % BUILTIN)
    def test_actions_from_list(self, mock_globals):
        """Test get_actions_from_list() with default_actions
        """
        self.fake_action_func(mock_globals)
        all_actions = []
        default_actions = []
        for name, enabled in TEST_ACTIONS:
            all_actions.append(name)
            if enabled:
                default_actions.append(name)
        action_tuple = scriptharness.get_actions_from_list(
            all_actions, default_actions=default_actions
        )
        self.compare_actions(action_tuple)


# TestScriptManager {{{1
class TestScriptManager(unittest.TestCase):
    """Test ScriptManager
    """
    def setUp(self):
        reload_module(scriptharness)

    def tearDown(self):
        """Cleanliness is close to godliness
        """
        assert self  # silence pyflakes
        if os.path.exists("localconfig.json"):
            os.remove("localconfig.json")

    def test_fake_script(self):
        """Test ScriptManager with FakeScript
        """
        scriptharness.set_script_class(FakeScript)
        script = scriptharness.get_script()
        script2 = scriptharness.get_script(name="root")
        self.assertTrue(script is script2)
        script.add_config()
        config = scriptharness.get_config("root")
        self.assertTrue(config['fakescript'] is True)

    def test_illegal_get_config(self):
        """Test illegal get_config
        """
        scriptharness.set_script_class(FakeScript)
        scriptharness.get_script()
        self.assertRaises(
            ScriptHarnessException, scriptharness.get_config
        )
        self.assertRaises(
            ScriptHarnessException, scriptharness.get_config,
            "nonexistent_script"
        )

    def test_actions_from_list(self):
        """Test get_actions_from_list() with FakeAction
        """
        scriptharness.set_action_class(FakeAction)
        action_tuple = scriptharness.get_actions_from_list(
            ["one", "two"]
        )
        for action in action_tuple:
            self.assertTrue(isinstance(action, FakeAction))
