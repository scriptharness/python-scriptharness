#!/usr/bin/env python
# http://stackoverflow.com/questions/1230669/subprocess-deleting-child-processes-in-windows/4229404#4229404

from __future__ import absolute_import, division, print_function, \
    unicode_literals
import logging
import multiprocessing
import os
import psutil  # requires venv update
import signal
import six
from six.moves.queue import Empty
import subprocess
import sys
import time

def kill_proc_tree(pid, including_parent=False):
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    for child in children:
        child.kill()
    psutil.wait_procs(children, timeout=5)
    if including_parent:
        parent.kill()
        parent.wait(5)

def kill_runner(runner):
    try:
        kill_proc_tree(runner.pid, including_parent=True)
    except psutil.NoSuchProcess:
        pass

def run_subprocess(queue, *args, **kwargs):
    handle = subprocess.Popen(
#        [sys.executable, "-c",
#         'from __future__ import print_function; import time;'
#         'print("one ");time.sleep(2);print("two", end=" ");time.sleep(5);'
#         'print("three ");time.sleep(4);print("four", end=" ");time.sleep(7);'
#         'print("five ");time.sleep(6);print("six", end=" ");time.sleep(9);'
#         'print("seven ");time.sleep(8);print("eight", end=" ");time.sleep(11);'
#        ],
        "/bin/echo 'one' && sleep 5 && "
        "/bin/echo -n 'two' && sleep 7 && "
        "/bin/echo 'three' && sleep 9 && "
        "/bin/echo -n 'bar' && sleep 300", shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        bufsize=0
    )
    loop = True
    while loop:
        if handle.poll() is not None:
            loop = False
        while True:
            line = handle.stdout.readline()
            if not line:
                break
            queue.put(line)

def watch_runner(queue, runner, max_timeout=None, output_timeout=None):
    last_output = start_time = time.time()
    empty = False
    while True:
        try:
            line = queue.get(block=True, timeout=.001)
            print(six.text_type(time.time()) + six.text_type(line).rstrip())
            last_output = time.time()
        except Empty:
            empty = True
        if empty:
            if not runner.is_alive():
                sys.exit(runner.exitcode)
            now = time.time()
            if output_timeout and (last_output + output_timeout < now):
                print("output_timeout")
                kill_runner(runner)
                # output timeout
                # TODO get this in statuses
                raise Exception("output timeout")
            if start_time + max_timeout < now:
                print("timeout")
                kill_runner(runner)
                raise Exception("max timeout")

# TODO catch signals and terminate processes
if __name__ == "__main__":
    queue = multiprocessing.Queue()
    output_timeout = 17
    max_timeout = 150

    runner = multiprocessing.Process(target=run, args=(queue,))
    runner.start()

#    watcher = multiprocessing.Process(
#        target=watch_runner, args=(queue, runner),
#        kwargs={
#            'output_timeout': output_timeout,
#            'max_timeout': max_timeout,
#        },
#    )
#    watcher.start()
#    watcher.join()
    watch_runner(queue, runner, output_timeout=output_timeout, max_timeout=max_timeout)
