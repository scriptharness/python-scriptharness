# Scriptharness
This is a ground-up rewrite of https://hg.mozilla.org/build/mozharness .

### Primary principles
* configuration
* full logging
* actions

### Secondary goals
* python 2.7 and python 3.x compatible
* rethink mozharness' self.config
* rethink mozharness' logging and mixin dependencies
* rethink mozharness' action behavior

### Running unit tests
```
pip install tox
tox
```
