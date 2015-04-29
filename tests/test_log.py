#!/usr/bin/env python
'''
Test scriptharness.log
'''
from copy import deepcopy
import mock
import scriptharness.log as log
import unittest
#from scriptharness import ScriptHarnessException


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
    @mock.patch('scriptharness.log.logging')
    def test_no_kwargs(self, mock_logging):
        '''
        Test LogMethod.__init__() with no keyword arguments
        '''
        func = 'x'
        lm = log.LogMethod(func)
        self.assertEqual(lm.config, log.LogMethod.config)
        self.assertEqual(lm.func, func)
