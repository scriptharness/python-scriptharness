#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test scriptharness/script.py
"""
from __future__ import absolute_import, division, print_function, \
                       unicode_literals
import argparse
import json
import os
import scriptharness.actions as actions
from scriptharness.config import get_config_template, update_dirs, \
    DEFAULT_CONFIG_DEFINITION
from scriptharness.exceptions import ScriptHarnessException, ScriptHarnessFatal
import scriptharness.script as script
import shutil
import six
import unittest

if six.PY3:
    BUILTIN = 'builtins'
else:
    BUILTIN = '__builtin__'


def noop(*args):
    """Noop function for testing Actions"""
    if args:
        pass


def get_action(name, function, **kwargs):
    """Helper function to generate Actions"""
    return actions.Action(name, function=function, **kwargs)


def get_grouped_actions():
    """Helper function for testing action_groups
    """
    return [
        get_action("one", noop, action_groups=['a', 'c', ]),
        get_action("two", noop, action_groups=['b', 'c', ]),
        get_action("three", noop, action_groups=['a', 'd', ]),
        get_action("four", noop, action_groups=['b', 'd', ]),
    ]


# Test enable_actions {{{1
class TestEnableActions(unittest.TestCase):
    """Test enable_actions
    """
    def test_action_groups(self):
        """test_script | action_group
        """
        inputs = {
            'a': ["one", "three"],
            'b': ["two", "four"],
            'c': ["one", "two"],
            'd': ["three", "four"],
            'none': [],
            'all': ["one", "two", "three", "four"],
        }
        for key, value in inputs.items():
            print("action_group %s" % key)
            action_list = get_grouped_actions()
            parsed_args = argparse.Namespace()
            setattr(parsed_args, 'scriptharness_volatile_action_group', key)
            script.enable_actions(parsed_args, action_list)
            enabled_actions = [x.name for x in action_list if x.enabled]
            self.assertEqual(enabled_actions, value)

    def test_dashdash_actions(self):
        """test_script | scriptharness_volatile_actions
        """
        parsed_args = argparse.Namespace()
        setattr(parsed_args, 'scriptharness_volatile_actions',
                ['two', 'three'])
        action_list = get_grouped_actions()
        script.enable_actions(parsed_args, action_list)
        enabled_actions = [x.name for x in action_list if x.enabled]
        self.assertEqual(enabled_actions, ['two', 'three'])

    def test_add_actions(self):
        """test_script | add_actions
        """
        parsed_args = argparse.Namespace()
        setattr(parsed_args, 'scriptharness_volatile_action_group', 'none')
        setattr(parsed_args, 'scriptharness_volatile_add_actions',
                ['two', 'four'])
        action_list = get_grouped_actions()
        script.enable_actions(parsed_args, action_list)
        enabled_actions = [x.name for x in action_list if x.enabled]
        self.assertEqual(enabled_actions, ['two', 'four'])

    def test_skip_actions(self):
        """test_script | skip_actions
        """
        parsed_args = argparse.Namespace()
        setattr(parsed_args, 'scriptharness_volatile_skip_actions',
                ['two', 'four'])
        action_list = get_grouped_actions()
        script.enable_actions(parsed_args, action_list)
        enabled_actions = [x.name for x in action_list if x.enabled]
        self.assertEqual(enabled_actions, ['one', 'three'])


# TestScript {{{1
class TestScript(unittest.TestCase):
    """Test Script()
    """
    timings = None

    def setUp(self):
        """Clear statuses before every test"""
        self.timings = []

    def tearDown(self):
        """Clean up artifacts"""
        if os.path.exists("artifacts"):
            shutil.rmtree("artifacts")

    def get_timing_func(self, name):
        """helper function for listeners and actions"""
        def func(context):
            """Test function"""
            assert context  # silence pylint
            self.timings.append(name)
        return func

    def get_action(self, name, enabled=True):
        """Helper function to generate Actions for Script"""
        return actions.Action(name, function=self.get_timing_func(name),
                              enabled=enabled)

    def get_script(self, template=None, cmdln_args=None, initial_config=None):
        """Create a Script for testing
        """
        action_list = [
            self.get_action("one"),
            self.get_action("two"),
            self.get_action("three", enabled=False),
            self.get_action("four"),
        ]
        template = template or get_config_template(all_actions=action_list)
        cmdln_args = cmdln_args or []
        kwargs = {}
        if initial_config is not None:
            kwargs['initial_config'] = initial_config
        return script.Script(action_list, template, cmdln_args=cmdln_args,
                             **kwargs)

    def raise_fatal(self, _):
        """Helper function for post_fatal() testing
        """
        self.timings.append("fatal")
        raise ScriptHarnessFatal("Fatal")

    def test_bad_actions(self):
        """test_script | Script() should throw with a bad action list
        """
        self.assertRaises(
            ScriptHarnessException,
            script.Script, ['one', 'two'], None
        )

    def test_run(self):
        """test_script | Try a basic run()
        """
        scr = self.get_script()
        scr.run()
        self.assertEqual(self.timings, ["one", "two", "four"])

    def test_enable_actions(self):
        """test_script | Enable/disable actions from the command line
        """
        scr = self.get_script(cmdln_args="--actions one three".split())
        scr.run()
        self.assertEqual(self.timings, ["one", "three"])

    def test_non_function_listener(self):
        """test_script | non-function listener
        """
        obj = object()
        scr = self.get_script()
        self.assertRaises(
            ScriptHarnessException, scr.add_listener, obj, "pre_action"
        )

    def test_bad_phase_listener(self):
        """test_script | bad phase listener
        """
        scr = self.get_script()
        self.assertRaises(
            ScriptHarnessException, scr.add_listener,
            self.get_timing_func("pre_action1"), "bad_phase"
        )

    def test_bad_actions_listener(self):
        """test_script | bad actions listener
        """
        scr = self.get_script()
        self.assertRaises(
            ScriptHarnessException, scr.add_listener,
            self.get_timing_func("pre_action1"), "pre_run",
            action_names=["one", "two"]
        )

    def test_pre_action_listener(self):
        """test_script | pre_action listeners
        """
        scr = self.get_script()
        scr.add_listener(
            self.get_timing_func("pre_action1"),
            "pre_action",
        )
        scr.add_listener(
            self.get_timing_func("pre_action2"),
            "pre_action",
            action_names=["two", "three", "five"]
        )
        scr.run()
        self.assertEqual(self.timings, [
            "pre_action1", "one", "pre_action1", "pre_action2", "two",
            "pre_action1", "four"
        ])

    def test_post_action_listener(self):
        """test_script | post_action listeners
        """
        scr = self.get_script()
        scr.add_listener(
            self.get_timing_func("post_action1"),
            "post_action",
        )
        scr.add_listener(
            self.get_timing_func("post_action2"),
            "post_action",
            action_names=["two", "three", "five"]
        )
        scr.run()
        self.assertEqual(self.timings, [
            "one", "post_action1", "two", "post_action1", "post_action2",
            "four", "post_action1"
        ])

    def test_prepost_run_listener(self):
        """test_script | pre_run and post_run listeners
        """
        scr = self.get_script()
        scr.add_listener(self.get_timing_func("pre_run1"), "pre_run")
        scr.add_listener(self.get_timing_func("pre_run2"), "pre_run")
        scr.add_listener(self.get_timing_func("post_run1"), "post_run")
        scr.add_listener(self.get_timing_func("post_run2"), "post_run")
        scr.run()
        self.assertEqual(self.timings, [
            "pre_run1", "pre_run2", "one", "two", "four", "post_run1",
            "post_run2"
        ])

    def test_post_fatal_listener(self):
        """test_script | post_fatal listeners
        """
        scr = self.get_script()
        scr.actions = list(scr.actions)
        scr.actions[1] = actions.Action(
            "two", function=self.raise_fatal, enabled=True)
        scr.add_listener(self.get_timing_func("post_fatal1"), "post_fatal")
        scr.add_listener(self.get_timing_func("post_fatal2"), "post_fatal",
                         action_names=["one", "three", "five"])
        scr.add_listener(self.get_timing_func("post_fatal3"), "post_fatal",
                         action_names=["two", "four"])
        self.assertRaises(ScriptHarnessFatal, scr.run)
        self.assertEqual(self.timings, ["one", "fatal", "post_fatal1",
                                        "post_fatal3"])

    def test_bad_phase_context(self):
        """test_script | bad phase build_context
        """
        scr = self.get_script()
        self.assertRaises(
            ScriptHarnessException, script.build_context,
            scr, "bad_phase"
        )

    def test_dup_action_name(self):
        """test_script | dup action name
        """
        action_list = [
            self.get_action("one"),
            self.get_action("two"),
            self.get_action("one", enabled=False),
            self.get_action("four"),
        ]
        template = get_config_template(all_actions=action_list)
        cmdln_args = []
        self.assertRaises(ScriptHarnessException, script.Script,
                          action_list, template, cmdln_args=cmdln_args)

    def test_dump_config(self):
        """test_script | --dump-config
        """
        initial_config = {}
        for key, value in DEFAULT_CONFIG_DEFINITION.items():
            if value.get("default"):
                initial_config[key] = value['default']
        update_dirs(initial_config)
        initial_config['a'] = 1
        self.assertRaises(SystemExit, self.get_script,
                          cmdln_args=["--dump-config"],
                          initial_config=initial_config)
        with open("artifacts/localconfig.json") as filehandle:
            contents = filehandle.read()
        self.assertEqual(
            contents, json.dumps(initial_config, sort_keys=True, indent=4)
        )


# TestStrictScript {{{1
def change_config1(context):
    """This should raise"""
    context.script.config = {'a': 1}


def change_config2(context):
    """This should raise"""
    context.script.config['a'] = 1


def change_attribute(context):
    """This should raise"""
    context.script.a = 1


class TestStrictScript(unittest.TestCase):
    """Test StrictScript()
    """
    def tearDown(self):
        """Clean up artifacts"""
        if os.path.exists("artifacts"):
            shutil.rmtree("artifacts")

    @staticmethod
    def get_script(template=None, cmdln_args=None, initial_config=None):
        """Create a StrictScript for testing
        """
        action_list = [
            get_action("one", change_config1),
            get_action("two", change_config2),
            get_action("three", change_attribute, enabled=False),
        ]
        template = template or get_config_template(all_actions=action_list)
        cmdln_args = cmdln_args or []
        kwargs = {}
        if initial_config is not None:
            kwargs['initial_config'] = initial_config
        return script.StrictScript(action_list, template, cmdln_args=cmdln_args,
                                   **kwargs)

    def test_pre_run(self):
        """test_script | StrictScript pre-run()
        """
        scr = self.get_script()
        scr.b = 1

        def testfunc():
            """set attribute"""
            scr.config['a'] = 1

        def testfunc2():
            """Set the lock; this shouldn't raise"""
            scr._lock = True  # pylint: disable=protected-access
        self.assertRaises(ScriptHarnessException, testfunc)
        testfunc2()  # lock
        testfunc2()  # relock

    def test_replace_config(self):
        """test_script | StrictScript replace config
        """
        scr = self.get_script()
        self.assertRaises(ScriptHarnessException, scr.run)

    def test_change_config(self):
        """test_script | StrictScript change config
        """
        scr = self.get_script(cmdln_args="--actions two".split())
        self.assertRaises(ScriptHarnessException, scr.run)

    def test_change_attribute(self):
        """test_script | StrictScript change attribute
        """
        scr = self.get_script(cmdln_args="--actions three".split())
        self.assertRaises(ScriptHarnessException, scr.run)
