Commands
========

.. _Command-and-run:

#################
Command and run()
#################

The ``Command`` object simply takes an external command and runs it, logging stdout and stderr as each message arrives.  The main benefits of using ``Command`` are logging and timeouts.  ``Command`` takes two timeouts: ``output_timeout``, which is how long the command can go without outputting anything before timing out, and ``max_timeout``, which is the total amount of time that can elapse from the start of the command.

(The command is run via ``subprocess.Popen`` and timeouts are monitored via the `multiprocessing` module.)

After the command is run, it runs the ``detect_error_cb`` callback function to determine whether the command was run successfully.

The process of creating and running a ``Command`` is twofold: ``Command.__init__`` and ``Command.run()``.  As a shortcut, there is a ``run()`` function_ that will do both steps for you.

.. _function: scriptharness.commands.html#scriptharness.commands.run


.. _ParsedCommand-and-parse:

#########################
ParsedCommand and parse()
#########################

Ideally, external command output would be for humans only, and the exit code would be meaningful.  In practice, this is not always the case.  Exit codes aren't always helpful or even meaningful, and sometimes critical information is buried in a flood of output.

``ParsedCommand`` takes the output of a command and parses it for matching substrings or regular expressions, using :ref:`ErrorLists` to determine the log level of a line of output.  Because it subclasses ``Command``, ``ParsedCommand`` also has built-in ``output_timeout`` and ``max_timeout`` support.

As with ``Command`` and ``run()``, ``ParsedCommand`` has a shortcut function_, ``parse()``.

.. _function: scriptharness.commands.html#scriptharness.commands.parse


.. _ErrorLists:

##########
ErrorLists
##########

.. _OutputParser:

############
OutputParser
############

.. _OutputBuffer-and-context-lines:

##############################
OutputBuffer and context lines
##############################

.. _Output-get_output-and-get_text_output:

###########################################
Output, get_output(), and get_text_output()
###########################################
