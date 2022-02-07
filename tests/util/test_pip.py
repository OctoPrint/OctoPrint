__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os
import site
import unittest
from unittest import mock

import ddt
import pkg_resources

import octoprint.util.pip


@ddt.ddt
class PipCallerTest(unittest.TestCase):
    @ddt.data(
        # remove --process-dependency-links for versions < 1.5
        (
            ["install", "--process-dependency-links", "http://example.com/foo.zip"],
            "1.1",
            True,
            False,
            False,
            True,
            ["install", "http://example.com/foo.zip"],
        ),
        # keep --process-dependency-links for versions >= 1.5, --no-use-wheel for ==1.5.0
        (
            ["install", "--process-dependency-links", "http://example.com/foo.zip"],
            "1.5",
            True,
            False,
            False,
            True,
            [
                "install",
                "--process-dependency-links",
                "http://example.com/foo.zip",
                "--no-use-wheel",
            ],
        ),
        # keep --process-dependency-links for versions >= 1.5
        (
            ["install", "--process-dependency-links", "http://example.com/foo.zip"],
            "9.0.1",
            True,
            False,
            False,
            True,
            ["install", "--process-dependency-links", "http://example.com/foo.zip"],
        ),
        # remove --user in virtual env
        (
            ["install", "--user", "http://example.com/foo.zip"],
            "9.0.1",
            True,
            False,
            False,
            True,
            ["install", "http://example.com/foo.zip"],
        ),
        # ignore use_user in virtual env
        (
            ["install", "http://example.com/foo.zip"],
            "9.0.1",
            True,
            True,
            False,
            True,
            ["install", "http://example.com/foo.zip"],
        ),
        # ignore force_user in virtual env
        (
            ["install", "http://example.com/foo.zip"],
            "9.0.1",
            True,
            False,
            True,
            True,
            ["install", "http://example.com/foo.zip"],
        ),
        # remove --user with disabled user_site
        (
            ["install", "--user", "http://example.com/foo.zip"],
            "9.0.1",
            False,
            False,
            False,
            False,
            ["install", "http://example.com/foo.zip"],
        ),
        # add --user when not in virtual env and use_user is True
        (
            ["install", "http://example.com/foo.zip"],
            "9.0.1",
            False,
            True,
            False,
            True,
            ["install", "http://example.com/foo.zip", "--user"],
        ),
        # ignore use_user with disabled user_site
        (
            ["install", "http://example.com/foo.zip"],
            "9.0.1",
            False,
            True,
            False,
            False,
            ["install", "http://example.com/foo.zip"],
        ),
        # add --user when not in virtual env and force_user is True
        (
            ["install", "http://example.com/foo.zip"],
            "9.0.1",
            False,
            False,
            True,
            True,
            ["install", "http://example.com/foo.zip", "--user"],
        ),
        # ignore force_user with disabled user_site
        (
            ["install", "http://example.com/foo.zip"],
            "9.0.1",
            False,
            False,
            True,
            False,
            ["install", "http://example.com/foo.zip"],
        ),
    )
    @ddt.unpack
    def test_clean_install_command(
        self, args, version, virtual_env, use_user, force_user, user_site, expected
    ):
        with mock.patch.object(site, "ENABLE_USER_SITE", user_site):
            parsed = pkg_resources.parse_version(version)
            actual = octoprint.util.pip.PipCaller.clean_install_command(
                args, parsed, virtual_env, use_user, force_user
            )
        self.assertEqual(expected, actual)

    def test_check_setup(self):
        """Initialization against local pip should work, including testballoon"""
        caller = octoprint.util.pip.PipCaller()
        self.assertIsNotNone(caller._command)
        self.assertIsNotNone(caller._version)


@ddt.ddt
class PipUtilTest(unittest.TestCase):
    def setUp(self):
        self._test_data = os.path.join(
            os.path.dirname(__file__), "_files", "pip_test_data"
        )

    def _get_lines(self, file):
        with open(os.path.join(self._test_data, file), encoding="utf-8") as f:
            lines = list(map(str.rstrip, f.readlines()))
        return lines

    @ddt.data(
        ("already_installed_1.txt", True),
        ("already_installed_2.txt", True),
        ("successful_install_1.txt", False),
    )
    @ddt.unpack
    def test_is_already_installed(self, file, expected):
        lines = self._get_lines(file)
        actual = octoprint.util.pip.is_already_installed(lines)
        self.assertEqual(expected, actual)

    @ddt.data(
        ("egg_problem_1.txt", True),
        ("egg_problem_2.txt", True),
        ("successful_install_1.txt", False),
        ("already_installed_1.txt", False),
    )
    @ddt.unpack
    def test_is_egg_problem(self, file, expected):
        lines = self._get_lines(file)
        actual = octoprint.util.pip.is_egg_problem(lines)
        self.assertEqual(expected, actual)

    @ddt.data(
        ("python_mismatch_1.txt", True),
        ("python_mismatch_2.txt", True),
        ("successful_install_1.txt", False),
        ("already_installed_1.txt", False),
    )
    @ddt.unpack
    def test_is_python_mismatch(self, file, expected):
        lines = self._get_lines(file)
        actual = octoprint.util.pip.is_python_mismatch(lines)
        self.assertEqual(expected, actual)

    @ddt.data(
        (
            "successful_install_1.txt",
            "Successfully installed Better-Grbl-Support-2.1.0-rc1.3",
        ),
        ("already_installed_1.txt", ""),
    )
    @ddt.unpack
    def test_get_result_line(self, file, expected):
        lines = self._get_lines(file)
        actual = octoprint.util.pip.get_result_line(lines)
        self.assertEqual(expected, actual)
