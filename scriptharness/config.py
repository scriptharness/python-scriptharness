#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Allow for flexible configuration.

There are two config dict models here:: one is to recursively lock the
dictionary.  This is to aid in debugging; one can assume the config hasn't
changed from the moment of locking.  This is the original mozharness model.

The other model is to log any changes to the dict or its children.  When
debugging, config changes will be marked in the log.

Attributes:
  DEFAULT_LEVEL (int): the default logging level to set
  DEFAULT_LOGGER_NAME (str): the default logger name to use
  QUOTES (tuple): the order of quotes to use for key logging
  SUPPORTED_LOGGING_TYPES (dict): a non-logging to logging class map, e.g.
    dict: LoggingDict.  Not yet supporting collections / OrderedDicts.
"""

from __future__ import absolute_import, division, print_function
from copy import deepcopy
from scriptharness import ScriptHarnessException
import logging
import six


DEFAULT_LEVEL = logging.INFO
DEFAULT_LOGGER_NAME = 'scriptharness.log'
QUOTES = ("'", '"', "'''", '"""')

# TODO use memo like deepcopy to prevent loop recursion
# TODO logging strings dict

# LoggingDict and helpers {{{1
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

        This both simplifies recursively_set_parent() and shushes pylint
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

        name (str): set self.name, for later logging purposes.
        parent (Logging* object, optional): set self.parent, for later logging
          purposes.
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

    def log_change(self, message, child_list=None, repl_dict=None):
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
            return self.parent.log_change(message, repl_dict=repl_dict,
                                          child_list=child_list)
        logger = logging.getLogger(self.logger_name)
        name = self.name or ""
        if child_list:
            for item in child_list:
                if isinstance(item, int):
                    name += "[%d]" % item
                else:
                    quote = ""
                    item = six.text_type(item)
                    for sep in QUOTES:
                        if sep not in item:
                            quote = sep
                            break
                    name += "[%s%s%s]" % (quote, six.text_type(item), quote)
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
    """
    level = None
    logger_name = None
    def __init__(self, items, level=DEFAULT_LEVEL,
                 logger_name=DEFAULT_LOGGER_NAME):
        self.level = level
        self.logger_name = logger_name
        for item in items:
            add_logging_to_obj(item, logger_name, level)
        super(LoggingList, self).__init__(items)

    def __deepcopy__(self, memo):
        """Return a list on deepcopy.
        """
        return [deepcopy(elem, memo) for elem in self]  # pragma: no branch

    def __delitem__(self, item):
        self.log_change("__delitem__ %(item)s",
                        repl_dict={'item': six.text_type(item)})
        if isinstance(item, slice):
            position = item.start
        else:
            position = self.index(item)
        super(LoggingList, self).__delitem__(item)
        self.log_change("now looks like %(self)s",
                        repl_dict={'self': six.text_type(self)})
        if position < len(self):
            self.child_set_parent(position)

    def __setitem__(self, position, value):
        self.log_change(
            "__setitem__ %(position)d to %(value)s",
            repl_dict={'position': position, 'value': six.text_type(value)}
        )
        value = add_logging_to_obj(value, logger_name=self.logger_name,
                                   level=self.level)
        super(LoggingList, self).__setitem__(position, value)
        self.log_change("now looks like %(self)s",
                        repl_dict={'self': six.text_type(self)})
        self.child_set_parent(position)

    def child_set_parent(self, position=0):
        """When the list changes, we either want to change all of the
        children's names (which correspond to indeces) or a subset of
        [position:]
        """
        for count, elem in enumerate(self, start=position):
            add_logging_to_obj(elem, logger_name=self.logger_name,
                               level=self.level)
            self._child_set_parent(elem, int(count))

    def log_self(self):
        """Log the current list.

        Since some methods insert values or rearrange them, it'll be easier to
        debug things if we log the list after those operations.
        """
        self.log_change("now looks like %(self)s",
                        repl_dict={'self': six.text_type(self)})

    def append(self, item):
        self.log_change("appending %(item)s",
                        repl_dict={'item': six.text_type(item)})
        super(LoggingList, self).append(item)
        self.log_self()
        self.child_set_parent(len(self) - 1)

    def extend(self, items):
        position = len(self)
        self.log_change("extending with %(items)s",
                        repl_dict={'items': six.text_type(items)})
        super(LoggingList, self).extend(items)
        self.log_self()
        self.child_set_parent(position)

    def insert(self, position, item):
        self.log_change(
            "inserting %(item)s at position %(position)s",
            repl_dict={
                'item': six.text_type(item),
                'position': six.text_type(position)
            }
        )
        super(LoggingList, self).insert(position, item)
        self.log_self()
        self.child_set_parent(position)

    def remove(self, item):
        self.log_change("removing %(item)s",
                        repl_dict={'item': six.text_type(item)})
        position = self.index(item)
        super(LoggingList, self).remove(item)
        self.log_self()
        if position < len(self):
            self.child_set_parent(position)

    def pop(self, position=None):
        if position is None:
            self.log_change("popping")
            value = super(LoggingList, self).pop()
        else:
            self.log_change(
                "popping position %(position)d",
                repl_dict={'position': position}
            )
            value = super(LoggingList, self).pop(position)
        self.log_self()
        if position is not None:
            self.child_set_parent(position)
        return value

    def sort(self, *args, **kwargs):
        self.log_change("sorting")
        super(LoggingList, self).sort(*args, **kwargs)
        self.log_self()
        self.child_set_parent()

    def reverse(self):
        self.log_change("reversing")
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
        return tuple(  # pragma: no branch
            [deepcopy(elem, memo) for elem in self]
        )


# LoggingDict {{{2
class LoggingDict(LoggingClass, dict):
    """A dict that logs any changes, as do its children.

    TODO use pprint?
    TODO secret key, e.g. {'credentials': {}} that notes changes but
         doesn't log them?

    Attributes:
      level (int): the logging level for changes
      logger_name (str): the logger name to use
      muted_keys (list): a list of keys that should be muted in logs, e.g.
        ['credentials', 'binary_blobs'].  The values of these keys should
        be muted in logs.
    """
    muted_keys = []
    def __init__(self, items, muted_keys=None, level=DEFAULT_LEVEL,
                 logger_name=DEFAULT_LOGGER_NAME):
        self.muted_keys = muted_keys or self.muted_keys
        self.level = level
        self.logger_name = logger_name
        for key, value in items.items():
            items[key] = add_logging_to_obj(
                value, logger_name=logger_name, level=level
            )
        super(LoggingDict, self).__init__(items)

    def __setitem__(self, key, value):
        repl_dict = {'key': six.text_type(key), 'value': six.text_type(value)}
        self.log_change(
            "__setitem__ %(key)s to %(value)s",
            muted_message="__setitem__ %(key)s to ********",
            repl_dict=repl_dict,
        )
        value = add_logging_to_obj(value, logger_name=self.logger_name,
                                   level=self.level)
        super(LoggingDict, self).__setitem__(key, value)
        self.child_set_parent(key)

    def __delitem__(self, key):
        self.log_change("__delitem__ %(key)s",
                        repl_dict={'key': six.text_type(key)})
        super(LoggingDict, self).__delitem__(key)

    def log_change(self, message, muted_message=None, repl_dict=None, **kwargs):
        if repl_dict:
            if muted_message and 'key' in repl_dict and \
                    repl_dict['key'] in self.muted_keys:
                message = muted_message
        super(LoggingDict, self).log_change(
            message, repl_dict=repl_dict, **kwargs
        )

    def child_set_parent(self, key):
        """When the dict changes, we can just target the specific changed
        children.  Very simple wrapper method.

        Args:
            key (str): the dict key to the child value.
        """
        self._child_set_parent(self[key], six.text_type(key))

    def clear(self):
        self.log_change("clearing dict")
        super(LoggingDict, self).clear()

    def pop(self, key, default=None):
        message = "popping dict key %(key)s"
        muted_message = message
        repl_dict = {'key': six.text_type(key)}
        if default:
            message += " (default %(default)s)"
            repl_dict['default'] = default
        self.log_change(message, repl_dict=repl_dict,
                        muted_message=muted_message)
        return super(LoggingDict, self).pop(key, default)

    def popitem(self):
        pre_keys = set(self.keys())
        self.log_change("popitem")
        status = super(LoggingDict, self).popitem()
        post_keys = set(self.keys())
        self.log_change(
            "the popitem removed the key %(key)s",
            repl_dict={
                'key': six.text_type(pre_keys.difference(post_keys)),
            },
        )
        return status

    def setdefault(self, key, default=None):
        value = self.get(key, default)
        repl_dict = {
            'key': six.text_type(key),
            'default': six.text_type(default),
            'value': value
        }
        self.log_change(
            "setdefault %(key)s to %(default)s",
            repl_dict=repl_dict,
            muted_message="setdefault %(key)s to ********"
        )
        if key in self and value == default:
            changed_message = "setdefault: %(key)s unchanged."
            changed_muted_message = None
        else:
            changed_message = "setdefault: %(key)s now %(value)s"
            changed_muted_message = "setdefault: %(key)s changed."
            status = super(LoggingDict, self).setdefault(key, default)
        self.log_change(changed_message, repl_dict=repl_dict,
                        muted_message=changed_muted_message)
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
            "update %(key)s to %(value)s",
            repl_dict=repl_dict,
            muted_message="update %(key)s to ********",
        )
        if key not in self:
            return key

    def update(self, args):
        changed_keys = []
        if isinstance(args, dict):
            for key, value in args.items():
                changed_keys.append(self.log_update(key, value))
        else:
            # odd values are keys, even values are values
            for key, value in zip(a[::2], a[1::2]):
                changed_keys.append(self.log_update(key, value))
        super(LoggingDict, self).update(args)
        for key in changed_keys:
            if key is None:
                continue
            self.log_change(
                "%(key)s is now %(value)s",
                repl_dict={'key': key, 'value': self[key]},
                muted_message="%(key)s changed."
            )
            self.child_set_parent(key)

    def __deepcopy__(self, memo):
        """Return a dict on deepcopy()

        TODO needed?
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
    """
    return issubclass(item.__class__, LoggingClass)

def add_logging_to_obj(item, logger_name=None, level=logging.INFO):
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
            result = value(item, logger_name=logger_name, level=level)
    return result


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
        return [deepcopy(elem, memo) for elem in self]  # pragma: no branch


class ReadOnlyDict(dict):
    """A dict that is lockable.  When locked, any changes raise exceptions.

    Slightly modified version of mozharness.base.config.ReadOnlyDict,
    largely for pylint.
    """
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
