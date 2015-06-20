Commands
========

.. _Command-and-run:

#################
Command and run()
#################

The ``Command`` object simply takes an external command and runs it, logging stdout and stderr as each message arrives.  The main benefits of using ``Command`` are logging and timeouts.  ``Command`` takes two timeouts: ``output_timeout``, which is how long the command can go without outputting anything before timing out, and ``max_timeout``, which is the total amount of time that can elapse from the start of the command.

(The command is run via ``subprocess.Popen`` and timeouts are monitored via the `multiprocessing` module.)

After the command is run, it runs the ``detect_error_cb`` callback function to determine whether the command was run successfully.

The process of creating and running a ``Command`` is twofold: ``Command.__init__`` and ``Command.run()``.  As a shortcut, there is a run_ function that will do both steps for you.

.. _run: scriptharness.commands.html#scriptharness.commands.run


.. _ParsedCommand-and-parse:

#########################
ParsedCommand and parse()
#########################

Ideally, external command output would be for humans only, and the exit code would be meaningful.  In practice, this is not always the case.  Exit codes aren't always helpful or even meaningful, and sometimes critical information is buried in a flood of output.

``ParsedCommand`` takes the output of a command and parses it for matching substrings or regular expressions, using :ref:`ErrorLists` to determine the log level of a line of output.  Because it subclasses ``Command``, ``ParsedCommand`` also has built-in ``output_timeout`` and ``max_timeout`` support.

As with ``Command`` and ``run()``, ``ParsedCommand`` has a shortcut function, parse_.

.. _parse: scriptharness.commands.html#scriptharness.commands.parse


.. _ErrorLists:

##########
ErrorLists
##########

The ErrorList_ object describes which lines of output are of special interest.  It's a class for better validation.

.. _ErrorList: scriptharness.errorlists.html#scriptharness.errorlists.ErrorList

An example error_list::

    [
        {
            "regex": re.compile("^Error: not actually an error!"),
            level=-1
        }, {
            "regex": re.compile("^Error:"),
            "level": logging.ERROR,
            "pre_context_lines": 5,
            "post_context_lines": 5
        }, {
            "substr": "Obscure error #94382",
            "explanation":
                "This is a fatal program error."
            "exception": ScriptHarnessFatal
        }
    ]

Any output line that matches the first regex will be ignored (discarded), because level is negative.  Because the list is matched in order, the more specific regex is placed before the more general 2nd regex.  If the order were reversed, the more specific regex would never match anything.  The second regex sets the level to logging.ERROR for this line, and 5 lines above and 5 lines below this message.

The final substring has an explanation that will be logged immediately after the matching line, to explain vague error messages.  Because it has a defined `exception`, it will raise.


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
