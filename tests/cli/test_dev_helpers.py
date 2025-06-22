__author__ = "Gina Häußge <gina@octoprint.org>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2025 The OctoPrint Project - Released under terms of the AGPLv3 License"

import pytest

import octoprint.cli.dev


@pytest.mark.parametrize(
    "name, expected",
    [
        ("OctoPrint", "OctoPrint"),
        ("OctoPrint-TestPlugin", "OctoPrint-TestPlugin"),
        ("OctoPrint Test Plugin", "OctoPrint-Test-Plugin"),
        ("OctöPrint", "Oct-Print"),
    ],
)
def test_get_pep508_name(name, expected):
    assert octoprint.cli.dev._get_pep508_name(name) == expected


@pytest.mark.parametrize("name", ["ÖctoPrint", " OctoPrint-Plugin", "äöüß"])
def test_get_pep508_name_fail(name):
    try:
        octoprint.cli.dev._get_pep508_name(name)
        pytest.fail(f"Expected a ValueError here: {name}")
    except ValueError:
        pass


@pytest.mark.parametrize(
    "license, expected",
    [
        ("agplv3", "AGPL-3.0-or-later"),
        ("AGPL v3", "AGPL-3.0-or-later"),
        ("aGPl-3.0", "AGPL-3.0-or-later"),
        ("Apache 2", "Apache-2.0"),
        ("Apache 2.0", "Apache-2.0"),
        ("Apache-2.0", "Apache-2.0"),
        ("BSD-3-Clause", "BSD-3-Clause"),
        ("CC BY-NC-SA 4.0", "CC-BY-NC-SA-4.0"),
        ("CC BY-ND", "CC-BY-ND-4.0"),
        ("GNU Affero General Public License", "LicenseRef-AGPL"),
        ("GNU General Public License v3.0", "GPL-3.0-or-later"),
        ("GNUv3", "GPL-3.0-or-later"),
        ("GNU v3.0", "GPL-3.0-or-later"),
        ("GPL-3.0 License", "GPL-3.0-or-later"),
        ("GPLv3", "GPL-3.0-or-later"),
        ("MIT", "MIT"),
        ("MIT License", "MIT"),
        ("Unlicense", "Unlicense"),
        ("Unknown License", "LicenseRef-Unknown-License"),
    ],
)
def test_get_spdx_license(license, expected):
    assert octoprint.cli.dev._get_spdx_license(license) == expected
