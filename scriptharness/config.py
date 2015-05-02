#!/usr/bin/env python
'''
Allow for flexible configuration.
'''

from __future__ import absolute_import, division, print_function
from copy import deepcopy
from scriptharness import ScriptHarnessException
#import logging
#try:
#    import simplejson as json
#except ImportError:
#    import json


# ReadOnlyDict {{{1
def make_immutable(item):
    '''
    In order to lock ReadOnlyDict, we also have to lock any children of
    ReadOnlyDict (for example, if r is a ReadOnlyDict that looks like

        {
            'a': 1,
            'b': ['contents', 'of', 'b'],
            'c': {
                'key': 'value',
            },
        }

    and we locked r on a shallow level, we could still r['b'].append() or
    r['c']['key2'] = 'value2'.  So to avoid that, we need to recursively
    lock r via make_immutable.

    Taken from mozharness, but added LockedFrozenSet.
    '''
    if isinstance(item, list) or isinstance(item, tuple):
        result = LockedTuple(item)
    elif isinstance(item, dict):
        result = ReadOnlyDict(item)
        result.lock()
    elif isinstance(item, set) or isinstance(item, frozenset):
        result = LockedFrozenSet(item)
    else:
        result = item
    return result


class LockedTuple(tuple):
    '''
    Tuples are read-only by nature, but we need to be able to recursively lock
    the contents of the tuple, since the tuple can contain dicts or lists.

    Taken straight from mozharness.
    '''
    def __new__(cls, items):
        return tuple.__new__(cls, (make_immutable(x) for x in items))
    def __deepcopy__(self, memo):
        return [deepcopy(elem, memo) for elem in self]


class LockedFrozenSet(frozenset):
    '''
    Frozensets are read-only by nature, but we need to be able to recursively
    lock the contents of the frozenset, since the frozenset can contain dicts
    or lists.
    '''
    def __new__(cls, items):
        return frozenset.__new__(cls, (make_immutable(x) for x in items))
    def __deepcopy__(self, memo):
        return set([deepcopy(elem, memo) for elem in self])


class ReadOnlyDict(dict):
    '''
    Slightly modified version of mozharness.base.config.ReadOnlyDict,
    largely for pylint.
    '''
    def __init__(self, *args, **kwargs):
        self._lock = False
        super(ReadOnlyDict, self).__init__(*args, **kwargs)

    def _check_lock(self):
        '''
        Throw an exception if we try to change anything while locked.
        '''
        if self._lock:
            raise ScriptHarnessException("ReadOnlyDict is locked!")

    def lock(self):
        '''
        Recursively lock the dictionary.
        '''
        for (key, value) in self.items():
            self[key] = make_immutable(value)
        self._lock = True

    def __setitem__(self, *args):
        self._check_lock()
        return super(ReadOnlyDict, self).__setitem__(*args)

    def __delitem__(self, *args):
        self._check_lock()
        return super(ReadOnlyDict, self).__delitem__(*args)

    def clear(self, *args):
        self._check_lock()
        return super(ReadOnlyDict, self).clear(*args)

    def pop(self, *args):
        self._check_lock()
        return super(ReadOnlyDict, self).pop(*args)

    def popitem(self, *args):
        self._check_lock()
        return super(ReadOnlyDict, self).popitem(*args)

    def setdefault(self, *args):
        self._check_lock()
        return super(ReadOnlyDict, self).setdefault(*args)

    def update(self, *args):
        self._check_lock()
        return super(ReadOnlyDict, self).update(*args)

    def __deepcopy__(self, memo):
        '''
        Create an unlocked ReadOnlyDict on deepcopy()
        '''
        result = self.__class__()
        memo[id(self)] = result
        for key, value in self.items():
            result[key] = deepcopy(value, memo)
        return result
