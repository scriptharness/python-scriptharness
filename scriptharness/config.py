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
        """Shut up pylint.
        The main negative here might be adding an attr items to non-dict
        data types.
        """
        return super(LoggingClass, self).items()

    def recusively_set_parent(self, name=None, parent=None):
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
        if issubclass(self, dict):
            for child_name, child in self.items():
                if is_logging_class(child):
                    child.recursively_set_parent(
                        six.text_type(child_name), self
                    )
        else:
            for count, elem in enumerate(self):
                if is_logging_class(elem):
                    elem.recursively_set_parent(six.text_type(count - 1), self)

    def _child_set_parent(self, child, child_name):
        """If child is a Logging* instance, set its parent and name.

        Args:
          child: an object, which might be a Logging* instance
          child_name: the name to set in the child
        """
        if is_logging_class(child):
            child.recursively_set_parent(child_name, parent=self)

    def log_change(self, message, child_list=None, *args):
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
            return self.parent.log_change(message, *args,
                                          child_list=child_list)
        logger = logging.getLogger(self.logger_name)
        if child_list:
            name = six.text_type(child_list.pop(0))
            for item in child_list:
                name += "[{0}]".format(six.text_type(item))
            message = "{0}: {1}".format(name, message)
        return logger.log(self.level, message, *args)


class LoggingList(LoggingClass, list):
    """A list that logs any changes, as do its children.
    """
    def __new__(cls, *args, **kwargs):
        return LoggingClass.__new__(cls, list, *args, **kwargs)

    def __deepcopy__(self, memo):
        """Return a list on deepcopy.
        """
        return [deepcopy(elem, memo) for elem in self]  # pragma: no branch

    def __delitem__(self, item):
        self.log_change("__delitem__ %s", six.text_type(item))
        if isinstance(item, slice):
            position = item.start
        else:
            position = self.index(item)
        super(LoggingList, self).__delitem__(item)
        self.log_change("now looks like %s", six.text_type(self))
        if position < len(self):
            self.child_set_parent(position)

    def __setitem__(self, position, value):
        self.log_change("__setitem__ %d to %s", position, six.text_type(value))
        super(LoggingList, self).__setitem__(position, value)
        self.log_change("now looks like %s", six.text_type(self))
        self.child_set_parent(position)

    def child_set_parent(self, position=0):
        """When the list changes, we either want to change all of the
        children's names (which correspond to indeces) or a subset of
        [position:]
        """
        for count, elem in enumerate(self, start=position):
            enable_logging(elem, logger_name=self.logger_name,
                           level=self.level)
            self._child_set_parent(elem, six.text_type(count))

    def append(self, item):
        self.log_change("appending %s}", six.text_type(item))
        super(LoggingList, self).append(item)
        self.log_change("now looks like %s", six.text_type(self))
        self.child_set_parent(len(self) - 1)

    def extend(self, items):
        position = len(self)
        self.log_change("extending with %s", six.text_type(items))
        super(LoggingList, self).extend(items)
        self.log_change("now looks like %s", six.text_type(self))
        self.child_set_parent(position)

    def insert(self, position, item):
        self.log_change("inserting %s at position %d", six.text_type(item),
                        position)
        super(LoggingList, self).insert(position, item)
        self.log_change("now looks like %s", six.text_type(self))
        self.child_set_parent(position)

    def remove(self, item):
        self.log_change("removing %s", six.text_type(item))
        position = self.index(item)
        super(LoggingList, self).remove(item)
        self.log_change("now looks like %s", six.text_type(self))
        if position < len(self):
            self.child_set_parent(position)

    def pop(self, position=None):
        message = ["popping"]
        if position:
            message = ["popping position %d", position]
        self.log_change(*message)
        value = super(LoggingList, self).pop(position)
        self.log_change("now looks like %s", six.text_type(self))
        if position:
            self.child_set_parent(position)
        return value

    def sort(self, *args, **kwargs):
        self.log_change("sorting")
        super(LoggingList, self).sort(*args, **kwargs)
        self.log_change("now looks like %s", six.text_type(self))
        self.child_set_parent()

    def reverse(self):
        self.log_change("reversing")
        super(LoggingList, self).reverse()
        self.log_change("now looks like %s", six.text_type(self))
        self.child_set_parent()


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


class LoggingDict(LoggingClass, dict):
    """A dict that logs any changes, as do its children.

    TODO use pprint?
    TODO secret key, e.g. {'credentials': {}} that notes changes but
         doesn't log them?

    Attributes:
      muted_keys (list): a list of keys that should be muted in logs, e.g.
        ['credentials', 'binary_blobs'].  The values of these keys should
        be muted in logs.
    """
    muted_keys = []

    def __new__(cls, muted_keys=None, *args, **kwargs):
        self = LoggingClass.__new__(cls, dict, *args, **kwargs)
        self.muted_keys = muted_keys or self.muted_keys

    def __setitem__(self, key, value):

        self.log_change(
            "__setitem__ %(key)s to %(value)s",
            "__setitem__ %(key)s to ********",
            {'key': six.text_type(key), 'value': six.text_type(value)}
        )
        super(LoggingDict, self).__setitem__(key, value)
        self.child_set_parent(key)

    def __delitem__(self, key):
        self.log_change("__delitem__ %(key)s", "",
                        repl_dict={'key': six.text_type(key)})
        super(LoggingDict, self).__delitem__(key)

    def log_change(self, message, child_list=None, muted_message=None, *args):
        repl_dict = {}
        if args and isinstance(args[0], dict):
            repl_dict = args[0]
        if repl_dict.get('key') in self.muted_keys and muted_message:
            message = muted_message
        super(LoggingDict, self).log_change(message, *args)

    def child_set_parent(self, key):
        """When the dict changes, we can just target the specific changed
        children.  Very simple wrapper method.

        Args:
            key (str): the dict key to the child value.
        """
        enable_logging(self[key], logger_name=self.logger_name,
                       level=self.level)
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
        self.log_change(message, repl_dict, muted_message=muted_message)
        return super(LoggingDict, self).pop(key, default)

    def popitem(self, *args):
        self.log_change("popitem dict: %s", "", six.text_type(args))
        status = super(LoggingDict, self).popitem(*args)
        return status

    def setdefault(self, key, default=None):
        if key not in self:
            self.log_change(
                "setdefault %(key)s: %(default)s",
                {'key': six.text_type(key), 'default': six.text_type(default)},
                muted_message="setdefault %(key)s: ********"
            )
        status = super(LoggingDict, self).setdefault(key, default)
        self.child_set_parent(key)
        return status

    def update(self, args):
        if isinstance(args, dict):
            keys = args.keys()
        else:
            keys = args[::2]
        super(LoggingDict, self).update(*args)
        # TODO will this auto-log or do I need to add it?
        # Is there a smarter way to do this?
        for key in keys:
            self.child_set_parent(key)

    def __deepcopy__(self, memo):
        """Return a dict on deepcopy()

        TODO needed?
        """
        result = {}
        memo[id(self)] = result
        for key, value in self.__dict__.items():
            setattr(result, key, deepcopy(value, memo))
        for key, value in self.items():
            result[key] = deepcopy(value, memo)
        return result

# end logging classes 2}}}

SUPPORTED_LOGGING_TYPES = {
    dict: LoggingDict,
    list: LoggingList,
    tuple: LoggingTuple,
}

def is_logging_class(item):
    """Determine if a class is one of the Logging* classes.
    """
    return item in SUPPORTED_LOGGING_TYPES.values()

def enable_logging(item, logger_name=None, level=logging.INFO):
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
