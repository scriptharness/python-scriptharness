Quickstart
==========

Here's an example script.  The file is also viewable here_.

.. _here: https://github.com/escapewindow/python-scriptharness/blob/0.1.0-dev/examples/quickstart.py

::

    #!/usr/bin/env python
    # -*- coding: utf-8 -*-
    # This file is formatted slightly differently for readability in ReadTheDocs.
    """python-scriptharness quickstart example.
    
    This file can be found in the examples/ directory of the source at
    https://github.com/escapewindow/python-scriptharness
    """
    from __future__ import absolute_import, division, print_function, \
                           unicode_literals
    import scriptharness
    
    
    """First, define functions for all actions.  Each action MUST have a function
    defined.
    
    Each action function should be idempotent, and able to run standalone.
    In this example, 'package' may require that the steps in 'build' ran at
    some point before 'package' is run, but we can't assume that happened in
    the same script run.  It could have happened yesterday, or three weeks ago,
    and 'package' should still be able to run.  If you need to save state
    between actions, consider saving state to disk.
    """
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
        """Enable logging to screen + log.txt.  Not required, but without it
        the script will run silently.
        """
        scriptharness.prepare_simple_logging("log.txt")
    
        """Define actions.  All six actions are available to run, but if the
        script is run without any action commandline options, only the
        enabled actions will run.
    
        If default_actions is specified, it MUST be a subset of all_actions
        (the first list), and any actions in default_actions will be enabled
        by default (the others will be disabled).  If default_actions isn't
        specified, all the actions are enabled.
    
        Each action MUST have a function defined (see above).
        """
        actions = scriptharness.get_actions_from_list(
            ["clobber", "pull", "build", "package", "upload", "notify"],
            default_actions=["pull", "build", "package"]
        )
    
        """Create a commandline argument parser, with default scriptharness
        argument options pre-populated.
        """
        parser = scriptharness.get_parser(all_actions=actions)
    
        """Add new commandline argument(s)
        """
        parser.add_argument("--new-argument", action='store',
                            help="help message for --new-argument")
    
        """Create the Script object.  If this is run a second time, it will
        retrieve the same-named script object.  ('name' in get_script() defaults
        to "root".  We'll explore running multiple Script objects within the
        same script in the not-distant future.)
    
        When this Script object is created, it will parse all commandline
        arguments sent to the script.  So it doesn't matter that this script
        (quickstart.py) didn't have the --new-argument option until one line
        above; the Script object will parse it and store the new_argument
        value in its config.
        """
        script = scriptharness.get_script(actions=actions, parser=parser)
    
        """This will run the script.
        Essentially, it will go through the list of actions, and if the action
        is enabled, it will run the associated function.
        """
        script.run()

If you run this without any arguments, you might get output like this::

    $ ./quickstart.py
    01:23:56     INFO - Starting at 2015-05-22 01:23 PDT.
    01:23:56     INFO - {'new_argument': None}
    01:23:56     INFO - Skipping action clobber
    01:23:56     INFO - Running action pull
    01:23:56     INFO - Action pull: finished successfully
    01:23:56     INFO - Running action build
    01:23:56     INFO - Action build: finished successfully
    01:23:56     INFO - Running action package
    01:23:56     INFO - Action package: finished successfully
    01:23:56     INFO - Skipping action upload
    01:23:56     INFO - Skipping action notify
    01:23:56     INFO - Done.

First, it announced it's starting the script.  Next, it outputs the running
config.  Then it logs each action as it runs enabled actions and skips disabled
actions.  Finally, it announces 'Done.'.

You can change which actions are run via the --actions option::

    $ ./quickstart.py --actions package upload notify
    01:26:12     INFO - Starting at 2015-05-22 01:26 PDT.
    01:26:12     INFO - {'new_argument': None}
    01:26:12     INFO - Skipping action clobber
    01:26:12     INFO - Skipping action pull
    01:26:12     INFO - Skipping action build
    01:26:12     INFO - Running action package
    01:26:12     INFO - Action package: finished successfully
    01:26:12     INFO - Running action upload
    01:26:12     INFO - Action upload: finished successfully
    01:26:12     INFO - Running action notify
    01:26:12     INFO - Action notify: finished successfully
    01:26:12     INFO - Done.

If you want to list which actions are available, and which are enabled by
default, use the --list-actions option:

    $ ./quickstart.py --list-actions
      clobber
    * pull
    * build
    * package
      upload
      notify

You can change the new_argument value in the config via the
--new-argument option that the script added.  Also, if you just want to
see what the config is without running anything, you can use the
--dump-config option::

    $ ./quickstart.py --new-argument foo --dump-config
    01:27:21     INFO - Dumping config:
    01:27:21     INFO - {'new_argument': 'foo'}

You can always use the --help option::

    $ ./quickstart.py --help
    usage: quickstart.py [-h] [--list-actions] [--actions ACTION [ACTION ...]]
                         [--config-file CONFIG_FILE]
                         [--opt-config-file CONFIG_FILE] [--dump-config]
                         [--new-argument NEW_ARGUMENT]
    
    optional arguments:
      -h, --help            show this help message and exit
      --list-actions        List all actions (default prepended with '*') and
                            exit.
      --actions ACTION [ACTION ...]
                            Specify the actions to run.
      --config-file CONFIG_FILE, --cfg CONFIG_FILE, -c CONFIG_FILE
                            Specify required config files/urls
      --opt-config-file CONFIG_FILE, --opt-cfg CONFIG_FILE
                            Specify optional config files/urls
      --dump-config         Log the built configuration and exit.
      --new-argument NEW_ARGUMENT
                            help message for --new-argument

