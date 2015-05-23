#!/usr/bin/env python
"""
setup.py for scriptharness
"""

import json
import os
from setuptools import setup, find_packages
import sys

dependencies = [
    'requests',
    'six',
]

path = os.path.join(os.path.dirname(__file__), "version.json")
with open(path) as filehandle:
    version = json.load(filehandle)['version_string']

if sys.version_info < (2, 7) or (sys.version_info[0] == 3 and
                                 sys.version_info[1] < 3):
    print('ERROR: scriptharness requires Python 2.7 or 3.3+! Exiting...')
    sys.exit(1)

setup(
    name='scriptharness',
    version=version,
    description='A generic logging, configuration, and workflow framework for scripts.',
    author='Aki Sasaki',
    author_email='aki@escapewindow.com',
    url='https://github.com/escapewindow/scriptharness',
    license='MPL2',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=dependencies,
    entry_points="""
# -*- Entry points: -*-
""",
)
