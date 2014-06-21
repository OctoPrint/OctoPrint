# coding=utf-8
#!/usr/bin/env python

import versioneer
versioneer.VCS = 'git'
versioneer.versionfile_source = 'src/octoprint/_version.py'
versioneer.versionfile_build = 'octoprint/_version.py'
versioneer.tag_prefix = ''
versioneer.parentdir_prefix = 'octoprint-'

from setuptools import setup, find_packages

VERSION = open("VERSION").read().strip()

def params():
	name = "OctoPrint"
	version = VERSION
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
	package_dir = {"octoprint": "src/octoprint"}

	include_package_data = True
	zip_safe = False
	install_requires = open("requirements.txt").read().split("\n")

	entry_points = {
		"console_scripts": [
			"octoprint = octoprint:main"
		]
	}

	#scripts = {
	#	"scripts/octoprint.init": "/etc/init.d/octoprint"
	#}

	version = versioneer.get_version()
	cmdclass = versioneer.get_cmdclass()

	return locals()

setup(**params())
