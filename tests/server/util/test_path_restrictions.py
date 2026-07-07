import copy

import pytest

from octoprint.access.permissions import Permissions
from octoprint.access.users import AnonymousUser, User
from octoprint.server.util.flask import apply_path_restrictions


@pytest.fixture
def data():
    return {"a": 1, "b": {"b1": 1, "b2": 2}, "c": [1, 2, 3]}


def generate_anonymous_user():
    return AnonymousUser(groups=[])


def generate_user_with(*permissions):
    return User("test", "test", True, permissions, groups=[], apikey=None, settings=None)


@pytest.mark.parametrize(
    "restrictions, user, inplace, keep_leaves, expected",
    [
        # "never" matching
        pytest.param(
            {"never": [["b"], ["c"]]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            False,
            {"a": 1, "b": {}, "c": []},
            id="never_as_user",
        ),
        pytest.param(
            {"never": [["b"], ["c"]]},
            generate_user_with(Permissions.SETTINGS),
            False,
            False,
            {"a": 1, "b": {}, "c": []},
            id="never_as_admin",
        ),
        # user type
        pytest.param(
            {"user": [["b"], ["c"]]},
            generate_anonymous_user(),
            False,
            False,
            {"a": 1, "b": {}, "c": []},
            id="user_as_anon",
        ),
        pytest.param(
            {"user": [["b"], ["c"]]},
            generate_user_with(Permissions.SETTINGS),
            False,
            False,
            {"a": 1, "b": {"b1": 1, "b2": 2}, "c": [1, 2, 3]},
            id="user_as_user",
        ),
        # admin type
        pytest.param(
            {"admin": [["b"], ["c"]]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            False,
            {"a": 1, "b": {}, "c": []},
            id="admin_as_user",
        ),
        pytest.param(
            {"admin": [["b"], ["c"]]},
            generate_user_with(Permissions.SETTINGS),
            False,
            False,
            {"a": 1, "b": {"b1": 1, "b2": 2}, "c": [1, 2, 3]},
            id="admin_as_admin",
        ),
        # permission based matching
        pytest.param(
            {Permissions.CONTROL: [["b"], ["c"]]},
            generate_user_with(Permissions.SETTINGS_READ, Permissions.CONTROL),
            False,
            False,
            {"a": 1, "b": {"b1": 1, "b2": 2}, "c": [1, 2, 3]},
            id="permission_match",
        ),
        pytest.param(
            {Permissions.CONTROL: [["b"], ["c"]]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            False,
            {"a": 1, "b": {}, "c": []},
            id="permission_fail",
        ),
        # keep leaves
        pytest.param(
            {"never": [["b"], ["c"]]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            True,
            {"a": 1, "b": {"b1": None, "b2": None}, "c": []},
            id="keep_leaves",
        ),
        # in place
        pytest.param(
            {"never": [["b"], ["c"]]},
            generate_user_with(Permissions.SETTINGS_READ),
            True,
            False,
            {"a": 1, "b": {}, "c": []},
            id="inplace",
        ),
        # custom default
        pytest.param(
            {"never": [["b"], [("c", "custom")]]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            False,
            {"a": 1, "b": {}, "c": "custom"},
            id="custom_default",
        ),
        pytest.param(
            {"never": [["b"], [("c", lambda: "callback")]]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            False,
            {"a": 1, "b": {}, "c": "callback"},
            id="custom_default_callback",
        ),
        # subpath
        pytest.param(
            {"never": [["b", "b1"], ["c"]]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            False,
            {"a": 1, "b": {"b1": None, "b2": 2}, "c": []},
            id="subpath",
        ),
        # unknown path
        pytest.param(
            {"never": [["b"], ["c"], ["d", "d1"]]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            False,
            {"a": 1, "b": {}, "c": []},
            id="unknown_path",
        ),
        # empty path
        pytest.param(
            {"never": [["b"], ["c"], []]},
            generate_user_with(Permissions.SETTINGS_READ),
            False,
            False,
            {"a": 1, "b": {}, "c": []},
            id="empty_path",
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
