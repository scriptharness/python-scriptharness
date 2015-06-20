Configuration
=============

######################
Configuration Overview
######################

The runtime configuration of a Script is built from several layers.

* There is a ``ConfigTemplate`` that can have default values for certain config variables.  These defaults are the basis of the config dict.  (See :ref:`Config-Templates` for more details on ``ConfigTemplate``s).

* The script can define an ``initial_config`` dict that is laid on top of the ``ConfigTemplate`` defaults, so any shared config variables are overwritten by the ``initial_config``.

* The ``ConfigTemplate`` has a ``get_parser()`` method that generates an ``argparse.ArgumentParser``.  This parser parses the commandline options.

* If the commandline options specify any files via the ``--config-file`` option, then those files are read, and the contents are overlaid on top of the config.  The first file specified will be overlaid first, then the second, and so on.

* If the commandline options specify any `optional` config files via the ``--opt-config-file`` option, and `if those files exist`, then each existing file is read and the contents are overlaid on top of the config.

* Finally, any other commandline options are overlaid on top of the config.

After the config is built, the script logs the config, and saves it to a ``localconfig.json`` file.  This file can be inspected or reused for a later script run.


.. _Config-Templates:

###############
ConfigTemplates
###############

It's very powerful to be able to build a configuration dict that can hold any key value pairs, but it's non-trivial for users to verify if their config is valid or if there are options that they're not taking advantage of.

To make the config more well-defined, we have the ``ConfigTemplate``.  The ``ConfigTemplate`` is comprised of ``ConfigVariables``, and is based on the ``argparse.ArgumentParser``, but with these qualities:

* The ``ConfigTemplate`` can keep track of all config variables, including ones that aren't available as commandline options.  The option-less config variables must be specified via default, config file, or ``initial_config``.

* The templates can be added together, via ``ConfigTemplate.update()``.

* Each ``ConfigVariable`` self-validates, and the ``ConfigTemplate`` makes sure there are no conflicting commandline options.

* There is a ``ConfigTemplate.remove_option()`` method to remove a commandline option from the corresponding ``ConfigVariable``.  This may be needed if you want to add two config templates together, but they both have a ``-f`` commandline option specified, for example.

* validation
* best practice modular


###########
LoggingDict
###########
