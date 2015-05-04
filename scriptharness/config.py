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
import six

# TODO use memo like deepcopy to prevent loop recursion

# LoggingDict and helpers {{{1
# logging classes {{{2
class LoggingClass(object):
    """General logging methods for the Logging* classes to subclass.

    Attributes:
      level (int): the logging level for changes
      logger_name (str): the logger name to use
      name (str): the name of the class for logs
      parent (str): the name of the parent, if applicable, for logs
    """
    level = None
    logger_name = None
    name = None
    parent = None
    def __new__(cls, super_class, items, level=logging.INFO,
                logger_name='scriptharness.config'):
        self = super_class.__new__(
            cls,
            (enable_logging(x, logger_name, level) for x in items)
        )
        self.level = level
        self.logger_name = logger_name
        return self
    def items(self):
        """Shut up pylint"""
        return super(LoggingClass, self).items()
    def recusively_set_parent(self, name, parent=None):
        """Recursively set name + parent.

        If our LoggingDict is a multi-level nested Logging* instance, then
        seeing a log message that something in one of the Logging* instances
        has changed can be confusing.  If we know that it's
        grandparent[parent][self][child] that has changed, then the log
        message is helpful.

        name (str): set self.name, for later logging purposes.
        parent (Logging* object, optional): set self.parent, for later logging
          purposes.
        """
        if name is not None:
            self.name = name
        if parent is not None:
            self.parent = parent
        if issubclass(self, dict):
            for child_name, child in self.items():
                if is_logging_class(child):
                    child.recursively_set_parent(child_name, self)
        else:
            for count, elem in enumerate(self):
                if is_logging_class(elem):
                    elem.recursively_set_parent(six.text_type(count - 1), self)
    def child_set_parent(self, child, child_name):
        """If child is a Logging* instance, set its parent and name.

        Args:
          child: an object, which might be a Logging* instance
          child_name: the name to set in the child
        """
        if is_logging_class(child):
            child.recursively_set_parent(child_name, parent=self)
    def log_change(self, message, child_list=None):
        """Log a change to self.

        Args:
          message (str): The message to log.
          child_list (list, automatically generated): in a multi-level nested
            Logging* class, generate the list of children's names so we can log
            which Logging* class has changed.  This list will be built by
            prepending our name and calling log_change() on self.parent.
        """
        if self.parent:
            if child_list is None:
                child_list = []
            child_list.insert(0, self.name)
            # TODO what happens on deletion?
            return self.parent.log_change(message, child_list)
        logger = logging.getLogger(self.logger_name)
        if child_list:
            name = six.text_type(child_list.pop(0))
            for item in child_list:
                name += "[{0}]".format(six.text_type(item))
            message = "{0}: {1}".format(name, message)
        return logger.log(self.level, message)

class LoggingList(LoggingClass, list):
    """A list that logs any changes, as do its children.
    """
    def __new__(cls, *args, **kwargs):
        return LoggingClass.__new__(cls, list, *args, **kwargs)

    def __deepcopy__(self, memo):
        """Return a list on deepcopy.
        """
        return [deepcopy(elem, memo) for elem in self]  # pragma: no branch

    def child_set_parent(self, position=0):
        """When the list changes, we either want to change all of the
        children's names (which correspond to indeces) or a subset of
        [position:]

        Override child_set_parent to make this simpler.
        """
        for count, elem in enumerate(self, start=position):
            super(LoggingList, self).child_set_parent(
                elem,
                six_text_type(count)
            )

    def append(self, item):
        self.log_change("appending {0}".format(six.text_type(item)))
        super(LoggingList, self).append(item)
        self.log_change("now looks like {0}".format(self))
        self.child_set_parent(item, six.text_type(len(self) - 1))

    def extend(self, items):
        self.log_change("extending with {0}".format(items))
        super(LoggingList, self).extend(items)
        self.log_change("now looks like {0}".format(self))
        for count, elem in enumerate(self):
            self.child_set_parent(elem, six.text_type(count))

    def insert(self, position, item):
        self.log_change("inserting {0} at position {1}".format(item, position))
        super(LoggingList, self).insert(position, item)
        self.log_change("now looks like {0}".format(self))
        for count, elem in enumerate(self, start=position):
            self.child_set_parent(elem, six.text_type(count))

    def remove(self, item):
        self.log_change("removing {0}".format(item))
        position = self.index(item)
        super(LoggingList, self).remove(item)
        self.log_change("now looks like {0}".format(self))
        for count, elem in enumerate(self, start=position):
            self.child_set_parent(elem, six.text_type(count))

    def pop(self, position=None):
        message = "popping"
        if position:
            message += " position {0}".format(position)
        self.log_change(message)
        value = super(LoggingList, self).pop(position)
        self.log_change("now looks like {0}".format(self))
        if position:
            for count, elem in enumerate(self, start=position):
                self.child_set_parent(elem, six.text_type(count))
        return value

    def sort(self, *args, **kwargs):
        self.log_change("sorting")
        super(LoggingList, self).sort(*args, **kwargs)
        self.log_change("now looks like {0}".format(self))
        for count, elem in enumerate(self):
            self.child_set_parent(elem, six.text_type(count))

    def reverse(self):
        self.log_change("reversing")
        super(LoggingList, self).reverse()
        self.log_change("now looks like {0}".format(self))
        for count, elem in enumerate(self):
            self.child_set_parent(elem, six.text_type(count))

class LoggingTuple(LoggingClass, tuple):
    """A tuple whose children log any changes.
    """
    def __new__(cls, *args, **kwargs):
        return LoggingClass.__new__(cls, tuple, *args, **kwargs)
    def __deepcopy__(self, memo):
        """Return a tuple on deepcopy.
        """
        return tuple(  # pragma: no branch
            [deepcopy(elem, memo) for elem in self]
        )

class LoggingSet(LoggingClass, set):
    """A set that logs any changes, as do its children.
    """
    def __new__(cls, *args, **kwargs):
        return LoggingClass.__new__(cls, set, *args, **kwargs)
    def __deepcopy__(self, memo):
        """Return a set on deepcopy.
        """
        return set(  # pragma: no branch
            [deepcopy(elem, memo) for elem in self]
        )
    # TODO add logging

class LoggingFrozenSet(LoggingClass, frozenset):
    """A frozenset whose children log any changes.
    """
    def __new__(cls, *args, **kwargs):
        return LoggingClass.__new__(cls, frozenset, *args, **kwargs)
    def __deepcopy__(self, memo):
        """Return a set on deepcopy.
        """
        return frozenset(  # pragma: no branch
            [deepcopy(elem, memo) for elem in self]
        )

class LoggingDict(LoggingClass, dict):
    """A dict that logs any changes, as do its children.
    """
    def __new__(cls, *args, **kwargs):
        return LoggingClass.__new__(cls, dict, *args, **kwargs)
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

def is_logging_class(item):
    """Determine if a class is one of the Logging* classes.
    """
    return item in SUPPORTED_LOGGING_TYPES.values()

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
