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

  TODO fix add_logging_to_obj recursion
  TODO move config strings to a dict for easier testing
"""
from copy import deepcopy
import mock
import scriptharness as sh
import scriptharness.config as config
import unittest


# Constants {{{1
TEST_LOG = "_test_config_log"
LOGGER_NAME = "scriptharness.test_config"
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
    'e': ['5', '6', {
        'turtles': ['turtle4', 'turtle5', 'turtle6'],
    }],
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
    'e': ['5', '6', {
        'turtles': ['turtle4', 'turtle5', 'turtle6'],
        'yurts': ('yurt4', 'yurt5', 'yurt6'),
    }],
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
def get_logging_dict():
    """Helper function to set up logging for the logging dict
    """
    logd = config.LoggingDict(deepcopy(LOGGING_CONTROL_DICT))
    logd.logger_name = LOGGER_NAME
    logd.recursively_set_parent(name=DICT_NAME)
    return logd

class LoggerReplacement(object):
    """A replacement logging.Logger to more easily test

    Attributes:
        all_messages (list): a list of all messages sent to log()
    """
    def __init__(self):
        super(LoggerReplacement, self).__init__()
        self.all_messages = []

    def log(self, _, msg, *args):
        """Keep track of all calls to logger.log()

        self.all_messages gets a list of all (msg, *args).
        """
        if args:
            msg = msg % args[0]
        self.all_messages.append(msg)

    def silence_pylint(self):
        """pylint complains about too few public methods"""
        pass

def get_logger_replacement(mock_logging):
    """Replace logging.getLogger() with LoggerReplacement
    """
    logger = LoggerReplacement()
    mock_logging.getLogger.return_value = logger
    return logger


# TestFullNames {{{2
class TestFullNames(unittest.TestCase):
    """Test LoggingClass.full_name()
    """
    def test_no_name(self):
        """The name should be None if not set explicitly
        """
        logd = config.LoggingDict(deepcopy(LOGGING_CONTROL_DICT))
        logd.recursively_set_parent()
        self.assertEqual(logd.full_name(), "")

    def test_logd_names(self):
        """get_logging_dict() should return a logd with name DICT_NAME
        """
        logd = get_logging_dict()
        self.assertEqual(logd.full_name(), DICT_NAME)
        self.assertEqual(logd['e'].full_name(), "%s['e']" % DICT_NAME)
        self.assertEqual(logd['d']['turtles'].full_name(),
                         "%s['d']['turtles']" % DICT_NAME)
        self.assertEqual(logd['d']['yurts'].full_name(),
                         "%s['d']['yurts']" % DICT_NAME)
        self.assertEqual(logd['e'][2].full_name(),
                         "%s['e'][2]" % DICT_NAME)
        self.assertEqual(logd['e'][2]['turtles'].full_name(),
                         "%s['e'][2]['turtles']" % DICT_NAME)
        self.assertEqual(logd['e'][2]['yurts'].full_name(),
                         "%s['e'][2]['yurts']" % DICT_NAME)

    def test_unicode_names(self):
        """Try unicode names!
        """
        logd = get_logging_dict()
        for string in UNICODE_STRINGS:
            logd[string] = {}
            self.assertEqual(logd[string].full_name(),
                             "%s['%s']" % (DICT_NAME, string))
            logd[string][string] = []
            self.assertEqual(logd[string][string].full_name(),
                             "%s['%s']['%s']" % (DICT_NAME, string, string))
            logd[string][string].append({string: []})
            self.assertEqual(
                logd[string][string][0][string].full_name(),
                "%s['%s']['%s'][0]['%s']" % (DICT_NAME, string, string, string)
            )

    def test_quotes(self):
        """Try names with quotes in them.

        Expected behavior: use the quotes in config.QUOTES in preferred order,
        moving on to the next if all the preceding quote types are in the name.
        If all quote types are in the name, don't use any quotes.
        """
        name = ''
        logd = get_logging_dict()
        for position, value in enumerate(config.QUOTES):
            name += value
            expected = name
            if position + 1 < len(config.QUOTES):
                expected = "%s%s%s" % (config.QUOTES[position + 1], name,
                                       config.QUOTES[position + 1])
            logd[name] = []
            self.assertEqual(logd[name].full_name(),
                             "%s[%s]" % (DICT_NAME, expected))


# TestLoggingDict {{{2
class TestLoggingDict(unittest.TestCase):
    """Test LoggingDict's logging methods

    Attributes:
      logger (LoggerReplacement): the LoggerReplacement for the running test
    """
    logger = None
    def verify_log(self, expected):
        """Helper function to compare the log vs expected output
        """
        self.assertEqual(self.logger.all_messages, expected)

    @mock.patch('scriptharness.config.logging')
    def test_setitem(self, mock_logging):
        """Test logging dict setitem
        """
        self.logger = get_logger_replacement(mock_logging)
        logd = get_logging_dict()
        logd['d'] = 3
        self.verify_log(["{}: __setitem__ d to 3".format(DICT_NAME)])

    @mock.patch('scriptharness.config.logging')
    def test_delitem(self, mock_logging):
        """Test logging dict delitem
        """
        self.logger = get_logger_replacement(mock_logging)
        logd = get_logging_dict()
        del logd['d']
        self.verify_log(["{}: __delitem__ d".format(DICT_NAME)])


# Test add_logging_to_obj() {{{2
class TestAddLogging(unittest.TestCase):
    """Test the portions of add_logging_to_class() that we're not testing
    in other ways
    """
    def test_recursion(self):
        """Known issue: recursion in add_logging_to_obj raises RuntimeError
        Rewrite test when this is fixed.
        """
        one = {}
        two = {}
        one['two'] = two
        two['one'] = one
        three = []
        four = []
        three.append(four)
        four.append(three)
        self.assertRaises(RuntimeError, config.add_logging_to_obj, one)
        self.assertRaises(RuntimeError, config.add_logging_to_obj, two)
        self.assertRaises(RuntimeError, config.add_logging_to_obj, three)
        self.assertRaises(RuntimeError, config.add_logging_to_obj, four)


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
