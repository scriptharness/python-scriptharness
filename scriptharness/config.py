#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The goal of `flexible configuration` is to make each script useful in a
variety of contexts and environments.

Attributes:
  LOGGER_NAME (str): logging.getLogger name

  OPTION_REGEX (re.compile): regular expression to validate a commandline
    option

  VALID_ARGPARSE_ACTIONS (tuple): for validating the ConfigVariable action

  STRINGS (dict): strings for ConfigVariable

  DEFAULT_CONFIG_DEFINITION (dict): Config definition to create the default
    ConfigTemplate for all scriptharness scripts.
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import argparse
import json
import logging
import os
import re
import requests
from requests.exceptions import RequestException, Timeout
from scriptharness.actions import Action
from scriptharness.exceptions import ScriptHarnessException, \
    ScriptHarnessTimeout
from scriptharness.structures import iterate_pairs
from scriptharness.unicode import to_unicode
import six
import six.moves.urllib as urllib
import sys
import time


LOGGER_NAME = "scriptharness.config"
OPTION_REGEX = re.compile(r'^-{1,2}[a-zA-Z0-9]\S*$')
VALID_ARGPARSE_ACTIONS = (None, 'store', 'store_const', 'store_true',
                          'store_false', 'append', 'append_const', 'count',
                          'help', 'version', 'parsers')
STRINGS = {
    "config_variable": {
        "missing_required": "%(name)s is required but not set!",
        "required_vars": "%(name)s is set without required var %(var)s!",
        "incompatible_vars": "Incompatible vars %(name)s and %(var)s are set!",
    },
}
DEFAULT_CONFIG_DEFINITION = {
    "scriptharness_base_dir": {
        "default": six.text_type(os.getcwd()),
        "help": "The base directory to run the script in.",
    },
    "scriptharness_work_dir": {
        "default": "%(scriptharness_base_dir)s{}build".format(os.sep),
        "help": "The directory to perform the work in."
    },
    "scriptharness_artifact_dir": {
        "default": "%(scriptharness_base_dir)s{}artifacts".format(os.sep),
        "help": "The directory to copy artifacts to."
    },
    "config_files": {
        "options": ['--config-file', '--cfg', '-c'],
        "action": 'append',
        "metavar": "CONFIG_FILE",
        "parent_parser": "config",
        "help": "Specify required config files/urls",
    },
    "opt_config_files": {
        "options": ['--opt-config-file', '--opt-cfg'],
        "action": 'append',
        "metavar": "CONFIG_FILE",
        "parent_parser": "config",
        "help": "Specify optional config files/urls",
    },
    "scriptharness_volatile_dump_config": {
        "options": ['--dump-config'],
        "action": 'store_true',
        "parent_parser": "config",
        "help": "Log the built configuration and exit.",
    },
}

# parse_config_file() {{{1
def parse_config_file(path):
    """Read a config file and return a dictionary.
    For now, only support json.

    Args:
      path (str): path or url to config file.

    Returns:
      config (dict): the parsed json dict.

    Raises:
      scriptharness.exceptions.ScriptHarnessException: if the path is
        unreadable or not valid json.
    """
    if is_url(path):
        path = download_url(path)
    # py3 may throw FileNotFoundError or IOError; both inherit OSError.
    # py2 throws IOError, which doesn't inherit OSError.
    if six.PY3:
        exception = OSError
    else:
        exception = IOError
    try:
        with open(path) as filehandle:
            config = dict(json.load(filehandle))
    except exception as exc_info:
        raise ScriptHarnessException(
            "Can't open path %s!" % path, exc_info
        )
    except ValueError as exc_info:
        raise ScriptHarnessException(
            "Can't parse json in %s!" % path, exc_info
        )
    return config


def get_filename_from_url(url):
    """Determine the filename of a file from its url.

    Args:
      url (str): the url to parse

    Returns:
      name (str): the name of the file
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.path != '':
        return parsed.path.rstrip('/').rsplit('/', 1)[-1]
    else:
        return parsed.netloc


def is_url(resource):
    """Is it a url?

    .. note:: This function will return False for `file://` strings

    Args:
      resource (str): possible url

    Returns:
      bool: True if it's a url, False otherwise.
    """
    parsed = urllib.parse.urlparse(resource)
    if parsed.scheme and parsed.netloc:
        return True
    return False


def download_url(url, path=None, timeout=None):
    """Download a url to a path.

    Args:
      url (str): the url to download

      path (Optional[str]): the path to write the contents to.

      timeout (Optional[float]): how long to wait before timing out.

    Returns:
      path (str): the path to the downloaded file.

    Raises:
      scriptharness.exceptions.ScriptHarnessException: if there are download
        issues, or if we can't write to path.
    """
    if path is None:
        path = get_filename_from_url(url)
    if timeout is None:
        timeout = 10
    try:
        with open(path, 'wb') as filehandle:
            try:
                start_time = time.time()
                session = requests.Session()
                session.mount(url, requests.adapters.HTTPAdapter(max_retries=5))
                response = session.get(url, timeout=timeout, stream=True)
                with open(path, 'wb') as filehandle:
                    for chunk in response.iter_content(  # pragma: no branch
                            chunk_size=1024):
                        if chunk:  # pragma: no branch
                            filehandle.write(chunk)
                            filehandle.flush()
                return path
            except RequestException as exc_info:
                if isinstance(exc_info, Timeout) or \
                        time.time() >= start_time + timeout:
                    raise ScriptHarnessTimeout(
                        "Timeout downloading from url %s" % url, exc_info
                    )
                raise ScriptHarnessException(
                    "Error downloading from url %s" % url, exc_info
                )
    except IOError as exc_info:
        raise ScriptHarnessException(
            "Error writing downloaded contents to path %s" % path, exc_info
        )


# config template functions {{{1
def get_list_actions_string(action_name, enabled, groups=None):
    """Build a string for --list-actions output.

    Args:
      action_name (str):  name of the action

      enabled (bool): whether the action is enabled by default

      groups (Optional[list]): a list of action_group names that the action
        belongs to.  Defaults to None.

    Returns:
      string (str): a line of --list-actions output.
    """
    string = "  "
    if enabled:
        string = "* "
    groups = set(groups or [])
    groups.update(set(['all']))
    string += '%s %s' % (action_name, list(groups))
    return string

def action_config_template(all_actions):
    """Create an action option parser from the action list.

    Actions to run are specified as the argparse.REMAINDER options.

    Args:
      all_actions (iterable): this is either all Action objects for the
        script, or a data structure of pairs of action_name:enabled to pass
        to iterate_pairs().

    Returns:
      ConfigTemplate: with action options
    """
    message = []
    action_names = []
    action_groups = set(['all', 'none'])
    for action in all_actions:
        if isinstance(action, Action):
            action_names.append(action.name)
            action_groups.update(set(action.action_groups))
            message.append(
                get_list_actions_string(action.name, action.enabled,
                                        action.action_groups)
            )
        else:
            message = []
            action_names = []
            for name, enabled in iterate_pairs(all_actions):
                message.append(get_list_actions_string(name, enabled))
                action_names.append(name)
            break
    def list_actions():
        """Helper function to list all actions (enabled shown with a '*')"""
        print(os.linesep.join(message))
        sys.exit(0)
    template = ConfigTemplate({
        "scriptharness_volatile_list_actions": {
            "options": ["--list-actions"],
            "action": 'store_const',
            "const": list_actions,
            "parent_parser": "actions",
            "help": "List all actions (default prepended with '*') and exit.",
        },
        "scriptharness_volatile_actions": {
            "options": ["--actions"],
            "nargs": '+',
            "choices": action_names,
            "metavar": "ACTION",
            "parent_parser": "actions",
            "help": "Specify the actions to run.",
        },
        "scriptharness_volatile_skip_actions": {
            "options": ["--skip-actions"],
            "nargs": '+',
            "choices": action_names,
            "metavar": "ACTION",
            "parent_parser": "actions",
            "help": "Specify the actions to skip.",
        },
        "scriptharness_volatile_add_actions": {
            "options": ["--add-actions"],
            "nargs": '+',
            "choices": action_names,
            "metavar": "ACTION",
            "parent_parser": "actions",
            "help": "Specify the actions to add to the default set.",
        },
        "scriptharness_volatile_action_group": {
            "options": ["--action-group"],
            "choices": action_groups,
            "parent_parser": "actions",
            "help": "Specify the action group to use.",
        },
    })
    return template


def get_config_template(template=None, all_actions=None, definition=None):
    """Create a script ConfigTemplate.

    If template is not defined, it will take the definition (defaults to
    DEFAULT_CONFIG_DEFINITION) and create a new ConfigTemplate.  Otherwise
    it uses template.

    If all_actions is defined, it will add an action ConfigTemplate to the
    template.

    Args:
      template (Optional[ConfigTemplate]): the ConfigTemplate to optionally
        append the action_template to.  Defaults to None.

      all_actions (Optional[list]): list of actions to generate an action
        ConfigTemplate.  Defaults to None.

      definition (Optional[dict]): config definition to prepopulate the
        ConfigTemplate with.  Defaults to DEFAULT_CONFIG_DEFINITION.

    Returns:
      ConfigTemplate
    """
    if template is None:
        if definition is None:
            definition = DEFAULT_CONFIG_DEFINITION
        template = ConfigTemplate(definition)
    if all_actions:
        action_template = action_config_template(all_actions)
        template.update(action_template)
    return template


def parse_args(template, cmdln_args=None, **kwargs):
    """Parse the commandline args.

    Args:
      template (ConfigTemplate): specify the config template to use

      cmdln_args (Optional[list]): override the commandline args with these

      **kwargs: sent to ConfigTemplate.get_parser() if parser is a
        ConfigTemplate

    Returns:
      tuple(ArgumentParser, parsed_args)
    """
    args = []
    parser = template.get_parser(**kwargs)
    if cmdln_args is not None:  # pragma: no branch
        args.append(cmdln_args)
    parsed_args = parser.parse_args(*args)
    if hasattr(parsed_args, 'scriptharness_volatile_list_actions') and \
            callable(parsed_args.scriptharness_volatile_list_actions):
        parsed_args.scriptharness_volatile_list_actions()
    return parsed_args


# update_dirs {{{1
def update_dirs(config, max_depth=2):
    """Directory paths for the script are defined in config.
    Absolute paths help avoid chdir issues.

    `scriptharness_base_dir` (or any other directory path, or any config value)
    can be overridden during build_config().  Defining the directory paths as
    formattable strings is configurable but not overly complex.

    Any key in `config` named scriptharness_SOMETHING_dir will be % formatted
    with the other dirs as the replacement dictionary.

    Args:
      config (dict): the config to parse for scriptharness_SOMETHING_dir keys.
    """
    repl_dict = {}
    for key, value in config.items():
        if key.startswith("scriptharness_") and key.endswith("_dir"):
            repl_dict[key] = value
    # Make a couple expansion passes, in case a dir is based on another dir
    # with a % formatting string.
    for _ in range(max_depth):
        for key in repl_dict:
            repl_dict[key] = repl_dict[key] % repl_dict
    config.update(repl_dict)

# build_config {{{1
def build_config(template, parsed_args, initial_config=None):
    """Build a configuration dict from the parser and initial config.

    The configuration is built in this order:

      * template defaults
      * initial_config
      * parsed_args.config_files, in order
      * parsed_args.opt_config_files, in order, if they exist
      * non-default parser args (cmdln_args)

    So the commandline args can override everything else, as long as there are
    options to do so. (Commandline args will need to be a subset of the parser
    args).  The final configuration file can override everything but the
    commandline args, and its config isn't restricted as a subset of the
    parser options.

    Args:
      parser (ArgumentParser): the parser used to parse_args()
      parsed_args (argparse Namespace): the results of parse_args()
      initial_config (Optional[dict]): initial configuration to set before
        commandline args
    """
    config = template.defaults()
    parser = template.get_parser()
    cmdln_config = {}
    resources = {}
    initial_config = initial_config or {}
    logger = logging.getLogger(LOGGER_NAME)
    for key, value in parsed_args.__dict__.items():
        if key.startswith('scriptharness_') and '_volatile_' in key:
            continue
        if key in ('config_files', 'opt_config_files'):
            resources.setdefault(key, value or [])
            continue
        if parser.get_default(key) == value:
            config[to_unicode(key)] = to_unicode(value)
        else:
            cmdln_config[key] = value
    config.update(initial_config)
    for resource in resources.get('config_files', []):
        config.update(parse_config_file(resource))
    for resource in resources.get('opt_config_files', []):
        try:
            config.update(parse_config_file(resource))
        except ScriptHarnessException:
            logger.info("Can't read optional config file %s; skipping.",
                        resource)
    if cmdln_config:
        config.update(cmdln_config)
    update_dirs(config)
    template.validate_config(config)
    return config


# validate_config_definition {{{1
def validate_config_definition(name, definition):
    """Validate the ConfigVariable definition's well-formedness.

    Args:
      name (str): the name of the variable
      definition (dict): the definition to validate

    Raises:
      ScriptHarnessException: if there are any error messages
    """
    messages = []
    if definition.get('options'):
        for opt in definition['options']:
            if OPTION_REGEX.search(opt) is None:
                messages.append("%s option %s is not valid!" % (name, opt))
    if 'help' not in definition:
        messages.append("%s must define 'help'" % name)
    if 'action' in definition and \
            definition['action'] not in VALID_ARGPARSE_ACTIONS:
        messages.append("%s action %s not a valid action!" %
                        (name, definition['action']))
    if 'type' in definition and not isinstance(definition['type'], type):
        messages.append('%s type %s is not a python type!' %
                        (name, definition['type']))
    if 'validate_cb' in definition and not callable(definition['validate_cb']):
        messages.append('%s validate_cb is not callable!' % name)
    for key in ('incompatible_vars', 'required_vars', 'optional_vars'):
        for var in definition.get(key, []):
            if not isinstance(var, six.text_type):
                messages.append(
                    "%s %s %s is not %s!" % (name, key, var, six.text_type)
                )
    # not sure how to validate 'required', 'choices', 'default'
    if messages:
        raise ScriptHarnessException('\n'.join(messages))


# ConfigVariable {{{1
class ConfigVariable(object):
    """This object defines what a single config variable looks like.

    The variable is overridable from the commandline when when
    self.definition['options'] is defined.  Otherwise the variable is only
    script-level and config-file-level settable.

    The definition will look like this::

      {
        # argparse-specific, for argparse.ArgumentParser.add_argument
        # if 'options' is not set, these will be ignored.
        'options': ['--foo', '-f'],
        'action': 'store',  # (None, 'store', 'store_const', 'store_true',
                            #  'store_false', 'append', 'append_const',
                            #  'count', 'help', 'version', 'parsers')
                            # defaults to 'store'

        # argparse-related
        # if 'options' is set, these will be used with
        # argparse.ArgumentParser.add_argument; otherwise they're here for
        # the non-commandline-config.
        'help': 'help string',  # not sure whether this should be required
                                # or highly recommended.
        'required': True,
        'default': 'bar',
        'parent_parser': 'parent',  # this is for argparse --help sorting
        'type': str,  # a python type
        'choices': [],  # enum / list of choices

        # Not related to argparse
        'validate_cb': None,  # optional, function to validate the
                              # config.  This function should take the args
                              # (name, parsed_args) and return a list of
                              # error message strings.
        'incompatible_vars': [],  # names of incompatible vars if this var
                                  # is set
        'required_vars': [],  # names of other vars that are required to be
                              # set if this var is set
        'optional_vars': [],  # names of other vars that are optionally
                              # used in relation to this var.  This is purely
                              # informational.
      }


    Attributes:
      name (str): the name of the variable.  This corresponds to the
        argparse `dest`, or the config dict key.

      definition (dict): the config definition for this variable.  See
        above for the format.
    """
    def __init__(self, name, definition):
        if not isinstance(name, six.text_type):
            raise ScriptHarnessException(
                "ConfigVariable name is not %s!" % six.text_type,
                name
            )
        self.name = name
        validate_config_definition(name, definition)
        self.definition = definition

    def add_argument(self, parser):
        """If self.definition['options'] is set, add the appropriate argument
        to the parser.

        Args:
          parser (argparse.ArgumentParser): the parser to add the argument to.

        Returns:
          argparse.Action: on success.

        Raises:
          ScriptHarnessException: on argparse.ArgumentParser.add_argument
            error.
        """
        if not self.definition.get('options'):
            return

        args = self.definition['options']
        kwargs = {
            'dest': self.name,
            'action': self.definition.get('action', None),
        }
        for key in self.definition.keys():
            if key not in ('dest', 'action', 'options', 'validate_cb',
                           'incompatible_vars', 'required_vars',
                           'optional_vars', 'parent_parser'):
                kwargs[key] = self.definition[key]
        try:
            return parser.add_argument(*args, **kwargs)
        except ValueError as exc_info:
            raise ScriptHarnessException(
                "Error adding %s argument to parser!" % self.name,
                exc_info
            )

    def validate_config(self, config):
        """Once we build the config, we can validate it by sending the built
        config to each of these methods.

        Args:
          config (dict): the config built from build_config()

        Returns:
          messages (list of strings): any error messages, if applicable.
        """
        # Only validate if this option is set
        if config.get(self.name) is None:
            if self.definition.get('required'):
                return [STRINGS['config_variable']['missing_required'] %
                        {'name': self.name}]
            return []
        messages = []
        # incompatible_vars cannot be set if this var is set
        for var in self.definition.get('incompatible_vars', []):
            if config.get(var) is not None:
                messages.append(
                    STRINGS['config_variable']['incompatible_vars'] %
                    {'name': self.name, 'var': var}
                )
        # required_vars must be set if this var is set
        for var in self.definition.get('required_vars', []):
            if config.get(var) is None:
                messages.append(
                    STRINGS['config_variable']['required_vars'] %
                    {'name': self.name, 'var': var}
                )
        # run the validate_cb function if defined
        if self.definition.get('validate_cb'):
            value = self.definition['validate_cb'](self.name, config)
            if isinstance(value, list):
                messages.extend(value)
        return messages


# ConfigTemplate {{{1
class ConfigTemplate(object):
    """Short for Config Template Definition, or CTD.
    Because scriptharness scripts can take any arbitrary configuration
    variables or commandline options from various locations, it's difficult
    to tell what requires what, what's optional, and what's extraneous.

    By allowing the developer to create a config template definition, we
    can check for config well-formedness.

    Attributes:
      config_variables (dict): a name to ConfigVariable dictionary

      parser (argparse.ArgumentParser): this is the commandline parser.
    """
    def __init__(self, config_dict):
        self.config_variables = {}
        self.parser = None
        self.update(config_dict)

    def items(self):
        """Have ConfigTemplate act more like a dict.

        Returns:
          self.config_variables.items()
        """
        return self.config_variables.items()

    def defaults(self):
        """Get the defaults for all the variables, even the non-commandline
        ones.

        Returns:
          dict: name to default value.
        """
        defaults = {}
        for name, variable in self.config_variables.items():
            if variable.definition.get("default"):
                defaults[name] = variable.definition['default']
        return defaults

    @property
    def all_options(self):
        """Build and return set of all commandline options

        Returns:
          options (set): all commandline options
        """
        options = set()
        for _, config_variable in self.config_variables.items():
            options.update(set(config_variable.definition.get('options', [])))
        return options

    def _add_variable(self, config_variable):
        """Add a ConfigVariable to self.config_variables after checking for
        conflicts.

        Args:
          config_variable (ConfigVariable): the ConfigVariable to add
        """
        if config_variable.name in self.config_variables:
            raise ScriptHarnessException(
                "%s already in config_template!" % config_variable.name
            )
        options = set(config_variable.definition.get('options', []))
        intersection = options.intersection(self.all_options)
        if intersection:
            raise ScriptHarnessException(
                "%s has conflicting options!" % config_variable.name,
                intersection
            )
        self.config_variables[config_variable.name] = config_variable

    def add_variable(self, definition, name=None):
        """Add a variable to the config template definition.

        See scriptharness.config.ConfigVariable for the definition format.

        Args:
          name (str): the variable name.  This maps to argparse's `dest`

          definition (dict or ConfigVariable): a ConfigVariable or the
            definition of the config variable.
        """
        if isinstance(definition, ConfigVariable):
            config_variable = definition
        else:
            config_variable = ConfigVariable(name, definition)
        self._add_variable(config_variable)

    def remove_option(self, option):
        """Remove a commandline option from the ConfigTemplate.

        Because we can add templates together, we may sometimes
        encounter conflicting commandline options.  This method allows us
        to remove those options from one or both templates.

        Args:
          option (str): The commandline option to remove.
        """
        for name, variable in self.config_variables.items():
            if option in variable.definition['options']:
                variable.definition['options'].remove(option)
                logger = logging.getLogger(LOGGER_NAME)
                logger.info("Removed option %s from %s.", option, name)
                break

    def add_argument(self, *args, **kwargs):
        """Helper method to make ConfigTemplate usage more similar to
        ArgumentParser.
        """
        if not args:
            raise ScriptHarnessException(
                "ConfigTemplate.add_argument needs *args!"
            )
        kwargs['options'] = args
        if 'dest' in kwargs:
            name = kwargs['dest']
        else:
            name = args[0].lstrip('-').replace('-', '_')
        self.add_variable(kwargs, name=name)

    def update(self, config_dict):
        """Update self with a new config_dict

        Args:
          config_dict (dict): A dict of ConfigVariables or dicts.

          strict (Optional[bool]): When True, throw an exception when there's
            a conflicting variable.
        """
        exceptions = []
        for name, definition in config_dict.items():
            try:
                self.add_variable(definition, name=name)
            except ScriptHarnessException as exc_info:
                exceptions.append(exc_info)
        if exceptions:
            raise ScriptHarnessException(
                "Errors while trying to update ConfigTemplate!",
                exceptions
            )

    def get_parser(self, **kwargs):
        """Create and populate the argparse.ArgumentParser for commandline
        parsing.

        Args:
          **kwargs: keyword arguments to send to argparse.ArgumentParser.

        Returns:
          argparse.ArgumentParser: the commandline parser for this Config
            Template
        """
        if self.parser is None:
            # Create parent parsers for neater --help output.
            parents = {}
            for variable in [x for x in self.config_variables.values() if
                             x.definition.get('parent_parser')]:
                parent = variable.definition['parent_parser']
                if parents.get(parent) is None:
                    parents[parent] = argparse.ArgumentParser(add_help=False)
                variable.add_argument(parents[parent])
            if parents:
                kwargs['parents'] = parents.values()
            # Create parser
            self.parser = argparse.ArgumentParser(**kwargs)
            for variable in [x for x in self.config_variables.values() if not
                             x.definition.get('parent_parser')]:
                variable.add_argument(self.parser)
        return self.parser

    def validate_config(self, config):
        """Validate a config dict against each
        ConfigVariable.validate_config check.

        Args:
          config (dict): the config dictionary to validate.

        Raises:
          scriptharness.exceptions.ScriptHarnessException: on error.
        """
        messages = []
        for variable in self.config_variables.values():
            message = variable.validate_config(config)
            messages += message
        if messages:
            raise ScriptHarnessException("Invalid config!", messages)
