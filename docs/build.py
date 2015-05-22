#!/usr/bin/env python

from __future__ import print_function, division, absolute_import, \
                       unicode_literals
from jinja2 import Template
import os
import subprocess

def nuke(*args):
    for path in args:
        if os.path.exists(path):
            os.remove(path)

def main():
    os.chdir(os.path.dirname(__file__))
    for line in subprocess.check_output(['git', 'branch', '--no-color'],
                                        stderr=subprocess.PIPE).splitlines():
        if line.startswith(b'*'):
            _, branch = line.split()
    branch = branch.decode()
    print(branch)
    subprocess.check_call("sphinx-apidoc -f -o . ../scriptharness".split())
    with open("quickstart.rst.j2") as filehandle:
        contents = filehandle.read()
    nuke("modules.rst")
    template = Template(contents)
    contents = ""
    with open("../examples/quickstart.py") as filehandle:
        for line in filehandle.readline():
            contents += "    {}".format(line)
    template.render(GIT_BRANCH=branch, QUICKSTART_CONTENTS_INDENTED=contents)
    subprocess.check_call(["make", "html"])

if __name__ == '__main__':
    main()
