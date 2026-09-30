import re

import pytest

from octoprint.server.util.sockjs import filter_lines, pattern_or_boolean, to_pattern

LINES = ["1 2 3", "foo bar fnord", "a b cdef ghi"]


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(False, False, id="False"),
        pytest.param(True, True, id="True"),
        pytest.param("", True, id="empty string"),
        pytest.param("  \t \r\n", True, id="only whitespace"),
        pytest.param("*", True, id="single star"),
        pytest.param("***", True, id="multi star"),
        pytest.param("foo", "foo", id="simple string"),
        pytest.param("*foo*", "foo", id="valid pattern turns string"),
        pytest.param(
            "****foo*****",
            "foo",
            id="valid pattern w/ multi star turns string",
        ),
        pytest.param("*foo", ".*foo", id="valid suffix pattern"),
        pytest.param("foo*", "foo.*", id="valid prefix pattern"),
    ],
)
def test_fnmatch_or_boolean(value, expected):
    actual = pattern_or_boolean(value)
    if isinstance(actual, re.Pattern):
        assert actual.pattern == expected
    else:
        assert actual == expected


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(None, id="None"),
        pytest.param(1, id="neither str nor bool"),
        pytest.param("a*b", id="no stars in between"),
    ],
)
def test_fnmatch_or_boolean_error(value):
    with pytest.raises(ValueError):
        pattern_or_boolean(value)


@pytest.mark.parametrize(
    "sub, expected",
    [
        pytest.param(True, LINES, id="match everything"),
        pytest.param("f", LINES[1:], id="substring match"),
        pytest.param(" ", LINES, id="substring match in all lines"),
        pytest.param("foo", LINES[1:2], id="longer substring match"),
        pytest.param(to_pattern("foo", after=True), LINES[1:2], id="suffix match"),
        pytest.param(to_pattern("fnord", before=True), LINES[1:2], id="prefix match"),
    ],
)
def test_filter_lines(sub, expected):
    actual = filter_lines(LINES, sub)
    assert actual == expected


@pytest.mark.parametrize(
    "value, before, after, expected",
    [
        pytest.param("foo", False, False, "foo"),
        pytest.param("foo", False, True, "foo.*"),
        pytest.param("foo", True, False, ".*foo"),
        pytest.param("foo", True, True, ".*foo.*"),
    ],
)
def test_to_pattern(value, before, after, expected):
    actual = to_pattern(value, before=before, after=after)
    assert actual.pattern == expected
