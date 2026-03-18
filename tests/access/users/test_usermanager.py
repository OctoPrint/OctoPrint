"""
Unit tests for octoprint.access.users.UserManager
"""

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import pytest

import octoprint.access.users


def test_createPasswordHash_nonascii():
    """Test for issue #1891"""

    password = "password with ümläutß"

    # should not throw an exception
    octoprint.access.users.UserManager.create_password_hash(password)


def test_createPasswordHash_is_valid():
    password = "test1234"
    password_hash = octoprint.access.users.UserManager.create_password_hash(password)
    user = octoprint.access.users.User(
        "username",
        password_hash,
        True,
        permissions=[],
        apikey="apikey",
        settings={"key": "value"},
    )

    assert user.check_password(password)


@pytest.mark.parametrize("password", [octoprint.access.users.NOLOGIN_PWHASH, "", None])
def test_nologin_user_check_password_always_false(password):
    user = octoprint.access.users.User(
        "username",
        octoprint.access.users.NOLOGIN_PWHASH,
        True,
        permissions=[],
        apikey="apikey",
        settings={"key": "value"},
    )

    assert not user.check_password(password)
