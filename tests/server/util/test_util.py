__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

import pytest


@pytest.mark.parametrize(
    "url,paths,expected",
    [
        # various default UI URLs
        ("/", ["/", "/recovery/"], True),
        ("/?", ["/", "/recovery/"], True),
        ("/?l10n=de", ["/", "/recovery/"], True),
        ("/?l10n=de&", ["/", "/recovery/"], True),
        ("/octoprint/", ["/octoprint/", "/octoprint/recovery/"], True),
        # various recovery URLs
        ("/recovery/", ["/", "/recovery/"], True),
        ("/recovery/?", ["/", "/recovery/"], True),
        ("/recovery/?l10n=de", ["/", "/recovery/"], True),
        ("/octoprint/recovery/?l10n=de", ["/octoprint/", "/octoprint/recovery/"], True),
        # various external URLs
        ("http://example.com", ["/", "/recovery/"], False),
        ("https://example.com", ["/", "/recovery/"], False),
        ("//example.com", ["/", "/recovery/"], False),
        ("/\\/\\example.com", ["/", "/recovery/"], False),
        (" /\\/\\example.com", ["/", "/recovery/"], False),
        ("\\/\\/example.com", ["/", "/recovery/"], False),
        (" \\/\\/example.com", ["/", "/recovery/"], False),
        # other stuff
        ("javascript:alert(document.cookie)", ["/", "/recovery/"], False),
    ],
)
def test_validate_local_redirect(url, paths, expected):
    from octoprint.server.util import validate_local_redirect

    assert validate_local_redirect(url, paths) == expected
