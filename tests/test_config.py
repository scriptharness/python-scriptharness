#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness.config

Attributes:
  TEST_LOG (str): the path to log to
  DICT_NAME (str): the logging dict's name
  RO_CONTROL_DICT (dict): used to prepopulate ReadOnlyDict
  LOGGING_CONTROL_DICT (dict): used to prepopulate LoggingDict
  SECONDARY_DICT (dict): used to add to the LoggingDict
  SECONDARY_LIST (dict): used to add to the LoggingDict
  UNICODE_STRINGS (list): a list of strings to test for unicode support
"""
from contextlib import contextmanager
from copy import deepcopy
import logging
import os
import scriptharness as sh
import scriptharness.config as config
import scriptharness.log as shlog
import unittest


# Constants {{{1
TEST_LOG = "_test_config_log"
LOGGER_NAME = "_test_log"
DICT_NAME = 'LOGD'
# Can only contain scalars, lists, and dicts, or the deepcopy tests will fail
RO_CONTROL_DICT = {
    'a': 1,
    'b': '2',
    'c': {
        'd': '4',
    },
    'd': {
        'turtles': ['turtle1', 'turtle2', 'turtle3'],
    },
    'e': [
        '5', '6', {
            'turtles': ['turtle4', 'turtle5', 'turtle6'],
        },
    ],
}
# Can contain scalars, lists, dicts, and tuples
LOGGING_CONTROL_DICT = {
    'a': 1,
    'b': '2',
    'c': {
        'd': '4',
    },
    'd': {
        'turtles': ['turtle1', 'turtle2', 'turtle3'],
        'yurts': ('yurt1', 'yurt2', 'yurt3'),
    },
    'e': [
        '5', '6', {
            'turtles': ['turtle4', 'turtle5', 'turtle6'],
            'yurts': ('yurt4', 'yurt5', 'yurt6'),
        },
    ],
}
SECONDARY_DICT = {
    'A': 1,
    'B': [1, 2, 3, 'four', (5, 6, 7), 'eight'],
    'C': (9, 10, [11, 12], 13),
    'D': {
        'E': 14,
        'F': [15, 16],
        'G': (17, 18),
    },
}
SECONDARY_LIST = [
    'Z', 'Y',
    (
        'X', 'W', 9,
        {
            'V': 8,
            'U': 7,
        },
    )
]
UNICODE_STRINGS = [
    'ascii',
    '日本語',
    '한국말',
    'हिन्दी',
    'العَرَبِيةُ',
    'ру́сский язы́к',
    'ខេមរភាសា',
]


# Test LoggingDict {{{1
# helper methods {{{2
@contextmanager
def get_logging_dict():
    """Helper function to set up logging for the logging dict
    """
    formatter = shlog.UnicodeFormatter(fmt='%(message)s')
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    handler = shlog.get_file_handler(
        TEST_LOG, mode='w', level=logging.INFO, formatter=formatter
    )
    logger.handlers = []
    logger.addHandler(handler)
    logd = config.LoggingDict(deepcopy(LOGGING_CONTROL_DICT))
    logd.logger_name = LOGGER_NAME
    logd.recursively_set_parent(name=DICT_NAME)
    try:
        yield logd
    finally:
        logger.removeHandler(handler)


# {{{2
class TestLoggingDict(unittest.TestCase):
    """Test LoggingDict's logging methods
    """
    def tearDown(self):
        assert self  # silence pylint
        if os.path.exists(TEST_LOG):
            os.remove(TEST_LOG)

    def verify_log(self, expected, to_unicode=False):
        """Helper function to compare the log vs expected output
        """
        with open(TEST_LOG) as log_fh:
            contents = log_fh.read().rstrip()
        if to_unicode:
            contents = to_unicode(contents)
            expected = to_unicode(expected)
        self.assertEqual(contents, expected)

    def test_setitem(self):
        with get_logging_dict() as logd:
            logd['d'] = 3
        self.verify_log("{}: __setitem__ d to 3".format(DICT_NAME))


# Test ReadOnlyDict {{{1
# helper methods {{{2
def get_unlocked_rod():
    """Helper function to create a known unlocked ReadOnlyDict
    """
    return config.ReadOnlyDict(deepcopy(RO_CONTROL_DICT))

def get_locked_rod():
    """Helper function to create a known locked ReadOnlyDict
    """
    rod = config.ReadOnlyDict(deepcopy(RO_CONTROL_DICT))
    rod.lock()
    return rod

# TestUnlockedROD {{{2
class TestUnlockedROD(unittest.TestCase):
    """Make sure the ReadOnlyDict is read-write before lock()ing.

    A lot of the constructs here include a try/except/else rather than a
    |with self.assertRaises(...):| because we want to support python 2.6.
    """

    def test_create_rod(self):
        """A ROD and the equivalent dict should be equal.
        """
        rod = get_unlocked_rod()
        self.assertEqual(rod, RO_CONTROL_DICT,
                         msg="can't transfer dict to ReadOnlyDict")

    def test_pop_item(self):
        """ROD.popitem() should work when unlocked.
        """
        rod = get_unlocked_rod()
        rod.popitem()
        self.assertEqual(len(rod), len(RO_CONTROL_DICT) - 1,
                         msg="can't popitem() ReadOnlyDict when unlocked")

    def test_pop(self):
        """ROD.pop() should work when unlocked.
        """
        rod = get_unlocked_rod()
        rod.pop('e')
        self.assertEqual(len(rod), len(RO_CONTROL_DICT) - 1,
                         msg="can't pop() ReadOnlyDict when unlocked")

    def test_del(self):
        """Del a key when unlocked
        """
        rod = get_unlocked_rod()
        del rod['e']
        self.assertEqual(len(rod), len(RO_CONTROL_DICT) - 1,
                         msg="can't del in ReadOnlyDict when unlocked")

    def test_clear(self):
        """Clear the dict when unlocked
        """
        rod = get_unlocked_rod()
        rod.clear()
        self.assertEqual(rod, {},
                         msg="can't clear() ReadOnlyDict when unlocked")

    def test_update(self):
        """Update the dict when unlocked
        """
        rod = get_unlocked_rod()
        dict2 = {
            'q': 'blah',
        }
        rod.update(dict2)
        dict2.update(RO_CONTROL_DICT)
        self.assertEqual(rod, dict2,
                         msg="can't update() ReadOnlyDict when unlocked")

    def test_set_default(self):
        """setdefault() when unlocked
        """
        rod = config.ReadOnlyDict()
        for key in RO_CONTROL_DICT.keys():
            rod.setdefault(key, RO_CONTROL_DICT[key])
        self.assertEqual(rod, RO_CONTROL_DICT,
                         msg="can't setdefault() ReadOnlyDict when unlocked")


# TestLockedROD {{{2
class TestLockedROD(unittest.TestCase):
    """Make sure the ReadOnlyDict is read-only after lock()ing.
    """
    def test_set(self):
        """locked list shouldn't have a __setitem__
        """
        rod = get_locked_rod()
        self.assertFalse(hasattr(rod['e'], '__setitem__'))

    def test_del(self):
        """locked list shouldn't have a __delitem__
        """
        rod = get_locked_rod()
        self.assertFalse(hasattr(rod['e'], '__delitem__'))

    def test_popitem(self):
        """locked popitem() should raise
        """
        rod = get_locked_rod()
        self.assertRaises(sh.ScriptHarnessException, rod.popitem)

    def test_update(self):
        """locked update() should raise
        """
        rod = get_locked_rod()
        self.assertRaises(sh.ScriptHarnessException, rod.update, {})

    def test_set_default(self):
        """locked setdefault() should raise
        """
        rod = get_locked_rod()
        self.assertRaises(sh.ScriptHarnessException, rod.setdefault, {})

    def test_pop(self):
        """locked pop() should raise
        """
        rod = get_locked_rod()
        self.assertRaises(sh.ScriptHarnessException, rod.pop)

    def test_clear(self):
        """locked clear() should raise
        """
        rod = get_locked_rod()
        self.assertRaises(sh.ScriptHarnessException, rod.clear)

    def test_second_level_dict_update(self):
        """locked child dict update() should raise
        """
        rod = get_locked_rod()
        self.assertRaises(sh.ScriptHarnessException, rod['c'].update, {})

    def test_second_level_list_pop(self):
        """locked child list pop() should raise
        """
        rod = get_locked_rod()
        self.assertFalse(hasattr(rod['e'], 'pop'))

    def test_third_level_mutate(self):
        """locked child list-in-dict append() should raise
        """
        rod = get_locked_rod()
        self.assertFalse(hasattr(rod['d']['turtles'], 'append'))

    def test_object_in_tuple_mutate(self):
        """locked child list-in-tuple append() should raise
        """
        rod = get_locked_rod()
        self.assertFalse(hasattr(rod['e'][2]['turtles'], 'append'))


# TestDeepcopyROD {{{2
class TestDeepcopyROD(unittest.TestCase):
    """Make sure deepcopy behaves properly on ReadOnlyDict
    """
    def test_deepcopy_equality(self):
        """deepcopy of locked rod should equal the original rod
        """
        rod = get_locked_rod()
        rod2 = deepcopy(rod)
        self.assertEqual(
            rod2, RO_CONTROL_DICT,
            msg="ReadOnlyDict deepcopy is not equal to original dict!"
        )

    def test_deepcopy_set(self):
        """deepcopy of locked rod should be read-write
        """
        rod = get_locked_rod()
        rod2 = deepcopy(rod)
        rod2['e'] = 'hey'
        self.assertEqual(rod2['e'], 'hey', "can't set var in rod2 after deepcopy")

    def test_deepcopy_new_lock(self):
        """deepcopy of locked rod should be lockable
        """
        rod = get_locked_rod()
        rod2 = deepcopy(rod)
        rod2.lock()
        with self.assertRaises(sh.ScriptHarnessException):
            rod2['e'] = 'hey'
