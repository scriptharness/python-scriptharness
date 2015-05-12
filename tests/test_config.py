#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness.config

Attributes:
  TEST_LOG (str): the path to log to
  TEST_NAME (str): the logging dict/list's name
  RO_CONTROL_DICT (dict): used to prepopulate ReadOnlyDict
  LOGGING_CONTROL_DICT (dict): used to prepopulate LoggingDict
  LOGGING_CONTROL_LIST (list): used to prepopulate LoggingList
  SECONDARY_DICT (dict): used to add to the LoggingDict
  SECONDARY_LIST (dict): used to add to the LoggingDict
  UNICODE_STRINGS (list): a list of strings to test for unicode support

  TODO fix add_logging_to_obj recursion
  TODO move config strings to a dict for easier testing
"""
from copy import deepcopy
import mock
import pprint
import scriptharness as sh
import scriptharness.config as config
import unittest


# Constants {{{1
TEST_LOG = "_test_config_log"
LOGGER_NAME = "scriptharness.test_config"
NAME = 'LOG'
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
LOGGING_CONTROL_LIST = [
    1,
    2,
    3,
    4,
    'five',
    6,
    7,
    ['1', 2, 'three'],
    'finally',
]
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
def get_logging_dict(name=NAME):
    """Helper function to set up logging for the logging dict
    """
    logdict = config.LoggingDict(deepcopy(LOGGING_CONTROL_DICT))
    logdict.logger_name = LOGGER_NAME
    logdict.recursively_set_parent(name=name)
    return logdict

def get_logging_list(name=NAME, values=None):
    """Helper function to set up logging for the logging dict

    Don't set name, for easier log testing
    """
    if values is None:
        values = LOGGING_CONTROL_LIST
    loglist = config.LoggingList(deepcopy(values))
    loglist.recursively_set_parent(name=name)
    return loglist


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


class TestLoggingClass(unittest.TestCase):
    """Test LoggingDict's logging methods

    Attributes:
      logger (LoggerReplacement): the LoggerReplacement for the running test
    """
    logger = None

    def get_logger_replacement(self, mock_logging):
        """Replace logging.getLogger() with LoggerReplacement
        """
        self.logger = LoggerReplacement()
        mock_logging.getLogger.return_value = self.logger
        return self.logger

    def verify_log(self, expected):
        """Helper function to compare the log vs expected output
        """
        self.assertEqual(self.logger.all_messages, expected)


# TestFullNames {{{2
class TestFullNames(unittest.TestCase):
    """Test LoggingClass.full_name()
    """
    def test_no_name(self):
        """The name should be None if not set explicitly
        """
        logdict = get_logging_dict(name=None)
        self.assertEqual(logdict.full_name(), "")

    def test_logdict_names(self):
        """get_logging_dict() should return a logdict with name NAME
        """
        logdict = get_logging_dict()
        self.assertEqual(logdict.full_name(), NAME)
        self.assertEqual(logdict['e'].full_name(), "%s['e']" % NAME)
        self.assertEqual(logdict['d']['turtles'].full_name(),
                         "%s['d']['turtles']" % NAME)
        self.assertEqual(logdict['d']['yurts'].full_name(),
                         "%s['d']['yurts']" % NAME)
        self.assertEqual(logdict['e'][2].full_name(),
                         "%s['e'][2]" % NAME)
        self.assertEqual(logdict['e'][2]['turtles'].full_name(),
                         "%s['e'][2]['turtles']" % NAME)
        self.assertEqual(logdict['e'][2]['yurts'].full_name(),
                         "%s['e'][2]['yurts']" % NAME)

    def test_unicode_names(self):
        """Try unicode names!
        """
        logdict = get_logging_dict()
        for string in UNICODE_STRINGS:
            logdict[string] = {}
            self.assertEqual(logdict[string].full_name(),
                             "%s['%s']" % (NAME, string))
            logdict[string][string] = []
            self.assertEqual(logdict[string][string].full_name(),
                             "%s['%s']['%s']" % (NAME, string, string))
            logdict[string][string].append({string: []})
            self.assertEqual(
                logdict[string][string][0][string].full_name(),
                "%s['%s']['%s'][0]['%s']" % (NAME, string, string, string)
            )

    def test_quotes(self):
        """Try names with quotes in them.

        Expected behavior: use the quotes in config.QUOTES in preferred order,
        moving on to the next if all the preceding quote types are in the name.
        If all quote types are in the name, don't use any quotes.
        """
        name = ''
        logdict = get_logging_dict()
        for position, value in enumerate(config.QUOTES):
            name += value
            expected = name
            if position + 1 < len(config.QUOTES):
                expected = "%s%s%s" % (config.QUOTES[position + 1], name,
                                       config.QUOTES[position + 1])
            logdict[name] = []
            self.assertEqual(logdict[name].full_name(),
                             "%s[%s]" % (NAME, expected))

# TestLoggingDeepcopy {{{2
class TestLoggingDeepcopy(unittest.TestCase):
    """Test deepcopy of the various Logging* classes
    """
    def test_list(self):
        """deepcopy(LoggingList) should return a non-logging list
        """
        loglist = get_logging_list()
        dup = deepcopy(loglist)
        self.assertEqual(LOGGING_CONTROL_LIST, dup)

    def test_dict(self):
        """deepcopy(LoggingDict) should return a non-logging dict
        """
        logdict = get_logging_dict()
        dup = deepcopy(logdict)
        self.assertEqual(LOGGING_CONTROL_DICT, dup)

    def test_tuple(self):
        """deepcopy(LoggingTuple) should return a non-logging tuple
        """
        logtuple = config.add_logging_to_obj(
            tuple(LOGGING_CONTROL_LIST)
        )
        self.assertTrue(isinstance(logtuple, config.LoggingClass))
        dup = deepcopy(logtuple)
        self.assertEqual(tuple(LOGGING_CONTROL_LIST), dup)


# TestLoggingDict {{{2
class TestLoggingDict(TestLoggingClass):
    """Test LoggingDict's logging methods

    Attributes:
      strings (dict): strings to test with
    """
    strings = deepcopy(config.LOGGING_STRINGS['dict'])

    @mock.patch('scriptharness.config.logging')
    def test_setitem(self, mock_logging):
        """Test logging dict setitem
        """
        self.get_logger_replacement(mock_logging)
        logdict = get_logging_dict(name=None)
        logdict['d'] = {}
        self.verify_log([
            self.strings['setitem'] % {'key': 'd', 'value': {}},
        ])
        self.assertTrue(isinstance(logdict['d'], config.LoggingClass))

    @mock.patch('scriptharness.config.logging')
    def test_delitem(self, mock_logging):
        """Test logging dict delitem
        """
        self.get_logger_replacement(mock_logging)
        logdict = get_logging_dict(name=None)
        del logdict['d']
        self.verify_log([
            self.strings['delitem'] % {'key': 'd'}
        ])
        self.assertEqual(logdict.get('d'), None)

    @mock.patch('scriptharness.config.logging')
    def test_clear(self, mock_logging):
        """Test logging dict clear
        """
        self.get_logger_replacement(mock_logging)
        logdict = get_logging_dict(name=None)
        logdict.clear()
        self.verify_log([self.strings['clear']])
        self.assertEqual(logdict, {})


# TestLoggingList {{{2
class TestLoggingList(TestLoggingClass):
    """Test LoggingList's logging methods

    Attributes:
      strings (dict): strings to test with
    """
    strings = deepcopy(config.LOGGING_STRINGS['list'])

    @mock.patch('scriptharness.config.logging')
    def test_delitem(self, mock_logging):
        """Test logging list delitem
        """
        for item in (2, 1, slice(0, 3), len(LOGGING_CONTROL_LIST) - 1):
            loglist = get_logging_list(name=None)
            self.get_logger_replacement(mock_logging)
            del loglist[item]
            self.verify_log([
                self.strings['delitem'] % {"item": item},
                self.strings['log_self'] % {"self": pprint.pformat(loglist)}
            ])

    @mock.patch('scriptharness.config.logging')
    def test_setitem(self, mock_logging):
        """Test logging list setitem
        """
        for position in 2, 1:
            self.get_logger_replacement(mock_logging)
            loglist = get_logging_list(name=None)
            loglist[position] = []
            self.verify_log([
                self.strings['setitem'] % {
                    "position": position,
                    "item": [],
                },
                self.strings['log_self'] % {"self": pprint.pformat(loglist)}
            ])
            self.assertTrue(isinstance(loglist[position], config.LoggingClass))

    @mock.patch('scriptharness.config.logging')
    def test_append(self, mock_logging):
        """Test logging list append
        """
        self.get_logger_replacement(mock_logging)
        loglist = get_logging_list(name=None)
        loglist.append({})
        self.verify_log([
            self.strings['append'] % {
                "item": {},
            },
            self.strings['log_self'] % {"self": pprint.pformat(loglist)}
        ])
        self.assertTrue(isinstance(loglist[-1], config.LoggingClass))

    @mock.patch('scriptharness.config.logging')
    def test_extend(self, mock_logging):
        """Test logging list extend
        """
        self.get_logger_replacement(mock_logging)
        loglist = get_logging_list(name=None)
        extend = ['a', 'b', {}]
        loglist.extend(extend)
        self.verify_log([
            self.strings['extend'] % {
                "item": pprint.pformat(extend)
            },
            self.strings['log_self'] % {"self": pprint.pformat(loglist)}
        ])
        self.assertTrue(isinstance(loglist[-1], config.LoggingClass))

    @mock.patch('scriptharness.config.logging')
    def test_insert(self, mock_logging):
        """Test logging list insert
        """
        for position in (0, 3, len(LOGGING_CONTROL_LIST)):
            self.get_logger_replacement(mock_logging)
            loglist = get_logging_list(name=None)
            item = ['a']
            loglist.insert(position, item)
            self.verify_log([
                self.strings['insert'] % {
                    "position": position,
                    "item": item,
                },
                self.strings['log_self'] % {"self": pprint.pformat(loglist)}
            ])
            self.assertTrue(isinstance(loglist[position], config.LoggingClass))

    @mock.patch('scriptharness.config.logging')
    def test_remove(self, mock_logging):
        """Test logging list remove
        """
        for item in (1, 2, "finally"):
            self.get_logger_replacement(mock_logging)
            loglist = get_logging_list(name=None)
            loglist.remove(item)
            self.verify_log([
                self.strings['remove'] % {
                    "item": item,
                },
                self.strings['log_self'] % {"self": pprint.pformat(loglist)}
            ])
            self.assertRaises(ValueError, loglist.index, item)

    @mock.patch('scriptharness.config.logging')
    def test_pop_no_args(self, mock_logging):
        """Test logging list pop with no args
        """
        self.get_logger_replacement(mock_logging)
        loglist = get_logging_list(name=None)
        length = len(loglist)
        loglist.pop()
        self.verify_log([
            self.strings['pop_no_args'],
            self.strings['log_self'] % {"self": pprint.pformat(loglist)}
        ])
        self.assertEqual(length - 1, len(loglist))

    @mock.patch('scriptharness.config.logging')
    def test_pop_args(self, mock_logging):
        """Test logging list pop with args
        """
        for position in (0, 3, len(LOGGING_CONTROL_LIST) - 1):
            self.get_logger_replacement(mock_logging)
            loglist = get_logging_list(name=None)
            length = len(loglist)
            loglist.pop(position)
            self.verify_log([
                self.strings['pop_args'] % {
                    "position": position,
                },
                self.strings['log_self'] % {"self": pprint.pformat(loglist)}
            ])
            self.assertEqual(length - 1, len(loglist))

    @mock.patch('scriptharness.config.logging')
    def test_sort(self, mock_logging):
        """Test logging list sort
        """
        self.get_logger_replacement(mock_logging)
        loglist = get_logging_list(name=None, values=[9, 3, 4, 0])
        loglist.sort()
        self.verify_log([
            self.strings['sort'],
            self.strings['log_self'] % {"self": pprint.pformat(loglist)}
        ])
        self.assertEqual(loglist[-1], 9)

    @mock.patch('scriptharness.config.logging')
    def test_reverse(self, mock_logging):
        """Test logging list reverse
        """
        self.get_logger_replacement(mock_logging)
        loglist = get_logging_list(name=None)
        loglist.reverse()
        self.verify_log([
            self.strings['reverse'],
            self.strings['log_self'] % {"self": pprint.pformat(loglist)}
        ])
        self.assertEqual(loglist[0], "finally")

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
