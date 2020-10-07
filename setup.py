#!/usr/bin/env python2
# coding=utf-8

import os
import sys
from distutils.command.build_py import build_py as _build_py

import versioneer  # noqa: F401

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "src"))
import setuptools  # noqa: F401,E402

import octoprint_setuptools  # noqa: F401,E402

# ----------------------------------------------------------------------------------------

# Supported python versions
PYTHON_REQUIRES = ">=3.6,<4"

# Requirements for setup.py
SETUP_REQUIRES = [
    "markdown>=3.2.2,<4",
]

# Requirements for our application
INSTALL_REQUIRES = [
    # additional OctoPrint plugins that are maintained on a different release cycle
    "OctoPrint-FirmwareCheck>=2020.06.22",
    "OctoPrint-FileCheck>=2020.07.06",
    # the following dependencies are non trivial to update since later versions
    # introduce backwards incompatible changes that might affect plugins, or due to
    # other observed problems
    "regex!=2018.11.6",  # avoid broken 2018.11.6. See #2874
    # anything below this should be checked on releases for new versions
    "tornado>=6.0.4,<7",
    "markdown>=3.2.2,<4",
    "flask>=1.1.2,<2",
    "Jinja2>=2.11.2,<3",
    "Flask-Login>=0.5,<0.6",  # flask-login doesn't use semver & breaks stuff on minor version increases
    "Flask-Babel>=1.0,<2",
    "Flask-Assets>=2.0,<3",
    "werkzeug>=1.0.1,<2",
    "itsdangerous>=1.1.0,<2",
    "cachelib>=0.1,<1",
    "PyYAML>=5.3.1,<6",
    "pyserial>=3.4,<4",
    "netaddr>=0.7.19,<1",
    "watchdog>=0.10.2,<1",
    "sarge==0.1.5post0",
    "netifaces>=0.10.9,<1",
    "pylru>=1.2,<2",
    "rsa>=4.0,<5",
    "pkginfo>=1.5.0.1,<2",
    "requests>=2.23.0,<3",
    "semantic_version>=2.8.5,<3",
    "psutil>=5.7,<6",
    "Click>=7.1.2,<8",
    "feedparser>=5.2.1,<6",
    "future>=0.18.2,<1",
    "websocket-client>=0.57,<1",
    "wrapt>=1.12.1,<2",
    "emoji>=0.5.4,<1",
    "frozendict>=1.2,<2",
    "sentry-sdk>=0.15.1,<1",
    "filetype>=1.0.7,<2",
    "zeroconf>=0.24,<0.25",
    # vendor bundled dependencies
    "unidecode>=0.04.14,<0.05",  # dependency of awesome-slugify
    "blinker>=1.4,<2",  # dependency of flask_principal
]

# OSX specific requirements
INSTALL_REQUIRES_OSX = [
    "appdirs>=1.4.4",
]

# Additional requirements for optional install options
EXTRA_REQUIRES = {
    "develop": [
        # Testing dependencies
        "pytest>=5.4.3,<6",
        "pytest-doctest-custom>=1.0.0,<2",
        "ddt",
        # pre-commit
        "pre-commit",
        # profiler
        "pyinstrument",
    ],
    # Dependencies for developing OctoPrint plugins
    "plugins": ["cookiecutter>=1.7.2,<1.8"],
    # Dependencies for building the documentation - Python 3 required!
    "docs": [
        "sphinx>=3,<4",
        "sphinxcontrib-httpdomain",
        "sphinxcontrib-mermaid",
        "sphinx_rtd_theme",
        "readthedocs-sphinx-ext",
    ],
}

# Dependency links for any of the aforementioned dependencies
DEPENDENCY_LINKS = []

EXTRA_REQUIRES[":sys_platform == 'darwin'"] = INSTALL_REQUIRES_OSX

# -----------------------------------------------------------------------------------------------------------------------
# Anything below here is just command setup and general setup configuration

here = os.path.abspath(os.path.dirname(__file__))


def read_file_contents(path):
    import codecs

    with codecs.open(path, encoding="utf-8") as f:
        return f.read()


def md_to_html_build_py_factory(files, baseclass):
    class md_to_html_build_py(baseclass):
        files = {}

        def run(self):
            print("RUNNING md_to_html_build_py")
            if not self.dry_run:
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
                            dest = os.path.join(target_dir, source + ".html")

                        print("Rendering markdown from {} to {}".format(source, dest))

                        from markdown import markdownFromFile

                        markdownFromFile(input=source, output=dest, encoding="utf-8")
            baseclass.run(self)

    return type(md_to_html_build_py)(
        md_to_html_build_py.__name__, (md_to_html_build_py,), {"files": files}
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

    cmdclass["build_py"] = md_to_html_build_py_factory(
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
    global versioneer, get_cmdclass, read_file_contents, here, PYTHON_REQUIRES, SETUP_REQUIRES, INSTALL_REQUIRES, EXTRA_REQUIRES, DEPENDENCY_LINKS

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
    dependency_links = DEPENDENCY_LINKS

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
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
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
        "Bug Reports": "https://github.com/foosel/OctoPrint/issues",
        "Source": "https://github.com/foosel/OctoPrint",
        "Funding": "https://donate.octoprint.org",
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
        # it a bit here by explicitly adding the development dependencies, which include our
        # documentation dependencies
        install_requires = install_requires + extras_require["docs"]

    entry_points = {"console_scripts": ["octoprint = octoprint:main"]}

    return locals()


setuptools.setup(**params())
