import pytest

import octoprint.util.text

_WITH_OLD_FORMATTING = """
%%
%s
%s two! %s
%(hi)s
%()s
%#o
% #0-+d
%5d
%*d
%.f
%.5f
%.*f
%ld
%(hi)#4.4f
%(hi)10s
%(hi)-10s
%(hi).5s
%(hi)-10.5s
%(hi)06.2f
%(hi)+d
"""


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello World", False),
        ("foo %(test)A bar", False),
        ("G1 X%(x)s F%(feedrate)s", True),
        *[
            (f"foo {line} bar", True)
            for line in _WITH_OLD_FORMATTING.strip().splitlines()
        ],
    ],
)
def test_has_old_style_formatting(text, expected):
    actual = octoprint.util.text.has_old_style_formatting(text)
    assert actual == expected
