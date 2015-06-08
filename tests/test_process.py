#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/process.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import mock
import os
import psutil
from scriptharness.exceptions import ScriptHarnessError, ScriptHarnessFatal
import scriptharness.process as shprocess
from scriptharness.unicode import to_unicode
from six.moves.queue import Queue
import sys
import unittest


def find_unused_pid():
    """Find an unused pid for testing.
    """
    for num in range(1000, 10000):
        if not psutil.pid_exists(num):
            return num
    return None


# TestProcess {{{1
class TestProcess(unittest.TestCase):
    """Test process.
    """
    def test_kill_nonexistent_pid(self):
        """test_process | Kill a nonexistent pid
        """
        pid = find_unused_pid()
        self.assertRaises(psutil.NoSuchProcess, shprocess.kill_proc_tree, pid,
                          include_parent=True)
        self.assertRaises(psutil.NoSuchProcess, shprocess.kill_proc_tree, pid,
                          include_parent=False)

    @mock.patch('scriptharness.process.psutil')
    def test_kill_proc_tree(self, mock_psutil):
        """test_process | kill_proc_tree
        """
        parent = mock.MagicMock()
        mock_psutil.Process.return_value = parent
        shprocess.kill_proc_tree(99, include_parent=False)
        self.assertFalse(parent.kill.called)
        shprocess.kill_proc_tree(99, include_parent=True)
        parent.kill.assert_called_once_with()

    @staticmethod
    @mock.patch('scriptharness.process.psutil')
    def test_kill_runner(mock_psutil):
        """test_process | kill_runner
        """
        def raise_nosuchprocess(*args, **kwargs):
            """test helper"""
            if args or kwargs:
                pass
            raise psutil.NoSuchProcess(50)
        mock_psutil.Process = raise_nosuchprocess
        process = mock.MagicMock()
        # This should not raise
        shprocess.kill_runner(process)

    def test_command_subprocess(self):
        """test_process | command_subprocess
        """
        queue = Queue()
        self.assertRaises(
            SystemExit, shprocess.command_subprocess,
            queue,
            [sys.executable, "-c",
             "from __future__ import print_function;print('foo')"],
        )
        line = queue.get(block=True, timeout=.1)
        self.assertEqual(to_unicode("foo"), to_unicode(line).rstrip())

    def test_nonexistent_command(self):
        """test_process | command_subprocess nonexistent command
        """
        queue = Queue()
        self.assertRaises(
            ScriptHarnessError, shprocess.command_subprocess,
            queue, ["this_command_should_not_exist"],
        )

    @mock.patch('scriptharness.process.psutil')
    def test_keyboard_interrupt(self, mock_psutil):
        """test_process | KeyboardInterrupt
        """
        class FakeQueue(object):
            """Raises KeyboardInterrupt"""
            def get(self, **_):
                """Raise KeyboardInterrupt"""
                self.raise_ki()
            @staticmethod
            def raise_ki():
                """Silence pylint"""
                raise KeyboardInterrupt()
        queue = FakeQueue()
        logger = mock.MagicMock()
        runner = mock.MagicMock()
        add_line_cb = mock.MagicMock()
        self.assertRaises(
            ScriptHarnessFatal, shprocess.watch_command,
            logger, queue, runner, add_line_cb
        )
        mock_psutil.Process.assert_called_once_with(os.getpid())
