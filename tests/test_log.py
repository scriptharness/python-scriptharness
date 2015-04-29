#!/usr/bin/env python
'''
Test scriptharness.log
'''
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
