# coding=utf-8
from __future__ import absolute_import, division, print_function

import sys


OPEN_SIGNATURE = 'builtins.open' if sys.version_info[0] >= 3 else '__builtin__.open'
