# coding=utf-8
#!/usr/bin/env python

import versioneer
versioneer.VCS = 'git'
versioneer.versionfile_source = 'src/octoprint/_version.py'
versioneer.versionfile_build = 'octoprint/_version.py'
versioneer.tag_prefix = ''
versioneer.parentdir_prefix = ''
versioneer.lookupfile = '.versioneer-lookup'

from setuptools import setup, find_packages, Command
import os
import shutil
import glob

I18N_MAPPING_FILE = "babel.cfg"
I18N_DOMAIN = "messages"
I18N_INPUT_DIRS = "."
I18N_OUTPUT_DIR_PY = os.path.join("src", "octoprint", "translations")
I18N_OUTPUT_DIR_JS = os.path.join("src", "octoprint", "static", "js", "i18n")
I18N_POT_FILE = os.path.join(I18N_OUTPUT_DIR_PY, "messages.pot")

def package_data_dirs(source, sub_folders):
	dirs = []

	for d in sub_folders:
		for dirname, _, files in os.walk(os.path.join(source, d)):
			dirname = os.path.relpath(dirname, source)
			for f in files:
				dirs.append(os.path.join(dirname, f))

	return dirs


def _recursively_handle_files(directory, file_matcher, folder_handler=None, file_handler=None):
	applied_handler = False

	for filename in os.listdir(directory):
		path = os.path.join(directory, filename)

		if file_handler is not None and file_matcher(filename):
			file_handler(path)
			applied_handler = True

		elif os.path.isdir(path):
			sub_applied_handler = _recursively_handle_files(path, file_matcher, folder_handler=folder_handler, file_handler=file_handler)
			if sub_applied_handler:
				applied_handler = True

			if folder_handler is not None:
				folder_handler(path, sub_applied_handler)

	return applied_handler

class CleanCommand(Command):
	description = "clean build artifacts"
	user_options = []
	boolean_options = []

	def initialize_options(self):
		pass

	def finalize_options(self):
		pass

	def run(self):
		# build folder
		if os.path.exists('build'):
			print "Deleting build directory"
			shutil.rmtree('build')

		# eggs
		eggs = glob.glob('OctoPrint*.egg-info')
		for egg in eggs:
			print "Deleting %s directory" % egg
			shutil.rmtree(egg)

		# pyc files
		def delete_folder_if_empty(path, applied_handler):
			if not applied_handler:
				return
			if len(os.listdir(path)) == 0:
				shutil.rmtree(path)
				print "Deleted %s since it was empty" % path

		def delete_file(path):
			os.remove(path)
			print "Deleted %s" % path

		import fnmatch
		_recursively_handle_files(
			os.path.abspath("src"),
			lambda name: fnmatch.fnmatch(name.lower(), "*.pyc"),
			folder_handler=delete_folder_if_empty,
			file_handler=delete_file
		)


class NewTranslation(Command):
	description = "create a new translation"
	user_options = [
		('locale=', 'l', 'locale for the new translation'),
	]
	boolean_options = []

	def __init__(self, dist, **kw):
		from babel.messages import frontend as babel
		self.babel_init_messages = babel.init_catalog(dist)
		Command.__init__(self, dist, **kw)

	def initialize_options(self):
		self.locale = None
		self.babel_init_messages.initialize_options()

	def finalize_options(self):
		self.babel_init_messages.locale = self.locale
		self.babel_init_messages.input_file = I18N_POT_FILE
		self.babel_init_messages.output_dir = I18N_OUTPUT_DIR_PY
		self.babel_init_messages.finalize_options()

	def run(self):
		self.babel_init_messages.run()


class ExtractTranslation(Command):
	description = "extract translations"
	user_options = []
	boolean_options = []

	def __init__(self, dist, **kw):
		from babel.messages import frontend as babel
		self.babel_extract_messages = babel.extract_messages(dist)
		Command.__init__(self, dist, **kw)

	def initialize_options(self):
		self.babel_extract_messages.initialize_options()

	def finalize_options(self):
		self.babel_extract_messages.mapping_file = I18N_MAPPING_FILE
		self.babel_extract_messages.output_file = I18N_POT_FILE
		self.babel_extract_messages.input_dirs = I18N_INPUT_DIRS
		self.babel_extract_messages.msgid_bugs_address = "i18n@octoprint.org"
		self.babel_extract_messages.copyright_holder = "The OctoPrint Project"
		self.babel_extract_messages.finalize_options()

	def run(self):
		self.babel_extract_messages.run()


class RefreshTranslation(Command):
	description = "refresh translations"
	user_options = [
		('locale=', 'l', 'locale for the translation to refresh'),
		]
	boolean_options = []

	def __init__(self, dist, **kw):
		from babel.messages import frontend as babel
		self.babel_extract_messages = babel.extract_messages(dist)
		self.babel_update_messages = babel.update_catalog(dist)
		Command.__init__(self, dist, **kw)

	def initialize_options(self):
		self.locale = None
		self.babel_extract_messages.initialize_options()
		self.babel_update_messages.initialize_options()

	def finalize_options(self):
		self.babel_extract_messages.mapping_file = I18N_MAPPING_FILE
		self.babel_extract_messages.output_file = I18N_POT_FILE
		self.babel_extract_messages.input_dirs = I18N_INPUT_DIRS
		self.babel_extract_messages.msgid_bugs_address = "i18n@octoprint.org"
		self.babel_extract_messages.copyright_holder = "The OctoPrint Project"
		self.babel_extract_messages.finalize_options()

		self.babel_update_messages.input_file = I18N_MAPPING_FILE
		self.babel_update_messages.output_dir = I18N_OUTPUT_DIR_PY
		self.babel_update_messages.locale = self.locale

	def run(self):
		self.babel_extract_messages.run()
		self.babel_update_messages.run()


class CompileTranslation(Command):
	description = "compile translations"
	user_options = []
	boolean_options = []

	def __init__(self, dist, **kw):
		from babel.messages import frontend as babel
		self.babel_compile_messages = babel.compile_catalog(dist)
		Command.__init__(self, dist, **kw)

	def initialize_options(self):
		self.babel_compile_messages.initialize_options()

	def finalize_options(self):
		self.babel_compile_messages.directory = I18N_OUTPUT_DIR_PY

	def run(self):
		self.babel_compile_messages.run()

		import po2json

		for lang_code in os.listdir(I18N_OUTPUT_DIR_PY):
			full_path = os.path.join(I18N_OUTPUT_DIR_PY, lang_code)

			if os.path.isdir(full_path):
				client_po_dir = os.path.join(full_path, "LC_MESSAGES")

				po2json.update_js_file(
					"%s/%s.po" % (client_po_dir, I18N_DOMAIN),
					lang_code,
					I18N_OUTPUT_DIR_JS,
					I18N_DOMAIN
				)


def get_cmdclass():
	cmdclass = versioneer.get_cmdclass()
	cmdclass.update({
		'clean': CleanCommand,
		'babel_new': NewTranslation,
		'babel_extract': ExtractTranslation,
		'babel_refresh': RefreshTranslation,
		'babel_compile': CompileTranslation
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
	package_data = {"octoprint": package_data_dirs('src/octoprint', ['static', 'templates', 'plugins'])}

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
