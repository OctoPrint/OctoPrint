import os

import pytest

from octoprint.util.plugins import (
    has_legacy_octoprint_setuptools_dependency,
    is_pre_pep517_plugin_package,
)

LEGACY_SETUP_PY_SNIPPET = b"""

from setuptools import setup

try:
    import octoprint_setuptools
except:
    print("Could not import OctoPrint's setuptools, are you sure you are running that under "
          "the same python installation that OctoPrint is installed under?")
    import sys
    sys.exit(-1)

setup_parameters = octoprint_setuptools.create_plugin_setup_parameters(
    identifier=plugin_identifier,
    package=plugin_package,
    name=plugin_name,
    version=plugin_version,
    description=plugin_description,
    author=plugin_author,
    mail=plugin_author_email,
    url=plugin_url,
    license=plugin_license,
    requires=plugin_requires,
    additional_packages=plugin_addtional_packages,
    ignored_packages=plugin_ignored_packages,
    additional_data=plugin_additional_data
)

if len(additional_setup_parameters):
    from octoprint.util import dict_merge
    setup_parameters = dict_merge(setup_parameters, additional_setup_parameters)

setup(**setup_parameters)
"""

MODERN_SETUP_PY_SNIPPET = b"""
import setuptools

# we define the license string like this to be backwards compatible to setuptools<77
setuptools.setup(license="AGPL-3.0-or-later")
"""

LEGACY_ZIP = "not-pep517.zip"
LEGACY_TARBALL = "not-pep517.tar.gz"
MODERN_ZIP = "pep517.zip"
MODERN_TARBALL = "pep517.tar.gz"
WHEEL = "pep517.whl"


@pytest.mark.parametrize(
    "input_name, expected",
    [
        pytest.param(LEGACY_ZIP, True, id="legacy_zip"),
        pytest.param(LEGACY_TARBALL, True, id="legacy_tarball"),
        pytest.param(MODERN_ZIP, False, id="modern_zip"),
        pytest.param(MODERN_TARBALL, False, id="modern_tarball"),
        pytest.param(WHEEL, False, id="wheel"),
    ],
)
def test_is_pre_pep517_plugin_package(input_name, expected):
    path = os.path.join(
        os.path.dirname(__file__), "_files", "plugins_test_data", input_name
    )

    actual = is_pre_pep517_plugin_package(path)

    assert actual == expected


@pytest.mark.parametrize(
    "content, expected",
    [
        pytest.param(LEGACY_SETUP_PY_SNIPPET, True, id="legacy_setup_py"),
        pytest.param(MODERN_SETUP_PY_SNIPPET, False, id="modern_setup_py"),
    ],
)
def test_has_legacy_octoprint_setuptools_dependency(content, expected):
    actual = has_legacy_octoprint_setuptools_dependency(content)

    assert actual == expected
