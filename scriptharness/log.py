#!/usr/bin/env python
'''
Logging.
'''

# Imports
from __future__ import absolute_import, division, print_function

import logging
import os
from scriptharness import ScriptHarnessException

# "Constants"
LOG = logging.getLogger(__name__)

LOGGING_DEFAULTS = {
    'level': logging.INFO,
    'datefmt': '%H:%M:%S',
    'format': '%(asctime)s %(levelname)8s - %(message)s',
}


def set_logging_config(**kwargs):
    '''
    Set the logging.basicConfig() defaults.
    These can be overridden on either a global level or per-logger.
    '''
    for key, value in LOGGING_DEFAULTS.items():
        kwargs.setdefault(key, value)
    logging.basicConfig(**kwargs)

# from http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
def simple_log(func):
    '''
    Use this decorator to add generic logging to any function.
    Most likely this will be abandoned in favor of the class.
    '''
    def inner(*args, **kwargs):
        '''
        Call the wrapped function.
        '''
        LOG.info('%s arguments were: %s %s', func.__name__, args, kwargs)
        return func(*args, **kwargs)
    return inner


class LogMethod(object):
    '''
    Wrapper decorator object for logging and error detection.
    '''
    return_value = None
    args = None
    kwargs = None
    repl_dict = {}

    config = {
        'level': logging.INFO,
        'error_level': logging.ERROR,
        'pre_msg': '%(func_name)s arguments were: %(args)s %(kwargs)s',
        'post_success_msg': '%(func_name)s completed.',
        'post_failure_msg': '%(func_name)s failed.',
        #'raise_on_failure': False,
        #'detect_error_cb': None,
    }

    def __init__(self, func, **kwargs):
        '''
        Set instance attributes from the decorator, e.g.

            @LogMethod(foo='bar')
            def decorated_function(...):

        In the above example, func will be decorated_function, and kwargs
        will be {'foo': 'bar'}.  (Which will raise an exception, because
        'foo' isn't in self.defaults.)

        All of the self.defaults are overrideable via **kwargs or
        subclassing and changing self.defaults.
        '''
        self.func = func
        message = ''
        for key, value in kwargs.items():
            if key not in self.config:
                message += 'Unknown key {0} in kwargs!{1}'.format(key, os.linesep)
            self.config[key] = value
        if message:
            raise ScriptHarnessException(message)

    def __call__(self, *args, **kwargs):
        '''
        Set self.args and self.kwargs before this workflow:

        * self.pre_function to log the call before running the function
        * self.call_function run the function
        * self.post_function to log the function completion.
        TODO detect errors
        '''
        self.args = args
        self.kwargs = kwargs
        self.set_repl_dict()
        self.pre_func()
        self.call_func()
        self.post_func()
        return self.return_value

    def set_repl_dict(self):
        '''
        The log messages in pre_func() and post_func() require some additional
        info.  Specify that info in the replacement dictionary.
        '''
        self.repl_dict = {
            'func_name': self.func.__name__,
            'args': self.args,
            'kwargs': self.kwargs,
        }

    def pre_func(self):
        '''
        Log the function call before proceeding.
        '''
        LOG.log(self.config['level'], self.config['pre_msg'], self.repl_dict)

    def call_func(self):
        '''
        Set self.return_value from the function call, and add it to the repl_dict.
        TODO error detection
        '''
        self.return_value = self.func(*self.args, **self.kwargs)
        self.repl_dict['return_value'] = self.return_value

    def post_func(self):
        '''
        Currently, log the success message until we get an error detection callback.
        TODO error detection
        '''
        LOG.log(self.config['level'], self.config['post_success_msg'], self.repl_dict)


@simple_log
def chdir(*args, **kwargs):
    '''
    Test log_decorator by wrapping os.chdir()
    '''
    os.chdir(*args, **kwargs)
    LOG.info('Now in %s', os.getcwd())



if __name__ == '__main__':
    set_logging_config()
    LOG.info('test')
    chdir('/tmp')
