#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Scriptharness unicode compatibility.

Once scriptharness drops python 2.x support, this module can go away.
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import six


def to_unicode(obj, encoding='utf-8'):
    """Encode a string as unicode in python2.

    http://farmdev.com/talks/unicode/

    Args:
        obj (str): the string to encode
        encoding (Optional[str]): the encoding to use.  Defaults to 'utf-8'.

    Returns:
        obj (unicode): the encoded string
    """
    if not isinstance(obj, six.text_type):
        try:
            obj = six.text_type(obj, encoding)
        except TypeError:
            pass
    return obj
