#!/usr/bin/env python
"""
Script harness.
"""
from __future__ import print_function

#Semantic versioning 2.0.0  http://semver.org/
__version__ = (0, 1, 0, 'alpha')
if len(__version__) == 3:
    __version_string__ = '.'.join(['%d' % i for i in __version__])
else:
    __version_string__ = '{0}.{1}.{2}-{3}'.format(*__version__)


if __name__ == '__main__':
    print(__version_string__)
