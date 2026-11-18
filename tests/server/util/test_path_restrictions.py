import copy

import pytest

from octoprint.access.permissions import Permissions
from octoprint.access.users import AnonymousUser, User
from octoprint.server.util.flask import apply_path_restrictions


@pytest.fixture
def data():
    return {"aaa": 1, "bbb": {"bbb1": 1, "bbb2": 2}, "ccc": [1, 2, 3]}


def generate_anonymous_user():
    return AnonymousUser(groups=[])


def generate_user_with(*permissions):
    return User("test", "test", True, permissions, groups=[], apikey=None, settings=None)


@pytest.mark.parametrize(
    "restrictions, user, inplace, keep_leaves, expected",
    [
        # "never" matching
        pytest.param(
            {"never": [["bbb"], ["ccc"]]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            False,
            {"aaa": 1, "bbb": {}, "ccc": []},
            id="never_as_user",
        ),
        pytest.param(
            {"never": [["bbb"], ["ccc"]]},
            generate_user_with(Permissions.SETTINGS),
            False,
            False,
            {"aaa": 1, "bbb": {}, "ccc": []},
            id="never_as_admin",
        ),
        # user type
        pytest.param(
            {"user": [["bbb"], ["ccc"]]},
            generate_anonymous_user(),
            False,
            False,
            {"aaa": 1, "bbb": {}, "ccc": []},
            id="user_as_anon",
        ),
        pytest.param(
            {"user": [["bbb"], ["ccc"]]},
            generate_user_with(Permissions.SETTINGS),
            False,
            False,
            {"aaa": 1, "bbb": {"bbb1": 1, "bbb2": 2}, "ccc": [1, 2, 3]},
            id="user_as_user",
        ),
        # admin type
        pytest.param(
            {"admin": [["bbb"], ["ccc"]]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            False,
            {"aaa": 1, "bbb": {}, "ccc": []},
            id="admin_as_user",
        ),
        pytest.param(
            {"admin": [["bbb"], ["ccc"]]},
            generate_user_with(Permissions.SETTINGS),
            False,
            False,
            {"aaa": 1, "bbb": {"bbb1": 1, "bbb2": 2}, "ccc": [1, 2, 3]},
            id="admin_as_admin",
        ),
        # permission based matching
        pytest.param(
            {Permissions.CONTROL: [["bbb"], ["ccc"]]},
            generate_user_with(Permissions.SETTINGS_READ, Permissions.CONTROL),
            False,
            False,
            {"aaa": 1, "bbb": {"bbb1": 1, "bbb2": 2}, "ccc": [1, 2, 3]},
            id="permission_match",
        ),
        pytest.param(
            {Permissions.CONTROL: [["bbb"], ["ccc"]]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            False,
            {"aaa": 1, "bbb": {}, "ccc": []},
            id="permission_fail",
        ),
        # keep leaves
        pytest.param(
            {"never": [["bbb"], ["ccc"]]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            True,
            {"aaa": 1, "bbb": {"bbb1": None, "bbb2": None}, "ccc": []},
            id="keep_leaves",
        ),
        # in place
        pytest.param(
            {"never": [["bbb"], ["ccc"]]},
            generate_user_with(Permissions.SETTINGS_READ),
            True,
            False,
            {"aaa": 1, "bbb": {}, "ccc": []},
            id="inplace",
        ),
        # custom default
        pytest.param(
            {"never": [["bbb"], [("ccc", "custom")]]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            False,
            {"aaa": 1, "bbb": {}, "ccc": "custom"},
            id="custom_default",
        ),
        pytest.param(
            {"never": [["bbb"], [("ccc", lambda: "callback")]]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            False,
            {"aaa": 1, "bbb": {}, "ccc": "callback"},
            id="custom_default_callback",
        ),
        # subpath
        pytest.param(
            {"never": [["bbb", "bbb1"], ["ccc"]]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            False,
            {"aaa": 1, "bbb": {"bbb1": None, "bbb2": 2}, "ccc": []},
            id="subpath",
        ),
        # unknown path
        pytest.param(
            {"never": [["bbb"], ["ccc"], ["d", "d1"]]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            False,
            {"aaa": 1, "bbb": {}, "ccc": []},
            id="unknown_path",
        ),
        # empty path
        pytest.param(
            {"never": [["bbb"], ["ccc"], []]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            False,
            {"aaa": 1, "bbb": {}, "ccc": []},
            id="empty_path",
        ),
        # accidental use of single str instead of list for path
        pytest.param(
            {"never": ["bbb", "ccc"]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            False,
            {"aaa": 1, "bbb": {}, "ccc": []},
            id="str path",
        ),
    ],
)
def test_apply_path_restrictions(
    data, restrictions, user, inplace, keep_leaves, expected
):
    # copy original data
    orig_data = copy.deepcopy(data)

    # run test
    actual = apply_path_restrictions(
        data, restrictions, user, inplace=inplace, keep_leaves=keep_leaves
    )

    # check actual
    assert actual == expected

    if inplace:
        # check data is also replaced
        assert data == expected
    else:
        # check data is NOT replaced
        assert data == orig_data
