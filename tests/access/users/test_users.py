"""
Unit tests for octoprint.access.users
"""

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest

import octoprint.access.users


class SessionUserTestCase(unittest.TestCase):
    def setUp(self):
        self.user = octoprint.access.users.User(
            "username",
            "passwordHash",
            True,
            permissions=[],
            apikey="apikey",
            settings={"key": "value"},
        )

    def test_two_sessions(self):
        session1 = octoprint.access.users.SessionUser(self.user)
        session2 = octoprint.access.users.SessionUser(self.user)

        # session should be different, wrapped object should be identical
        self.assertNotEqual(session1.session, session2.session)
        self.assertEqual(session1.__wrapped__, session2.__wrapped__)
        self.assertEqual(session1.get_name(), session2.get_name())

    def test_settings_change_propagates(self):
        session1 = octoprint.access.users.SessionUser(self.user)
        session2 = octoprint.access.users.SessionUser(self.user)

        # change should propagate from User to SessionUser
        self.user.set_setting("otherkey", "othervalue")
        self.assertDictEqual(
            {"key": "value", "otherkey": "othervalue"}, session1.get_all_settings()
        )

        # change should propagate from SessionUser to SessionUser
        session2.set_setting("otherkey", "yetanothervalue")
        self.assertDictEqual(
            {"key": "value", "otherkey": "yetanothervalue"}, session1.get_all_settings()
        )

    def test_repr(self):
        user = octoprint.access.users.SessionUser(self.user)
        expected = "SessionUser({!r},session={},created={})".format(
            self.user, user.session, user.created
        )
        self.assertEqual(expected, repr(user))

    def test_isinstance(self):
        session = octoprint.access.users.SessionUser(self.user)

        # needs to be detected as User instance
        self.assertTrue(isinstance(session, octoprint.access.users.User))

        # also needs to be detected as SessionUser instance
        self.assertTrue(isinstance(session, octoprint.access.users.SessionUser))

        # but wrapped user should NOT be detected as SessionUser instance of course
        self.assertFalse(isinstance(self.user, octoprint.access.users.SessionUser))
