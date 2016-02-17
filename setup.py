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

# Requirements for our application
INSTALL_REQUIRES = [
	"flask>=0.9,<0.11",
	"werkzeug>=0.8.3,<0.9",
	"tornado>=4.0.2,<4.1",
	"sockjs-tornado>=1.0.2,<1.1",
	"PyYAML>=3.10,<3.11",
	"Flask-Login>=0.2.2,<0.3",
	"Flask-Principal>=0.3.5,<0.4",
	"Flask-Babel>=0.9,<0.10",
	"Flask-Assets>=0.10,<0.11",
	"Flask-Markdown>=0.3,<0.4",
	"pyserial>=2.7,<2.8",
	"netaddr>=0.7.17,<0.8",
	"watchdog>=0.8.3,<0.9",
	"sarge>=0.1.4,<0.2",
	"netifaces>=0.10,<0.11",
	"pylru>=1.0.9,<1.1",
	"rsa>=3.2,<3.3",
	"pkginfo>=1.2.1,<1.3",
	"requests>=2.7,<2.8",
	"semantic_version>=2.4.2,<2.5",
	"psutil>=3.2.1,<3.3",
	"Click>=5.1,<5.2",
	"awesome-slugify>=1.6.5,<1.7"
]

# Additional requirements for optional install options
EXTRA_REQUIRES = dict(
	# Dependencies for developing OctoPrint
	develop=[
		# Testing dependencies
		"mock>=1.0.1,<1.1",
		"nose>=1.3.0,<1.4",
		"ddt",

		# Documentation dependencies
		"sphinx>=1.3,<1.4",
		"sphinxcontrib-httpdomain",
		"sphinx_rtd_theme",

		# PyPi upload related
		"pypandoc"
	],

	# Dependencies for developing OctoPrint plugins
	plugins=[
		"cookiecutter"
	]
)

# Additional requirements for setup
SETUP_REQUIRES = []

# Dependency links for any of the aforementioned dependencies
DEPENDENCY_LINKS = []

#-----------------------------------------------------------------------------------------------------------------------
# Anything below here is just command setup and general setup configuration

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
			"THIRDPARTYLICENSES.md",
		]
	}, cmdclass["build_py"] if "build_py" in cmdclass else _build_py)

	return cmdclass


def params():
	name = "OctoPrint"
	version = versioneer.get_version()
	cmdclass = get_cmdclass()

	description = "A snappy web interface for 3D printers"
	long_description = open("README.md").read()

	install_requires = INSTALL_REQUIRES
	extras_require = EXTRA_REQUIRES
	dependency_links = DEPENDENCY_LINKS
	setup_requires = SETUP_REQUIRES

	try:
		import pypandoc
		setup_requires += ["setuptools-markdown"]
		long_description_markdown_filename = "README.md"
		del pypandoc
	except:
		pass

	classifiers = [
		"Development Status :: 4 - Beta",
		"Environment :: Web Environment",
		"Framework :: Flask",
		"Intended Audience :: Education",
		"Intended Audience :: End Users/Desktop",
		"Intended Audience :: Manufacturing",
		"Intended Audience :: Science/Research",
		"License :: OSI Approved :: GNU Affero General Public License v3",
		"Natural Language :: English",
		"Operating System :: OS Independent",
		"Programming Language :: Python :: 2.7",
		"Programming Language :: JavaScript",
		"Topic :: Internet :: WWW/HTTP",
		"Topic :: Internet :: WWW/HTTP :: Dynamic Content",
		"Topic :: Internet :: WWW/HTTP :: WSGI",
		"Topic :: Printing",
		"Topic :: System :: Networking :: Monitoring"
	]
	author = "Gina Häußge"
	author_email = "osd@foosel.net"
	url = "http://octoprint.org"
	license = "AGPLv3"

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
