"""
Unit tests for octoprint.access.groups.GroupManager
"""

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import contextlib
import os
import tempfile
import unittest

import octoprint.access.groups
from octoprint.access.permissions import OctoPrintPermission

TEST_PERMISSION_1 = OctoPrintPermission("Test 1", "Test permission 1", "p1")
TEST_PERMISSION_2 = OctoPrintPermission("Test 2", "Test permission 2", "p2")


@contextlib.contextmanager
def group_manager_with_temp_file():
    with tempfile.NamedTemporaryFile() as f:
        path = f.name
        try:
            f.close()
            group_manager = octoprint.access.groups.FilebasedGroupManager(path=path)
            yield group_manager
        finally:
            if os.path.exists(path):
                os.remove(path)


class GroupManagerTestCase(unittest.TestCase):
    def test_add_remove_group(self):
        with group_manager_with_temp_file() as group_manager:
            group_manager.add_group(
                "fancy",
                "Fancy Group",
                "My Fancy New Group",
                permissions=[TEST_PERMISSION_1],
                subgroups=[],
                save=False,
            )
            self.assertIsNotNone(group_manager.find_group("fancy"))

            group_manager.remove_group("fancy")
            self.assertIsNone(group_manager.find_group("fancy"))
