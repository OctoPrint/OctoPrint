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

sys.path.insert(0, os.path.dirname(__file__))

import setuptools  # noqa: F401,E402

try:
    import octoprint_setuptools  # noqa: F401,E402
except ImportError:
    octoprint_setuptools = None

# ----------------------------------------------------------------------------------------

# Supported python versions
PYTHON_REQUIRES = ">=3.7, <3.14"

# Requirements for setup.py
SETUP_REQUIRES = []

# Requirements for our application
bundled_plugins = [
    "OctoPrint-FileCheck>=2024.11.12",
    "OctoPrint-FirmwareCheck>=2021.10.11",
    "OctoPrint-PiSupport>=2023.10.10",
]
core_deps = [
    "argon2-cffi>=23.1.0",
    "Babel>=2.16,<2.17 ; python_version>='3.8'",  # breaking changes can happen on minor version increases
    "cachelib>=0.13.0,<0.14 ; python_version>='3.8'",
    "Click>=8.1.8,<9",
    "colorlog>=6.9.0,<7",
    "emoji>=2.14.1,<3",
    "feedparser>=6.0.11,<7",
    "filetype>=1.2.0,<2",
    "Flask-Assets>=2.1.0,<3",
    "Flask-Babel>=4.0.0,<5 ; python_version>='3.8'",
    "Flask-Login>=0.6.3,<0.7",  # breaking changes can happen on minor version increases
    "Flask-Limiter>=3.8,<3.9 ; python_version>='3.8'",  # later versions require Python 3.9+
    "flask>=3.0.3,<3.1 ; python_version>='3.8'",  # later versions require Python 3.9+, breaking changes can happen on minor version increases (with deprecation warnings)
    "frozendict>=2.4.6,<3",
    "limits<5",  # dependency of Flask-Limiter, v5 was released days before 1.11.0 and contains backwards incompatibilities, pinning upper limit out of caution
    "markdown>=3.7,<3.8 ; python_version>='3.8'",
    "netaddr>=1.3.0,<1.4",  # changelog hints at breaking changes on minor version increases
    # "netifaces2>=0.0.21,<0.1",  # fork of netifaces in Rust, use rolled back due to build issues in some environments
    "netifaces>=0.11.0,<0.12",
    "packaging",
    "libpass>=1.8.1,<2 ; python_version>='3.9'",  # replacement for unmaintained passlib
    "passlib==1.7.4 ; python_version<'3.9'",
    "pathvalidate>=3.2.1,<4",  # later versions require Python 3.9
    "psutil>=6.1.1,<7",
    "pydantic>=2.10.6,<3 ; python_version>='3.8'",
    "pylru>=1.2.1,<2",
    "pyserial>=3.5,<4",
    "pytz",
    "PyYAML>=6.0.2,<7 ; python_version>='3.8'",  # changelog at https://github.com/yaml/pyyaml/blob/master/CHANGES
    "requests>=2.32.3,<3 ; python_version>='3.8'",
    "sarge==0.1.7.post1",
    "semantic_version>=2.10.0,<3",
    "sentry-sdk>=2.20.0,<3",
    "setuptools",
    "tornado>=6.4.2,<6.5 ; python_version>='3.8'",
    "watchdog>=4.0.2,<5 ; python_version>='3.8'",  # later versions require Python 3.9+
    "websocket-client>=1.8.0,<1.9 ; python_version>='3.8'",  # breaking changes can happen on patch version increases, changelog incomplete
    "werkzeug>=3.0.6,<3.1 ; python_version>='3.8'",  # later versions require Python 3.9+, breaking changes can happen on minor version increases
    "wrapt>=1.17.2,<1.18 ; python_version>='3.8'",
    "zeroconf>=0.136.2,<0.137 ; python_version>='3.8'",  # later versions require Python 3.9+, breaking changes can happen on minor version increases (despite semantic versioning)
    "zipstream-ng>=1.8.0,<2.0.0",
]
core_deps_37 = [
    "Babel>=2.14.0,<2.15 ; python_version<'3.8'",
    "cachelib>=0.10.2,<0.11 ; python_version<'3.8'",
    "Flask-Babel>=3.1.0,<4 ; python_version<'3.8'",
    "Flask-Limiter>=3.5,<3.6 ; python_version<'3.8'",
    "flask>=2.2.3,<2.3 ; python_version<'3.8'",
    "importlib-metadata>=6.7.0 ; python_version<'3.8'",  # backport of importlib.metadata for python 3.7, later versions require Python 3.8+
    "markdown>=3.4.4,<3.5 ; python_version<'3.8'",
    "pydantic==1.10.16 ; python_version<'3.8'",  # to be kept pinned until https://github.com/pydantic/pydantic/issues/7689 is resolved
    "PyYAML==6.0.1 ; python_version<'3.8'",
    "requests>=2.31,<2.32 ; python_version<'3.8'",
    "tornado>=6.2,<6.3 ; python_version<'3.8'",
    "watchdog>=3.0.0,<4 ; python_version<'3.8'",
    "websocket-client==1.6.1 ; python_version<'3.8'",
    "werkzeug>=2.2.3,<2.3.0 ; python_version<'3.8'",
    "wrapt>=1.16,<1.17 ; python_version<'3.8'",
    "zeroconf>=0.131.0,<0.132 ; python_version<'3.8'",
]
vendored_deps = [
    "blinker>=1.8.0,<1.9.0 ; python_version>='3.8'",  # dependency of flask_principal, later versions require Python 3.9+
    "blinker>=1.6.3,<1.7.0 ; python_version<'3.8'",
    "more-itertools>=10.5.0 ; python_version>='3.8'",  # dependency of class-doc, later versions require Python 3.9+
    "more-itertools>=9.1,<10 ; python_version<'3.8'",
    "regex",  # dependency of awesome-slugify
    "unidecode",  # dependency of awesome-slugify
]
plugin_deps = [
    # "OctoPrint-Setuptools>=1.0.3",  # makes sure plugins can import this on setup.py based install
    "future",  # some plugins might still depend on this but not in their own requirements
    "wheel",  # makes sure plugins can be built as wheels in OctoPrint's venv, see #4682
]

INSTALL_REQUIRES = (
    bundled_plugins + core_deps + core_deps_37 + vendored_deps + plugin_deps
)

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
        "mock>=5.1.0,<6",
        "pytest-doctest-custom>=1.0.0,<2",
        "pytest>=8.3.4,<9 ; python_version>='3.8'",
        "pytest>=7.4.4,<8 ; python_version<'3.8'",
        # formatting, liniting, etc
        "ruff",
        # pre-commit
        "pre-commit",
        # profiler
        "pyinstrument",
    ],
    # Dependencies for developing OctoPrint plugins
    "plugins": ["cookiecutter>=2.6.0,<3"],  # update plugin tutorial when updating this
    # Dependencies for building the documentation
    "docs": [
        "sphinx",
        "sphinxcontrib-httpdomain",
        "sphinxcontrib-mermaid",
        "sphinx_rtd_theme",
        "readthedocs-sphinx-ext",
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


class ScanDepsCommand(setuptools.Command):
    description = "Scan dependencies for updates"
    user_options = []

    PYPI = "https://pypi.org/simple/{package}/"

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        from collections import namedtuple

        import requests
        from packaging.requirements import Requirement
        from packaging.version import parse as parse_version

        Update = namedtuple("Update", ["name", "spec", "current", "latest"])
        update_lower_bounds = []
        update_bounds = []

        all_requires = list(INSTALL_REQUIRES)
        for value in EXTRA_REQUIRES.values():
            all_requires += value

        for r in all_requires:
            requirement = Requirement(r)

            resp = requests.get(
                self.PYPI.format(package=requirement.name),
                headers={"Accept": "application/vnd.pypi.simple.v1+json"},
            )
            resp.raise_for_status()

            def safe_parse_version(version):
                try:
                    return parse_version(version)
                except ValueError:
                    return None

            data = resp.json()
            versions = list(
                filter(
                    lambda x: x and not x.is_prerelease and not x.is_devrelease,
                    (safe_parse_version(x) for x in data.get("versions", [])),
                )
            )
            if not versions:
                continue

            lower = None
            for spec in requirement.specifier._specs:
                if spec.operator == ">=":
                    lower = spec.version
                    break

            latest = versions[-1]

            update = Update(requirement.name, str(requirement), lower, latest)

            if str(latest) not in requirement.specifier:
                update_bounds.append(update)
            elif lower and parse_version(lower) < latest:
                update_lower_bounds.append(update)

        def print_update(update):
            print(
                f"{update.spec}: latest {update.latest}, pypi: https://pypi.org/project/{update.name}/"
            )

        print("")
        print("The following dependencies can get their lower bounds updated:")
        print("")
        for update in update_lower_bounds:
            print_update(update)

        print("")
        print("The following dependencies should get looked at for a full update:")
        print("")
        for update in update_bounds:
            print_update(update)


def get_version_and_cmdclass(pkg_path):
    import os
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("version", os.path.join(pkg_path, "_version.py"))
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    data = module.get_data()
    return data["version"], module.get_cmdclass(pkg_path)


def get_cmdclass(cmdclass):
    # make sure these are always available, even when run by dependabot
    global octoprint_setuptools, md_to_html_build_py_factory

    from setuptools.command.build_py import build_py as _build_py

    if octoprint_setuptools:
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
        cmdclass.get("build_py", _build_py),
    )

    cmdclass["scan_deps"] = ScanDepsCommand

    return cmdclass


def package_data_dirs(source, sub_folders):
    dirs = []

    for d in sub_folders:
        folder = os.path.join(source, d)
        if not os.path.exists(folder):
            continue

        for dirname, _, files in os.walk(folder):
            dirname = os.path.relpath(dirname, source)
            for f in files:
                dirs.append(os.path.join(dirname, f))

    return dirs


if __name__ == "__main__":
    version, cmdclass = get_version_and_cmdclass(os.path.join("src", "octoprint"))
    setuptools.setup(
        name="OctoPrint",
        version=version,
        cmdclass=get_cmdclass(cmdclass),
        description="The snappy web interface for your 3D printer",
        long_description=read_file_contents(os.path.join(here, "README.md")),
        long_description_content_type="text/markdown",
        python_requires=PYTHON_REQUIRES,
        setup_requires=SETUP_REQUIRES,
        install_requires=INSTALL_REQUIRES,
        extras_require=EXTRA_REQUIRES,
        classifiers=[
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
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Programming Language :: Python :: 3.13",
            "Programming Language :: Python :: 3 :: Only",
            "Programming Language :: Python :: Implementation :: CPython",
            "Programming Language :: JavaScript",
            "Topic :: Printing",
        ],
        author="Gina Häußge",
        author_email="gina@octoprint.org",
        url="https://octoprint.org",
        license="GNU Affero General Public License v3",
        keywords="3dprinting 3dprinter 3d-printing 3d-printer octoprint",
        project_urls={
            "Community Forum": "https://community.octoprint.org",
            "Bug Reports": "https://github.com/OctoPrint/OctoPrint/issues",
            "Source": "https://github.com/OctoPrint/OctoPrint",
            "Funding": "https://support.octoprint.org",
        },
        packages=setuptools.find_packages(where="src"),
        package_dir={"": "src"},
        package_data={
            "octoprint": package_data_dirs(
                "src/octoprint", ["static", "templates", "plugins", "translations"]
            )
            + ["util/piptestballoon/setup.py"]
        },
        include_package_data=True,
        zip_safe=False,
        entry_points={"console_scripts": ["octoprint = octoprint:main"]},
    )
