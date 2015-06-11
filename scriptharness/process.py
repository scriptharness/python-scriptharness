#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Scriptharness multiprocessing support.
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals
import os
import psutil
from psutil import NoSuchProcess
from scriptharness.exceptions import ScriptHarnessError, ScriptHarnessFatal, \
    ScriptHarnessTimeout
from six.moves.queue import Empty
import subprocess
import sys
import time


def kill_proc_tree(pid, include_parent=False, wait=5):
    """Find the children of a process and kill them; optionally also kill
    the process.  Uses psutil, which is cross-platform and py2&3 compatible.

    From http://stackoverflow.com/a/4229404

    Args:
      pid (int): The process ID of the parent.

      include_parent (Optional[bool]): kill the parent as well if True.
        Defaults to False.

      wait (Optional[int]): How long to wait for the children and parent to
        die.  Defaults to 5.
    """
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    for child in children:
        child.kill()
    psutil.wait_procs(children, timeout=wait)
    if include_parent:
        parent.kill()
        parent.wait(wait)


def kill_runner(runner):
    """Kill the runner process and children.

    Args:
      runner (multiprocessing.Process): the process to kill.
    """
    try:
        kill_proc_tree(runner.pid, include_parent=True)
    except NoSuchProcess:
        pass


def command_subprocess(queue, *args, **kwargs):
    """Run a subprocess as a multiprocess.Process.
    This will open STDOUT and STDERR to the same pipe, and read lines from
    it.  Use this with watch_command() for timeout support.

    .. Note:: This is intended for non-binary output only.

    Args:
      queue (multiprocessing.Queue): the queue to write to
      *args: sent to subprocess.Popen
      **kwargs: sent to subprocess.Popen
    """
    kwargs['stdout'] = subprocess.PIPE
    kwargs['stderr'] = subprocess.STDOUT
    kwargs['bufsize'] = 0
    try:
        handle = subprocess.Popen(*args, **kwargs)
    except OSError as exc_info:
        raise ScriptHarnessError("Can't run command!", args, exc_info)
    loop = True
    while loop:
        if handle.poll() is not None:
            loop = False
        while True:
            line = handle.stdout.readline()
            if not line:
                break
            queue.put(line)
    sys.exit(handle.returncode)


def watch_command(logger, queue, runner, # pylint: disable=too-many-arguments
                  add_line_cb, max_timeout=None, output_timeout=None):
    """This function watches the queue of the command_subprocess process.

    Usage::

      queue = multiprocessing.Queue()
      runner = multiprocessing.Process(target=command_subprocess,
                                       args=(queue,))
      runner.start()
      watch_command(logger, queue, runner, add_line_cb,
                    output_timeout=output_timeout, max_timeout=max_timeout)

    Args:
      logger (logging.Logger): the logger to use.

      queue (multiprocessing.Queue): the queue that the runner is writing to.

      runner (multiprocessing.Process): the runner Process to watch.

      add_line_cb (function): any output lines read will be sent here.

      max_timeout (Optional[int]): when specified, the process will be killed
        if it takes longer than this number of seconds.  Default: None

      output_timeout (Optional[int]): when specified, the process will be
        killed if it doesn't produce any output for this number of seconds.
        Default: None

    Returns:
      runner.exitcode (int): on non-timeout.

    Raises:
      scriptharness.exceptions.ScriptHarnessFatal: on KeyboardInterrupt

      scriptharness.exceptions.ScriptHarnessTimeout: on output_timeout or
        max_timeout.
    """
    last_output = start_time = time.time()
    while True:
        empty = False
        try:
            line = queue.get(block=True, timeout=.001)
            add_line_cb(line)
            last_output = time.time()
        except KeyboardInterrupt:
            logger.warning("KeyboardInterrupt: Killing processes!")
            kill_proc_tree(os.getpid(), include_parent=True)
            raise ScriptHarnessFatal("KeyboardInterrupt")
        except Empty:
            # This is to avoid "During handling of the above exception,
            #                   another exception occurred:"
            empty = True
        if empty:
            if not runner.is_alive():
                return runner.exitcode
            now = time.time()
            if output_timeout and (last_output + output_timeout < now):
                message = "%d seconds without output!" % output_timeout
                logger.error(message + "  Killing process...")
                kill_runner(runner)
                raise ScriptHarnessTimeout(message)
            if max_timeout and (start_time + max_timeout < now):
                message = "Hit max timeout of %d seconds!" % max_timeout
                logger.error(message + "  Killing process...")
                kill_runner(runner)
                raise ScriptHarnessTimeout(message)


def watch_output(logger, runner, stdout, # pylint: disable=too-many-arguments
                 stderr, max_timeout=None, output_timeout=None):
    """This function watches the queue of the output_subprocess process.

    Usage::

      runner = multiprocessing.Process(target=output_subprocess, args=(queue,))
      runner.start()
      watch_output(logger, runner, output_timeout=output_timeout,
                   max_timeout=max_timeout)

    Args:
      logger (logging.Logger): the logger to use.

      runner (subprocess.Popen): the runner process to watch.

      max_timeout (Optional[int]): when specified, the process will be killed
        if it takes longer than this number of seconds.  Default: None

      output_timeout (Optional[int]): when specified, the process will be
        killed if it doesn't produce any output for this number of seconds.
        Default: None

    Returns:
      runner.exitcode (int): on non-timeout.

    Raises:
      scriptharness.exceptions.ScriptHarnessFatal: on KeyboardInterrupt

      scriptharness.exceptions.ScriptHarnessTimeout: on output_timeout or
        max_timeout.
    """
    start_time = time.time()
    while True:
        if runner.poll() is not None:
            return runner.returncode
        now = time.time()
        if output_timeout:
            last_output = max(
                os.path.getmtime(stdout.name), os.path.getmtime(stderr.name)
            )
            if last_output + output_timeout < now:
                message = "%d seconds without output!" % output_timeout
                logger.error(message + "  Killing process...")
                runner.kill()
                raise ScriptHarnessTimeout(message)
        if max_timeout and (start_time + max_timeout < now):
            message = "Hit max timeout of %d seconds!" % max_timeout
            logger.error(message + "  Killing process...")
            runner.kill()
            raise ScriptHarnessTimeout(message)
        time.sleep(.1)
