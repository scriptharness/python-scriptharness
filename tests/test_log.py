#!/usr/bin/env python
'''
Test scriptharness.log
'''
from copy import deepcopy
import logging
import mock
import scriptharness.log as log
import unittest
from scriptharness import ScriptHarnessUsageException, ScriptHarnessFailure


# TestSetLoggingConfig {{{1
class TestSetLoggingConfig(unittest.TestCase):
    '''
    Test scriptharness.log.set_logging_config() method
    '''
    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_no_kwargs(mock_logging):
        '''
        Test set_logging_config with no arguments
        '''
        log.set_logging_config()
        mock_logging.basicConfig.assert_called_once_with(**log.LOGGING_DEFAULTS)

    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_default_kwargs(mock_logging):
        '''
        Test set_logging_config with default kwargs
        '''
        log.set_logging_config(**log.LOGGING_DEFAULTS)
        mock_logging.basicConfig.assert_called_once_with(**log.LOGGING_DEFAULTS)

    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_kwargs(mock_logging):
        '''
        Test set_logging_config with non-default kwargs
        '''
        test_kwargs = (
            {'filemode': 'a'},
            {'format': '%(message)s'},
            {'filename': 'x', 'filemode': 'w'},
        )
        for orig_kwargs in test_kwargs:
            log.set_logging_config(**orig_kwargs)
            kwargs = deepcopy(log.LOGGING_DEFAULTS)
            kwargs.update(orig_kwargs)
            mock_logging.basicConfig.assert_called_with(**kwargs)


# TestLogMethodInit {{{1
class TestLogMethodInit(unittest.TestCase):
    '''
    Test scriptharness.log.LogMethod.__init__()
    '''
    def test_no_kwargs(self):
        '''
        LogMethod.__init__() with no keyword arguments
        '''
        func = 'x'
        log_method = log.LogMethod(func)
        self.assertEqual(log_method.config, log.LogMethod.config)
        self.assertEqual(log_method.func, func)

    def test_illegal_kwargs(self):
        '''
        LogMethod.__init__() with illegal keyword argument
        '''
        kwargs = {
            'level': logging.WARNING,
            'illegal_scriptharness_option': 1,
        }
        self.assertRaises(
            ScriptHarnessUsageException, log.LogMethod, 'x', **kwargs
        )

    def test_basic_decorator_return(self):
        '''
        Basic @LogMethod decorator return
        '''
        @log.LogMethod
        def test_func(*args, **kwargs):
            ''' test method '''
            return args, kwargs
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        self.assertEqual((args, kwargs), test_func(*args, **kwargs))


# TestLogMethod {{{1
class TestLogMethod(unittest.TestCase):
    '''
    scriptharness.log.LogMethod, outside of __init__()
    '''
    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_basic_decorator_prefunc(mock_logging):
        '''
        Basic @LogMethod pre_func()
        '''
        class NoPostFunc(log.LogMethod):
            '''
            Subclass LogMethod to only log from pre_func()
            '''
            def call_func(self):
                ''' Skip calling '''
                pass
            def post_func(self):
                ''' Skip logging '''
                pass

        @NoPostFunc
        def test_func(*args, **kwargs):
            ''' test method '''
            return args, kwargs

        mock_func = mock.MagicMock()
        mock_logging.getLogger.return_value = mock_func

        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        test_func(*args, **kwargs)
        mock_func.log.assert_called_once_with(
            log.LogMethod.config['level'],
            log.LogMethod.config['pre_msg'],
            {
                'func_name': 'test_func',
                'args': args,
                'kwargs': kwargs,
            },
        )

    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_basic_decorator_postfunc(mock_logging):
        '''
        Basic @LogMethod post_func()
        '''
        @log.LogMethod
        def test_func(*args, **kwargs):
            ''' test method '''
            return args, kwargs

        mock_func = mock.MagicMock()
        mock_logging.getLogger.return_value = mock_func

        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        test_func(*args, **kwargs)
        mock_func.log.assert_called_with(
            log.LogMethod.config['level'],
            log.LogMethod.config['post_success_msg'],
            {
                'func_name': 'test_func',
                'args': args,
                'kwargs': kwargs,
                'return_value': (args, kwargs)
            },
        )
