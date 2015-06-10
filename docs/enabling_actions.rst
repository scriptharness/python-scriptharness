.. _Enabling-and-Disabling-Actions:

Enabling and Disabling Actions
==============================

##################
``--action-group``
##################

Some actions are enabled by default and others are disabled by default, based on the script.  However, sometimes the set of default actions are biased towards developers, or a production environment, and are not the ideal set of default actions for another environment.

Action groups allow for defining other sets of defaults.  For example, there could be a `development`, `staging`, or `production` action group for that environment.  These would have to be defined in the script.

Consider the following action groups.

    +---------------+-----------+----------+
    |Action         |development|production|
    +===============+===========+==========+
    |clobber        |no         |yes       |
    +---------------+-----------+----------+
    |pull           |no         |yes       |
    +---------------+-----------+----------+
    |prepare-dev-env|yes        |no        |
    +---------------+-----------+----------+
    |build          |yes        |yes       |
    +---------------+-----------+----------+
    |package        |yes        |yes       |
    +---------------+-----------+----------+
    |upload         |no         |yes       |
    +---------------+-----------+----------+
    |notify         |no         |yes       |
    +---------------+-----------+----------+

Running the script with ``--action-group development`` would enable the ``prepare-dev-env``, ``build``, and ``package`` actions, while ``--action-group production`` would enable all actions except for ``prepare-dev-env``.

There are also the built-in ``all`` and ``none`` groups, that enable all and disable all actions, respectively.

#############
``--actions``
#############

The ``--actions`` option takes a number of action names as arguments.  Those actions will be enabled; all others will be disabled.

``--actions`` and ``--action-group`` are incompatible.  Currently ``--actions`` will override ``--action-group`` and is not an error.

For an example, see :ref:`quickstart-actions` in the quickstart.

#################
``--add-actions``
#################

The ``--add-actions`` option adds a set of actions to the set of already enabled actions.  In the above example, ``--action-group development --add-actions notify`` would enable the ``prepare-dev-env``, ``build``, ``package``, and ``notify`` actions.

##################
``--skip-actions``
##################


The ``--skip-actions`` option removes a set of actions from the set of already enabled actions.  In the above example, ``--action-group development --skip-actions package`` would enable the ``prepare-dev-env`` and ``build`` actions.
