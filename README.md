# Scriptharness
`scriptharness` is a ground-up rewrite of the generic portions (`mozharness.base.*`) of [`mozharness`](https://hg.mozilla.org/build/mozharness).

## Principles

There are three core principles:

### Full logging

Many scripts log.  However, logging can happen sporadically, and it's generally acceptable to run a number of actions silently (e.g., `os.chdir()` will happily change directories with no indication in the log).  In *full logging*, the goal is to be able to debug bustage purely through the log.

At the outset, the user can add a generic logging wrapper to any method with minimal fuss.  As `scriptharness` matures, there will be more customized wrappers to use as drop-in replacements for previously-non-logging methods.

### Flexible configuration

Many scripts use some sort of configuration, whether hardcoded, in a file, or through the command line.  A family of scripts written by the same author(s) may have similar configuration options and patterns, but often times they vary wildly from script to script.

By offering a standard way of accepting configuration options, and then exporting that config to a file for later debugging or replication, `scriptharness` makes things a bit neater and cleaner and more familiar between scripts.

By either disallowing runtime configuration changes, or by explicitly logging them, `scriptharness` removes some of the guesswork when debugging bustage.

### Modular actions

`scriptharness` actions allow for:
* faster development feedback loops.  No need to rerun the entirety of a long-running script when trying to debug a single action inside that script.
* different workflows for different usage requirements, such as running standalone versus running in cloud infrastructure

This is in the same spirit of other frameworks that allow for discrete targets, tasks, or actions: make, maven, ansible, and many more.

## Secondary goals

* python 2.6 - python 3.x compatible
* full test coverage
* rethink `mozharness`' monolithic object + mixin dependencies
 * allow for easier usage and adoption.
* rethink mozharness' config locking requirement
* rethink mozharness' hardcoded action behavior


## Running unit tests
    # By default, this will look for all minor versions of python between 2.6 and 3.5
    # This can be changed by editing tox.ini
    pip install tox
    tox
