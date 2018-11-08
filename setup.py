#!/usr/bin/env python2
# coding=utf-8

from setuptools import setup, find_packages
from distutils.command.build_py import build_py as _build_py
import os
import versioneer

import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "src"))
import octoprint_setuptools

#-----------------------------------------------------------------------------------------------------------------------

# Supported python versions
PYTHON_REQUIRES = ">=2.7.3,<3" # TODO change to >=2.7.9,<3 in 1.3.11

# Requirements for our application
INSTALL_REQUIRES = [
	"flask>=0.10.1,<0.11",
	"Jinja2>=2.8.1,<2.9", # Jinja 2.9 has breaking changes WRT template scope - we can't
	                      # guarantee backwards compatibility for plugins and such with that
	                      # version, hence we need to pin to a lower version for now. See #1697
	"regex!=2018.11.6", # avoid broken 2018.11.6. See #2874
	"werkzeug>=0.8.3,<0.9",
	"tornado==4.5.3",
	#"sockjs-tornado>=1.0.3,<1.1", # current version is incompatible to tornado 5, we use a
	                               # vendored one
	"PyYAML>=3.10,<3.11",
	"Flask-Login>=0.2.11,<0.3",
	"Flask-Principal>=0.3.5,<0.4",
	"Flask-Babel>=0.9,<0.10",
	"Flask-Assets>=0.10,<0.11",
	"markdown>=2.6.9,<2.7",
	"pyserial>=3.4,<3.5",
	"netaddr>=0.7.19,<0.8",
	"watchdog>=0.8.3,<0.9",
	"sarge==0.1.5post0",
	"netifaces>=0.10.6,<0.11",
	"pylru>=1.0.9,<1.1",
	"rsa>=3.2.3,<3.3",
	"pkginfo>=1.4.2,<1.5",
	"requests>=2.18.4,<3",
	"semantic_version>=2.4.2,<2.5",
	"psutil>=5.4.6,<5.5",
	"Click>=6.2,<6.3",
	"awesome-slugify>=1.6.5,<1.7",
	"feedparser>=5.2.1,<5.3",
	"chainmap>=1.0.2,<1.1",
	"future>=0.15.2,<0.16",
	"scandir>=1.3,<1.4",
	"websocket-client>=0.40.0,<0.41",
	"python-dateutil>=2.6.1,<2.7",
	"wrapt>=1.10.11,<1.11",
	"futures>=3.1.1,<3.2",
	"emoji>=0.4.5,<0.5",
	"monotonic>=1.3,<1.4",
	"frozendict>=1.2,<1.3"
]

if sys.platform == "darwin":
	INSTALL_REQUIRES.append("appdirs>=1.4.0")

# Additional requirements for optional install options
EXTRA_REQUIRES = dict(
	# Dependencies for developing OctoPrint
	develop=[
		# Testing dependencies
		"mock>=2.0.0,<3",
		"nose>=1.3.0,<1.4",
		"ddt",

		# Documentation dependencies
		"sphinx>=1.6,<1.7",
		"sphinxcontrib-httpdomain",
		"sphinxcontrib-mermaid>=0.3",
		"sphinx_rtd_theme",
	],

	# Dependencies for developing OctoPrint plugins
	plugins=[
		"cookiecutter>=1.4,<1.7"
	]
)

# Dependency links for any of the aforementioned dependencies
DEPENDENCY_LINKS = []

#-----------------------------------------------------------------------------------------------------------------------
# Anything below here is just command setup and general setup configuration

here = os.path.abspath(os.path.dirname(__file__))

def read_file_contents(path):
	import codecs
	with codecs.open(path, encoding="utf-8") as f:
		return f.read()

def data_copy_build_py_factory(files, baseclass):
	class data_copy_build_py(baseclass):
		files = dict()

		def run(self):
			import shutil
			if not self.dry_run:
				for directory, files in self.__class__.files.items():
					target_dir = os.path.join(self.build_lib, directory)
					self.mkpath(target_dir)

					for entry in files:
						if isinstance(entry, tuple):
							if len(entry) != 2:
								continue
							source, dest = entry
						else:
							source = dest = entry
						shutil.copy(source, os.path.join(target_dir, dest))

			baseclass.run(self)

	return type(data_copy_build_py)(data_copy_build_py.__name__,
	                                (data_copy_build_py,),
	                                dict(files=files))

def get_cmdclass():
	cmdclass = versioneer.get_cmdclass()

	# add clean command
	cmdclass.update(dict(clean=octoprint_setuptools.CleanCommand.for_options(source_folder="src", eggs=["OctoPrint*.egg-info"])))

	# add translation commands
	translation_dir = "translations"
	pot_file = os.path.join(translation_dir, "messages.pot")
	bundled_dir = os.path.join("src", "octoprint", "translations")
	cmdclass.update(octoprint_setuptools.get_babel_commandclasses(pot_file=pot_file, output_dir=translation_dir, pack_name_prefix="OctoPrint-i18n-", pack_path_prefix="", bundled_dir=bundled_dir))

	cmdclass["build_py"] = data_copy_build_py_factory({
		"octoprint/templates/_data": [
			"AUTHORS.md",
			"CHANGELOG.md",
			"SUPPORTERS.md",
			"THIRDPARTYLICENSES.md",
		]
	}, cmdclass["build_py"] if "build_py" in cmdclass else _build_py)

	return cmdclass


def params():
	name = "OctoPrint"
	version = versioneer.get_version()
	cmdclass = get_cmdclass()

	description = "The snappy web interface for your 3D printer"
	long_description = read_file_contents(os.path.join(here, "README.md"))
	long_description_content_type = "text/markdown"

	python_requires = PYTHON_REQUIRES
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
		"Programming Language :: Python :: 2",
		"Programming Language :: Python :: 2.7",
		"Programming Language :: Python :: Implementation :: CPython",
		"Programming Language :: JavaScript",
		"Topic :: Printing",
		"Topic :: System :: Monitoring"
	]
	author = "Gina Häußge"
	author_email = "gina@octoprint.org"
	url = "https://octoprint.org"
	license = "GNU Affero General Public License v3"
	keywords = "3dprinting 3dprinter 3d-printing 3d-printer octoprint"

	project_urls={
		"Community Forum": "https://discourse.octoprint.org",
		"Bug Reports": "https://github.com/foosel/OctoPrint/issues",
		"Source": "https://github.com/foosel/OctoPrint",
		"Funding": "https://donate.octoprint.org"
	}

	packages = find_packages(where="src")
	package_dir = {
		"": "src",
	}
	package_data = {
		"octoprint": octoprint_setuptools.package_data_dirs('src/octoprint',
		                                                    ['static', 'templates', 'plugins', 'translations'])
		             + ['util/piptestballoon/setup.py']
	}

	include_package_data = True
	zip_safe = False

	if os.environ.get('READTHEDOCS', None) == 'True':
		# we can't tell read the docs to please perform a pip install -e .[develop], so we help
		# it a bit here by explicitly adding the development dependencies, which include our
		# documentation dependencies
		install_requires = install_requires + extras_require['develop']

	entry_points = {
		"console_scripts": [
			"octoprint = octoprint:main"
		]
	}

	return locals()

setup(**params())
