__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

import pytest

DEFAULT_ALLOWED_PATHS = ["/", "/recovery/", "/plugin/appkeys/auth/*"]
PREFIXED_ALLOWED_PATHS = list(map(lambda x: "/octoprint" + x, DEFAULT_ALLOWED_PATHS))


@pytest.mark.parametrize(
    "url,paths,expected",
    [
        # various default UI URLs
        ("/", DEFAULT_ALLOWED_PATHS, True),
        ("/?", DEFAULT_ALLOWED_PATHS, True),
        ("/?l10n=de", DEFAULT_ALLOWED_PATHS, True),
        ("/?l10n=de&", DEFAULT_ALLOWED_PATHS, True),
        ("/octoprint/", PREFIXED_ALLOWED_PATHS, True),
        # various recovery URLs
        ("/recovery/", DEFAULT_ALLOWED_PATHS, True),
        ("/recovery/?", DEFAULT_ALLOWED_PATHS, True),
        ("/recovery/?l10n=de", DEFAULT_ALLOWED_PATHS, True),
        ("/octoprint/recovery/?l10n=de", PREFIXED_ALLOWED_PATHS, True),
        # various appkeys URLs
        ("/plugin/appkeys/auth/1234567890", DEFAULT_ALLOWED_PATHS, True),
        ("/plugin/appkeys/auth/1234567890?", DEFAULT_ALLOWED_PATHS, True),
        ("/plugin/appkeys/auth/1234567890?l10n=de", DEFAULT_ALLOWED_PATHS, True),
        ("/octoprint/plugin/appkeys/auth/1234567890", PREFIXED_ALLOWED_PATHS, True),
        # various external URLs
        ("http://example.com", DEFAULT_ALLOWED_PATHS, False),
        ("https://example.com", DEFAULT_ALLOWED_PATHS, False),
        ("//example.com", DEFAULT_ALLOWED_PATHS, False),
        ("/\\/\\example.com", DEFAULT_ALLOWED_PATHS, False),
        (" /\\/\\example.com", DEFAULT_ALLOWED_PATHS, False),
        ("\\/\\/example.com", DEFAULT_ALLOWED_PATHS, False),
        (" \\/\\/example.com", DEFAULT_ALLOWED_PATHS, False),
        # other stuff
        ("javascript:alert(document.cookie)", DEFAULT_ALLOWED_PATHS, False),
    ],
)
def test_validate_local_redirect(url, paths, expected):
    from octoprint.server.util import validate_local_redirect

    assert validate_local_redirect(url, paths) == expected
