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

try:
	from os import scandir
except ImportError:
	from scandir import scandir

try:
	import zlib # check if zlib is available
except ImportError:
	zlib = None

from flask_babel import gettext

import flask
import os
import shutil
import threading
import time
import zipfile
import json

"""
TODO:

* Restore:
  * UI to upload a backup zip
  * tornado endpoint to stream the upload
  * apply upload
    * unzip
    * sanity check (config.yaml, users.yaml if acl is on)
    * read plugin list from json, extract list of plugins installable from repo vs. those that need to be installed manually
    * rename existing
    * move over new
    * delete old
    * in case of any error roll back to old and abort
* offer command line interface as well
"""

class BackupPlugin(octoprint.plugin.SettingsPlugin,
                   octoprint.plugin.TemplatePlugin,
                   octoprint.plugin.AssetPlugin,
                   octoprint.plugin.BlueprintPlugin):

	# noinspection PyMissingConstructor
	def __init__(self):
		self._in_progress = []
		self._in_progress_lock = threading.RLock()

	##~~ TemplatePlugin

	##~~ AssetPlugin

	def get_assets(self):
		return dict(js=["js/backup.js"],
		            css=["css/backup.css"],
		            less=["less/backup.less"])

	##~~ BlueprintPlugin

	@octoprint.plugin.BlueprintPlugin.route("/backup", methods=["GET"])
	@admin_permission.require(403)
	@restricted_access
	def get_backups(self):
		# TODO add caching
		backups = []
		for entry in scandir(self.get_plugin_data_folder()):
			if is_hidden_path(entry.path):
				continue
			backups.append(dict(name=entry.name,
			                    date=entry.stat().st_mtime,
			                    size=entry.stat().st_size,
			                    url=flask.url_for("index") + "plugin/backup/download/" + entry.name))
		return flask.jsonify(backups=backups,
		                     in_progress=len(self._in_progress) > 0)

	@octoprint.plugin.BlueprintPlugin.route("/backup", methods=["POST"])
	@admin_permission.require(403)
	@restricted_access
	def create_backup(self):
		backup_file = "backup-{}.zip".format(time.strftime("%Y%m%d-%H%M%S"))

		data = flask.request.json
		exclude = data.get("exclude", [])

		thread = threading.Thread(target=self._create_backup,
		                          args=(backup_file,),
		                          kwargs=dict(exclude=exclude))
		thread.daemon = True
		thread.start()

		response = flask.jsonify(started=True)
		response.headers["Location"] = flask.url_for("index") + "plugin/backup/download/" + backup_file
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
				self._logger.exception("Could not delete {}".format(filename))
				raise
		return NO_CONTENT

	@octoprint.plugin.BlueprintPlugin.route("/restore", methods=["POST"])
	@admin_permission.require(403)
	@restricted_access
	def perform_restore(self):
		pass

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

	##~~ helpers

	def _get_disk_size(self, path):
		total = 0
		for entry in scandir(path):
			if entry.is_dir():
				total += self._get_disk_size(entry.path)
			elif entry.is_file():
				total += entry.stat().st_size
		return total

	def _free_space(self, path, size):
		from psutil import disk_usage
		return disk_usage(path).free > size

	def _create_backup(self, name, exclude=None):
		if exclude is None:
			exclude = []

		configfile = self._settings._configfile
		basedir = self._settings._basedir

		temporary_path = os.path.join(self.get_plugin_data_folder(), ".{}".format(name))
		final_path = os.path.join(self.get_plugin_data_folder(), name)

		size = self._get_disk_size(basedir)
		if not self._free_space(os.path.dirname(temporary_path), size):
			raise InsufficientSpace()

		own_folder = self.get_plugin_data_folder()
		defaults = [os.path.join(basedir, "config.yaml"),] + \
		           [os.path.join(basedir, folder) for folder in default_settings["folder"].keys()]

		compression = zipfile.ZIP_DEFLATED if zlib else zipfile.ZIP_STORED

		with self._in_progress_lock:
			self._in_progress.append(name)
			self._send_client_message("backup_started", payload=dict(name=name))

		self._logger.info("Creating backup zip at {} (excluded: {})...".format(temporary_path,
		                                                                       ",".join(exclude) if len(exclude) else "-"))

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

			# backup current config file
			add_to_zip(configfile, "config.yaml", ignored=[own_folder,])

			# backup configured folder paths
			for folder in default_settings["folder"].keys():
				if folder in exclude:
					continue
				add_to_zip(self._settings.global_get_basefolder(folder),
				           folder.replace("_", "/"),
				           ignored=[own_folder,])

			# backup anything else that might be lying around in our basedir
			add_to_zip(basedir, "", ignored=defaults + [own_folder, ])

			# add list of installed plugins
			plugins = []
			plugin_folder = self._settings.global_get_basefolder("plugins")
			for key, plugin in self._plugin_manager.plugins.items():
				if plugin.bundled or (isinstance(plugin.origin, FolderOrigin) and plugin.origin.folder == plugin_folder):
					# ignore anything bundled or from the plugins folder we already include in the backup
					continue

				plugins.append(dict(key=plugin.key,
				                    name=plugin.name,
				                    url=plugin.url))

			if len(plugins):
				zip.writestr("plugin_list.json", json.dumps(plugins))

		shutil.move(temporary_path, final_path)
		self._logger.info("... done creating backup zip.")

		with self._in_progress_lock:
			self._in_progress.remove(name)
			self._send_client_message("backup_done", payload=dict(name=name))

	def _restore_backup(self, path):
		pass

	def _send_client_message(self, message, payload=None):
		if payload is None:
			payload = dict()
		payload["type"] = message
		self._plugin_manager.send_plugin_message(self._identifier, payload)



class InsufficientSpace(Exception):
	pass

__plugin_name__ = gettext("Backup & Restore")
__plugin_author__ = "Gina Häußge"
__plugin_description__ = "Backup & restore your OctoPrint settings and data"
__plugin_disabling_discouraged__ = gettext("Without this plugin you will no longer be able to backup "
                                           "& restore your OctoPrint settings and data.")
__plugin_license__ = "AGPLv3"
__plugin_implementation__ = BackupPlugin()
__plugin_hooks__ = {
	"octoprint.server.http.routes": __plugin_implementation__.route_hook
}
