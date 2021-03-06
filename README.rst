Scriptharness
=============
.. This file is built from docs/README.rst.j2; do not edit!

Scriptharness is a framework for writing scripts.  There are three core principles: full logging, flexible configuration, and modular actions.  The goal of `full logging` is to be able to debug problems purely through the log.  The goal of `flexible configuration` is to make each script useful in a variety of contexts and environments.  The goals of `modular actions` are a) faster development feedback loops and b) different workflows for different usage requirements.

.. image:: https://readthedocs.org/projects/python-scriptharness/badge/?version=latest
    :target: https://readthedocs.org/projects/python-scriptharness/?badge=latest
    :alt: Documentation Status

############
Full logging
############

Many scripts log.  However, logging can happen sporadically, and it's generally acceptable to run a number of actions silently (e.g., ``os.chdir()`` will happily change directories with no indication in the log).  In *full logging*, the goal is to be able to debug bustage purely through the log.

At the outset, the user can add a generic logging wrapper to any method with minimal fuss.  As scriptharness matures, there will be more customized wrappers to use as drop-in replacements for previously-non-logging methods.

######################
Flexible configuration
######################

Many scripts use some sort of configuration, whether hardcoded, in a file, or through the command line.  A family of scripts written by the same author(s) may have similar configuration options and patterns, but often times they vary wildly from script to script.

By offering a standard way of accepting configuration options, and then exporting that config to a file for later debugging or replication, scriptharness makes things a bit neater and cleaner and more familiar between scripts.

By either disallowing runtime configuration changes, or by explicitly logging them, scriptharness removes some of the guesswork when debugging bustage.

###############
Modular actions
###############

Scriptharness actions allow for:

* faster development feedback loops.  No need to rerun the entirety of a long-running script when trying to debug a single action inside that script.

* different workflows for different usage requirements, such as running standalone versus running in cloud infrastructure

This is in the same spirit of other frameworks that allow for discrete targets, tasks, or actions: make, maven, ansible, and many more.

#######
Install
#######

::

    # This will automatically bring in all requirements.
    pip install scriptharness

    # To do a full install with docs/testing requirements,
    pip install -r requirements.txt

##################
Running unit tests
##################

Linux and OS X
--------------

::

    # By default, this will look for python 2.7 + 3.{3,4,5}.
    # You can run |tox -e ENV| to run a specific env, e.g. |tox -e py27|
    pip install tox
    tox
    # alternately, ./run_tests.sh

Windows
-------

::

    # By default, this will look for python 2.7 + 3.4
    # You can run |tox -c tox_win.ini -e ENV| to run a specific env, e.g. |tox -c tox_win.ini -e py27|
    pip install tox
    tox -c win.ini
