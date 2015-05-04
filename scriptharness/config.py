#!/usr/bin/env python
"""Allow for flexible configuration.

There are two config dict models here:: one is to recursively lock the
dictionary.  This is to aid in debugging; one can assume the config hasn't
changed from the moment of locking.  This is the original mozharness model.

The other model is to log any changes to the dict or its children.  When
debugging, config changes will be marked in the log.

Attributes:
  SUPPORTED_LOGGING_TYPES (dict): a non-logging to logging class map, e.g.
    dict: LoggingDict.  Not yet supporting collections / OrderedDicts.
"""

from __future__ import absolute_import, division, print_function
from copy import deepcopy
from scriptharness import ScriptHarnessException
import logging
#try:
#    import simplejson as json
#except ImportError:
#    import json


# LoggingDict and helpers {{{1
# logging classes {{{2
class LoggingList(list):
    """A list that logs any changes, as do its children.
    """
    def __new__(cls, items, logger_name='scriptharness.config',
                level=logging.INFO):
        self = list.__new__(
            cls,
            (enable_logging(x, logger_name, level) for x in items)
        )
        self.logger_name = logger_name
        self.level = level
        return self
    def __deepcopy__(self, memo):
        """Return a list on deepcopy.
        """
        return [deepcopy(elem, memo) for elem in self]  # pragma: no branch
    # TODO add logging

class LoggingTuple(tuple):
    """A tuple whose children log any changes.
    """
    def __new__(cls, items, logger_name='scriptharness.config',
                level=logging.INFO):
        self = tuple.__new__(
            cls,
            (enable_logging(x, logger_name, level) for x in items)
        )
        self.logger_name = logger_name
        self.level = level
        return self
    def __deepcopy__(self, memo):
        """Return a tuple on deepcopy.
        """
        return tuple(  # pragma: no branch
            [deepcopy(elem, memo) for elem in self]
        )

class LoggingSet(set):
    """A set that logs any changes, as do its children.
    """
    def __new__(cls, items, logger_name='scriptharness.config',
                level=logging.INFO):
        self = set.__new__(
            cls, (enable_logging(x, logger_name, level) for x in items)
        )
        self.logger_name = logger_name
        self.level = level
        return self
    def __deepcopy__(self, memo):
        """Return a set on deepcopy.
        """
        return set(  # pragma: no branch
            [deepcopy(elem, memo) for elem in self]
        )
    # TODO add logging

class LoggingFrozenSet(frozenset):
    """A frozenset whose children log any changes.
    """
    def __new__(cls, items, logger_name='scriptharness.config',
                level=logging.INFO):
        self = frozenset.__new__(
            cls, (enable_logging(x, logger_name, level) for x in items)
        )
        self.logger_name = logger_name
        self.level = level
        return self
    def __deepcopy__(self, memo):
        """Return a set on deepcopy.
        """
        return frozenset(  # pragma: no branch
            [deepcopy(elem, memo) for elem in self]
        )

class LoggingDict(dict):
    """A dict that logs any changes, as do its children.
    """
    def __init__(self, logger_name="scriptharness.config", level=logging.INFO,
                 *args, **kwargs):
        self.logger_name = logger_name
        self.level = level
        super(LoggingDict, self).__init__(*args, **kwargs)
    def __setitem__(self, *args):
        return super(LoggingDict, self).__setitem__(*args)
    def __delitem__(self, *args):
        return super(LoggingDict, self).__delitem__(*args)
    def clear(self, *args):
        return super(LoggingDict, self).clear(*args)
    def pop(self, *args):
        return super(LoggingDict, self).pop(*args)
    def popitem(self, *args):
        return super(LoggingDict, self).popitem(*args)
    def setdefault(self, *args):
        return super(LoggingDict, self).setdefault(*args)
    def update(self, *args):
        return super(LoggingDict, self).update(*args)
    def __deepcopy__(self, memo):
        """Return a dict on deepcopy()
        """
        # TODO needed?
        result = {}
        memo[id(self)] = result
        for key, value in self.items():
            result[key] = deepcopy(value, memo)
        return result
    # TODO add logging
    # TODO secret key, e.g. {'credentials': {}} that notes changes but
    # doesn't log them?

# end logging classes 2}}}

SUPPORTED_LOGGING_TYPES = {
    dict: LoggingDict,
    frozenset: LoggingFrozenSet,
    list: LoggingList,
    set: LoggingSet,
    tuple: LoggingTuple,
}

def enable_logging(item, logger_name=None, level=logging.INFO):
    """Recursively add logging to all contents of a LoggingDict.

    Any children of supported types will also have logging enabled.
    Currently supported:: list, tuple, dict, set, frozenset.

    Note:: a tuple or frozenset will become a LoggingList or LoggingSet,
    respectively; this means they will become read/write.  We can
    add non-recursive locking capability to these if this becomes a problem.

    Args:
      item (object): a child of a LoggingDict.

    Returns:
      A logging version of item, when applicable, or item.
    """
    result = item
    for key, value in SUPPORTED_LOGGING_TYPES.items():
        if isinstance(item, key):
            result = value(item, logger_name=logger_name, level=level)
    return result


# ReadOnlyDict {{{1
def make_immutable(item):
    """Recursively lock all contents of a ReadOnlyDict.

    Any children of supported types will also be locked.
    Currently supported:: list, tuple, dict, set, frozenset.

    and we locked r on a shallow level, we could still r['b'].append() or
    r['c']['key2'] = 'value2'.  So to avoid that, we need to recursively
    lock r via make_immutable.

    Taken from mozharness, but added LockedFrozenSet.

    Args:
      item (object): a child of a ReadOnlyDict.

    Returns:
      A locked version of item, when applicable, or item.
    """
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
    """A tuple with its children recursively locked.

    Tuples are read-only by nature, but we need to be able to recursively lock
    the contents of the tuple, since the tuple can contain dicts or lists.

    Taken straight from mozharness.
    """
    def __new__(cls, items):
        return tuple.__new__(cls, (make_immutable(x) for x in items))
    def __deepcopy__(self, memo):
        """Return a list on deepcopy.
        """
        return [deepcopy(elem, memo) for elem in self]  # pragma: no branch


class LockedFrozenSet(frozenset):
    """A frozenset with its children recursively locked.

    Frozensets are read-only by nature, but we need to be able to recursively
    lock the contents of the frozenset, since the frozenset can contain dicts
    or lists.
    """
    def __new__(cls, items):
        return frozenset.__new__(cls, (make_immutable(x) for x in items))
    def __deepcopy__(self, memo):
        """Return a set on deepcopy.
        """
        return set(  # pragma: no branch
            [deepcopy(elem, memo) for elem in self]
        )


class ReadOnlyDict(dict):
    '''A dict that is lockable.  When locked, any changes raise exceptions.

    Slightly modified version of mozharness.base.config.ReadOnlyDict,
    largely for pylint.
    '''
    def __init__(self, *args, **kwargs):
        self._lock = False
        super(ReadOnlyDict, self).__init__(*args, **kwargs)

    def _check_lock(self):
        """Throw an exception if we try to change anything while locked.
        """
        if self._lock:
            raise ScriptHarnessException("ReadOnlyDict is locked!")

    def lock(self):
        """Recursively lock the dictionary.
        """
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
        """Create an unlocked ReadOnlyDict on deepcopy()
        """
        result = self.__class__()
        memo[id(self)] = result
        for key, value in self.items():
            result[key] = deepcopy(value, memo)
        return result
