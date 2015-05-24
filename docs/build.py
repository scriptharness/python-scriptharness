#!/usr/bin/env python
"""Build scriptharness documentation.  At some point it would be good to
automate all CI/Release tasks for scriptharness; this is a good start.
"""
from __future__ import print_function, division, absolute_import, \
                       unicode_literals
from jinja2 import Template
import os
import re
import shutil
import subprocess
import sys

READTHEDOCS_LINK = """
.. image:: https://readthedocs.org/projects/python-scriptharness/badge/?version=latest
    :target: https://readthedocs.org/projects/python-scriptharness/?badge=latest
    :alt: Documentation Status
"""

def cleanup(*args):
    """Cleanliness."""
    for path in args:
        if os.path.exists(path):
            os.remove(path)

def build_readme_rst():
    with open("README.rst.j2") as filehandle:
        contents = filehandle.read()
    template = Template(contents)
    with open("../README.rst", "w") as filehandle:
        filehandle.write(template.render(readthedocs_link=READTHEDOCS_LINK))
    with open("README.rst", "w") as filehandle:
        filehandle.write(template.render())

def indent_output(command, time_string='00:00:00', required_string="INFO",
                  **kwargs):
    output = ""
    kwargs.setdefault('stderr', subprocess.STDOUT)
    for line in subprocess.check_output(command, **kwargs).splitlines():
        line = re.sub(r"\d\d:\d\d:\d\d", time_string, line.decode())
        output += "    {}{}".format(line, os.linesep)
    assert required_string in output
    return output

def build_quickstart():
    for line in subprocess.check_output(['git', 'branch', '--no-color'],
                                        stderr=subprocess.PIPE).splitlines():
        if line.startswith(b'*'):
            _, branch = line.split()
    branch = branch.decode()
    with open("quickstart.rst.j2") as filehandle:
        contents = filehandle.read()
    template = Template(contents)
    quickstart_contents = ""
    with open("../examples/quickstart.py") as filehandle:
        for line in filehandle.readlines():
            quickstart_contents += "    {}".format(line)
    run_output = indent_output(
        [sys.executable, "../examples/quickstart.py"],
    )
    actions_output = indent_output(
        [sys.executable, "../examples/quickstart.py", "--actions",
         "package", "upload", "notify"],
        time_string="00:00:05",
    )
    list_actions_output = indent_output(
        [sys.executable, "../examples/quickstart.py", "--list-actions"],
        required_string="clobber",
    )
    dump_config_output = indent_output(
        [sys.executable, "../examples/quickstart.py", "--new-argument",
         "foo", "--dump-config"],
        time_string="00:00:14", required_string="Dumping",
    )
    help_output = indent_output(
        [sys.executable, "../examples/quickstart.py", "--help"],
        required_string="usage:"
    )
    with open("quickstart.rst", "w") as filehandle:
        filehandle.write(
            template.render(
                git_branch=branch,
                quickstart_contents=quickstart_contents,
                run_output=run_output,
                actions_output=actions_output,
                list_actions_output=list_actions_output,
                dump_config_output=dump_config_output,
                help_output=help_output,
            )
        )

def main():
    """Main function"""
    os.chdir(os.path.dirname(__file__))
    subprocess.check_call("sphinx-apidoc -f -o . ../scriptharness".split())
    cleanup("modules.rst")
    build_readme_rst()
    build_quickstart()
    subprocess.check_call(["make", "html"])
    subprocess.check_call(["make", "text"])
    subprocess.check_call(["cp", "_build/text/README.txt", "../README"])
    if os.path.exists("artifacts"):
        shutil.rmtree("artifacts")

if __name__ == '__main__':
    main()
