#!/usr/bin/env python2
# coding=utf-8
from __future__ import absolute_import, division, print_function

import sys
if sys.version_info[0] >= 3:
	raise RuntimeError("Sorry, OctoPrint does not yet support Python 3")

if __name__ == "__main__":
	import octoprint
	octoprint.main()
