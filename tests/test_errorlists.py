#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness.log

Attributes:
  TEST_FILE (str): the filename to use for test log files
  TEST_CONSOLE (str): the filename to use for testing console output
  TEST_FILE_CONTENTS (str): a string to prepopulate logs to test overwriting
  TEST_STRING (str): a sample ascii string to use to test log output
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import re
from scriptharness.errorlists import ErrorList
from scriptharness.exceptions import ScriptHarnessException
import unittest


# TestErrorList {{{1
class TestErrorList(unittest.TestCase):
    """Test ErrorList.
    """
    def test_check_ignore(self):
        """test_log | ErrorList check_ignore()
        """
        elists = [
            [{'level': -1, 'substr': 'foo', 'pre_context_lines': 5}],
            [{'level': -1, 'substr': 'foo', 'post_context_lines': 5}],
        ]
        for error_list in elists:
            self.assertRaises(
                ScriptHarnessException, ErrorList,
                error_list, strict=True
            )
            # shouldn't raise when strict is False
            ErrorList(error_list, strict=False)

    def test_context_lines(self):
        """test_log | ErrorList context lines
        """
        for var in None, -1:
            self.assertRaises(
                ScriptHarnessException, ErrorList,
                [{'level': 0, 'substr': 'foo', 'pre_context_lines': var}]
            )
        error_list = ErrorList([
            {'level': 0, 'substr': 'foo', 'pre_context_lines': 2,
             'post_context_lines': 9},
            {'level': 0, 'substr': 'bar', 'pre_context_lines': 5,
             'post_context_lines': 3},
            {'level': 0, 'substr': 'baz', 'pre_context_lines': 9,
             'post_context_lines': 1},
        ])
        self.assertEqual(error_list.pre_context_lines, 9)
        self.assertEqual(error_list.post_context_lines, 9)

    def test_exactly_one(self):
        """test_log | ErrorList.exactly_one()
        """
        elists = [
            [{'substr': 'foo'}],
            [{'level': 0}],
            [{'level': 0, 'substr': 'foo', 'regex': re.compile("foo")}],
            [['level', 0, 'substr', 'foo', 'regex', re.compile("foo")]],
        ]
        for error_list in elists:
            print(error_list)
            self.assertRaises(
                ScriptHarnessException, ErrorList, error_list
            )

    def test_illegal_values(self):
        """test_log | ErrorList illegal values
        """
        elists = [
            [{'level': None}],
            [{'exception': "foo"}],
            [{'level': 1, 'substr': b'lksjdf'}],
            [{'level': 1, 'regex': 'lksjdf'}],
        ]
        for error_list in elists:
            print(error_list)
            self.assertRaises(
                ScriptHarnessException, ErrorList, error_list
            )
