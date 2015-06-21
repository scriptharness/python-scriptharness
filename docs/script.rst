Scripts and Actions
===================

##################
Scripts and Phases
##################

The Script_ is generally what one would think of as the script itself: it parses the commandline arguments and runs each enabled Action_.  There's the possibility of enabling `running multiple Scripts in parallel`_ at some point.

It's possible to add callbacks, called listeners, to the Script_.  These get triggered in phases.  The list of phases are in ALL_PHASES_; the phases that allow listeners are in LISTENER_PHASES_.

* The ``PRE_RUN`` phase is first, before any actions are run.
* The ``PRE_ACTION`` phase happens before every enabled action, but a listener can be added to a subset of those actions if desired.
* The ``ACTION`` phase is when the enabled Action_ is run.  No listener can be added to the ``ACTION`` phase.
* The ``POST_ACTION`` phase happens after every enabled action, but a listener can be added to a subset of those actions if desired.
* The ``POST_RUN`` phase happens after all enabled actions are run.
* The ``POST_FATAL`` phase happens after a ScriptHarnessFatal_ exception is raised, but before the script exits.


.. _Contexts:

########
Contexts
########

Each listener or Action_ function is passed a Context_.  The Context_ is a ``namedtuple`` with the following properties:

* script (Script_): the Script_ calling the function
* config (dict): by default this is a LoggingDict_
* logger (logging.Logger): the logger for the Script_
* action (Action_): this is only defined during the ``RUN_ACTION``, ``PRE_ACTION``, and ``POST_ACTION`` phases; it is ``None`` in the other phases.
* phase (str): this will be one of ``PRE_RUN``, ``POST_RUN``, ``PRE_ACTION``, ``POST_ACTION``, or ``POST_FATAL``, depending on which phase we're in.

The logger and config (and to a lesser degree, the script and action) objects are all available to each function called for convenience and consistency.


#######
Actions
#######

Each action can be enabled or disabled via commandline options (see :ref:`Enabling-and-Disabling-Actions`).  By default they look for a function with the same name as the action name, with ``-`` replaced by ``_``.  However, any function or method may be specified as the Action.function_.

When run, the Action_ calls the Action.function_ with a Context_.  The function should raise ScriptHarnessError_ on error, or ScriptHarnessFatal_ on fatal error.

Afterwards, the Action.history_ contains the ``return_value``, status_, ``start_time``, and ``end_time``.


.. _ALL_PHASES: ../scriptharness.script/#scriptharness.script.ALL_PHASES
.. _LISTENER_PHASES: ../scriptharness.script/#scriptharness.script.LISTENER_PHASES
.. _Action: ../scriptharness.actions/#scriptharness.actions.Action
.. _Action.function: ../scriptharness.actions/#scriptharness.actions.Action.function
.. _Action.history: ../scriptharness.actions/#scriptharness.actions.Action.history
.. _Context: ../scriptharness.script/#scriptharness.script.Context
.. _LoggingDict: ../scriptharness.structures/#scriptharness.structures.LoggingDict
.. _Script: ../scriptharness.script/#scriptharness.script.Script
.. _Script.run(): ../scriptharness.script/#scriptharness.script.Script.run
.. _ScriptHarnessError: ../scriptharness.exceptions/#scriptharness.exceptions.ScriptHarnessError
.. _ScriptHarnessFatal: ../scriptharness.exceptions/#scriptharness.exceptions.ScriptHarnessFatal
.. _running multiple Scripts in parallel: https://github.com/scriptharness/python-scriptharness/issues/12
.. _status: scriptharness.status/
