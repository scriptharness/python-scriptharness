#!/usr/bin/env python
'''
Allow for full logging.
'''

from __future__ import absolute_import, division, print_function
from copy import deepcopy
import logging
import os
from scriptharness import ScriptHarnessException, ScriptHarnessFailure


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


# LogMethod decorator {{{1
class LogMethod(object):
    '''
    Wrapper decorator object for logging and error detection.
    '''
    # Beware: Changes to default_config will carry over to other decorated
    # LogMethod functions!
    default_config = {
        'level': logging.INFO,
        'error_level': logging.ERROR,
        'logger_name': '{func_name}',
        'pre_msg': '%(func_name)s arguments were: %(args)s %(kwargs)s',
        'post_success_msg': '%(func_name)s completed.',
        'post_failure_msg': '%(func_name)s failed.',
        'raise_on_error': False,
        'detect_error_cb': None,
    }

    def __init__(self, func=None, **kwargs):
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
        self.return_value = None
        self.args = None
        self.kwargs = None
        self.repl_dict = {}
        self.detected_errors = False
        self.config = deepcopy(self.default_config)
        messages = []
        for key, value in kwargs.items():
            if key not in self.config:
                messages.append('Unknown key {0} in kwargs!'.format(key))
            self.config[key] = value
        if kwargs.get('detect_error_cb') is not None and \
                not callable(kwargs['detect_error_cb']):
            messages.append('detect_error_cb not callable!')
        if messages:
            raise ScriptHarnessException(os.linesep.join(messages))

    def __call__(self, func, *args, **kwargs):
        '''
        When there are decorator arguments, __call__ is only called once, at
        decorator time.  *args and **kwargs only show up when func is called,
        so we need to create and return a wrapping function.
        '''
        self.func = func
        def wrapped_func(*args, **kwargs):
            '''
            This function replaces the decorated function.
            '''
            self.args = args
            self.kwargs = kwargs
            self.set_repl_dict()
            self.pre_func()
            self.return_value = self.func(*self.args, **self.kwargs)
            self.repl_dict['return_value'] = self.return_value
            if self.config['detect_error_cb'] is not None:
                self.detected_errors = self.config['detect_error_cb'].__call__(self)
            self.post_func()
            return self.return_value
        return wrapped_func

    def set_repl_dict(self):
        '''
        The log messages in pre_func() and post_func() require some additional
        info.  Specify that info in the replacement dictionary.

        Currently, set the following:

            func_name: self.func.__name__
            args: the args passed to self.func()
            kwargs: the kwargs passed to self.func()

        After running self.func, we'll also set return_value.
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
        log = logging.getLogger(
            self.config['logger_name'].format(**self.repl_dict)
        )
        log.log(self.config['level'], self.config['pre_msg'], self.repl_dict)

    def post_func(self):
        '''
        Currently, log the success message until we get an error detection callback.

        This method is split out for easier subclassing.
        '''
        log = logging.getLogger(
            self.config['logger_name'].format(**self.repl_dict)
        )
        if self.detected_errors:
            msg = self.config['post_failure_msg']
            level = self.config['error_level']
        else:
            msg = self.config['post_success_msg']
            level = self.config['level']
        log.log(level, msg, self.repl_dict)
        if self.detected_errors and self.config['raise_on_error']:
            raise ScriptHarnessFailure(
                self.config['post_failure_msg'].format(**self.repl_dict)
            )
