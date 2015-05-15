# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os
import shutil
import glob

from setuptools import Command


def package_data_dirs(source, sub_folders):
	import os
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


def recursively_handle_files(directory, file_matcher, folder_matcher=None, folder_handler=None, file_handler=None):
	applied_handler = False

	for filename in os.listdir(directory):
		path = os.path.join(directory, filename)

		if file_handler is not None and file_matcher(filename):
			file_handler(path)
			applied_handler = True

		elif os.path.isdir(path) and (folder_matcher is None or folder_matcher(directory, filename, path)):
			sub_applied_handler = recursively_handle_files(path, file_matcher, folder_handler=folder_handler, file_handler=file_handler)
			if sub_applied_handler:
				applied_handler = True

			if folder_handler is not None:
				folder_handler(path, sub_applied_handler)

	return applied_handler


class CleanCommand(Command):
	description = "clean build artifacts"
	user_options = []
	boolean_options = []

	build_folder = "build"
	source_folder = "src"
	eggs = []

	@classmethod
	def for_options(cls, build_folder="build", source_folder="src", eggs=None):
		if eggs is None:
			eggs = []
		return type(cls)(cls.__name__, (cls,), dict(
			build_folder=build_folder,
			source_folder=source_folder,
			eggs=eggs
		))

	def initialize_options(self):
		pass

	def finalize_options(self):
		pass

	def run(self):
		# build folder
		if os.path.exists(self.__class__.build_folder):
			print "Deleting build directory"
			shutil.rmtree(self.__class__.build_folder)

		# eggs
		for egg in self.__class__.eggs:
			globbed_eggs = glob.glob(egg)
			for globbed_egg in globbed_eggs:
				print "Deleting %s directory" % globbed_egg
				shutil.rmtree(globbed_egg)

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
		recursively_handle_files(
			os.path.abspath(self.__class__.source_folder),
			lambda name: fnmatch.fnmatch(name.lower(), "*.pyc"),
			folder_matcher=lambda dir, name, path: name != ".git",
			folder_handler=delete_folder_if_empty,
			file_handler=delete_file
		)


class NewTranslation(Command):
	description = "create a new translation"
	user_options = [
		('locale=', 'l', 'locale for the new translation'),
		]
	boolean_options = []

	pot_file = None
	output_dir = None

	@classmethod
	def for_options(cls, pot_file=None, output_dir=None):
		if pot_file is None:
			raise ValueError("pot_file must not be None")
		if output_dir is None:
			raise ValueError("output_dir must not be None")

		return type(cls)(cls.__name__, (cls,), dict(
			pot_file=pot_file,
			output_dir=output_dir
		))

	def __init__(self, dist, **kw):
		from babel.messages import frontend as babel
		self.babel_init_messages = babel.init_catalog(dist)
		Command.__init__(self, dist, **kw)

	def initialize_options(self):
		self.locale = None
		self.babel_init_messages.initialize_options()

	def finalize_options(self):
		self.babel_init_messages.locale = self.locale
		self.babel_init_messages.input_file = self.__class__.pot_file
		self.babel_init_messages.output_dir = self.__class__.output_dir
		self.babel_init_messages.finalize_options()

	def run(self):
		self.babel_init_messages.run()


class ExtractTranslation(Command):
	description = "extract translations"
	user_options = []
	boolean_options = []

	mail_address = "i18n@octoprint.org"
	copyright_holder = "The OctoPrint Project"
	mapping_file = None
	pot_file = None
	input_dirs = None

	@classmethod
	def for_options(cls, mail_address="i18n@octoprint.org", copyright_holder="The OctoPrint Project", mapping_file=None, pot_file=None, input_dirs=None):
		if mapping_file is None:
			raise ValueError("mapping_file must not be None")
		if pot_file is None:
			raise ValueError("pot_file must not be None")
		if input_dirs is None:
			raise ValueError("input_dirs must not be None")

		return type(cls)(cls.__name__, (cls,), dict(
			mapping_file=mapping_file,
			pot_file=pot_file,
			input_dirs=input_dirs,
			mail_address=mail_address,
			copyright_holder=copyright_holder
		))

	def __init__(self, dist, **kw):
		from babel.messages import frontend as babel
		self.babel_extract_messages = babel.extract_messages(dist)
		Command.__init__(self, dist, **kw)

	def initialize_options(self):
		self.babel_extract_messages.initialize_options()

	def finalize_options(self):
		self.babel_extract_messages.mapping_file = self.__class__.mapping_file
		self.babel_extract_messages.output_file = self.__class__.pot_file
		self.babel_extract_messages.input_dirs = self.__class__.input_dirs
		self.babel_extract_messages.msgid_bugs_address = self.__class__.mail_address
		self.babel_extract_messages.copyright_holder = self.__class__.copyright_holder
		self.babel_extract_messages.finalize_options()

	def run(self):
		self.babel_extract_messages.run()


class RefreshTranslation(Command):
	description = "refresh translations"
	user_options = [
		('locale=', 'l', 'locale for the translation to refresh'),
		]
	boolean_options = []

	mail_address = "i18n@octoprint.org"
	copyright_holder = "The OctoPrint Project"
	mapping_file = None
	pot_file = None
	input_dirs = None
	output_dir = None

	@classmethod
	def for_options(cls, mail_address="i18n@octoprint.org", copyright_holder="The OctoPrint Project", mapping_file=None, pot_file=None, input_dirs=None, output_dir=None):
		if mapping_file is None:
			raise ValueError("mapping_file must not be None")
		if pot_file is None:
			raise ValueError("pot_file must not be None")
		if input_dirs is None:
			raise ValueError("input_dirs must not be None")
		if output_dir is None:
			raise ValueError("output_dir must not be None")

		return type(cls)(cls.__name__, (cls,), dict(
			mapping_file=mapping_file,
			pot_file=pot_file,
			input_dirs=input_dirs,
			mail_address=mail_address,
			copyright_holder=copyright_holder,
			output_dir=output_dir
		))

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
		self.babel_extract_messages.mapping_file = self.__class__.mapping_file
		self.babel_extract_messages.output_file = self.__class__.pot_file
		self.babel_extract_messages.input_dirs = self.__class__.input_dirs
		self.babel_extract_messages.msgid_bugs_address = self.__class__.mail_address
		self.babel_extract_messages.copyright_holder = self.__class__.copyright_holder
		self.babel_extract_messages.finalize_options()

		self.babel_update_messages.input_file = self.__class__.pot_file
		self.babel_update_messages.output_dir = self.__class__.output_dir
		self.babel_update_messages.locale = self.locale

	def run(self):
		self.babel_extract_messages.run()
		self.babel_update_messages.run()


class CompileTranslation(Command):
	description = "compile translations"
	user_options = []
	boolean_options = []

	output_dir = None

	@classmethod
	def for_options(cls, output_dir=None):
		if output_dir is None:
			raise ValueError("output_dir must not be None")

		return type(cls)(cls.__name__, (cls,), dict(
			output_dir=output_dir
		))

	def __init__(self, dist, **kw):
		from babel.messages import frontend as babel
		self.babel_compile_messages = babel.compile_catalog(dist)
		Command.__init__(self, dist, **kw)

	def initialize_options(self):
		self.babel_compile_messages.initialize_options()

	def finalize_options(self):
		self.babel_compile_messages.directory = self.__class__.output_dir

	def run(self):
		self.babel_compile_messages.run()


def get_babel_commandclasses(pot_file=None, mapping_file="babel.cfg", input_dirs=".", output_dir=None, mail_address="i18n@octoprint.org", copyright_holder="The OctoPrint Project"):
	return dict(
		babel_new=NewTranslation.for_options(pot_file=pot_file, output_dir=output_dir),
		babel_extract=ExtractTranslation.for_options(mapping_file=mapping_file, pot_file=pot_file, input_dirs=input_dirs, mail_address=mail_address, copyright_holder=copyright_holder),
		babel_refresh=RefreshTranslation.for_options(mapping_file=mapping_file, pot_file=pot_file, input_dirs=input_dirs, output_dir=output_dir, mail_address=mail_address, copyright_holder=copyright_holder),
		babel_compile=CompileTranslation.for_options(output_dir=output_dir)
	)


def create_plugin_setup_parameters(identifier="todo", name="TODO", version="0.1", description="TODO", author="TODO",
                                   mail="todo@example.com", url="TODO", license="AGPLv3", additional_data=None,
                                   requires=None, extra_requires=None, cmdclass=None, eggs=None):
	import pkg_resources

	package = "octoprint_{identifier}".format(**locals())

	if additional_data is None:
		additional_data = list()

	if requires is None:
		requires = ["OctoPrint"]
	if not isinstance(requires, list):
		raise ValueError("requires must be a list")
	if "OctoPrint" not in requires:
		requires = ["OctoPrint"] + list(requires)

	if extra_requires is None:
		extra_requires = dict()
	if not isinstance(extra_requires, dict):
		raise ValueError("extra_requires must be a dict")

	if cmdclass is None:
		cmdclass = dict()
	if not isinstance(cmdclass, dict):
		raise ValueError("cmdclass must be a dict")

	if eggs is None:
		eggs = []
	if not isinstance(eggs, list):
		raise ValueError("eggs must be a list")

	egg = "{name}*.egg-info".format(name=pkg_resources.to_filename(pkg_resources.safe_name(name)))
	if egg not in eggs:
		eggs = [egg] + eggs

	cmdclass.update(dict(
		clean=CleanCommand.for_options(source_folder=package, eggs=eggs)
	))

	translation_dir = os.path.join(package, "translations")
	pot_file = os.path.join(translation_dir, "messages.pot")
	if os.path.isdir(translation_dir) and os.path.isfile(pot_file):
		cmdclass.update(get_babel_commandclasses(pot_file=pot_file, output_dir=translation_dir))

	return dict(
		name=name,
		version=version,
		description=description,
		author=author,
		author_email=mail,
		url=url,
		license=license,

		# adding new commands
		cmdclass=cmdclass,

		# we only have our plugin package to install
		packages=[package],

		# we might have additional data files in sub folders that need to be installed too
		package_data={package: package_data_dirs(package, ["static", "templates", "translations"] + additional_data)},
		include_package_data=True,

		# If you have any package data that needs to be accessible on the file system, such as templates or static assets
		# this plugin is not zip_safe.
		zip_safe=False,

		install_requires=requires,
		extras_require=extra_requires,

		# Hook the plugin into the "octoprint.plugin" entry point, mapping the plugin_identifier to the plugin_package.
		# That way OctoPrint will be able to find the plugin and load it.
		entry_points={
			"octoprint.plugin": ["{identifier} = {package}".format(**locals())]
		}
	)
