#!/usr/bin/env python
'''
Allow for full logging.
'''

# Imports
from __future__ import absolute_import, division, print_function

import logging
import os

from scriptharness import ScriptHarnessUsageException, ScriptHarnessFailure

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


class LogMethod(object):
    '''
    Wrapper decorator object for logging and error detection.
    '''
    return_value = None
    args = None
    kwargs = None
    repl_dict = {}
    detected_errors = False

    config = {
        'level': logging.INFO,
        'error_level': logging.ERROR,
        'pre_msg': '%(func_name)s arguments were: %(args)s %(kwargs)s',
        'post_success_msg': '%(func_name)s completed.',
        'post_failure_msg': '%(func_name)s failed.',
        'raise_on_error': False,
        'detect_error_cb': None,
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
        messages = []
        for key, value in kwargs.items():
            if key not in self.config:
                messages.append('Unknown key {0} in kwargs!'.format(key))
            self.config[key] = value
        if kwargs.get('detect_error_cb') is not None and \
                not callable(kwargs['detect_error_cb']):
            messages.append('detect_error_cb not callable!')
        if messages:
            raise ScriptHarnessUsageException(os.linesep.join(messages))

    def __call__(self, *args, **kwargs):
        '''
        Set self.args and self.kwargs before this workflow:

        * self.pre_function to log the call before running the function
        * self.call_function run the function
        * self.post_function to log the function completion.
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

        Currently, set the following:

            func_name: self.func.__name__
            args: the args passed to self.func()
            kwargs: the kwargs passed to self.func()

        After self.call_func(), return_value will also be set.
        '''
        self.repl_dict = {
            'func_name': self.func.__name__,
            'args': self.args,
            'kwargs': self.kwargs,
        }

    def pre_func(self):
        '''
        Log the function call before proceeding.

        This method is split out for easier subclassing.
        '''
        # should I getLogger(self.func.__name__) ?
        log = logging.getLogger('scriptharness')
        log.log(self.config['level'], self.config['pre_msg'], self.repl_dict)

    def call_func(self):
        '''
        Set self.return_value from the function call, and add it to the repl_dict.

        This method is split out for easier subclassing.

        TODO try/except?
        '''
        self.return_value = self.func(*self.args, **self.kwargs)
        self.repl_dict['return_value'] = self.return_value
        if self.config['detect_error_cb'] is not None:
            self.detected_errors = self.config['detect_error_cb'].__call__(self)

    def post_func(self):
        '''
        Currently, log the success message until we get an error detection callback.

        This method is split out for easier subclassing.
        '''
        # should I getLogger(self.func.__name__) ?
        log = logging.getLogger('scriptharness')
        if self.detected_errors:
            msg = self.config['post_failure_msg']
            level = self.config['error_level']
        else:
            msg = self.config['post_success_msg']
            level = self.config['level']
        log.log(level, msg, self.repl_dict)
        if self.detected_errors and self.config['raise_on_error']:
            raise ScriptHarnessFailure(
                self.config['post_failure_msg'].format(self.repl_dict)
            )


#@LogMethod
#def chdir(*args, **kwargs):
#    '''
#    Test log_decorator by wrapping os.chdir()
#
#    I haven't decided yet whether I'm going to wrap a bunch of python builtins,
#    but this could potentially become scriptharness.os.chdir()
#    '''
#    os.chdir(*args, **kwargs)
#    log = logging.getLogger('scriptharness')
#    log.info('Now in %s', os.getcwd())
