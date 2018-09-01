# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import octoprint.plugin

from octoprint.settings import default_settings
from octoprint.plugin.core import FolderOrigin
from octoprint.server import admin_permission, NO_CONTENT
from octoprint.server.util.flask import restricted_access
from octoprint.util import is_hidden_path
from octoprint.util.version import get_octoprint_version_string, get_octoprint_version, get_comparable_version
from octoprint.util.pip import LocalPipCaller

try:
	from os import scandir
except ImportError:
	from scandir import scandir

try:
	import zlib # check if zlib is available
except ImportError:
	zlib = None


from flask_babel import gettext

import codecs
import flask
import logging
import os
import requests
import sarge
import shutil
import tempfile
import threading
import time
import zipfile
import json
import sys
import traceback


UNKNOWN_PLUGINS_FILE = "unknown_plugins_from_restore.json"


class BackupPlugin(octoprint.plugin.SettingsPlugin,
                   octoprint.plugin.TemplatePlugin,
                   octoprint.plugin.AssetPlugin,
                   octoprint.plugin.BlueprintPlugin,
                   octoprint.plugin.StartupPlugin):

	_pip_caller = None

	# noinspection PyMissingConstructor
	def __init__(self):
		self._in_progress = []
		self._in_progress_lock = threading.RLock()

	##~~ StarupPlugin

	def on_after_startup(self):
		self._clean_dir_backup(self._settings._basedir,
		                       on_log_progress=self._logger.info)

	##~~ AssetPlugin

	def get_assets(self):
		return dict(js=["js/backup.js"],
		            css=["css/backup.css"],
		            less=["less/backup.less"])

	##~~ BlueprintPlugin

	@octoprint.plugin.BlueprintPlugin.route("/", methods=["GET"])
	@admin_permission.require(403)
	@restricted_access
	def get_state(self):
		backups = self._get_backups()
		unknown_plugins = self._get_unknown_plugins()
		return flask.jsonify(backups=backups,
		                     backup_in_progress=len(self._in_progress) > 0,
		                     unknown_plugins=unknown_plugins)

	@octoprint.plugin.BlueprintPlugin.route("/unknown_plugins", methods=["GET"])
	@admin_permission.require(403)
	@restricted_access
	def get_unknown_plugins(self):
		# TODO add caching
		unknown_plugins = self._get_unknown_plugins()
		return flask.jsonify(unknown_plugins=unknown_plugins)

	@octoprint.plugin.BlueprintPlugin.route("/unknown_plugins", methods=["DELETE"])
	@admin_permission.require(403)
	@restricted_access
	def delete_unknown_plugins(self):
		data_file = os.path.join(self.get_plugin_data_folder(), UNKNOWN_PLUGINS_FILE)
		try:
			os.remove(data_file)
		except:
			pass
		return NO_CONTENT

	@octoprint.plugin.BlueprintPlugin.route("/backup", methods=["GET"])
	@admin_permission.require(403)
	@restricted_access
	def get_backups(self):
		backups = self._get_backups()
		return flask.jsonify(backups=backups)

	@octoprint.plugin.BlueprintPlugin.route("/backup", methods=["POST"])
	@admin_permission.require(403)
	@restricted_access
	def create_backup(self):
		backup_file = "backup-{}.zip".format(time.strftime("%Y%m%d-%H%M%S"))

		data = flask.request.json
		exclude = data.get("exclude", [])

		def on_backup_start(name, temporary_path, exclude):
			self._logger.info(u"Creating backup zip at {} (excluded: {})...".format(temporary_path,
			                                                                        u",".join(exclude) if len(exclude) else "-"))

			with self._in_progress_lock:
				self._in_progress.append(name)
				self._send_client_message("backup_started", payload=dict(name=name))

		def on_backup_done(name, final_path, exclude):
			with self._in_progress_lock:
				self._in_progress.remove(name)
				self._send_client_message("backup_done", payload=dict(name=name))

			self._logger.info(u"... done creating backup zip.")


		thread = threading.Thread(target=self._create_backup,
		                          args=(backup_file,),
		                          kwargs=dict(exclude=exclude,
		                                      settings=self._settings,
		                                      plugin_manager=self._plugin_manager,
		                                      datafolder=self.get_plugin_data_folder(),
		                                      on_backup_start=on_backup_start,
		                                      on_backup_done=on_backup_done))
		thread.daemon = True
		thread.start()

		response = flask.jsonify(started=True,
		                         name=backup_file)
		response.status_code = 201
		return response

	@octoprint.plugin.BlueprintPlugin.route("/backup/<filename>", methods=["DELETE"])
	@admin_permission.require(403)
	@restricted_access
	def delete_backup(self, filename):
		backup_folder = self.get_plugin_data_folder()
		full_path = os.path.realpath(os.path.join(backup_folder, filename))
		if full_path.startswith(backup_folder) \
			and os.path.exists(full_path) \
			and not is_hidden_path(full_path):
			try:
				os.remove(full_path)
			except:
				self._logger.exception(u"Could not delete {}".format(filename))
				raise
		return NO_CONTENT

	@octoprint.plugin.BlueprintPlugin.route("/restore", methods=["POST"])
	@admin_permission.require(403)
	@restricted_access
	def perform_restore(self):
		input_name = "file"
		input_upload_path = input_name + "." + self._settings.global_get(["server", "uploads", "pathSuffix"])

		if input_upload_path in flask.request.values:
			# file to restore was uploaded
			path = flask.request.values[input_upload_path]

		elif flask.request.json and "path" in flask.request.json:
			# existing backup is supposed to be restored
			backup_folder = self.get_plugin_data_folder()
			path = os.path.realpath(os.path.join(backup_folder, flask.request.json["path"]))
			if not path.startswith(backup_folder) \
				or not os.path.exists(path) \
				or is_hidden_path(path):
				return flask.abort(404)

		else:
			return flask.make_response(u"Invalid request, neither a file nor a path of a file to restore provided", 400)

		def on_install_plugins(plugins):
			force_user = self._settings.global_get_boolean(["plugins", "pluginmanager", "pip_force_user"])
			pip_args = self._settings.global_get(["plugins", "pluginmanager", "pip_args"])

			def on_log(line):
				self._logger.info(line)
				self._send_client_message("logline", dict(line=line, type="stdout"))

			for plugin in plugins:
				octoprint_compatible = plugin["compatibility"]["octoprint"]
				os_compatible = plugin["compatibility"]["os"]
				compatible = octoprint_compatible and os_compatible
				if not compatible:
					if not octoprint_compatible and not os_compatible:
						self._logger.warn(u"Cannot install plugin {}, it is incompatible to this version "
						                  u"of OctoPrint and the underlying operating system".format(plugin["id"]))
					elif not octoprint_compatible:
						self._logger.warn(u"Cannot install plugin {}, it is incompatible to this version "
						                  u"of OctoPrint".format(plugin["id"]))
					elif not os_compatible:
						self._logger.warn(u"Cannot install plugin {}, it is incompatible to the underlying "
						                  u"operating system".format(plugin["id"]))
					self._send_client_message("plugin_incompatible", dict(plugin=plugin["id"],
					                                                      octoprint_compatible=octoprint_compatible,
					                                                      os_compatible=os_compatible))
					continue

				self._logger.info(u"Installing plugin {}".format(plugin["id"]))
				self._send_client_message("installing_plugin", dict(plugin=plugin["id"]))
				self.__class__._install_plugin(plugin,
				                               force_user=force_user,
				                               pip_args=pip_args,
				                               on_log=on_log)

		def on_report_unknown_plugins(plugins):
			self._send_client_message("unknown_plugins", payload=dict(plugins=plugins))

		def on_log_progress(line):
			self._logger.info(line)
			self._send_client_message("logline", payload=dict(line=line, stream="stdout"))

		def on_log_error(line, exc_info=None):
			self._logger.error(line, exc_info=exc_info)
			self._send_client_message("logline", payload=dict(line=line, stream="stderr"))

			if exc_info is not None:
				exc_type, exc_value, exc_tb = exc_info
				output = traceback.format_exception(exc_type, exc_value, exc_tb)
				for line in output:
					self._send_client_message("logline", payload=dict(line=line.rstrip(), stream="stderr"))

		def on_restore_start(path):
			self._send_client_message("restore_started")

		def on_restore_done(path):
			self._send_client_message("restore_done")

		def on_restore_failed(path):
			self._send_client_message("restore_failed")

		archive = tempfile.NamedTemporaryFile(delete=False)
		archive.close()
		shutil.copy(path, archive.name)
		path = archive.name

		# noinspection PyTypeChecker
		thread = threading.Thread(target=self._restore_backup,
		                          args=(path,),
		                          kwargs=dict(settings=self._settings,
		                                      plugin_manager=self._plugin_manager,
		                                      datafolder=self.get_plugin_data_folder(),
		                                      on_install_plugins=on_install_plugins,
		                                      on_report_unknown_plugins=on_report_unknown_plugins,
		                                      on_log_progress=on_log_progress,
		                                      on_log_error=on_log_error,
		                                      on_restore_start=on_restore_start,
		                                      on_restore_done=on_restore_done,
		                                      on_restore_failed=on_restore_failed))
		thread.daemon = True
		thread.start()

		return flask.jsonify(started=True)

	##~~ tornado hook

	def route_hook(self, *args, **kwargs):
		from octoprint.server.util.tornado import LargeResponseHandler, path_validation_factory
		from octoprint.util import is_hidden_path
		from octoprint.server import app
		from octoprint.server.util.tornado import access_validation_factory
		from octoprint.server.util.flask import admin_validator

		return [
			(r"/download/(.*)", LargeResponseHandler, dict(path=self.get_plugin_data_folder(),
			                                               as_attachment=True,
			                                               path_validation=path_validation_factory(lambda path: not is_hidden_path(path),
			                                                                                       status_code=404),
			                                               access_validation=access_validation_factory(app, admin_validator)))
		]

	def bodysize_hook(self, current_max_body_sizes, *args, **kwargs):
		# max upload size of 1GB for the restore endpoint
		return [("POST", r"/restore", 1024 * 1024 * 1024)]

	##~~ CLI hook

	def cli_commands_hook(self, cli_group, pass_octoprint_ctx, *args, **kwargs):
		import click

		@click.command("backup")
		@click.option("--exclude", multiple=True)
		def backup_command(exclude):
			backup_file = "backup-{}.zip".format(time.strftime("%Y%m%d-%H%M%S"))
			settings = octoprint.plugin.plugin_settings_for_settings_plugin("backup", self, settings=cli_group.settings)

			datafolder = os.path.join(settings.getBaseFolder("data"), "backup")
			if not os.path.isdir(datafolder):
				os.makedirs(datafolder)

			self._create_backup(backup_file,
			                    exclude=exclude,
			                    settings=settings,
			                    plugin_manager=cli_group.plugin_manager,
			                    datafolder=datafolder)
			click.echo("Created {}".format(backup_file))

		@click.command("restore")
		@click.argument("path")
		def restore_command(path):
			settings = octoprint.plugin.plugin_settings_for_settings_plugin("backup", self, settings=cli_group.settings)
			plugin_manager = cli_group.plugin_manager

			datafolder = os.path.join(settings.getBaseFolder("data"), "backup")
			if not os.path.isdir(datafolder):
				os.makedirs(datafolder)

			# register plugin manager plugin setting overlays
			plugin_info = plugin_manager.get_plugin_info("pluginmanager")
			if plugin_info and plugin_info.implementation:
				default_settings_overlay = dict(plugins=dict())
				default_settings_overlay["plugins"]["pluginmanager"] = plugin_info.implementation.get_settings_defaults()
				settings.add_overlay(default_settings_overlay, at_end=True)

			if not os.path.isabs(path):
				datafolder = os.path.join(settings.getBaseFolder("data"), "backup")
				if not os.path.isdir(datafolder):
					os.makedirs(datafolder)
				path = os.path.join(datafolder, path)

			if not os.path.exists(path):
				click.echo(u"Backup {} does not exist".format(path), err=True)
				sys.exit(-1)

			archive = tempfile.NamedTemporaryFile(delete=False)
			archive.close()
			shutil.copy(path, archive.name)
			path = archive.name

			def on_install_plugins(plugins):
				if not plugins:
					return

				force_user = settings.global_get_boolean(["plugins", "pluginmanager", "pip_force_user"])
				pip_args = settings.global_get(["plugins", "pluginmanager", "pip_args"])

				def log(line):
					click.echo(u"\t{}".format(line))

				for plugin in plugins:
					octoprint_compatible = plugin["compatibility"]["octoprint"]
					os_compatible = plugin["compatibility"]["os"]
					compatible = octoprint_compatible and os_compatible
					if not compatible:
						if not octoprint_compatible and not os_compatible:
							click.echo(u"Cannot install plugin {}, it is incompatible to this version of "
							           u"OctoPrint and the underlying operating system".format(plugin["id"]))
						elif not octoprint_compatible:
							click.echo(u"Cannot install plugin {}, it is incompatible to this version of "
							           u"OctoPrint".format(plugin["id"]))
						elif not os_compatible:
							click.echo(u"Cannot install plugin {}, it is incompatible to the underlying "
							           u"operating system".format(plugin["id"]))
						continue

					click.echo(u"Installing plugin {}".format(plugin["id"]))
					self.__class__._install_plugin(plugin,
					                               force_user=force_user,
					                               pip_args=pip_args,
					                               on_log=log)

			def on_report_unknown_plugins(plugins):
				if not plugins:
					return

				click.echo(u"The following plugins were not found in the plugin repository. You'll need to install them manually.")
				for plugin in plugins:
					click.echo(u"\t{} (Homepage: {})".format(plugin["name"], plugin["url"] if plugin["url"] else "?"))

			def on_log_progress(line):
				click.echo(line)

			def on_log_error(line, exc_info=None):
				click.echo(line, err=True)

				if exc_info is not None:
					exc_type, exc_value, exc_tb = exc_info
					output = traceback.format_exception(exc_type, exc_value, exc_tb)
					for line in output:
						click.echo(line.rstrip(), err=True)

			if self._restore_backup(path,
			                        settings=settings,
			                        plugin_manager=plugin_manager,
			                        datafolder=datafolder,
			                        on_install_plugins=on_install_plugins,
			                        on_report_unknown_plugins=on_report_unknown_plugins,
			                        on_log_progress=on_log_progress,
			                        on_log_error=on_log_error):
				click.echo(u"Restored from {}".format(path))
			else:
				click.echo(u"Restoring from {} failed".format(path), err=True)

		return [backup_command, restore_command]

	##~~ helpers

	def _get_backups(self):
		backups = []
		for entry in scandir(self.get_plugin_data_folder()):
			if is_hidden_path(entry.path):
				continue
			if not entry.is_file():
				continue
			if not entry.name.endswith(".zip"):
				continue

			backups.append(dict(name=entry.name,
			                    date=entry.stat().st_mtime,
			                    size=entry.stat().st_size,
			                    url=flask.url_for("index") + "plugin/backup/download/" + entry.name))
		return backups

	def _get_unknown_plugins(self):
		data_file = os.path.join(self.get_plugin_data_folder(), UNKNOWN_PLUGINS_FILE)
		if os.path.exists(data_file):
			try:
				with codecs.open(data_file, mode="r", encoding="utf-8") as f:
					unknown_plugins = json.load(f)

				assert isinstance(unknown_plugins, list)
				assert all(map(lambda x: isinstance(x, dict) and "key" in x and "name" in x and "url" in x, unknown_plugins))

				installed_plugins = self._plugin_manager.plugins
				unknown_plugins = filter(lambda x: x["key"] not in installed_plugins, unknown_plugins)
				if not unknown_plugins:
					# no plugins left uninstalled, delete data file
					try:
						os.remove(data_file)
					except:
						self._logger.exception(u"Error while deleting list of unknown plugins at {}".format(data_file))

				return unknown_plugins
			except:
				self._logger.exception(u"Error while reading list of unknown plugins from {}".format(data_file))
				try:
					os.remove(data_file)
				except:
					self._logger.exception(u"Error while deleting list of unknown plugins at {}".format(data_file))

		return []

	@classmethod
	def _clean_dir_backup(cls, basedir,
	                      on_log_progress=None):
		basedir_backup = basedir + ".bck"

		if os.path.exists(basedir_backup):
			def remove_bck():
				if callable(on_log_progress):
					on_log_progress(u"Found config folder backup from prior restore, deleting it...")
				shutil.rmtree(basedir_backup)
				if callable(on_log_progress):
					on_log_progress(u"... deleted.")

			thread = threading.Thread(target=remove_bck)
			thread.daemon = True
			thread.start()

	@classmethod
	def _get_disk_size(cls, path):
		total = 0
		for entry in scandir(path):
			if entry.is_dir():
				total += cls._get_disk_size(entry.path)
			elif entry.is_file():
				total += entry.stat().st_size
		return total

	@classmethod
	def _free_space(cls, path, size):
		from psutil import disk_usage
		return disk_usage(path).free > size

	@classmethod
	def _get_plugin_repository_data(cls, url, logger=None):
		if logger is None:
			logger = logging.getLogger(__name__)

		try:
			r = requests.get(url, timeout=30)
			r.raise_for_status()
		except:
			logger.exception(u"Error while fetching the plugin repository data from {}".format(url))
			return dict()

		from octoprint.plugins.pluginmanager import map_repository_entry
		return dict((plugin["id"], plugin) for plugin in map(map_repository_entry, r.json()))

	@classmethod
	def _install_plugin(cls, plugin, force_user=False, pip_args=None, on_log=None):
		if pip_args is None:
			pip_args = []

		if on_log is None:
			on_log = logging.getLogger(__name__).info

		# prepare pip caller
		def log(prefix, *lines):
			for line in lines:
				on_log(u"{} {}".format(prefix, line.rstrip()))

		def log_call(*lines):
			log(u">", *lines)

		def log_stdout(*lines):
			log(u"<", *lines)

		def log_stderr(*lines):
			log(u"!", *lines)

		if cls._pip_caller is None:
			cls._pip_caller = LocalPipCaller(force_user=force_user)

		cls._pip_caller.on_log_call = log_call
		cls._pip_caller.on_log_stdout = log_stdout
		cls._pip_caller.on_log_stderr = log_stderr

		# install plugin
		pip = ["install", sarge.shell_quote(plugin["archive"]), '--no-cache-dir']

		if plugin.get("follow_dependency_links"):
			pip.append("--process-dependency-links")

		if force_user:
			pip.append("--user")

		if pip_args:
			pip += pip_args

		cls._pip_caller.execute(*pip)

	@classmethod
	def _create_backup(cls, name,
	                   exclude=None,
	                   settings=None,
	                   plugin_manager=None,
	                   datafolder=None,
	                   on_backup_start=None,
	                   on_backup_done=None):
		if exclude is None:
			exclude = []

		configfile = settings._configfile
		basedir = settings._basedir

		temporary_path = os.path.join(datafolder, ".{}".format(name))
		final_path = os.path.join(datafolder, name)

		size = cls._get_disk_size(basedir)
		if not cls._free_space(os.path.dirname(temporary_path), size):
			raise InsufficientSpace()

		own_folder = datafolder
		defaults = [os.path.join(basedir, "config.yaml"),] + \
		           [os.path.join(basedir, folder) for folder in default_settings["folder"].keys()]

		compression = zipfile.ZIP_DEFLATED if zlib else zipfile.ZIP_STORED

		if callable(on_backup_start):
			on_backup_start(name, temporary_path, exclude)

		with zipfile.ZipFile(temporary_path, "w", compression) as zip:
			def add_to_zip(source, target, ignored=None):
				if ignored is None:
					ignored = []

				if source in ignored:
					return

				if os.path.isdir(source):
					for entry in scandir(source):
						add_to_zip(entry.path, os.path.join(target, entry.name), ignored=ignored)
				elif os.path.isfile(source):
					zip.write(source, arcname=target)

			# add metadata
			metadata = dict(version=get_octoprint_version_string(),
			                excludes=exclude)
			zip.writestr("metadata.json", json.dumps(metadata))

			# backup current config file
			add_to_zip(configfile, "basedir/config.yaml", ignored=[own_folder,])

			# backup configured folder paths
			for folder in default_settings["folder"].keys():
				if folder in exclude:
					continue
				add_to_zip(settings.global_get_basefolder(folder),
				           "basedir/" + folder.replace("_", "/"),
				           ignored=[own_folder,])

			# backup anything else that might be lying around in our basedir
			add_to_zip(basedir, "basedir", ignored=defaults + [own_folder, ])

			# add list of installed plugins
			plugins = []
			plugin_folder = settings.global_get_basefolder("plugins")
			for key, plugin in plugin_manager.plugins.items():
				if plugin.bundled or (isinstance(plugin.origin, FolderOrigin) and plugin.origin.folder == plugin_folder):
					# ignore anything bundled or from the plugins folder we already include in the backup
					continue

				plugins.append(dict(key=plugin.key,
				                    name=plugin.name,
				                    url=plugin.url))

			if len(plugins):
				zip.writestr("plugin_list.json", json.dumps(plugins))

		os.rename(temporary_path, final_path)

		if callable(on_backup_done):
			on_backup_done(name, final_path, exclude)

	@classmethod
	def _restore_backup(cls, path,
	                    settings=None,
	                    plugin_manager=None,
	                    datafolder=None,
	                    on_install_plugins=None,
	                    on_report_unknown_plugins=None,
	                    on_invalid_backup=None,
	                    on_log_progress=None,
	                    on_log_error=None,
	                    on_restore_start=None,
	                    on_restore_done=None,
	                    on_restore_failed=None):
		restart_command = settings.global_get(["server", "commands", "serverRestartCommand"])

		basedir = settings._basedir
		cls._clean_dir_backup(basedir,
		                       on_log_progress=on_log_progress)

		plugin_repo = dict()
		repo_url = settings.global_get(["plugins", "pluginmanager", "repository"])
		if repo_url:
			plugin_repo = cls._get_plugin_repository_data(repo_url)

		if callable(on_restore_start):
			on_restore_start(path)

		try:

			with zipfile.ZipFile(path, "r") as zip:
				# read metadata
				try:
					metadata_zipinfo = zip.getinfo("metadata.json")
				except KeyError:
					if callable(on_invalid_backup):
						on_invalid_backup(u"Not an OctoPrint backup, lacks metadata.json")
					return False

				metadata_bytes = zip.read(metadata_zipinfo)
				metadata = json.loads(metadata_bytes)

				backup_version = get_comparable_version(metadata["version"])
				if backup_version > get_octoprint_version():
					if callable(on_invalid_backup):
						on_invalid_backup(u"Backup is from a newer version of OctoPrint and cannot be applied")
					return False

				# unzip to temporary folder
				temp = tempfile.mkdtemp()
				try:
					if callable(on_log_progress):
						on_log_progress(u"Unpacking backup to {}...".format(temp))
					abstemp = os.path.abspath(temp)
					for member in zip.infolist():
						abspath = os.path.abspath(os.path.join(temp, member.filename))
						if abspath.startswith(abstemp):
							zip.extract(member, temp)

					# sanity check
					configfile = os.path.join(temp, "basedir", "config.yaml")
					if not os.path.exists(configfile):
						if callable(on_invalid_backup):
							on_invalid_backup(u"Backup lacks config.yaml")
						return False

					import yaml

					with codecs.open(configfile) as f:
						configdata = yaml.safe_load(f)

					if configdata.get("accessControl", dict()).get("enabled", True):
						userfile = os.path.join(temp, "basedir", "users.yaml")
						if not os.path.exists(userfile):
							if callable(on_invalid_backup):
								on_invalid_backup(u"Backup lacks users.yaml")
							return False

					if callable(on_log_progress):
						on_log_progress(u"Unpacked")

					# install available plugins
					with codecs.open(os.path.join(temp, "plugin_list.json"), "r") as f:
						plugins = json.load(f)

					known_plugins = []
					unknown_plugins = []
					if plugins:
						if plugin_repo:
							for plugin in plugins:
								if plugin["key"] in plugin_manager.plugins:
									# already installed
									continue

								if plugin["key"] in plugin_repo:
									# not installed, can be installed from repository url
									known_plugins.append(plugin_repo[plugin["key"]])
								else:
									# not installed, not installable
									unknown_plugins.append(plugin)

						else:
							# no repo, all plugins are not installable
							unknown_plugins = plugins

						if callable(on_log_progress):
							if known_plugins:
								on_log_progress(u"Known and installable plugins: {}".format(u", ".join(map(lambda x: x["id"], known_plugins))))
							if unknown_plugins:
								on_log_progress(u"Unknown plugins: {}".format(u", ".join(map(lambda x: x["key"], unknown_plugins))))

						if callable(on_install_plugins):
							on_install_plugins(known_plugins)

						if callable(on_report_unknown_plugins):
							on_report_unknown_plugins(unknown_plugins)

					# move config data
					basedir_backup = basedir + ".bck"
					basedir_extracted = os.path.join(temp, "basedir")

					if callable(on_log_progress):
						on_log_progress(u"Renaming {} to {}...".format(basedir, basedir_backup))
					os.rename(basedir, basedir_backup)

					try:
						if callable(on_log_progress):
							on_log_progress(u"Moving {} to {}...".format(basedir_extracted, basedir))
						os.rename(basedir_extracted, basedir)
					except:
						if callable(on_log_error):
							on_log_error(u"Error while restoring config data", exc_info=sys.exc_info())
							on_log_error(u"Rolling back old config data")

						os.rename(basedir_backup, basedir)

						if callable(on_restore_failed):
							on_restore_failed(path)
						return False

					if unknown_plugins:
						if callable(on_log_progress):
							on_log_progress(u"Writing info file about unknown plugins")

						if not os.path.isdir(datafolder):
							os.makedirs(datafolder)

						unknown_plugins_path = os.path.join(datafolder, UNKNOWN_PLUGINS_FILE)
						try:
							with codecs.open(unknown_plugins_path, mode="w", encoding="utf-8") as f:
								json.dump(unknown_plugins, f)
						except:
							if callable(on_log_error):
								on_log_error(u"Could not persist list of unknown plugins to {}".format(unknown_plugins_path),
								             exc_info = sys.exc_info())

				finally:
					if callable(on_log_progress):
						on_log_progress(u"Removing temporary unpacked folder")
					shutil.rmtree(temp)

		except:
			if callable(on_log_error):
				on_log_error(u"Error while running restore", exc_info=sys.exc_info())
			if callable(on_restore_failed):
				on_restore_failed(path)
			return False

		finally:
			# remove zip
			if callable(on_log_progress):
				on_log_progress(u"Removing temporary zip")
			os.remove(path)

		# restart server
		if restart_command:
			import sarge

			if callable(on_log_progress):
				on_log_progress(u"Restarting...")
			try:
				sarge.run(restart_command, async_=True)
			except:
				if callable(on_log_error):
					on_log_error(u"Error while restarting via command {}".format(restart_command),
					             exc_info=sys.exc_info())
					on_log_error(u"Please restart OctoPrint manually")
				return False

		if callable(on_restore_done):
			on_restore_done(path)

		return True


	def _send_client_message(self, message, payload=None):
		if payload is None:
			payload = dict()
		payload["type"] = message
		self._plugin_manager.send_plugin_message(self._identifier, payload)



class InsufficientSpace(Exception):
	pass

__plugin_name__ = gettext(u"Backup & Restore")
__plugin_author__ = u"Gina Häußge"
__plugin_description__ = u"Backup & restore your OctoPrint settings and data"
__plugin_disabling_discouraged__ = gettext(u"Without this plugin you will no longer be able to backup "
                                           u"& restore your OctoPrint settings and data.")
__plugin_license__ = u"AGPLv3"
__plugin_implementation__ = BackupPlugin()
__plugin_hooks__ = {
	"octoprint.server.http.routes": __plugin_implementation__.route_hook,
	"octoprint.server.http.bodysize": __plugin_implementation__.bodysize_hook,
	"octoprint.cli.commands": __plugin_implementation__.cli_commands_hook
}
