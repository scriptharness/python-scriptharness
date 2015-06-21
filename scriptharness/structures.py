#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Data structures for configs.

There are two config dict models here:
 * LoggingDict logs any changes to the dict or its children.  When debugging,
   config changes will be marked in the log.  This is the default model.

 * ReadOnlyDict recursively locks the dictionary.  This is to aid in debugging;
   one can assume the config hasn't changed from the moment of locking.
   This is the original `mozharness` model.

Attributes:
  DEFAULT_LEVEL (int): the default logging level to set
  DEFAULT_LOGGER_NAME (str): the default logger name to use
  QUOTES (tuple): the order of quotes to use for key logging
  LOGGING_STRINGS (dict): a dict of strings to use for logging, for easier
    unittesting and potentially for future localization.
  MUTED_LOGGING_STRINGS (dict): a dict of strings to use for logging when
    the values in the list/dict shouldn't be logged
  SUPPORTED_LOGGING_TYPES (dict): a non-logging to logging class map, e.g.
    dict: LoggingDict.  Not currently supporting sets or collections.
"""

from __future__ import absolute_import, division, print_function, \
                       unicode_literals
from copy import deepcopy
from scriptharness.exceptions import ScriptHarnessException
import six
import logging
import pprint


# Constants {{{1
DEFAULT_LEVEL = logging.INFO
DEFAULT_LOGGER_NAME = 'scriptharness.data_structures'
QUOTES = ("'", '"', "'''", '"""')
LOGGING_STRINGS = {
    # position, self, item
    "list": {
        "delitem": "__delitem__ %(item)s",
        "log_self": "now looks like %(self)s",
        "setitem": "__setitem__ %(position)d to %(item)s",
        "append": "appending %(item)s",
        "extend": "extending with %(item)s",
        "insert": "inserting %(item)s at position %(position)s",
        "remove": "removing %(item)s",
        "pop_no_args": "popping",
        "pop_args": "popping position %(position)s",
        "sort": "sorting",
        "reverse": "reversing",
    },
    # key, value, default
    "dict": {
        "delitem": "__delitem__ %(key)s",
        "setitem": "__setitem__ %(key)s to %(value)s",
        "clear": "clearing dict",
        "pop": {
            "message_no_default": "popping dict key %(key)s",
            "message_default": "popping dict key %(key)s (default %(default)s)",
        },
        "popitem": {
            "message": "popitem",
            "changed": "the popitem removed the key %(key)s",
        },
        "setdefault": {
            "message": "setdefault %(key)s to %(default)s",
            "unchanged": "setdefault: %(key)s unchanged",
            "changed": "setdefault: %(key)s now %(value)s",
        },
        "update": {
            "message": "update %(key)s to %(value)s",
            "changed": "update: %(key)s now %(value)s",
            "unchanged": "update: %(key)s unchanged",
        },
    },
}
MUTED_LOGGING_STRINGS = {
    # position, self, item
    "list": {
        "delitem": "__delitem__ %(item)s",
        "setitem": "__setitem__ %(position)d ...",
        "append": "appending ...",
        "extend": "extending ...",
        "insert": "inserting at position %(position)s",
        "remove": "removing ...",
        "pop_no_args": "popping",
        "pop_args": "popping position %(position)s",
        "sort": "sorting",
        "reverse": "reversing",
    },
    # key, value, default
    "dict": {
        "delitem": "__delitem__ %(key)s",
        "setitem": "__setitem__ %(key)s ...",
        "clear": "clearing dict",
        "pop": {
            "message_no_default": "popping dict key %(key)s",
            "message_default": "popping dict key %(key)s with default ...",
        },
        "popitem": {
            "message": "popitem",
            "changed": "the popitem removed the key %(key)s",
        },
        "setdefault": {
            "message": "setdefault %(key)s ...",
            "unchanged": "setdefault: %(key)s unchanged",
            "changed": "setdefault: %(key)s changed",
        },
        "update": {
            "message": "update %(key)s ...",
            "changed": "update: %(key)s changed",
            "unchanged": "update: %(key)s unchanged",
        },
    },
}


def iterate_pairs(data):
    """Iterate over pairs of a data structure.

    Usage:: for key, value in iterate_pairs(data_structure)::

    Args:
      data (data structure): a dict, iterable-of-iterable pairs
    """
    if isinstance(data, dict):
        if six.PY2:
            iterable = data.iteritems()
        else:
            iterable = data.items()
    else:
        iterable = data
        if len(data) >= 2 and not isinstance(data[0], (tuple, list)):
            iterable = zip(data[::2], data[1::2])
    return iterable


# LoggingClasses and helpers {{{1
# LoggingClass {{{2
class LoggingClass(object):
    """General logging methods for the Logging* classes to subclass.

    Attributes:
      level (int): the logging level for changes
      logger_name (str): the logger name to use
      name (str): the name of the class for logs
      parent (str): the name of the parent, if applicable, for logs
    """
    name = None
    parent = None
    level = None
    logger_name = None

    def items(self):
        """Return dict.items() for dicts, and enumerate(self) for lists+tuples.

        This both simplifies recursively_set_parent() and silences pylint
        complaining that LoggingClass doesn't have an items() method.

        The main negative here might be adding an attr items to non-dict
        data types.
        """
        if issubclass(self.__class__, dict):
            return super(LoggingClass, self).items()
        else:
            return enumerate(self)

    def recursively_set_parent(self, name=None, parent=None):
        """Recursively set name + parent.

        If our LoggingDict is a multi-level nested Logging* instance, then
        seeing a log message that something in one of the Logging* instances
        has changed can be confusing.  If we know that it's
        grandparent[parent][self][child] that has changed, then the log
        message is helpful.

        For each child, set name automatically.  For dicts, the name is the
        key.  For everything else, the name is the index.

        Args:
          name (Optional[str]): set self.name, for later logging purposes.
            Defaults to None.

          parent (Optional[Logging*]): set self.parent, for logging purposes.
            Defaults to None.
        """
        if name is not None:
            self.name = name
        if parent is not None:
            self.parent = parent
        for child_name, child in self.items():
            if is_logging_class(child):
                child.recursively_set_parent(
                    child_name, self
                )

    def _child_set_parent(self, child, child_name):
        """If child is a Logging* instance, set its parent and name.

        Args:
          child: an object, which might be a Logging* instance
          child_name: the name to set in the child
        """
        if is_logging_class(child):
            child.recursively_set_parent(child_name, parent=self)

    def ancestor_child_list(self, child_list=None):
        """Get the original ancestor of self, and the descending, linear list
        of descendents' names leading up to (and including) self.

        Args:

          child_list (list, automatically generated): in a multi-level nested
            Logging* class, generate the list of children's names. This list
            will be built by prepending our name and calling
            ancestor_child_list() on self.parent.

        Returns:
          (ancestor, child_list) (LoggingClass, list): for self.full_name and
          self.log_change support
        """
        child_list = child_list or []
        if self.parent:
            child_list.insert(0, self.name)
            return self.parent.ancestor_child_list(child_list=child_list)
        else:
            return self, child_list

    def full_name(self):
        """Get the full name of self.

        This will call self.ancestor_child_list to get the original ancestor +
        all the names of its descendents up to and including self, then
        build the name from that.

        Args:
          ancestor (Optional[LoggingClass]): specify the ancestor
          child_list (Optional[list]): a list of descendents' names, in order

        Returns:
          name (string): the full name of self.
        """
        ancestor, child_list = self.ancestor_child_list()
        name = ancestor.name or ""
        for item in child_list:
            if isinstance(item, int):
                name += "[%d]" % item
            else:
                quote = ""
                item = item
                for sep in QUOTES:
                    if sep not in item:
                        quote = sep
                        break
                name += "[%s%s%s]" % (quote, item, quote)
        return name

    def log_change(self, message, repl_dict=None):
        """Log a change to self.

        Args:
          message (str): The message to log.
        """
        logger = logging.getLogger(self.logger_name)
        name = self.full_name()
        if name:
            message = "{}: {}".format(name, message)
        args = [self.level, message]
        if repl_dict:
            args.append(repl_dict)
        return logger.log(*args)


# LoggingList {{{2
class LoggingList(LoggingClass, list):
    """A list that logs any changes, as do its children.

    Attributes:
      level (int): the logging level for changes
      logger_name (str): the logger name to use
      muted (bool): whether our logging messages are muted
      strings (dict): a dict of strings to use for messages
    """
    def __init__(self, items, level=DEFAULT_LEVEL, muted=False,
                 logger_name=DEFAULT_LOGGER_NAME):
        self.level = level
        self.logger_name = logger_name
        self.muted = muted
        self.strings = get_strings(self, muted=self.muted)
        super(LoggingList, self).__init__(
            [add_logging_to_obj(x, logger_name=self.logger_name,
                                level=level, muted=self.muted) for x in items]
        )

    def __deepcopy__(self, memo):
        """Return a list on deepcopy.
        """
        return [deepcopy(elem, memo) for elem in self]

    def __delitem__(self, item):
        self.log_change(self.strings['delitem'],
                        repl_dict={'item': item})
        position = item
        if isinstance(item, slice):
            position = item.start
        super(LoggingList, self).__delitem__(item)
        self.log_self()
        if position < len(self):
            self.child_set_parent(position)

    def __setitem__(self, position, item):
        self.log_change(
            self.strings['setitem'],
            repl_dict={'position': position, 'item': item}
        )
        item = add_logging_to_obj(item, logger_name=self.logger_name,
                                  level=self.level, muted=self.muted)
        super(LoggingList, self).__setitem__(position, item)
        self.log_self()
        self.child_set_parent(position)

    def child_set_parent(self, position=0):
        """When the list changes, we either want to change all of the
        children's names (which correspond to indeces) or a subset of
        [position:]
        """
        for count, elem in enumerate(self, start=position):
            self._child_set_parent(elem, int(count))

    def log_self(self):
        """Log the current list.

        Since some methods insert values or rearrange them, it'll be easier to
        debug things if we log the list after those operations.
        """
        if self.strings.get('log_self'):
            self.log_change(self.strings['log_self'],
                            repl_dict={'self': pprint.pformat(self)})

    def append(self, item):
        self.log_change(self.strings['append'],
                        repl_dict={'item': item})
        super(LoggingList, self).append(
            add_logging_to_obj(item, logger_name=self.logger_name,
                               level=self.level, muted=self.muted)
        )
        self.log_self()
        self.child_set_parent(len(self) - 1)

    def extend(self, item):
        position = len(self)
        self.log_change(self.strings['extend'],
                        repl_dict={'item': pprint.pformat(item)})
        super(LoggingList, self).extend(
            add_logging_to_obj(item, logger_name=self.logger_name,
                               level=self.level, muted=self.muted)
        )
        self.log_self()
        self.child_set_parent(position)

    def insert(self, position, item):
        self.log_change(
            self.strings['insert'],
            repl_dict={
                'item': item,
                'position': position
            }
        )
        super(LoggingList, self).insert(
            position, add_logging_to_obj(item, logger_name=self.logger_name,
                                         level=self.level, muted=self.muted)
        )
        self.log_self()
        self.child_set_parent(position)

    def remove(self, item):
        self.log_change(self.strings['remove'],
                        repl_dict={'item': item})
        position = self.index(item)
        super(LoggingList, self).remove(item)
        self.log_self()
        if position < len(self):
            self.child_set_parent(position)

    def pop(self, position=None):
        if position is None:
            self.log_change(self.strings['pop_no_args'])
            value = super(LoggingList, self).pop()
        else:
            self.log_change(
                self.strings['pop_args'],
                repl_dict={'position': position}
            )
            value = super(LoggingList, self).pop(position)
        self.log_self()
        if position is not None:
            self.child_set_parent(position)
        return value

    def sort(self, *args, **kwargs):
        self.log_change(self.strings['sort'])
        super(LoggingList, self).sort(*args, **kwargs)
        self.log_self()
        self.child_set_parent()

    def reverse(self):
        self.log_change(self.strings['reverse'])
        super(LoggingList, self).reverse()
        self.log_self()
        self.child_set_parent()


# LoggingTuple {{{2
class LoggingTuple(LoggingClass, tuple):
    """A tuple whose children log any changes.
    """
    def __new__(cls, items, **kwargs):
        return tuple.__new__(
            cls, (add_logging_to_obj(x, **kwargs) for x in items)
        )

    def __deepcopy__(self, memo):
        """Return a tuple on deepcopy.
        """
        return tuple(
            [deepcopy(elem, memo) for elem in self]
        )


# LoggingDict {{{2
class LoggingDict(LoggingClass, dict):
    """A dict that logs any changes, as do its children.

    Attributes:
      level (int): the logging level for changes
      logger_name (str): the logger name to use
      muted (bool): whether our logging messages are muted
      strings (dict): a dict of strings to use for messages
    """
    def __init__(self, items, level=DEFAULT_LEVEL, muted=False,
                 logger_name=DEFAULT_LOGGER_NAME):
        self.level = level
        self.logger_name = logger_name
        self.muted = muted
        self.strings = get_strings(self, muted=muted)
        for key, value in items.items():
            items[key] = add_logging_to_obj(
                value, logger_name=logger_name, level=level, muted=self.muted
            )
        super(LoggingDict, self).__init__(items)

    def __setitem__(self, key, value):
        repl_dict = {'key': key, 'value': value}
        self.log_change(
            self.strings['setitem'],
            repl_dict=repl_dict,
        )
        value = add_logging_to_obj(value, logger_name=self.logger_name,
                                   level=self.level, muted=self.muted)
        super(LoggingDict, self).__setitem__(key, value)
        self.child_set_parent(key)

    def __delitem__(self, key):
        self.log_change(self.strings['delitem'],
                        repl_dict={'key': key})
        super(LoggingDict, self).__delitem__(key)

    def child_set_parent(self, key):
        """When the dict changes, we can just target the specific changed
        children.  Very simple wrapper method.

        Args:
            key (str): the dict key to the child value.
        """
        self._child_set_parent(self[key], key)

    def clear(self):
        self.log_change(self.strings['clear'])
        super(LoggingDict, self).clear()

    def pop(self, key, default=None):
        repl_dict = {'key': key}
        args = []
        if default:
            message = self.strings['pop']['message_default']
            repl_dict['default'] = default
            args.append(default)
        else:
            message = self.strings['pop']['message_no_default']
        self.log_change(message, repl_dict=repl_dict)
        return super(LoggingDict, self).pop(key, *args)

    def popitem(self):
        pre_keys = set(self.keys())
        self.log_change(self.strings["popitem"]["message"])
        status = super(LoggingDict, self).popitem()
        post_keys = set(self.keys())
        key = list(pre_keys.difference(post_keys))
        self.log_change(
            self.strings['popitem']['changed'],
            repl_dict={'key': key[0]},
        )
        return status

    def setdefault(self, key, default=None):
        changed = True
        if key in self:
            changed = False
        repl_dict = {
            'key': key,
            'default': default,
        }
        self.log_change(
            self.strings['setdefault']['message'],
            repl_dict=repl_dict,
        )
        default = add_logging_to_obj(default, logger_name=self.logger_name,
                                     level=self.level, muted=self.muted)
        status = super(LoggingDict, self).setdefault(key, default)
        if not changed:
            message = self.strings['setdefault']['unchanged']
        else:
            repl_dict['value'] = status
            message = self.strings['setdefault']['changed']
        self.log_change(message, repl_dict=repl_dict)
        self.child_set_parent(key)
        return status

    def log_update(self, key, value):
        """Helper method for update(): log one key/value pair at a time.

        Args:
            key (str): key to update
            value (any): value to set

        Returns:
            key (str) if it doesn't exist in self, else None
        """
        repl_dict = {
            'key': key, 'value': value,
        }
        self.log_change(
            self.strings['update']['message'],
            repl_dict=repl_dict,
        )
        status = [key, None]
        if key not in self or self[key] != value:
            status = [key, value]
        return status

    def update(self, args):
        changed_keys = []
        new_args = {}
        for key, value in iterate_pairs(args):
            changed_keys.append(self.log_update(key, value))
            new_args[key] = add_logging_to_obj(
                value, logger_name=self.logger_name, level=self.level,
                muted=self.muted
            )
            args = new_args
        super(LoggingDict, self).update(args)
        for key, value in changed_keys:
            if value is not None:
                message = self.strings['update']['changed']
            else:
                message = self.strings['update']['unchanged']
            self.log_change(
                message,
                repl_dict={'key': key, 'value': self[key]},
            )
            self.child_set_parent(key)

    def __deepcopy__(self, memo):
        """Return a dict on deepcopy()
        """
        result = {}
        memo[id(self)] = result
        for key, value in self.items():
            result[key] = deepcopy(value, memo)
        return result


# LoggingHelpers {{{2
SUPPORTED_LOGGING_TYPES = {
    dict: LoggingDict,
    list: LoggingList,
    tuple: LoggingTuple,
}

def is_logging_class(item):
    """Determine if a class is one of the Logging* classes.

    Args:
      item (object): the object to check.
    """
    return issubclass(item.__class__, LoggingClass)

def add_logging_to_obj(item, **kwargs):
    """Recursively add logging to all contents of a LoggingDict.

    Any children of supported types will also have logging enabled.
    Currently supported:: list, tuple, dict.

    Args:
      item (object): a child of a LoggingDict.

    Returns:
      A logging version of item, when applicable, or item.
    """
    result = item
    for key, value in SUPPORTED_LOGGING_TYPES.items():
        if isinstance(item, key):
            result = value(item, **kwargs)
    return result

def get_strings(instance_type, muted=False):
    """Get the strings for LoggingClass instance, muted or unmuted

    Args:
      instance (obj): LoggingClass instance or 'list' or 'dict'
      muted (Optional[bool]): return the MUTED_LOGGING_STRINGS strings if True
    """
    strings = MUTED_LOGGING_STRINGS if muted else LOGGING_STRINGS
    if isinstance(instance_type, LoggingList) or instance_type == 'list':
        return strings['list']
    elif isinstance(instance_type, LoggingDict) or instance_type == 'dict':
        return strings['dict']
    else:
        raise ScriptHarnessException("Unknown type sent to get_strings!",
                                     instance_type)


# ReadOnlyDict {{{1
def make_immutable(item):
    """Recursively lock all contents of a ReadOnlyDict.

    Any children of supported types will also be locked.
    Currently supported:: list, tuple, dict.

    and we locked r on a shallow level, we could still r['b'].append() or
    r['c']['key2'] = 'value2'.  So to avoid that, we need to recursively
    lock r via make_immutable.

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
        return [deepcopy(elem, memo) for elem in self]


class ReadOnlyDict(dict):
    """A dict that is lockable.  When locked, any changes raise exceptions.

    Slightly modified version of mozharness.base.config.ReadOnlyDict,
    largely for pylint.

    Attributes:
      _lock (bool): When locked, the dict is read-only and cannot be unlocked.
    """
    _lock = None
    def __init__(self, *args, **kwargs):
        super(ReadOnlyDict, self).__init__(*args, **kwargs)
        self._lock = False

    def __setattr__(self, name, *args):
        if name == '_lock' and self._lock and not args[0]:
            raise ScriptHarnessException(
                "Not allowed to unlock a locked ReadOnlyDict!"
            )
        return super(ReadOnlyDict, self).__setattr__(name, *args)

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
