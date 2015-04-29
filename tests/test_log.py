#!/usr/bin/env python
'''
Test scriptharness.log
'''
import logging
import mock
import scriptharness.log as log
import unittest
from scriptharness import ScriptHarnessException


# TestSetLoggingConfig {{{1

class TestSetLoggingConfig(unittest.TestCase):
    '''
    Test scriptharness.log.set_logging_config() method
    '''
    @mock.patch('scriptharness.log.logging')
    def test_no_kwargs_set_logging_config(self, mock_logging):
        '''
        '''
        log.set_logging_config()
        mock_logging.basicConfig.assert_called_once_with(**log.LOGGING_DEFAULTS)
