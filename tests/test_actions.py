#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/actions.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import mock
import scriptharness.actions as actions
import six
import unittest
from . import TEST_ACTIONS

if six.PY3:
    BUILTIN = 'builtins'
else:
    BUILTIN = '__builtin__'


# TestHelperFunctions {{{1
class TestHelperFunctions(unittest.TestCase):
    """Test the helper functions.
    """
    @mock.patch('%s.globals' % BUILTIN)
    def test_get_actions(self, mock_globals):
        """Test get_actions()
        """
        def func():
            """Test function so Action() doesn't throw"""
            pass
        get_mock = mock.MagicMock()
        get_mock.get.return_value = func
        mock_globals.return_value = get_mock
        action_tuple = actions.get_actions(TEST_ACTIONS)
        for position, action in enumerate(action_tuple):
            self.assertEqual(
                (action.name, action.enabled),
                TEST_ACTIONS[position]
            )
