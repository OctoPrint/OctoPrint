# coding=utf-8
from __future__ import absolute_import

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest
import ddt
import mock

import octoprint.util.pip

import site
import pkg_resources

@ddt.ddt
class PipCallerTest(unittest.TestCase):

	@ddt.data(
		# remove --process-dependency-links for versions < 1.5
		(["install", "--process-dependency-links", "http://example.com/foo.zip"], "1.1", True, False, False,
		 True,
		 ["install", "http://example.com/foo.zip"]),

		# keep --process-dependency-links for versions >= 1.5, --no-use-wheel for ==1.5.0
		(["install", "--process-dependency-links", "http://example.com/foo.zip"], "1.5", True, False, False,
		 True,
		 ["install", "--process-dependency-links", "http://example.com/foo.zip", "--no-use-wheel"]),

		# keep --process-dependency-links for versions >= 1.5
		(["install", "--process-dependency-links", "http://example.com/foo.zip"], "9.0.1", True, False, False,
		 True,
		 ["install", "--process-dependency-links", "http://example.com/foo.zip"]),

		# remove --user in virtual env
		(["install", "--user", "http://example.com/foo.zip"], "9.0.1", True, False, False,
		 True,
		 ["install", "http://example.com/foo.zip"]),

		# ignore use_user in virtual env
		(["install", "http://example.com/foo.zip"], "9.0.1", True, True, False,
		 True,
		 ["install", "http://example.com/foo.zip"]),

		# ignore force_user in virtual env
		(["install", "http://example.com/foo.zip"], "9.0.1", True, False, True,
		 True,
		 ["install", "http://example.com/foo.zip"]),

		# remove --user with disabled user_site
		(["install", "--user", "http://example.com/foo.zip"], "9.0.1", False, False, False,
		 False,
		 ["install", "http://example.com/foo.zip"]),

		# add --user when not in virtual env and use_user is True
		(["install", "http://example.com/foo.zip"], "9.0.1", False, True, False,
		 True,
		 ["install", "http://example.com/foo.zip", "--user"]),

		# ignore use_user with disabled user_site
		(["install", "http://example.com/foo.zip"], "9.0.1", False, True, False,
		 False,
		 ["install", "http://example.com/foo.zip"]),

		# add --user when not in virtual env and force_user is True
		(["install", "http://example.com/foo.zip"], "9.0.1", False, False, True,
		 True,
		 ["install", "http://example.com/foo.zip", "--user"]),

		# ignore force_user with disabled user_site
		(["install", "http://example.com/foo.zip"], "9.0.1", False, False, True,
		 False,
		 ["install", "http://example.com/foo.zip"]),
	)
	@ddt.unpack
	def test_clean_install_command(self, args, version, virtual_env, use_user, force_user, user_site, expected):
		with mock.patch.object(site, "ENABLE_USER_SITE", user_site):
			parsed = pkg_resources.parse_version(version)
			actual = octoprint.util.pip.PipCaller.clean_install_command(args, parsed, virtual_env, use_user, force_user)
		self.assertEquals(expected, actual)
