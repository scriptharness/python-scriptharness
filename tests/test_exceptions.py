#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/__init__.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals

import scriptharness.exceptions as exceptions
import six
import unittest
from . import UNICODE_STRINGS


# TestUnicode {{{1
class TestUnicode(unittest.TestCase):
    """Test unicode support.
    """
    def test_exception(self):
        """test_exceptions | Verify ScriptHarnessBaseException works
        """
        for ustring in UNICODE_STRINGS:
            for exception in (exceptions.ScriptHarnessBaseException,
                              exceptions.ScriptHarnessFatal):
                exc = exception(ustring)
                if six.PY2:
                    if not isinstance(ustring, six.text_type):
                        self.assertEqual(ustring, str(exc))
                    else:
                        self.assertEqual(ustring, six.text_type(exc))
                else:
                    self.assertEqual(ustring, str(exc))
