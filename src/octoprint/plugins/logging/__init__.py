# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import octoprint.plugin
from octoprint.settings import settings

from octoprint.server import NO_CONTENT, admin_permission
from octoprint.server.util.flask import redirect_to_tornado, restricted_access

from flask import request, jsonify, url_for, make_response
from flask_babel import gettext
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest
import yaml

import os

try:
	from os import scandir
except ImportError:
	from scandir import scandir

class LoggingPlugin(octoprint.plugin.AssetPlugin,
                    octoprint.plugin.SettingsPlugin,
                    octoprint.plugin.TemplatePlugin,
                    octoprint.plugin.BlueprintPlugin):
	@octoprint.plugin.BlueprintPlugin.route("/", methods=["GET"])
	@restricted_access
	@admin_permission.require(403)
	def get_all(self):
		files = self._getLogFiles()
		free, total = self._get_usage()
		loggers = self._get_available_loggers()
		levels = self._get_logging_levels()
		return jsonify(logs=dict(files=files, free=free, total=total),
		               setup=dict(loggers=loggers, levels=levels))

	@octoprint.plugin.BlueprintPlugin.route("/logs", methods=["GET"])
	@restricted_access
	@admin_permission.require(403)
	def get_log_files(self):
		files = self._getLogFiles()
		free, total = self._get_usage()
		return jsonify(files=files, free=free, total=total)

	@octoprint.plugin.BlueprintPlugin.route("/logs/<path:filename>", methods=["GET"])
	@restricted_access
	@admin_permission.require(403)
	def download_log(self, filename):
		return redirect_to_tornado(request, url_for("index") + "downloads/logs/" + filename)

	@octoprint.plugin.BlueprintPlugin.route("/logs/<path:filename>", methods=["DELETE"])
	@restricted_access
	@admin_permission.require(403)
	def delete_log(self, filename):
		secure = os.path.join(settings().getBaseFolder("logs"), secure_filename(filename))
		if not os.path.exists(secure):
			return make_response("File not found: %s" % filename, 404)

		os.remove(secure)

		return NO_CONTENT

	@octoprint.plugin.BlueprintPlugin.route("/setup", methods=["GET"])
	@restricted_access
	@admin_permission.require(403)
	def get_logging_setup(self):
		loggers = self._get_available_loggers()
		levels = self._get_logging_levels()
		return jsonify(loggers=loggers, levels=levels)

	@octoprint.plugin.BlueprintPlugin.route("/setup/levels", methods=["GET"])
	@restricted_access
	@admin_permission.require(403)
	def get_logging_levels_api(self):
		return jsonify(self._get_logging_levels())

	@octoprint.plugin.BlueprintPlugin.route("/setup/levels", methods=["PUT"])
	@restricted_access
	@admin_permission.require(403)
	def set_logging_levels_api(self):
		if not "application/json" in request.headers["Content-Type"]:
			return make_response("Expected content-type JSON", 400)

		try:
			json_data = request.json
		except BadRequest:
			return make_response("Malformed JSON body in request", 400)

		if not isinstance(json_data, dict):
			return make_response("Invalid log level configuration", 400)

		# TODO validate further

		self._set_logging_levels(json_data)
		return self.get_logging_levels_api()

	def _get_usage(self):
		import psutil
		usage = psutil.disk_usage(settings().getBaseFolder("logs", check_writable=False))
		return usage.free, usage.total

	def _getLogFiles(self):
		files = []
		basedir = settings().getBaseFolder("logs", check_writable=False)
		for entry in scandir(basedir):
			files.append({
				"name": entry.name,
				"date": int(entry.stat().st_mtime),
				"size": entry.stat().st_size,
				"refs": {
					"resource": url_for(".download_log", filename=entry.name, _external=True),
					"download": url_for("index", _external=True) + "downloads/logs/" + entry.name
				}
			})

		return files

	def _get_available_loggers(self):
		return filter(lambda x: self._is_managed_logger(x), self._logger.manager.loggerDict.keys())

	def _get_logging_file(self):
		# TODO this might not be the logging config we are actually using here (command line parameter...)
		return os.path.join(self._settings.getBaseFolder("base"), "logging.yaml")

	def _get_logging_config(self):
		logging_file = self._get_logging_file()

		config_from_file = {}
		if os.path.exists(logging_file) and os.path.isfile(logging_file):
			import yaml
			with open(logging_file, "r") as f:
				config_from_file = yaml.safe_load(f)
		return config_from_file

	def _get_logging_levels(self):
		config = self._get_logging_config()
		if config is None or not isinstance(config, dict):
			return dict()

		return dict((key, value.get("level"))
		            for key, value in config.get("loggers", dict()).items()
		            if isinstance(value, dict) and "level" in value)

	def _set_logging_levels(self, new_levels):
		import logging

		config = self._get_logging_config()

		# clear all configured logging levels
		if config.has_key("loggers"):
			purge = []
			for component in config["loggers"]:
				if not self._is_managed_logger(component): continue
				try:
					del config["loggers"][component]["level"]
					self._logger.manager.loggerDict[component].setLevel(logging.INFO)
				except:
					pass
				if len(config["loggers"][component]) == 0:
					purge.append(component)
		else:
			config["loggers"] = dict()

		# update all logging levels
		for logger, level in new_levels.items():
			if not config["loggers"].has_key(logger):
				config["loggers"][logger] = dict()
			config["loggers"][logger]["level"] = level

		# delete empty entries
		config["loggers"] = {k: v for k, v in config["loggers"].items() if len(v)}

		# save
		with octoprint.util.atomic_write(self._get_logging_file(), "wb", max_permissions=0o666) as f:
			yaml.safe_dump(config, f, default_flow_style=False, indent="  ", allow_unicode=True)

		# set runtime logging levels now
		for logger, level in new_levels.items():
			level = logging.getLevelName(level)

			self._logger.info("Setting logger {} level to {}".format(logger, level))
			self._logger.manager.loggerDict[logger].setLevel(level)

	def _is_managed_logger(self, logger):
		return logger and (logger.startswith("octoprint") or logger.startswith("tornado"))

	def get_template_configs(self):
		return [
			dict(type="settings", custom_bindings=True)
		]

	def get_assets(self):
		return dict(js=["js/logging.js"],
		            clientjs=["clientjs/logging.js"],
		            less=["less/logging.less"],
		            css=["css/logging.css"])

__plugin_name__ = "Logging"
__plugin_author__ = "Shawn Bruce, based on work by Gina Häußge and Marc Hannappel"
__plugin_description__ = "Provides access to OctoPrint's logs and logging configuration."
__plugin_disabling_discouraged__ = gettext("Without this plugin you will no longer be able to retrieve "
                                           "OctoPrint's logs or modify the current logging levels through "
                                           "the web interface.")
__plugin_implementation__ = LoggingPlugin()
