#!/bin/bash -x
set -e
if [[ ! -f scriptharness.rst ]]; then
    echo "Please cd into the docs/ dir and then run."
    exit
fi
sphinx-apidoc -f -o . ../scriptharness
rm modules.rst
echo "Quickstart" > quickstart.rst
echo "==========" >> quickstart.rst
echo "" >> quickstart.rst
echo "::" >> quickstart.rst
echo "" >> quickstart.rst
cat ../examples/quickstart.py | sed -e 's/^/    /' >> quickstart.rst
echo "" >> quickstart.rst
make html
