#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/__init__.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
from scriptharness.unicode import to_unicode
import six
import unittest
from . import UNICODE_STRINGS


# TestUnicode {{{1
class TestUnicode(unittest.TestCase):
    """Test unicode support.
    """
    def test_to_unicode(self):
        """test_unicode | Verify to_unicode gives a unicode string
        """
        for ustring in UNICODE_STRINGS:
            astring = to_unicode(ustring)
            if six.PY2 and not isinstance(ustring, six.text_type):
                self.assertEqual(ustring.decode('utf-8'), astring)
            else:
                self.assertEqual(ustring, astring)

    def test_to_unicode_none(self):
        """test_unicode | Verify to_unicode of a None object gives None
        """
        value = to_unicode(None)
        self.assertTrue(value is None)
