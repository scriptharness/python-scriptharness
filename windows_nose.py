#/usr/bin/env python
"""Wrapper for nose for Windows.

This is primarily here because multiprocessing will die under nosetests on
Windows py27 unless there is an |if __name__ == "__main__":| block for
multiprocessing to multiprocessing.freeze_support().
https://bugs.python.org/issue11240#msg151479
"""
import nose
if __name__ == "__main__":
    nose.main()
