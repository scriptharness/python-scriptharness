#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Error lists.
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import re
from scriptharness.exceptions import ScriptHarnessException
import six

# ErrorList {{{1
class ErrorList(list):
    """Error lists, to describe how to parse output.  In object form for
    better validation.

    An example error_list::

        [
            {
                "regex": re.compile("^Error: not actually an error!"),
                level=-1
            }, {
                "regex": re.compile("^Error:"),
                "level": logging.ERROR,
                "pre_context_lines": 5,
                "post_context_lines": 5
            }, {
                "substr": "Obscure error #94382",
                "explanation":
                    "This is a fatal program error."
                "exception": ScriptHarnessFatal
            }
        ]

    Any output line that matches the first regex will be ignored (discarded),
    because level is negative.  Because the list is matched in order, the
    more specific regex is placed before the more general 2nd regex.  If the
    order were reversed, the more specific regex would never match anything.
    The second regex sets the level to logging.ERROR for this line, and 5
    lines above and 5 lines below this message.

    Attributes:
      strict (bool): If True, be more strict about well-formed error_lists.
      pre_context_lines (int): The max number of lines the error_list defines
        in pre_context_lines.
      post_context_lines (int): The max number of lines the error_list defines
        in post_context_lines.
      error_list (list of dicts): The error list.
    """
    def __init__(self, error_list, strict=True):
        self.strict = strict
        (self.pre_context_lines, self.post_context_lines) = \
            self.validate_error_list(error_list)
        super(ErrorList, self).__init__(error_list)

    @staticmethod
    def check_context_lines(context_lines, orig_context_lines, name, messages):
        """Verifies and returns the larger int of context_lines and
        orig_context_lines.

        Args:
          context_lines (value): The value of pre_context_lines or
            post_context_lines to validate.

          orig_context_lines (int): The previous max int sent to
            check_context_lines

          name (str): The name of the field (pre_context_lines or
            post_context_lines)

          messages (list): The list of error messages so far.

        Returns:
          int: If context_lines is a non-int or negative, an error is appended
            to messages and we return orig_context_lines.  Otherwise, we return
            the max of context_lines or orig_context_lines.
        """
        if not isinstance(context_lines, int) or context_lines < 0:
            messages.append(
                "%s %s must be a positive int!" %
                (name, six.text_type(context_lines))
            )
            return orig_context_lines
        return max(context_lines, orig_context_lines)

    @staticmethod
    def exactly_one(key1, key2, error_check, messages):
        """Make sure one, and only one, of key1 and key2 are in error_check.
        If that's not the case, append an error message in messages.

        Args:
          key1 (str): Dictionary key.

          key2 (str): Dictionary key.

          error_check (dict): a single item of error_list.

          messages (list): the list of error messages so far.

        Returns:
          Bool: True if there is exactly one of the two keys in error_check.
        """
        status = True
        error_check_str = six.text_type(error_check)
        if key1 not in error_check and key2 not in error_check:
            messages.append(
                "%s must contain '%s' or '%s'!" % (error_check_str, key1, key2)
            )
            status = False
        elif key1 in error_check and key2 in error_check:
            messages.append(
                "%s has both '%s' and '%s'!" % (error_check_str, key1, key2)
            )
            status = False
        return status

    @staticmethod
    def verify_unicode(key, error_check, messages):
        """If key is in error_check, it must be of type six.text_type.
        If not, append an error message to messages.

        Args:
          key (str): a dict key
          error_check (dict): a single item of error_list
          messages (list): The error messages so far
        """
        if key in error_check and not \
                isinstance(error_check[key], six.text_type):
            messages.append(
                "%s %s is not of type %s!" % (error_check, key, six.text_type)
            )

    def check_ignore(self, ignore, name, error_check, messages):
        """If the level of an error_check is negative, it will be ignored.
        There is currently no pre_context_lines or post_context_lines support
        for ignored lines.  When self.strict is True, append an error to
        messages.

        Args:
          ignore (bool): True when 'level' is in error_check and negative.
          name (str): The name of the key (pre_context_lines,
            post_context_lines)
          error_check (dict): A single item of error_list
          messages (list): The error messages so far.
        """
        if ignore and self.strict:
            messages.append(
                "%s '%s' will be ignored because 'level' < 0." %
                (error_check, name)
            )

    def validate_error_list(self, error_list):
        """Validate an error_list.
        This is going to be a pain to unit test properly.

        Args:
          error_list (list of dicts): an error_list.

        Returns:
          (pre_context_lines, post_context_lines) (tuple of int, int)

        Raises:
          scriptharness.exceptions.ScriptHarnessException: if error_list is not
            well-formed.
        """
        messages = []
        context_lines_re = re.compile(r'^(\d+):(\d+)')
        re_compile_class = context_lines_re.__class__
        pre_context_lines = 0
        post_context_lines = 0
        for error_check in error_list:
            ignore = False
            error_check_str = six.text_type(error_check)
            if not isinstance(error_check, dict):
                messages.append("%s is not a dict!" % error_check_str)
                continue
            if 'level' in error_check:
                if not isinstance(error_check['level'], int):
                    messages.append(
                        "%s level must be an int!" % error_check_str
                    )
                elif error_check['level'] < 0:
                    ignore = True
            elif 'exception' not in error_check:
                messages.append(
                    "%s level must be set if exception is not set!" %
                    error_check_str
                )
            if 'exception' in error_check and (not \
                    isinstance(error_check['exception'], type) or not \
                    issubclass(error_check['exception'], Exception)):
                messages.append(
                    "%s exception must be a subclass of Exception!" %
                    error_check_str
                )
            self.exactly_one('substr', 'regex', error_check, messages)
            self.verify_unicode('substr', error_check, messages)
            if 'regex' in error_check and not \
                    isinstance(error_check['regex'], re_compile_class):
                messages.append(
                    "%s regex needs to be re.compile'd!" % error_check_str
                )
            if 'pre_context_lines' in error_check:
                pre_context_lines = self.check_context_lines(
                    error_check['pre_context_lines'], pre_context_lines,
                    "pre_context_lines", messages
                )
                self.check_ignore(ignore, 'pre_context_lines', error_check,
                                  messages)
            if 'post_context_lines' in error_check:
                post_context_lines = self.check_context_lines(
                    error_check['post_context_lines'], post_context_lines,
                    "post_context_lines", messages
                )
                self.check_ignore(ignore, 'post_context_lines', error_check,
                                  messages)
            self.verify_unicode('explanation', error_check, messages)
        if messages:
            raise ScriptHarnessException(messages)
        return (pre_context_lines, post_context_lines)


