#!/usr/bin/env python
'''
Test scriptharness.config
'''
from copy import deepcopy
import unittest

import scriptharness.config as config
from scriptharness import ScriptHarnessException


CONTROL_DICT = {
    'b': '2',
    'c': {
        'd': '4',
    },
    'd': {
        'turtles': ['turtle1']
    },
    'e': [
        'f', 'g', {
            'turtles': ['turtle1']
        },
    ],
}

# Test ReadOnlyDict {{{1
# helper methods {{{2
def get_unlocked_rod():
    '''
    Helper function to create a known unlocked ReadOnlyDict
    '''
    return config.ReadOnlyDict(deepcopy(CONTROL_DICT))

def get_locked_rod():
    '''
    Helper function to create a known locked ReadOnlyDict
    '''
    rod = config.ReadOnlyDict(deepcopy(CONTROL_DICT))
    rod.lock()
    return rod

# TestUnlockedROD {{{2
class TestUnlockedROD(unittest.TestCase):
    '''
    Make sure the ReadOnlyDict is read-write before lock()ing.

    A lot of the constructs here include a try/except/else rather than a
    |with self.assertRaises(...):| because we want to support python 2.6.
    '''

    def test_create_rod(self):
        '''
        A ROD and the equivalent dict should be equal.
        '''
        rod = get_unlocked_rod()
        self.assertEqual(rod, CONTROL_DICT,
                         msg="can't transfer dict to ReadOnlyDict")

    def test_pop_item(self):
        '''
        ROD.popitem() should work when unlocked.
        '''
        rod = get_unlocked_rod()
        rod.popitem()
        self.assertEqual(len(rod), len(CONTROL_DICT) - 1,
                         msg="can't popitem() ReadOnlyDict when unlocked")

    def test_pop(self):
        '''
        ROD.pop() should work when unlocked.
        '''
        rod = get_unlocked_rod()
        rod.pop('e')
        self.assertEqual(len(rod), len(CONTROL_DICT) - 1,
                         msg="can't pop() ReadOnlyDict when unlocked")

    def test_del(self):
        '''
        Del a key when unlocked
        '''
        rod = get_unlocked_rod()
        del rod['e']
        self.assertEqual(len(rod), len(CONTROL_DICT) - 1,
                         msg="can't del in ReadOnlyDict when unlocked")

    def test_clear(self):
        '''
        Clear the dict when unlocked
        '''
        rod = get_unlocked_rod()
        rod.clear()
        self.assertEqual(rod, {},
                         msg="can't clear() ReadOnlyDict when unlocked")

    def test_update(self):
        '''
        Update the dict when unlocked
        '''
        rod = get_unlocked_rod()
        dict2 = {
            'q': 'blah',
        }
        rod.update(dict2)
        dict2.update(CONTROL_DICT)
        self.assertEqual(rod, dict2,
                         msg="can't update() ReadOnlyDict when unlocked")

    def test_set_default(self):
        '''
        setdefault() when unlocked
        '''
        rod = config.ReadOnlyDict()
        for key in CONTROL_DICT.keys():
            rod.setdefault(key, CONTROL_DICT[key])
        self.assertEqual(rod, CONTROL_DICT,
                         msg="can't setdefault() ReadOnlyDict when unlocked")


# TestLockedROD {{{2
class TestLockedROD(unittest.TestCase):
    '''
    Make sure the ReadOnlyDict is read-only after lock()ing.

    A lot of the constructs here include a try/except/else rather than a
    |with self.assertRaises(...):| because we want to support python 2.6.
    '''
    def test_set(self):
        '''
        locked set() should raise
        '''
        rod = get_locked_rod()
        try:
            rod['e'] = 2
        except ScriptHarnessException:
            pass
        else:
            self.assertEqual(0, 1, msg="can set rod['e'] when locked")

    def test_del(self):
        '''
        locked del should raise
        '''
        rod = get_locked_rod()
        try:
            del rod['e']
        except ScriptHarnessException:
            pass
        else:
            self.assertEqual(0, 1, "can del rod['e'] when locked")

    def test_popitem(self):
        '''
        locked popitem() should raise
        '''
        rod = get_locked_rod()
        self.assertRaises(ScriptHarnessException, rod.popitem)

    def test_update(self):
        '''
        locked update() should raise
        '''
        rod = get_locked_rod()
        self.assertRaises(ScriptHarnessException, rod.update, {})

    def test_set_default(self):
        '''
        locked setdefault() should raise
        '''
        rod = get_locked_rod()
        self.assertRaises(ScriptHarnessException, rod.setdefault, {})

    def test_pop(self):
        '''
        locked pop() should raise
        '''
        rod = get_locked_rod()
        self.assertRaises(ScriptHarnessException, rod.pop)

    def test_clear(self):
        '''
        locked clear() should raise
        '''
        rod = get_locked_rod()
        self.assertRaises(ScriptHarnessException, rod.clear)

    def test_second_level_dict_update(self):
        '''
        locked child dict update() should raise
        '''
        rod = get_locked_rod()
        self.assertRaises(ScriptHarnessException, rod['c'].update, {})

    def test_second_level_list_pop(self):
        '''
        locked child list pop() should raise
        '''
        rod = get_locked_rod()
        try:
            rod['e'].pop()
        except AttributeError:
            pass
        else:
            self.assertEqual(0, 1, "can pop rod['e'] when locked")

    def test_third_level_mutate(self):
        '''
        locked child list-in-dict append() should raise
        '''
        rod = get_locked_rod()
        try:
            rod['d']['turtles'].append('turtle2')
        except AttributeError:
            pass
        else:
            self.assertEqual(0, 1, "can modify list-in-dict when locked")

    def test_object_in_tuple_mutate(self):
        '''
        locked child list-in-tuple append() should raise
        '''
        rod = get_locked_rod()
        try:
            rod['e'][2]['turtles'].append('turtle2')
        except AttributeError:
            pass
        else:
            self.assertEqual(0, 1, "can append to list-in-tuple when locked")


# TestDeepcopyROD {{{2
class TestDeepcopyROD(unittest.TestCase):
    '''
    Make sure deepcopy behaves properly on ReadOnlyDict
    '''
    def test_deepcopy_equality(self):
        '''
        deepcopy of locked rod should equal the original rod
        '''
        rod = get_locked_rod()
        rod2 = deepcopy(rod)
        self.assertEqual(
            rod2, CONTROL_DICT,
            msg="ReadOnlyDict deepcopy is not equal to original dict!"
        )

    def test_deepcopy_set(self):
        '''
        deepcopy of locked rod should be read-write
        '''
        rod = get_locked_rod()
        rod2 = deepcopy(rod)
        rod2['e'] = 'hey'
        self.assertEqual(rod2['e'], 'hey', "can't set var in rod2 after deepcopy")

    def test_deepcopy_new_lock(self):
        '''
        deepcopy of locked rod should be lockable
        '''
        rod = get_locked_rod()
        rod2 = deepcopy(rod)
        rod2.lock()
        try:
            rod2['e'] = 'hey'
        except ScriptHarnessException:
            pass
        else:
            self.assertEqual(0, 1, "can set var in rod2 after deepcopy + lock")
