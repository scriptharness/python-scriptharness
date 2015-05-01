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
        self.assertEqual(log_method.config, log.LogMethod.default_config)
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
        @log.LogMethod()
        def test_func(*args, **kwargs):
            ''' test method '''
            return args, kwargs
        import pprint
        pprint.pprint(log.LogMethod.default_config)
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        self.assertEqual((args, kwargs), test_func(*args, **kwargs))

    def test_illegal_callback(self):
        '''
        LogMethod.__init__() with illegal detect_error_cb
        '''
        self.assertRaises(
            ScriptHarnessUsageException, log.LogMethod,
            'x', **{'detect_error_cb': 'y'}
        )


# TestLogMethodFunction {{{1
class TestLogMethodFunction(unittest.TestCase):
    '''
    scriptharness.log.LogMethod wrapping a function
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

        @NoPostFunc()
        def test_func(*args, **kwargs):
            ''' test method '''
            return args, kwargs

        mock_func = mock.MagicMock()
        mock_logging.getLogger.return_value = mock_func

        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        test_func(*args, **kwargs)
        mock_func.log.assert_called_once_with(
            log.LogMethod.default_config['level'],
            log.LogMethod.default_config['pre_msg'],
            {
                'func_name': 'test_func',
                'args': args,
                'kwargs': kwargs,
                'return_value': (args, kwargs)
            },
        )

    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_basic_decorator_postfunc(mock_logging):
        '''
        Basic @LogMethod post_func()
        '''
        @log.LogMethod()
        def test_func(*args, **kwargs):
            ''' test method '''
            return args, kwargs

        mock_func = mock.MagicMock()
        mock_logging.getLogger.return_value = mock_func

        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        test_func(*args, **kwargs)
        mock_func.log.assert_called_with(
            log.LogMethod.default_config['level'],
            log.LogMethod.default_config['post_success_msg'],
            {
                'func_name': 'test_func',
                'args': args,
                'kwargs': kwargs,
                'return_value': (args, kwargs)
            },
        )

    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_error_cb_failure(mock_logging):
        '''
        Use @LogMethod detect_error_cb, fail
        '''
        def detect_error_cb(*args):
            ''' always detect errors '''
            return True

        mock_func = mock.MagicMock()
        mock_logging.getLogger.return_value = mock_func
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}

        for level in logging.ERROR, logging.WARNING, logging.CRITICAL:
            @log.LogMethod(detect_error_cb=detect_error_cb, error_level=level)
            def test_func(*args, **kwargs):
                ''' test method '''
                return args, kwargs

            test_func(*args, **kwargs)
            mock_func.log.assert_called_with(
                level,
                log.LogMethod.default_config['post_failure_msg'],
                {
                    'func_name': 'test_func',
                    'args': args,
                    'kwargs': kwargs,
                    'return_value': (args, kwargs)
                },
            )

    @mock.patch('scriptharness.log.logging')
    def test_raise_on_error(self, mock_logging):
        '''
        Use @LogMethod detect_error_cb, raise
        '''
        def detect_error_cb(*args):
            ''' always detect errors '''
            return True
        mock_func = mock.MagicMock()
        mock_logging.getLogger.return_value = mock_func
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        @log.LogMethod(detect_error_cb=detect_error_cb, raise_on_error=True)
        def test_func(*args, **kwargs):
            ''' test method '''
            return args, kwargs
        self.assertRaises(ScriptHarnessFailure, test_func, *args, **kwargs)
        mock_func.log.assert_called_with(
            log.LogMethod.default_config['error_level'],
            log.LogMethod.default_config['post_failure_msg'],
            {
                'func_name': 'test_func',
                'args': args,
                'kwargs': kwargs,
                'return_value': (args, kwargs)
            },
        )
