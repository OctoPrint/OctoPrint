# -*- coding: utf-8 -*-

### NOTE #################################################################################
# This file has to stay format compatible to Python 2, or pip under Python 2 will
# not be able to detect that OctoPrint requires Python 3 but instead fail with a
# syntax error.
#
# So, no f-strings, no walrus operators, no pyupgrade or codemods.
##########################################################################################

import os
import sys
from distutils.command.build_py import build_py as _build_py

import versioneer  # noqa: F401

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "src"))
import setuptools  # noqa: F401,E402

import octoprint_setuptools  # noqa: F401,E402

# ----------------------------------------------------------------------------------------

# Supported python versions
PYTHON_REQUIRES = ">=3.7, <4"

# Requirements for setup.py
SETUP_REQUIRES = []

# Requirements for our application
bundled_plugins = [
    "OctoPrint-FileCheck>=2021.2.23",
    "OctoPrint-FirmwareCheck>=2021.10.11",
    "OctoPrint-PiSupport>=2021.10.28",
]
core_deps = [
    "cachelib>=0.2,<0.3",
    "Click>=8.0.3,<9",
    "colorlog>=5.0.1,<6",
    "emoji>=1.4.2,<2",
    "feedparser>=6.0.8,<7",
    "filetype>=1.0.7,<2",
    "Flask-Assets>=2.0,<3",
    "Flask-Babel>=2.0,<3",
    "Flask-Login>=0.5,<0.6",  # flask-login doesn't use semver & breaks stuff on minor version increases
    "flask>=2,<3",
    "frozendict>=2.0,<3",
    "future>=0.18.2,<1",  # not really needed anymore, but leaving in for py2/3 compat plugins
    "markdown>=3.2.2,<4",
    "netaddr>=0.8,<0.9",  # changelog hints at breaking changes on minor version increases
    "netifaces>=0.11,<1",
    "pathvalidate>=2.4.1,<3",
    "pkginfo>=1.7.1,<2",
    "psutil>=5.8,<6",
    "pylru>=1.2,<2",
    "pyserial>=3.4,<4",
    "PyYAML>=5.4.1,<6",
    "requests>=2.26.0,<3",
    "sarge==0.1.6",
    "semantic_version>=2.8.5,<3",
    "sentry-sdk>=1.3.1,<2",
    "tornado>=6.0.4,<7",
    "watchdog==1.0.0",
    "websocket-client>=1.2.1,<2",
    "wrapt>=1.13.3,<1.14",
    "zeroconf>=0.33,<0.34",  # breaking changes can happen on minor version increases
    "zipstream-ng>=1.3.4,<2.0.0",
]
vendored_deps = [
    "blinker>=1.4,<2",  # dependency of flask_principal
    "regex",  # dependency of awesome-slugify
    "unidecode",  # dependency of awesome-slugify
]

INSTALL_REQUIRES = bundled_plugins + core_deps + vendored_deps

# Additional requirements for optional install options and/or OS-specific dependencies
EXTRA_REQUIRES = {
    # Dependencies for OSX
    ":sys_platform == 'darwin'": [
        "appdirs>=1.4.4,<2",
    ],
    # Dependencies for core development
    "develop": [
        # Testing dependencies
        "ddt",
        "mock>=4,<5",
        "pytest-doctest-custom>=1.0.0,<2",
        "pytest>=6.2.5,<7",
        # pre-commit
        "pre-commit",
        # profiler
        "pyinstrument",
    ],
    # Dependencies for developing OctoPrint plugins
    "plugins": ["cookiecutter>=1.7.2,<1.8"],
    # Dependencies for building the documentation
    "docs": [
        "readthedocs-sphinx-ext",
        "sphinx_rtd_theme",
        "sphinx>=3,<4",
        "sphinxcontrib-httpdomain",
        "sphinxcontrib-mermaid",
    ],
}

# ----------------------------------------------------------------------------------------
# Anything below here is just command setup and general setup configuration

here = os.path.abspath(os.path.dirname(__file__))


def read_file_contents(path):
    import io

    with io.open(path, encoding="utf-8") as f:
        return f.read()


def copy_files_build_py_factory(files, baseclass):
    class copy_files_build_py(baseclass):
        files = {}

        def run(self):
            print("RUNNING copy_files_build_py")
            if not self.dry_run:
                import shutil

                for directory, files in self.files.items():
                    target_dir = os.path.join(self.build_lib, directory)
                    self.mkpath(target_dir)

                    for entry in files:
                        if isinstance(entry, tuple):
                            if len(entry) != 2:
                                continue
                            source, dest = entry[0], os.path.join(target_dir, entry[1])
                        else:
                            source = entry
                            dest = os.path.join(target_dir, source)

                        print("Copying {} to {}".format(source, dest))
                        shutil.copy2(source, dest)

            baseclass.run(self)

    return type(copy_files_build_py)(
        copy_files_build_py.__name__, (copy_files_build_py,), {"files": files}
    )


def get_cmdclass():
    # make sure these are always available, even when run by dependabot
    global versioneer, octoprint_setuptools, md_to_html_build_py_factory

    cmdclass = versioneer.get_cmdclass()

    # add clean command
    cmdclass.update(
        {
            "clean": octoprint_setuptools.CleanCommand.for_options(
                source_folder="src", eggs=["OctoPrint*.egg-info"]
            )
        }
    )

    # add translation commands
    translation_dir = "translations"
    pot_file = os.path.join(translation_dir, "messages.pot")
    bundled_dir = os.path.join("src", "octoprint", "translations")
    cmdclass.update(
        octoprint_setuptools.get_babel_commandclasses(
            pot_file=pot_file,
            output_dir=translation_dir,
            pack_name_prefix="OctoPrint-i18n-",
            pack_path_prefix="",
            bundled_dir=bundled_dir,
        )
    )

    cmdclass["build_py"] = copy_files_build_py_factory(
        {
            "octoprint/templates/_data": [
                "AUTHORS.md",
                "SUPPORTERS.md",
                "THIRDPARTYLICENSES.md",
            ]
        },
        cmdclass["build_py"] if "build_py" in cmdclass else _build_py,
    )

    return cmdclass


def params():
    # make sure these are always available, even when run by dependabot
    global versioneer, get_cmdclass, read_file_contents, here, PYTHON_REQUIRES, SETUP_REQUIRES, INSTALL_REQUIRES, EXTRA_REQUIRES

    name = "OctoPrint"
    version = versioneer.get_version()
    cmdclass = get_cmdclass()

    description = "The snappy web interface for your 3D printer"
    long_description = read_file_contents(os.path.join(here, "README.md"))
    long_description_content_type = "text/markdown"

    python_requires = PYTHON_REQUIRES
    setup_requires = SETUP_REQUIRES
    install_requires = INSTALL_REQUIRES
    extras_require = EXTRA_REQUIRES

    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Flask",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Manufacturing",
        "Intended Audience :: Other Audience",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Natural Language :: English",
        "Natural Language :: German",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: JavaScript",
        "Topic :: Printing",
        "Topic :: System :: Monitoring",
    ]
    author = "Gina Häußge"
    author_email = "gina@octoprint.org"
    url = "https://octoprint.org"
    license = "GNU Affero General Public License v3"
    keywords = "3dprinting 3dprinter 3d-printing 3d-printer octoprint"

    project_urls = {
        "Community Forum": "https://community.octoprint.org",
        "Bug Reports": "https://github.com/OctoPrint/OctoPrint/issues",
        "Source": "https://github.com/OctoPrint/OctoPrint",
        "Funding": "https://support.octoprint.org",
    }

    packages = setuptools.find_packages(where="src")
    package_dir = {
        "": "src",
    }
    package_data = {
        "octoprint": octoprint_setuptools.package_data_dirs(
            "src/octoprint", ["static", "templates", "plugins", "translations"]
        )
        + ["util/piptestballoon/setup.py"]
    }

    include_package_data = True
    zip_safe = False

    if os.environ.get("READTHEDOCS", None) == "True":
        # we can't tell read the docs to please perform a pip install -e .[docs], so we help
        # it a bit here by explicitly adding the docs dependencies
        install_requires = install_requires + extras_require["docs"]

    entry_points = {"console_scripts": ["octoprint = octoprint:main"]}

    return locals()


setuptools.setup(**params())
