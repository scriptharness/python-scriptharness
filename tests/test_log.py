#!/usr/bin/env python
"""Test scriptharness.log
"""
from __future__ import absolute_import, division, print_function
from copy import deepcopy
import logging
import mock
import os
import scriptharness.log as log
import unittest
from scriptharness import ScriptHarnessException, ScriptHarnessFailure


# Helper methods {{{1
class NoPostFunc(log.LogMethod):
    """Subclass LogMethod to only log from pre_func()
    """
    def call_func(self):
        """Skip calling"""
        pass
    def post_func(self):
        """Skip logging"""
        pass

def always_fail_cb(*args):
    """always fail"""
    return True

def always_succeed_cb(*args):
    """always succeed"""
    return False


# TestSetLoggingConfig {{{1
class TestSetLoggingConfig(unittest.TestCase):
    """Test scriptharness.log.set_logging_config() method
    """
    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_no_kwargs(mock_logging):
        """Test set_logging_config with no arguments
        """
        log.set_logging_config()
        mock_logging.basicConfig.assert_called_once_with(**log.LOGGING_DEFAULTS)

    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_default_kwargs(mock_logging):
        """Test set_logging_config with default kwargs
        """
        log.set_logging_config(**log.LOGGING_DEFAULTS)
        mock_logging.basicConfig.assert_called_once_with(**log.LOGGING_DEFAULTS)

    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_kwargs(mock_logging):
        """Test set_logging_config with non-default kwargs
        """
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


# TestGetFormatter {{{1
class TestGetFormatter(unittest.TestCase):
    """Test scriptharness.log.get_formatter() method
    """
    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_no_kwargs(mock_logging):
        """Test get_formatter with no arguments
        """
        log.get_formatter()
        mock_logging.Formatter.assert_called_once_with(
            fmt=log.LOGGING_DEFAULTS['format'],
            datefmt=log.LOGGING_DEFAULTS['datefmt'],
        )

    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_with_kwargs(mock_logging):
        """Test get_formatter with arguments
        """
        for fmt, datefmt in [
                ('%(message)s', '%H:%M:%S'),
                ('%(name)s:%(levelname)s:%(message)s', '%Y-%m-%d %H:%M:%S'),
                ('%(name)s - %(levelname)s: %(message)s', None),
                (None, '%D:%H:%M:%S'),
            ]:
            log.get_formatter(fmt=fmt, datefmt=datefmt)
            mock_logging.Formatter.assert_called_with(
                fmt=fmt or log.LOGGING_DEFAULTS['format'],
                datefmt=datefmt or log.LOGGING_DEFAULTS['datefmt'],
            )


# TestGetFileHandler {{{1
class TestGetFileHandler(unittest.TestCase):
    """Test scriptharness.log.get_file_handler() method
    """
    test_file = '_test_log'
    test_contents = "Newly initialized test file"

    def _absent_test_file(self):
        """Return a test file path that doesn't exist.
        """
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        assert not os.path.exists(self.test_file)
        return self.test_file

    def _present_test_file(self):
        """Return a test file path that exists with initialized content.
        """
        filehandle = open(self.test_file, 'w')
        print(self.test_contents, file=filehandle)
        filehandle.close()
        return self.test_file

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    @mock.patch('scriptharness.log.logging')
    def test_basic(self, mock_logging):
        """Test basic get_file_handler
        """
        log_file = self._absent_test_file()
        formatter = mock.MagicMock()
        handler = log.get_file_handler(log_file, formatter=formatter)
        mock_logging.FileHandler.assert_called_once_with(log_file)
        handler.setFormatter.assert_called_once_with(formatter)

    @mock.patch('scriptharness.log.logging')
    @mock.patch('scriptharness.log.os')
    @mock.patch('scriptharness.log.os.path')
    def test_delete_file(self, mock_logging, mock_os, mock_os_path):
        """Test get_file_handler with existing log file
        """
        assert mock_logging  # shush pylint
        mock_os_path.exists.return_value = True
        log_file = self._present_test_file()
        logger = mock.MagicMock()
        handler = log.get_file_handler(log_file, logger=logger)
        mock_os.remove.assert_called_once_with(log_file)
        logger.addHandler.assert_called_once_with(handler)

# TestGetConsoleHandler {{{1
class TestGetConsoleHandler(unittest.TestCase):
    """Test scriptharness.log.get_console_handler() method
    """
    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_addhandler(mock_logging):
        """Test get_console_handler with existing log file
        """
        assert mock_logging  # shush pylint
        logger = mock.MagicMock()
        handler = log.get_console_handler(logger=logger)
        logger.addHandler.assert_called_once_with(handler)

    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_handler(mock_logging):
        """Test basic get_console_handler
        """
        assert mock_logging  # shush pylint
        formatter = mock.MagicMock()
        handler = log.get_console_handler(formatter=formatter,
                                          level=logging.DEBUG)
        handler.setLevel.assert_called_once_with(logging.DEBUG)
        handler.setFormatter.assert_called_once_with(formatter)

# TestLogMethodInit {{{1
class TestLogMethodInit(unittest.TestCase):
    """Test scriptharness.log.LogMethod.__init__()
    """
    def test_no_kwargs(self):
        """LogMethod.__init__() with no keyword arguments
        """
        func = 'x'
        log_method = log.LogMethod(func)
        self.assertEqual(log_method.config, log.LogMethod.default_config)
        self.assertEqual(log_method.func, func)

    def test_illegal_kwargs(self):
        """LogMethod.__init__() with illegal keyword argument
        """
        kwargs = {
            'level': logging.WARNING,
            'illegal_scriptharness_option': 1,
        }
        self.assertRaises(
            ScriptHarnessException, log.LogMethod, 'x', **kwargs
        )

    def test_basic_decorator_return(self):
        """Basic @LogMethod decorator return
        """
        @log.LogMethod()
        def test_func(*args, **kwargs):
            """test method"""
            return args, kwargs
        import pprint
        pprint.pprint(log.LogMethod.default_config)
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        self.assertEqual((args, kwargs), test_func(*args, **kwargs))

    def test_illegal_callback(self):
        """LogMethod.__init__() with illegal detect_error_cb
        """
        self.assertRaises(
            ScriptHarnessException, log.LogMethod,
            'x', **{'detect_error_cb': 'y'}
        )


# TestLogMethodFunction {{{1
class TestLogMethodFunction(unittest.TestCase):
    """scriptharness.log.LogMethod wrapping a function
    """
    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_basic_decorator_prefunc(mock_logging):
        """Basic @LogMethod pre_func(), function
        """
        @NoPostFunc()
        def test_func(*args, **kwargs):
            """test method"""
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
        """Basic @LogMethod post_func(), function
        """
        @log.LogMethod()
        def test_func(*args, **kwargs):
            """test method"""
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
        """Use @LogMethod detect_error_cb, function, fail
        """
        mock_func = mock.MagicMock()
        mock_logging.getLogger.return_value = mock_func
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        for level in logging.ERROR, logging.WARNING, logging.CRITICAL:
            @log.LogMethod(detect_error_cb=always_fail_cb, error_level=level)
            def test_func(*args, **kwargs):
                """test method"""
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

    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_error_cb_success(mock_logging):
        """Use @LogMethod detect_error_cb, function, succeed
        """
        mock_func = mock.MagicMock()
        mock_logging.getLogger.return_value = mock_func
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        for level in logging.INFO, logging.DEBUG:
            @log.LogMethod(detect_error_cb=always_succeed_cb, level=level)
            def test_func(*args, **kwargs):
                """test method"""
                return args, kwargs
            test_func(*args, **kwargs)
            mock_func.log.assert_called_with(
                level,
                log.LogMethod.default_config['post_success_msg'],
                {
                    'func_name': 'test_func',
                    'args': args,
                    'kwargs': kwargs,
                    'return_value': (args, kwargs)
                },
            )

    @mock.patch('scriptharness.log.logging')
    def test_raise_on_error(self, mock_logging):
        """Use @LogMethod detect_error_cb, function, raise
        """
        mock_func = mock.MagicMock()
        mock_logging.getLogger.return_value = mock_func
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        @log.LogMethod(detect_error_cb=always_fail_cb, raise_on_error=True)
        def test_func(*args, **kwargs):
            """test method"""
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

    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_no_raise_success(mock_logging):
        """Use @LogMethod detect_error_cb, function, don't raise on success
        """
        mock_func = mock.MagicMock()
        mock_logging.getLogger.return_value = mock_func
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        @log.LogMethod(detect_error_cb=always_succeed_cb, raise_on_error=True)
        def test_func(*args, **kwargs):
            """test method"""
            return args, kwargs
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


# TestLogMethodClass {{{1
class TestLogMethodClass(unittest.TestCase):
    """scriptharness.log.LogMethod wrapping a class method.

    This will largely be the same as TestLogMethodFunction, but will need to
    take into account for the 'self' arg.

    It's debatable whether these tests add anything; if they don't catch any
    additional errors that the TestLogMethodFunction tests miss then they're
    a candidate for deletion.
    """
    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_basic_decorator_prefunc(mock_logging):
        """Basic @LogMethod pre_func(), class method
        """
        class TestClass(object):
            """test class"""
            @NoPostFunc()
            def test_func(self, *args, **kwargs):
                """test method"""
                return self, args, kwargs
            def shutup_pylint(self):
                """pylint complains about too few public methods"""
                pass
        mock_func = mock.MagicMock()
        mock_logging.getLogger.return_value = mock_func
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        test_instance = TestClass()
        test_instance.test_func(*args, **kwargs)
        mock_func.log.assert_called_once_with(
            log.LogMethod.default_config['level'],
            log.LogMethod.default_config['pre_msg'],
            {
                'func_name': 'test_func',
                'args': tuple([test_instance] + list(args)),
                'kwargs': kwargs,
                'return_value': (test_instance, args, kwargs)
            },
        )

    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_basic_decorator_postfunc(mock_logging):
        """Basic @LogMethod post_func(), class method
        """
        class TestClass(object):
            """test class"""
            @log.LogMethod()
            def test_func(self, *args, **kwargs):
                """test method"""
                return self, args, kwargs
            def shutup_pylint(self):
                """pylint complains about too few public methods"""
                pass
        mock_func = mock.MagicMock()
        mock_logging.getLogger.return_value = mock_func

        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        test_instance = TestClass()
        test_instance.test_func(*args, **kwargs)
        mock_func.log.assert_called_with(
            log.LogMethod.default_config['level'],
            log.LogMethod.default_config['post_success_msg'],
            {
                'func_name': 'test_func',
                'args': tuple([test_instance] + list(args)),
                'kwargs': kwargs,
                'return_value': (test_instance, args, kwargs)
            },
        )

    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_error_cb_failure(mock_logging):
        """Use @LogMethod detect_error_cb, class method, fail
        """
        mock_func = mock.MagicMock()
        mock_logging.getLogger.return_value = mock_func
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        for level in logging.ERROR, logging.WARNING, logging.CRITICAL:
            class TestClass(object):
                """test class"""
                @log.LogMethod(detect_error_cb=always_fail_cb,
                               error_level=level)
                def test_func(self, *args, **kwargs):
                    """test method"""
                    return self, args, kwargs
                def shutup_pylint(self):
                    """pylint complains about too few public methods"""
                    pass
            test_instance = TestClass()
            test_instance.test_func(*args, **kwargs)
            mock_func.log.assert_called_with(
                level,
                log.LogMethod.default_config['post_failure_msg'],
                {
                    'func_name': 'test_func',
                    'args': tuple([test_instance] + list(args)),
                    'kwargs': kwargs,
                    'return_value': (test_instance, args, kwargs)
                },
            )

    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_error_cb_success(mock_logging):
        """Use @LogMethod detect_error_cb, class method, succeed
        """
        mock_func = mock.MagicMock()
        mock_logging.getLogger.return_value = mock_func
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        for level in logging.INFO, logging.DEBUG:
            class TestClass(object):
                """test class"""
                @log.LogMethod(detect_error_cb=always_succeed_cb, level=level)
                def test_func(self, *args, **kwargs):
                    """test method"""
                    return self, args, kwargs
                def shutup_pylint(self):
                    """pylint complains about too few public methods"""
                    pass
            test_instance = TestClass()
            test_instance.test_func(*args, **kwargs)
            mock_func.log.assert_called_with(
                level,
                log.LogMethod.default_config['post_success_msg'],
                {
                    'func_name': 'test_func',
                    'args': tuple([test_instance] + list(args)),
                    'kwargs': kwargs,
                    'return_value': (test_instance, args, kwargs)
                },
            )

    @mock.patch('scriptharness.log.logging')
    def test_raise_on_error(self, mock_logging):
        """Use @LogMethod detect_error_cb, class method, raise
        """
        mock_func = mock.MagicMock()
        mock_logging.getLogger.return_value = mock_func
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        class TestClass(object):
            """test class"""
            @log.LogMethod(detect_error_cb=always_fail_cb, raise_on_error=True)
            def test_func(self, *args, **kwargs):
                """test method"""
                return self, args, kwargs
            def shutup_pylint(self):
                """pylint complains about too few public methods"""
                pass
        test_instance = TestClass()
        self.assertRaises(ScriptHarnessFailure, test_instance.test_func,
                          *args, **kwargs)
        mock_func.log.assert_called_with(
            log.LogMethod.default_config['error_level'],
            log.LogMethod.default_config['post_failure_msg'],
            {
                'func_name': 'test_func',
                'args': tuple([test_instance] + list(args)),
                'kwargs': kwargs,
                'return_value': (test_instance, args, kwargs)
            },
        )

    @staticmethod
    @mock.patch('scriptharness.log.logging')
    def test_no_raise_success(mock_logging):
        """Use @LogMethod detect_error_cb, class method, don't raise on success
        """
        mock_func = mock.MagicMock()
        mock_logging.getLogger.return_value = mock_func
        args = ('a', 'b')
        kwargs = {'c': 1, 'd': 2}
        class TestClass(object):
            """test class"""
            @log.LogMethod(detect_error_cb=always_succeed_cb, raise_on_error=True)
            def test_func(self, *args, **kwargs):
                """test method"""
                return self, args, kwargs
            def shutup_pylint(self):
                """pylint complains about too few public methods"""
                pass
        test_instance = TestClass()
        test_instance.test_func(*args, **kwargs)
        mock_func.log.assert_called_with(
            log.LogMethod.default_config['level'],
            log.LogMethod.default_config['post_success_msg'],
            {
                'func_name': 'test_func',
                'args': tuple([test_instance] + list(args)),
                'kwargs': kwargs,
                'return_value': (test_instance, args, kwargs)
            },
        )
