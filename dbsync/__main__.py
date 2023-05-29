#!/usr/bin/env python

"""Entrypoint module for `python -m dbsync`.

Why does this file exist, and why __main__? For more info, read:
- https://www.python.org/dev/peps/pep-0338/
- https://docs.python.org/2/using/cmdline.html#cmdoption-m
- https://docs.python.org/3/using/cmdline.html#cmdoption-m
"""

import sys

from dbsync.main import main

if __name__ == '__main__':
    sys.exit(main())
