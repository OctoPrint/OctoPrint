from typing import Union

import pytest

import octoprint.util


@pytest.mark.parametrize(
    "line, expected_ct, expected_params",
    (
        ("text/html", "text/html", {}),
        ("text/html; charset=UTF-8", "text/html", {"charset": "UTF-8"}),
        ("*/*", "*/*", {}),
        ("*", "text/plain", {}),
    ),
)
def test_parse_content_type_line(
    line: str, expected_ct: str, expected_params: dict
) -> None:
    actual_ct, actual_params = octoprint.util.parse_content_type_line(line)
    assert actual_ct == expected_ct
    assert actual_params == expected_params


@pytest.mark.parametrize(
    "line, expected_type, expected_sub, expected_params",
    (
        ("text/html", "text", "html", {}),
        ("text/html; charset=UTF-8", "text", "html", {"charset": "UTF-8"}),
        ("*/*", "*", "*", {}),
        ("*", "*", "*", {}),
    ),
)
def test_parse_mime_typ(
    line: str, expected_type: str, expected_sub: str, expected_params: dict
) -> None:
    actual = octoprint.util.parse_mime_type(line)
    assert actual == (expected_type, expected_sub, expected_params)


@pytest.mark.parametrize(
    "mime, other, expected",
    (
        (octoprint.util.parse_mime_type("text/html"), "text/html", True),
        ("text/html", "text/html", True),
        ("text/html; charset=UTF-8", "text/html", True),
        ("text/html", "text/*", True),
        ("text/html", "*/*", True),
        ("text/html", "*", True),
        ("text/html", "image/png", False),
        ("text/html", "image/*", False),
    ),
)
def test_mime_type_matches(
    mime: Union[str, tuple], other: Union[str, tuple], expected: bool
) -> None:
    actual1 = octoprint.util.mime_type_matches(mime, other)
    actual2 = octoprint.util.mime_type_matches(other, mime)
    assert actual1 == expected
    assert actual2 == expected
