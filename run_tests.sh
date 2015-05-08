#!/bin/bash

coverage erase
tox && coverage html
rm -f pylint.out
files=$(find tests scriptharness -type f -name \*.py)
for file in $files ; do
    echo $file
    pylint $file 2>&1 | tee -a pylint.out | grep 'Your code has been rated at '
done
