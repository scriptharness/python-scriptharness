#!/usr/bin/env python
'''
Logging.
'''

from __future__ import absolute_import, division, print_function

import logging

log = logging.getLogger(__name__)


def set_logging_basic_config(**kwargs):
    '''
    Set the logging.basicConfig() defaults.
    These can be overridden on either a global level or per-logger.
    '''
    kwargs.setdefault('level', logging.INFO)
    kwargs.setdefault('datefmt', '%H:%M:%S')
    kwargs.setdefault('format', '%(asctime)s %(levelname)8s - %(message)s')
    logging.basicConfig(**kwargs)

# from http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
def log_decorator(func):
    '''
    Use this decorator to add generic logging to any function.
    '''
    def inner(*args, **kwargs):
        '''
        Call the wrapped function.
        '''
        log.info('%s arguments were: %s %s', func.__name__, args, kwargs)
        return func(*args, **kwargs)
    return inner

import os
@log_decorator
def chdir(*args, **kwargs):
    '''
    Test log_decorator by wrapping os.chdir()
    '''
    os.chdir(*args, **kwargs)
    log.info('Now in %s', os.getcwd())



if __name__ == '__main__':
    set_logging_basic_config()
    log.info('test')
    chdir('/tmp')
