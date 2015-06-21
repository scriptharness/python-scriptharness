Configuration
=============

######################
Configuration Overview
######################

The runtime configuration of a Script_ is built from several layers.

* There is a ConfigTemplate_ that can have default values for certain config variables.  These defaults are the basis of the config dict.  (See :ref:`ConfigTemplates` for more details on ConfigTemplate_).

* The script can define an ``initial_config`` dict that is laid on top of the ConfigTemplate_ defaults, so any shared config variables are overwritten by the ``initial_config``.

* The `ConfigTemplate.get_parser()`_ method generates an ``argparse.ArgumentParser``.  This parser parses the commandline options.

* If the commandline options specify any files via the ``--config-file`` option, then those files are read, and the contents are overlaid on top of the config.  The first file specified will be overlaid first, then the second, and so on.

* If the commandline options specify any `optional` config files via the ``--opt-config-file`` option, and `if those files exist`, then each existing file is read and the contents are overlaid on top of the config.

* Finally, any other commandline options are overlaid on top of the config.

After the config is built, the script logs the config, and saves it to a ``localconfig.json`` file.  This file can be inspected or reused for a later script run.


.. _ConfigTemplates:

###############
ConfigTemplates
###############

It's very powerful to be able to build a configuration dict that can hold any key value pairs, but it's non-trivial for users to verify if their config is valid or if there are options that they're not taking advantage of.

To make the config more well-defined, we have the ConfigTemplate_.  The ConfigTemplate_ is comprised of ConfigVariable_ objects, and is based on the ``argparse.ArgumentParser``, but with these qualities:

* The ConfigTemplate_ can keep track of all config variables, including ones that aren't available as commandline options.  The option-less config variables must be specified via default, config file, or ``initial_config``.

* The templates can be added together, via `ConfigTemplate.update()`_.

* Each ConfigVariable_ self-validates, and the ConfigTemplate_ makes sure there are no conflicting commandline options.

* There is a `ConfigTemplate.remove_option()`_ method to remove a commandline option from the corresponding ConfigVariable_.  This may be needed if you want to add two config templates together, but they both have a ``-f`` commandline option specified, for example.

* The `ConfigTemplate.validate_config()`_ method validates the built configuration.  Each ConfigVariable_ can define whether they're required, whether they require or are incompatible with other variables (``required_vars`` and ``incompatible_vars``), and each can define their own ``validate_cb`` callback function.

* There is a `ConfigTemplate.add_argument()`_ for those who want to maintain argparse syntax.

Parent parsers are supported, to group commandline options in the ``--help`` output.  Subparsers are not currently supported, though it may be possible to replace the ConfigTemplate.parser_ with a subparser-enabled parser at the expense of validation and the ability to `ConfigTemplate.update()`_.

When supporting downstream scripts, it's best to keep each ConfigTemplate_ modular.  It's easy to combine them via `ConfigTemplate.update()`_, but less trivial to remove functionality.  The action config template, for instance, can be added to the base config template right before running `parse_args()`_.


############################
LoggingDict and ReadOnlyDict
############################

Each Script_ has a config dict.  By default, this dict is a LoggingDict_, which logs any changes made to the config.

For example, if the config looked like::

    {
        "foo": 1,
        "bar": [2, 3, 4],
        "baz": {
            "z": 5,
            "y": 6,
            "x": 7,
        },
    }

then updating the config might log::

    00:11:22  INFO - root.config['baz'] update: y now 8

Alternatively, someone could change the script class to StrictScript_, which uses ReadOnlyDict_.  Once the ReadOnlyDict_ is locked, it cannot be modified.

By either explicitly logging any changes to the config, and/or preventing any changes to the config, it's easier to debug any unexpected behavior.


.. _ConfigTemplate: ../scriptharness.config/#scriptharness.config.ConfigTemplate
.. _ConfigTemplate.add_argument(): ../scriptharness.config/#scriptharness.config.ConfigTemplate.add_argument
.. _ConfigTemplate.get_parser(): ../scriptharness.config/#scriptharness.config.ConfigTemplate.get_parser
.. _ConfigTemplate.parser: ../scriptharness.config/#scriptharness.config.ConfigTemplate.parser
.. _ConfigTemplate.remove_option(): ../scriptharness.config/#scriptharness.config.ConfigTemplate.remove_option
.. _ConfigTemplate.update(): ../scriptharness.config/#scriptharness.config.ConfigTemplate.update
.. _ConfigTemplate.validate_config(): ../scriptharness.config/#scriptharness.config.ConfigTemplate.validate_config
.. _ConfigVariable: ../scriptharness.config/#scriptharness.config.ConfigVariable
.. _LoggingDict: ../scriptharness.structures/#scriptharness.structures.LoggingDict
.. _ReadOnlyDict: ../scriptharness.structures/#scriptharness.structures.ReadOnlyDict
.. _Script: ../scriptharness.script/#scriptharness.script.Script
.. _StrictScript: ../scriptharness.script/#scriptharness.script.StrictScript
.. _parse_args(): ../scriptharness.config/#scriptharness.config.parse_args
