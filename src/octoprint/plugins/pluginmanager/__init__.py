# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import octoprint.plugin
import octoprint.plugin.core

from octoprint.settings import valid_boolean_trues
from octoprint.server.util.flask import restricted_access
from octoprint.server import admin_permission

from flask import jsonify, make_response
from flask.ext.babel import gettext

import logging
import sarge
import sys
import requests
import re

class PluginManagerPlugin(octoprint.plugin.SimpleApiPlugin,
                          octoprint.plugin.TemplatePlugin,
                          octoprint.plugin.AssetPlugin,
                          octoprint.plugin.SettingsPlugin,
                          octoprint.plugin.StartupPlugin,
                          octoprint.plugin.BlueprintPlugin):

	def __init__(self):
		self._pending_enable = set()
		self._pending_disable = set()
		self._pending_install = set()
		self._pending_uninstall = set()

		self._repository_available = False
		self._repository_plugins = []

	def initialize(self):
		self._console_logger = logging.getLogger("octoprint.plugins.pluginmanager.console")

	##~~ StartupPlugin

	def on_startup(self, host, port):
		console_logging_handler = logging.handlers.RotatingFileHandler(self._settings.get_plugin_logfile_path(postfix="console"), maxBytes=2*1024*1024)
		console_logging_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
		console_logging_handler.setLevel(logging.DEBUG)

		self._console_logger.addHandler(console_logging_handler)
		self._console_logger.setLevel(logging.DEBUG)
		self._console_logger.propagate = False

		self._repository_available = self._refresh_repository()

	##~~ SettingsPlugin

	def get_settings_defaults(self):
		return dict(
			repository="http://plugins.octoprint.org/plugins.json",
			pip=None,
			dependency_links=False
		)

	##~~ AssetPlugin

	def get_assets(self):
		return dict(
			js=["js/pluginmanager.js"],
			css=["css/pluginmanager.css"],
			less=["less/pluginmanager.less"]
		)

	##~~ TemplatePlugin

	def get_template_configs(self):
		return [
			dict(type="settings", name=gettext("Plugin Manager"), template="pluginmanager_settings.jinja2", custom_bindings=True)
		]

	##~~ BlueprintPlugin

	@octoprint.plugin.BlueprintPlugin.route("/upload_archive", methods=["POST"])
	@restricted_access
	@admin_permission.require(403)
	def upload_archive(self):
		import flask

		input_name = "file"
		input_upload_path = input_name + "." + self._settings.global_get(["server", "uploads", "pathSuffix"])
		input_upload_name = input_name + "." + self._settings.global_get(["server", "uploads", "nameSuffix"])

		if input_upload_path not in flask.request.values or input_upload_name not in flask.request.values:
			return flask.make_response("No file included", 400)
		upload_path = flask.request.values[input_upload_path]
		upload_name = flask.request.values[input_upload_name]

		import tempfile
		import shutil
		import os

		archive = tempfile.NamedTemporaryFile(delete=False, suffix="-{upload_name}".format(**locals()))
		try:
			archive.close()
			shutil.copy(upload_path, archive.name)
			return self.command_install(path=archive.name, force="force" in flask.request.values and flask.request.values["force"] in valid_boolean_trues)
		finally:
			try:
				os.remove(archive.name)
			except Exception as e:
				self._logger.warn("Could not remove temporary file {path} again: {message}".format(path=archive.name, message=str(e)))

	##~~ SimpleApiPlugin

	def get_api_commands(self):
		return {
			"install": ["url"],
			"uninstall": ["plugin"],
			"enable": ["plugin"],
			"disable": ["plugin"],
			"refresh_repository": []
		}

	def on_api_get(self, request):
		if not admin_permission.can():
			return make_response("Insufficient rights", 403)

		plugins = self._plugin_manager.plugins

		result = []
		for name, plugin in plugins.items():
			result.append(self._to_external_representation(plugin))

		if "refresh_repository" in request.values and request.values["refresh_repository"] in valid_boolean_trues:
			self._refresh_repository()

		return jsonify(plugins=result, repository=dict(available=self._repository_available, plugins=self._repository_plugins), os=self._get_os(), octoprint=self._get_octoprint_version())

	def on_api_command(self, command, data):
		if not admin_permission.can():
			return make_response("Insufficient rights", 403)

		if command == "install":
			url = data["url"]
			plugin_name = data["plugin"] if "plugin" in data else None
			return self.command_install(url=url,
			                            force="force" in data and data["force"] in valid_boolean_trues,
			                            dependency_links="dependency_links" in data and data["dependency_links"] in valid_boolean_trues,
			                            reinstall=plugin_name)

		elif command == "uninstall":
			plugin_name = data["plugin"]
			if not plugin_name in self._plugin_manager.plugins:
				return make_response("Unknown plugin: %s" % plugin_name, 404)

			plugin = self._plugin_manager.plugins[plugin_name]
			return self.command_uninstall(plugin)

		elif command == "enable" or command == "disable":
			plugin_name = data["plugin"]
			if not plugin_name in self._plugin_manager.plugins:
				return make_response("Unknown plugin: %s" % plugin_name, 404)

			plugin = self._plugin_manager.plugins[plugin_name]
			return self.command_toggle(plugin, command)

		elif command == "refresh_repository":
			self._repository_available = self._refresh_repository()
			return jsonify(repository=dict(available=self._repository_available, plugins=self._repository_plugins))

	def command_install(self, url=None, path=None, force=False, reinstall=None, dependency_links=False):
		if url is not None:
			pip_args = ["install", sarge.shell_quote(url)]
		elif path is not None:
			pip_args = ["install", path]
		else:
			raise ValueError("Either url or path must be provided")

		if dependency_links or self._settings.get_boolean(["dependency_links"]):
			pip_args.append("--process-dependency-links")

		all_plugins_before = self._plugin_manager.find_plugins()

		success_string = "Successfully installed"
		failure_string = "Could not install"
		try:
			returncode, stdout, stderr = self._call_pip(pip_args)
		except:
			self._logger.exception("Could not install plugin from %s" % url)
			return make_response("Could not install plugin from url, see the log for more details", 500)
		else:
			if force:
				pip_args += ["--ignore-installed", "--force-reinstall", "--no-deps"]
				try:
					returncode, stdout, stderr = self._call_pip(pip_args)
				except:
					self._logger.exception("Could not install plugin from %s" % url)
					return make_response("Could not install plugin from url, see the log for more details", 500)

		try:
			result_line = filter(lambda x: x.startswith(success_string) or x.startswith(failure_string), stdout)[-1]
		except IndexError:
			result = dict(result=False, reason="Could not parse output from pip")
			self._send_result_notification("install", result)
			return jsonify(result)

		# The final output of a pip install command looks something like this:
		#
		#   Successfully installed OctoPrint-Plugin-1.0 Dependency-One-0.1 Dependency-Two-9.3
		#
		# or this:
		#
		#   Successfully installed OctoPrint-Plugin Dependency-One Dependency-Two
		#   Cleaning up...
		#
		# So we'll need to fetch the "Successfully installed" line, strip the "Successfully" part, then split by whitespace
		# and strip to get all installed packages.
		#
		# We then need to iterate over all known plugins and see if either the package name or the package name plus
		# version number matches one of our installed packages. If it does, that's our installed plugin.
		#
		# Known issue: This might return the wrong plugin if more than one plugin was installed through this
		# command (e.g. due to pulling in another plugin as dependency). It should be safe for now though to
		# consider this a rare corner case. Once it becomes a real problem we'll just extend the plugin manager
		# so that it can report on more than one installed plugin.

		result_line = result_line.strip()
		if not result_line.startswith(success_string):
			result = dict(result=False, reason="Pip did not report successful installation")
			self._send_result_notification("install", result)
			return jsonify(result)

		installed = map(lambda x: x.strip(), result_line[len(success_string):].split(" "))
		all_plugins_after = self._plugin_manager.find_plugins(existing=dict(), ignore_uninstalled=False)

		for key, plugin in all_plugins_after.items():
			if plugin.origin is None or plugin.origin.type != "entry_point":
				continue

			package_name = plugin.origin.package_name
			package_version = plugin.origin.package_version
			versioned_package = "{package_name}-{package_version}".format(**locals())
			if package_name in installed or versioned_package in installed:
				new_plugin_key = key
				new_plugin = plugin
				break
		else:
			return make_response("Could not find plugin that was installed", 500)

		self._plugin_manager.mark_plugin(new_plugin_key, uninstalled=False)
		self._plugin_manager.reload_plugins()

		needs_restart = self._plugin_manager.is_restart_needing_plugin(new_plugin) or new_plugin_key in all_plugins_before or reinstall is not None
		needs_refresh = new_plugin.implementation and isinstance(new_plugin.implementation, octoprint.plugin.ReloadNeedingPlugin)

		self._plugin_manager.log_all_plugins()

		result = dict(result=True, url=url, needs_restart=needs_restart, needs_refresh=needs_refresh, was_reinstalled=new_plugin_key in all_plugins_before or reinstall is not None, plugin=self._to_external_representation(new_plugin))
		self._send_result_notification("install", result)
		return jsonify(result)

	def command_uninstall(self, plugin):
		if plugin.key == "pluginmanager":
			return make_response("Can't uninstall Plugin Manager", 400)

		if plugin.bundled:
			return make_response("Bundled plugins cannot be uninstalled", 400)

		if plugin.origin is None:
			self._logger.warn(u"Trying to uninstall plugin {plugin} but origin is unknown".format(**locals()))
			return make_response("Could not uninstall plugin, its origin is unknown")

		if plugin.origin.type == "entry_point":
			# plugin is installed through entry point, need to use pip to uninstall it
			origin = plugin.origin[3]
			if origin is None:
				origin = plugin.origin[2]

			pip_args = ["uninstall", "--yes", origin]
			try:
				self._call_pip(pip_args)
			except:
				self._logger.exception(u"Could not uninstall plugin via pip")
				return make_response("Could not uninstall plugin via pip, see the log for more details", 500)

		elif plugin.origin.type == "folder":
			import os
			import shutil
			full_path = os.path.realpath(plugin.location)

			if os.path.isdir(full_path):
				# plugin is installed via a plugin folder, need to use rmtree to get rid of it
				self._log_stdout(u"Deleting plugin from {folder}".format(folder=plugin.location))
				shutil.rmtree(full_path)
			elif os.path.isfile(full_path):
				self._log_stdout(u"Deleting plugin from {file}".format(file=plugin.location))
				os.remove(full_path)

				if full_path.endswith(".py"):
					pyc_file = "{full_path}c".format(**locals())
					if os.path.isfile(pyc_file):
						os.remove(pyc_file)

		else:
			self._logger.warn(u"Trying to uninstall plugin {plugin} but origin is unknown ({plugin.origin.type})".format(**locals()))
			return make_response("Could not uninstall plugin, its origin is unknown")

		needs_restart = self._plugin_manager.is_restart_needing_plugin(plugin)
		needs_refresh = plugin.implementation and isinstance(plugin.implementation, octoprint.plugin.ReloadNeedingPlugin)

		self._plugin_manager.mark_plugin(plugin.key, uninstalled=True)

		if not needs_restart:
			try:
				self._plugin_manager.disable_plugin(plugin.key, plugin=plugin)
			except octoprint.plugin.core.PluginLifecycleException as e:
				self._logger.exception(u"Problem disabling plugin {name}".format(name=plugin.key))
				result = dict(result=False, uninstalled=True, disabled=False, unloaded=False, reason=e.reason)
				self._send_result_notification("uninstall", result)
				return jsonify(result)

			try:
				self._plugin_manager.unload_plugin(plugin.key)
			except octoprint.plugin.core.PluginLifecycleException as e:
				self._logger.exception(u"Problem unloading plugin {name}".format(name=plugin.key))
				result = dict(result=False, uninstalled=True, disabled=True, unloaded=False, reason=e.reason)
				self._send_result_notification("uninstall", result)
				return jsonify(result)

		self._plugin_manager.reload_plugins()

		result = dict(result=True, needs_restart=needs_restart, needs_refresh=needs_refresh, plugin=self._to_external_representation(plugin))
		self._send_result_notification("uninstall", result)
		return jsonify(result)

	def command_toggle(self, plugin, command):
		if plugin.key == "pluginmanager":
			return make_response("Can't enable/disable Plugin Manager", 400)

		needs_restart = self._plugin_manager.is_restart_needing_plugin(plugin)
		needs_refresh = plugin.implementation and isinstance(plugin.implementation, octoprint.plugin.ReloadNeedingPlugin)

		pending = ((command == "disable" and plugin.key in self._pending_enable) or (command == "enable" and plugin.key in self._pending_disable))
		needs_restart_api = needs_restart and not pending
		needs_refresh_api = needs_refresh and not pending

		try:
			if command == "disable":
				self._mark_plugin_disabled(plugin, needs_restart=needs_restart)
			elif command == "enable":
				self._mark_plugin_enabled(plugin, needs_restart=needs_restart)
		except octoprint.plugin.core.PluginLifecycleException as e:
			self._logger.exception(u"Problem toggling enabled state of {name}: {reason}".format(name=plugin.key, reason=e.reason))
			result = dict(result=False, reason=e.reason)
		except octoprint.plugin.core.PluginNeedsRestart:
			result = dict(result=True, needs_restart=True, needs_refresh=True, plugin=self._to_external_representation(plugin))
		else:
			result = dict(result=True, needs_restart=needs_restart_api, needs_refresh=needs_refresh_api, plugin=self._to_external_representation(plugin))

		self._send_result_notification(command, result)
		return jsonify(result)

	def _send_result_notification(self, action, result):
		notification = dict(type="result", action=action)
		notification.update(result)
		self._plugin_manager.send_plugin_message(self._identifier, notification)

	def _call_pip(self, args):
		pip_command = self._settings.get(["pip"])
		if pip_command is None:
			import os
			python_command = sys.executable
			binary_dir = os.path.dirname(python_command)

			pip_command = os.path.join(binary_dir, "pip")
			if sys.platform == "win32":
				# Windows is a bit special... first of all the file will be called pip.exe, not just pip, and secondly
				# for a non-virtualenv install (e.g. global install) the pip binary will not be located in the
				# same folder as python.exe, but in a subfolder Scripts, e.g.
				#
				# C:\Python2.7\
				#  |- python.exe
				#  `- Scripts
				#      `- pip.exe

				# virtual env?
				pip_command = os.path.join(binary_dir, "pip.exe")

				if not os.path.isfile(pip_command):
					# nope, let's try the Scripts folder then
					scripts_dir = os.path.join(binary_dir, "Scripts")
					if os.path.isdir(scripts_dir):
						pip_command = os.path.join(scripts_dir, "pip.exe")

			if not os.path.isfile(pip_command) or not os.access(pip_command, os.X_OK):
				raise RuntimeError(u"No pip path configured and {pip_command} does not exist or is not executable, can't install".format(**locals()))

		command = [pip_command] + args

		self._logger.debug(u"Calling: {}".format(" ".join(command)))

		p = sarge.run(" ".join(command), shell=True, async=True, stdout=sarge.Capture(), stderr=sarge.Capture())
		p.wait_events()

		all_stdout = []
		all_stderr = []
		try:
			while p.returncode is None:
				line = p.stderr.readline(timeout=0.5)
				if line:
					self._log_stderr(line)
					all_stderr.append(line)

				line = p.stdout.readline(timeout=0.5)
				if line:
					self._log_stdout(line)
					all_stdout.append(line)

				p.commands[0].poll()

		finally:
			p.close()

		stderr = p.stderr.text
		if stderr:
			split_lines = stderr.split("\n")
			self._log_stderr(*split_lines)
			all_stderr += split_lines

		stdout = p.stdout.text
		if stdout:
			split_lines = stdout.split("\n")
			self._log_stdout(*split_lines)
			all_stdout += split_lines

		return p.returncode, all_stdout, all_stderr

	def _log_stdout(self, *lines):
		self._log(lines, prefix=">", stream="stdout")

	def _log_stderr(self, *lines):
		self._log(lines, prefix="!", stream="stderr")

	def _log(self, lines, prefix=None, stream=None, strip=True):
		if strip:
			lines = map(lambda x: x.strip(), lines)

		self._plugin_manager.send_plugin_message(self._identifier, dict(type="loglines", loglines=[dict(line=line, stream=stream) for line in lines]))
		for line in lines:
			self._console_logger.debug(u"{prefix} {line}".format(**locals()))

	def _mark_plugin_enabled(self, plugin, needs_restart=False):
		disabled_list = list(self._settings.global_get(["plugins", "_disabled"]))
		if plugin.key in disabled_list:
			disabled_list.remove(plugin.key)
			self._settings.global_set(["plugins", "_disabled"], disabled_list)
			self._settings.save(force=True)

		if not needs_restart:
			self._plugin_manager.enable_plugin(plugin.key)
		else:
			if plugin.key in self._pending_disable:
				self._pending_disable.remove(plugin.key)
			elif not plugin.enabled and plugin.key not in self._pending_enable:
				self._pending_enable.add(plugin.key)

	def _mark_plugin_disabled(self, plugin, needs_restart=False):
		disabled_list = list(self._settings.global_get(["plugins", "_disabled"]))
		if not plugin.key in disabled_list:
			disabled_list.append(plugin.key)
			self._settings.global_set(["plugins", "_disabled"], disabled_list)
			self._settings.save(force=True)

		if not needs_restart:
			self._plugin_manager.disable_plugin(plugin.key)
		else:
			if plugin.key in self._pending_enable:
				self._pending_enable.remove(plugin.key)
			elif plugin.enabled and plugin.key not in self._pending_disable:
				self._pending_disable.add(plugin.key)

	def _refresh_repository(self):
		import requests
		repository_url = self._settings.get(["repository"])
		try:
			r = requests.get(repository_url)
		except Exception as e:
			self._logger.warn("Could not fetch plugins from repository at {repository_url}: {message}".format(repository_url=repository_url, message=str(e)))
			return False

		current_os = self._get_os()
		octoprint_version = self._get_octoprint_version()
		if "-" in octoprint_version:
			octoprint_version = octoprint_version[:octoprint_version.find("-")]

		def map_repository_entry(entry):
			result = dict(entry)

			if not "follow_dependency_links" in result:
				result["follow_dependency_links"] = False

			result["is_compatible"] = dict(
				octoprint=True,
				os=True
			)

			if "compatibility" in entry:
				if "octoprint" in entry["compatibility"]:
					import semantic_version
					for octo_compat in entry["compatibility"]["octoprint"]:
						s = semantic_version.Spec("=={}".format(octo_compat))
						if semantic_version.Version(octoprint_version) in s:
							break
					else:
						result["is_compatible"]["octoprint"] = False

				if "os" in entry["compatibility"]:
					result["is_compatible"]["os"] = current_os in entry["compatibility"]["os"]

			return result

		self._repository_plugins = map(map_repository_entry, r.json())
		return True

	def _get_os(self):
		if sys.platform == "win32":
			return "windows"
		elif sys.platform == "linux2":
			return "linux"
		elif sys.platform == "darwin":
			return "macos"
		else:
			return "unknown"

	def _get_octoprint_version(self):
		from octoprint._version import get_versions
		return get_versions()["version"]

	def _to_external_representation(self, plugin):
		return dict(
			key=plugin.key,
			name=plugin.name,
			description=plugin.description,
			author=plugin.author,
			version=plugin.version,
			url=plugin.url,
			license=plugin.license,
			bundled=plugin.bundled,
			enabled=plugin.enabled,
			pending_enable=(not plugin.enabled and plugin.key in self._pending_enable),
			pending_disable=(plugin.enabled and plugin.key in self._pending_disable),
			pending_install=(plugin.key in self._pending_install),
			pending_uninstall=(plugin.key in self._pending_uninstall)
		)

__plugin_name__ = "Plugin Manager"
__plugin_author__ = "Gina Häußge"
__plugin_url__ = "https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager"
__plugin_description__ = "Allows installing and managing OctoPrint plugins"
__plugin_license__ = "AGPLv3"
__plugin_implementation__ = PluginManagerPlugin()
