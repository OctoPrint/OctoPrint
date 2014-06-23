# coding=utf-8
#!/usr/bin/env python

import versioneer
versioneer.VCS = 'git'
versioneer.versionfile_source = 'src/octoprint/_version.py'
versioneer.versionfile_build = 'octoprint/_version.py'
versioneer.tag_prefix = ''
versioneer.parentdir_prefix = ''

from setuptools import setup, find_packages, Command
import os
import shutil
import glob


def package_data_dirs(source, sub_folders):
	dirs = []

	for d in sub_folders:
		for dirname, _, files in os.walk(os.path.join(source, d)):
			dirname = os.path.relpath(dirname, source)
			for f in files:
				dirs.append(os.path.join(dirname, f))

	return dirs


class CleanCommand(Command):
	description = "clean build artifacts"
	user_options = []
	boolean_options = []

	def initialize_options(self):
		pass

	def finalize_options(self):
		pass

	def run(self):
		if os.path.exists('build'):
			print "Deleting build directory"
			shutil.rmtree('build')
		eggs = glob.glob('OctoPrint*.egg-info')
		for egg in eggs:
			print "Deleting %s directory" % egg
			shutil.rmtree(egg)


def get_cmdclass():
	cmdclass = versioneer.get_cmdclass()
	cmdclass.update({
		'clean': CleanCommand
	})
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
	package_dir = {"octoprint": "src/octoprint"}
	package_data = {"octoprint": package_data_dirs('src/octoprint', ['static', 'templates'])}

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

	return locals()

setup(**params())
