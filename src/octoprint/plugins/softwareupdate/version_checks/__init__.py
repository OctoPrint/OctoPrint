# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from . import commandline, git_commit, github_commit, github_release, bitbucket_commit, python_checker

def log_github_ratelimit(logger, r):
	ratelimit = r.headers["X-RateLimit-Limit"] if "X-RateLimit-Limit" in r.headers else "?"
	remaining = r.headers["X-RateLimit-Remaining"] if "X-RateLimit-Remaining" in r.headers else "?"
	reset = r.headers["X-RateLimit-Reset"] if "X-RateLimit-Reset" in r.headers else None
	try:
		import time
		reset = time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(reset)))
	except:
		reset = "?"

	logger.debug("Github rate limit: %s/%s, reset at %s" % (remaining, ratelimit, reset))
