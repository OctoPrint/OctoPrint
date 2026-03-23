__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from unittest.mock import MagicMock, patch

import pytest

DEFAULT_ALLOWED_PATHS = ["/", "/recovery/", "/plugin/appkeys/auth/*"]
PREFIXED_ALLOWED_PATHS = ["/octoprint" + x for x in DEFAULT_ALLOWED_PATHS]


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
        # path traversal URLs
        ("/../evil", DEFAULT_ALLOWED_PATHS, False),
        ("/recovery/../evil", DEFAULT_ALLOWED_PATHS, False),
        ("/plugin/appkeys/auth/../evil", DEFAULT_ALLOWED_PATHS, False),
        ("/octoprint/../evil", PREFIXED_ALLOWED_PATHS, False),
        ("/octoprint/recovery/../evil", PREFIXED_ALLOWED_PATHS, False),
        ("/octoprint/plugin/appkeys/auth/../evil", PREFIXED_ALLOWED_PATHS, False),
        # other stuff
        ("javascript:alert(document.cookie)", DEFAULT_ALLOWED_PATHS, False),
    ],
)
def test_validate_local_redirect(url, paths, expected):
    from octoprint.server.util import validate_local_redirect

    assert validate_local_redirect(url, paths) == expected


@pytest.mark.parametrize(
    "remote_addr, ff_header, remote_user_header, trusted_auth_proxies, trusted_reverse_proxies, expected",
    [
        ("127.0.0.1", "", "user", [], [], None),  # localhost, nothing trusted
        (
            "127.0.0.1",
            "",
            "user",
            [],
            ["127.0.0.0/8", "::1"],
            None,
        ),  # direct from localhost, no trusted auth proxy
        (
            "127.0.0.1",
            "",
            "user",
            ["192.168.1.10"],
            ["127.0.0.0/8", "::1"],
            None,
        ),  # direct from localhost, trusted auth proxy but not trusted reverse proxy (localhost not automatically added)
        (
            "127.0.0.1",
            "",
            "user",
            ["127.0.0.0/8", "::1"],
            ["127.0.0.0/8", "::1"],
            "user",
        ),  # direct from localhost, trusted auth proxy
        (
            "192.168.1.10",
            "",
            "user",
            ["127.0.0.0/8", "::1"],
            ["127.0.0.0/8", "::1"],
            None,
        ),  # direct from lan, no match against trusted proxy
        (
            "127.0.0.1",
            "192.168.1.10",
            "user",
            ["127.0.0.0/8", "::1"],
            ["127.0.0.0/8", "::1"],
            "user",
        ),  # lan via proxy, trusted auth proxy
        (
            "127.0.0.1",
            "10.1.2.3, 192.168.1.10",
            "user",
            ["192.168.1.10"],
            ["127.0.0.0/8", "::1"],
            None,
            # lan via proxy, trusted auth proxy not among trusted reverse proxies
        ),
        (
            "127.0.0.1",
            "10.1.2.3, 192.168.1.10",
            "user",
            ["192.168.1.10"],
            ["127.0.0.0/8", "::1", "192.168.1.10"],
            "user",
        ),  # lan via proxy, trusted auth proxy also trusted as reverse proxy
        (
            "127.0.0.1",
            "10.1.2.3",
            "user",
            ["192.168.1.10"],
            ["127.0.0.0/8", "::1", "192.168.1.10"],
            None,
        ),  # lan via proxy, trusted auth proxy not in chain, ignored
        (
            "127.0.0.1",
            "192.168.1.10, 10.1.2.3",
            "user",
            ["192.168.1.10"],
            ["127.0.0.0/8", "::1", "192.168.1.10"],
            None,
        ),  # lan via proxy, spoofed auth proxy address in X-Forwarded-For, ignored
        (
            "192.168.1.10",
            "127.0.0.1, 10.1.2.3",
            "user",
            ["127.0.0.0/8", "::1"],
            ["127.0.0.0/8", "::1"],
            None,
        ),  # lan via untrusted reverse proxy, spoofed remote address, ignored
        (
            "192.168.1.10",
            "127.0.0.1, 10.1.2.3",
            "user",
            ["127.0.0.0/8", "::1"],
            ["127.0.0.0/8", "::1", "192.168.1.10"],
            None,
        ),  # lan via trusted reverse proxy, not trusted as auth proxy though, spoofed remote address, ignored
        (
            "192.168.1.10",
            "10.1.2.3",
            "user",
            ["192.168.1.10"],
            ["127.0.0.0/8", "::1", "192.168.1.10"],
            "user",
        ),  # lan via auth proxy directly, no reverse proxies
    ],
)
def test_get_user_for_remote_user_header(
    remote_addr,
    ff_header,
    remote_user_header,
    trusted_auth_proxies,
    trusted_reverse_proxies,
    expected,
):
    from octoprint.server.util import LoginMechanism, get_user_for_remote_user_header
    from octoprint.settings import Settings

    def settings_get(path, *args, **kwargs):
        if path == ["accessControl", "remoteUserHeader"]:
            return "X-Remote-User"
        elif path == ["accessControl", "trustedAuthProxies"]:
            return trusted_auth_proxies
        else:
            return None

    settings = MagicMock(spec=Settings)
    settings.get.side_effect = settings_get

    # mock settings
    with patch("octoprint.server.util.settings") as settings_mock:
        settings_mock.return_value = settings

        # mock usable_trusted_proxies_from_settings
        with patch(
            "octoprint.server.util.usable_trusted_proxies_from_settings"
        ) as trusted_proxies_mock:
            trusted_proxies_mock.side_effect = (
                lambda *args, **kwargs: trusted_reverse_proxies
            )

            # mock request
            mocked_environ = {"ORIG_REMOTE_ADDR": remote_addr}
            mocked_headers = {
                "X-Forwarded-For": ff_header,
                "X-Remote-User": remote_user_header,
            }
            mocked_request = MagicMock()
            mocked_request.environ = mocked_environ
            mocked_request.headers = mocked_headers

            # mock user manager
            with patch("octoprint.server.userManager") as user_manager_mock:
                user_manager_mock.find_user.return_value = remote_user_header

                with patch("octoprint.server.util._flask") as flask_mock:
                    flask_mock.session = dict()

                    # call function
                    returned_user = get_user_for_remote_user_header(mocked_request)

                    assert returned_user == expected
                    if expected is not None:
                        assert (
                            flask_mock.session["login_mechanism"]
                            == LoginMechanism.REMOTE_USER
                        )
                        assert flask_mock.session["credentials_seen"]
