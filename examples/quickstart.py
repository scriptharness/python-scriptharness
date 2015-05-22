#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""python-scriptharness quickstart example.
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import scriptharness

# First, define functions for all actions.  Each action MUST have a function
# defined.
#
# Each action function should be idempotent, and able to run standalone.
# In this example, 'package' may require that the steps in 'build' ran at
# some point before 'package' is run, but we can't assume that happened in
# the same script run.  It could have happened yesterday, or three weeks ago,
# and 'package' should still be able to run.  If you need to save state
# between actions, consider saving state to disk.
def clobber(config):
    """Clobber the source"""
    ...

def pull(config):
    """Pull source"""
    ...

def build(config):
    """Build source"""
    ...

def package(config):
    """Package source"""
    ...

def upload(config):
    """Upload packages"""
    ...

def notify(config):
    """Notify watchers"""
    ...

if __name__ == '__main__':
    # Enable logging to screen + log.txt.  Not required, but without it
    # the script will run silently.
    scriptharness.prepare_simple_logging("log.txt")

    # Define actions.  All six actions are available to run, but if the
    # script is run without any action commandline options, only the
    # enabled actions will run.
    #
    # If default_actions is specified, it MUST be a subset of all_actions
    # (the first list), and any actions in default_actions will be enabled
    # by default (the others will be disabled).  If default_actions isn't
    # specified, all the actions are enabled.
    #
    # Each action MUST have a function defined (see above).
    actions = scriptharness.get_actions_from_list(
        ["clobber", "pull", "build", "package", "upload", "notify"],
        default_actions=["pull", "build", "package"]
    )

    # Create a commandline argument parser, with default scriptharness
    # argument options pre-populated.
    parser = scriptharness.get_parser(all_actions=actions)

    # Add new commandline argument(s)
    parser.add_argument("--new-argument", action='store',
                        help="help message for --new-argument")

    # Create the Script object.  If this is run a second time, it will
    # retrieve the same-named script object.  ('name' in get_script() defaults
    # to "root".  We'll explore running multiple Script objects within the
    # same script in the not-distant future.)
    #
    # When this Script object is created, it will parse all commandline
    # arguments sent to the script.  So it doesn't matter that this script
    # (quickstart.py) didn't have the --new-argument option until one line
    # above; the Script object will parse it and store the new_argument
    # value in its config.
    script = scriptharness.get_script(actions, parser)

    # This will run the script.
    # Essentially, it will go through the list of actions, and if the action
    # is enabled, it will run the associated function.
    script.run()
