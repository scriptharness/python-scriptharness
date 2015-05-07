#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Test scriptharness/__init__.py
'''

import scriptharness as sh
import unittest


# TestVersionString {{{1
class TestVersionString(unittest.TestCase):
    '''
    Test the various semver version->version string conversions
    '''
    def test_three_version(self):
        '''
        3 digit tuple -> version string
        '''
        test_dict = {
            '0.1.0': (0, 1, 0),
            '1.2.3': (1, 2, 3),
            '4.1.5': (4, 1, 5),
        }
        for key, value in test_dict.items():
            self.assertEqual(sh.get_version_string(value), key)

    def test_illegal_three_version(self):
        '''
        Raise if a 3-len tuple has a non-digit
        '''
        self.assertRaises(
            TypeError, sh.get_version_string, (('one', 'two', 'three'))
        )

    def test_four_version(self):
        '''
        3 digit + string tuple -> version string
        '''
        self.assertEqual(
            sh.get_version_string((0, 1, 0, 'alpha')), '0.1.0-alpha'
        )

    def test_illegal_len_version(self):
        '''
        Raise if len(version) not in (3, 4)
        '''
        test_versions = (
            (0, ),
            (0, 1),
            (0, 1, 0, 'alpha', 'beta'),
        )
        for version in test_versions:
            self.assertRaises(
                sh.ScriptHarnessException, sh.get_version_string, (version, )
            )
