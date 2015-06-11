#!/usr/bin/env python
# coding=utf-8

from setuptools import setup, find_packages
import os
import versioneer

import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "src"))
import octoprint_setuptools

#-----------------------------------------------------------------------------------------------------------------------

# Requirements for our application
INSTALL_REQUIRES = [
	"flask>=0.9,<0.11",
	"werkzeug==0.8.3",
	"tornado==4.0.1",
	"sockjs-tornado>=1.0.0",
	"PyYAML==3.10",
	"Flask-Login==0.2.2",
	"Flask-Principal==0.3.5",
	"Flask-Babel==0.9",
	"Flask-Assets==0.10",
	"pyserial",
	"netaddr",
	"watchdog",
	"sarge>=0.1.4",
	"netifaces",
	"pylru",
	"rsa",
	"pkginfo",
	"requests",
	"semantic_version"
]

# Additional requirements for optional install options
EXTRA_REQUIRES = dict(
	# Dependencies for developing OctoPrint
	develop=[
		# Testing dependencies
		"mock>=1.0.1",
		"nose>=1.3.0",
		"ddt",

		# Documentation dependencies
		"sphinx>=1.3",
		"sphinxcontrib-httpdomain",
		"sphinx_rtd_theme"
	],

	# Dependencies for developing OctoPrint plugins
	plugins=[
		"cookiecutter"
	]
)

# Dependency links for any of the aforementioned dependencies
DEPENDENCY_LINKS = []

# Versioneer configuration
versioneer.VCS = 'git'
versioneer.versionfile_source = 'src/octoprint/_version.py'
versioneer.versionfile_build = 'octoprint/_version.py'
versioneer.tag_prefix = ''
versioneer.parentdir_prefix = ''
versioneer.lookupfile = '.versioneer-lookup'

#-----------------------------------------------------------------------------------------------------------------------
# Anything below here is just command setup and general setup configuration

def get_cmdclass():
	cmdclass = versioneer.get_cmdclass()

	# add clean command
	cmdclass.update(dict(clean=octoprint_setuptools.CleanCommand.for_options(source_folder="src", eggs=["OctoPrint*.egg-info"])))

	# add translation commands
	translation_dir = "translations"
	pot_file = os.path.join(translation_dir, "messages.pot")
	bundled_dir = os.path.join("src", "octoprint", "translations")
	cmdclass.update(octoprint_setuptools.get_babel_commandclasses(pot_file=pot_file, output_dir=translation_dir, pack_name_prefix="OctoPrint-i18n-", pack_path_prefix="", bundled_dir=bundled_dir))

	return cmdclass


def params():
	name = "OctoPrint"
	version = versioneer.get_version()
	cmdclass = get_cmdclass()

	description = "A responsive web interface for 3D printers"
	long_description = open("README.md").read()
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
		"": "src"
	}
	package_data = {
		"octoprint": octoprint_setuptools.package_data_dirs('src/octoprint', ['static', 'templates', 'plugins', 'translations'])
	}

	include_package_data = True
	zip_safe = False
	install_requires = INSTALL_REQUIRES
	extras_require = EXTRA_REQUIRES
	dependency_links = DEPENDENCY_LINKS

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
