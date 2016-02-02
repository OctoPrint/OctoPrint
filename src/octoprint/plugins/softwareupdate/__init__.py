# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import octoprint.plugin

import flask
import os
import threading
import time
import hashlib

from . import version_checks, updaters, exceptions, util


from octoprint.server.util.flask import restricted_access
from octoprint.server import admin_permission, VERSION, REVISION
from octoprint.util import dict_merge
import octoprint.settings


##~~ Plugin


class SoftwareUpdatePlugin(octoprint.plugin.BlueprintPlugin,
                           octoprint.plugin.SettingsPlugin,
                           octoprint.plugin.AssetPlugin,
                           octoprint.plugin.TemplatePlugin):
	def __init__(self):
		self._update_in_progress = False
		self._configured_checks_mutex = threading.Lock()
		self._configured_checks = None
		self._refresh_configured_checks = False

		self._version_cache = dict()
		self._version_cache_ttl = 0
		self._version_cache_path = None
		self._version_cache_dirty = False

	def initialize(self):
		self._version_cache_ttl = self._settings.get_int(["cache_ttl"]) * 60
		self._version_cache_path = os.path.join(self.get_plugin_data_folder(), "versioncache.yaml")
		self._load_version_cache()

		def refresh_checks(name, plugin):
			self._refresh_configured_checks = True
			self._send_client_message("update_versions")

		self._plugin_lifecycle_manager.add_callback("enabled", refresh_checks)
		self._plugin_lifecycle_manager.add_callback("disabled", refresh_checks)

	def _get_configured_checks(self):
		with self._configured_checks_mutex:
			if self._refresh_configured_checks or self._configured_checks is None:
				self._refresh_configured_checks = False
				self._configured_checks = self._settings.get(["checks"], merged=True)
				update_check_hooks = self._plugin_manager.get_hooks("octoprint.plugin.softwareupdate.check_config")
				check_providers = self._settings.get(["check_providers"], merged=True)
				for name, hook in update_check_hooks.items():
					try:
						hook_checks = hook()
					except:
						self._logger.exception("Error while retrieving update information from plugin {name}".format(**locals()))
					else:
						for key, data in hook_checks.items():
							check_providers[key] = name
							if key in self._configured_checks:
								data = dict_merge(data, self._configured_checks[key])
							self._configured_checks[key] = data
				self._settings.set(["check_providers"], check_providers)
				self._settings.save()

				# we only want to process checks that came from plugins for
				# which the plugins are still installed and enabled
				config_checks = self._settings.get(["checks"])
				plugin_and_not_enabled = lambda k: k in check_providers and \
				                                   not check_providers[k] in self._plugin_manager.enabled_plugins
				obsolete_plugin_checks = filter(plugin_and_not_enabled,
				                                config_checks.keys())
				for key in obsolete_plugin_checks:
					self._logger.debug("Check for key {} was provided by plugin {} that's no longer available, ignoring it".format(key, check_providers[key]))
					del self._configured_checks[key]

			return self._configured_checks

	def _load_version_cache(self):
		if not os.path.isfile(self._version_cache_path):
			return

		import yaml
		try:
			with open(self._version_cache_path) as f:
				data = yaml.safe_load(f)
		except:
			self._logger.exception("Error while loading version cache from disk")
		else:
			try:
				if not isinstance(data, dict):
					self._logger.info("Version cache was created in a different format, not using it")
					return

				if "__version" in data:
					data_version = data["__version"]
				else:
					self._logger.info("Can't determine version of OctoPrint version cache was created for, not using it")
					return

				from octoprint._version import get_versions
				octoprint_version = get_versions()["version"]
				if data_version != octoprint_version:
					self._logger.info("Version cache was created for another version of OctoPrint, not using it")
					return

				self._version_cache = data
				self._version_cache_dirty = False
				self._logger.info("Loaded version cache from disk")
			except:
				self._logger.exception("Error parsing in version cache data")

	def _save_version_cache(self):
		import yaml
		from octoprint.util import atomic_write
		from octoprint._version import get_versions

		octoprint_version = get_versions()["version"]
		self._version_cache["__version"] = octoprint_version

		with atomic_write(self._version_cache_path) as file_obj:
			yaml.safe_dump(self._version_cache, stream=file_obj, default_flow_style=False, indent="  ", allow_unicode=True)

		self._version_cache_dirty = False
		self._logger.info("Saved version cache to disk")

	#~~ SettingsPlugin API

	def get_settings_defaults(self):
		return {
			"checks": {
				"octoprint": {
					"type": "github_release",
					"user": "foosel",
					"repo": "OctoPrint",
					"update_script": "{{python}} \"{update_script}\" --python=\"{{python}}\" \"{{folder}}\" {{target}}".format(update_script=os.path.join(self._basefolder, "scripts", "update-octoprint.py")),
					"restart": "octoprint"
				},
			},
			"pip_command": None,
			"check_providers": {},

			"cache_ttl": 24 * 60,
		}

	def on_settings_load(self):
		data = dict(octoprint.plugin.SettingsPlugin.on_settings_load(self))
		if "checks" in data:
			del data["checks"]

		checks = self._get_configured_checks()
		if "octoprint" in checks:
			if "checkout_folder" in checks["octoprint"]:
				data["octoprint_checkout_folder"] = checks["octoprint"]["checkout_folder"]
			elif "update_folder" in checks["octoprint"]:
				data["octoprint_checkout_folder"] = checks["octoprint"]["update_folder"]
			else:
				data["octoprint_checkout_folder"] = None
			data["octoprint_type"] = checks["octoprint"].get("type", None)
		else:
			data["octoprint_checkout_folder"] = None
			data["octoprint_type"] = None

		return data

	def on_settings_save(self, data):
		for key in self.get_settings_defaults():
			if key == "checks" or key == "cache_ttl" or key == "octoprint_checkout_folder" or key == "octoprint_type":
				continue
			if key in data:
				self._settings.set([key], data[key])

		if "cache_ttl" in data:
			self._settings.set_int(["cache_ttl"], data["cache_ttl"])
		self._version_cache_ttl = self._settings.get_int(["cache_ttl"]) * 60

		checks = self._get_configured_checks()
		if "octoprint" in checks:
			check = checks["octoprint"]
			update_type = check.get("type", None)
			checkout_folder = check.get("checkout_folder", None)
			update_folder = check.get("update_folder", None)

		defaults = dict(
			plugins=dict(softwareupdate=dict(
				checks=dict(
					octoprint=dict(
						type=update_type,
						checkout_folder=checkout_folder,
						update_folder=update_folder
					)
				)
			))
		)

		if "octoprint_checkout_folder" in data:
			self._settings.set(["checks", "octoprint", "checkout_folder"], data["octoprint_checkout_folder"], defaults=defaults, force=True)
			if update_folder and data["octoprint_checkout_folder"]:
				self._settings.set(["checks", "octoprint", "update_folder"], None, defaults=defaults, force=True)
			self._refresh_configured_checks = True

		if "octoprint_type" in data and data["octoprint_type"] in ("github_release", "git_commit"):
			self._settings.set(["checks", "octoprint", "type"], data["octoprint_type"], defaults=defaults, force=True)
			self._refresh_configured_checks = True

	def get_settings_version(self):
		return 4

	def on_settings_migrate(self, target, current=None):

		if current is None or current < 4:
			# config version 4 and higher moves octoprint_restart_command and
			# environment_restart_command to the core configuration

			# current plugin commands
			configured_octoprint_restart_command = self._settings.get(["octoprint_restart_command"])
			configured_environment_restart_command = self._settings.get(["environment_restart_command"])

			# current global commands
			configured_system_restart_command = self._settings.global_get(["server", "commands", "systemRestartCommand"])
			configured_server_restart_command = self._settings.global_get(["server", "commands", "serverRestartCommand"])

			# only set global commands if they are not yet set
			if configured_system_restart_command is None and configured_environment_restart_command is not None:
				self._settings.global_set(["server", "commands", "systemRestartCommand"], configured_environment_restart_command)
			if configured_server_restart_command is None and configured_octoprint_restart_command is not None:
				self._settings.global_set(["server", "commands", "serverRestartCommand"], configured_octoprint_restart_command)

			# delete current plugin commands from config
			self._settings.set(["environment_restart_command"], None)
			self._settings.set(["octoprint_restart_command"], None)

		if current is None or current == 2:
			# No config version and config version 2 need the same fix, stripping
			# accidentally persisted data off the checks

			configured_checks = self._settings.get(["checks"], incl_defaults=False)
			if configured_checks is None:
				configured_checks = dict()

			check_keys = configured_checks.keys()

			# take care of the octoprint entry
			if "octoprint" in configured_checks:
				octoprint_check = dict(configured_checks["octoprint"])
				if "type" not in octoprint_check or octoprint_check["type"] != "github_commit":
					deletables=["current", "displayName", "displayVersion"]
				else:
					deletables=[]
				octoprint_check = self._clean_settings_check("octoprint", octoprint_check, self.get_settings_defaults()["checks"]["octoprint"], delete=deletables, save=False)
				check_keys.remove("octoprint")

			# and the hooks
			update_check_hooks = self._plugin_manager.get_hooks("octoprint.plugin.softwareupdate.check_config")
			for name, hook in update_check_hooks.items():
				try:
					hook_checks = hook()
				except:
					self._logger.exception("Error while retrieving update information from plugin {name}".format(**locals()))
				else:
					for key, data in hook_checks.items():
						if key in configured_checks:
							settings_check = dict(configured_checks[key])
							merged = dict_merge(data, settings_check)
							if "type" not in merged or merged["type"] != "github_commit":
								deletables = ["current", "displayVersion"]
							else:
								deletables = []

							self._clean_settings_check(key, settings_check, data, delete=deletables, save=False)
							check_keys.remove(key)

			# and anything that's left over we'll just remove now
			for key in check_keys:
				dummy_defaults = dict(plugins=dict())
				dummy_defaults["plugins"][self._identifier] = dict(checks=dict())
				dummy_defaults["plugins"][self._identifier]["checks"][key] = None
				self._settings.set(["checks", key], None, defaults=dummy_defaults)

		elif current == 1:
			# config version 1 had the error that the octoprint check got accidentally
			# included in checks["octoprint"], leading to recursion and hence to
			# yaml parser errors

			configured_checks = self._settings.get(["checks"], incl_defaults=False)
			if configured_checks is None:
				return

			if "octoprint" in configured_checks and "octoprint" in configured_checks["octoprint"]:
				# that's a circular reference, back to defaults
				dummy_defaults = dict(plugins=dict())
				dummy_defaults["plugins"][self._identifier] = dict(checks=dict())
				dummy_defaults["plugins"][self._identifier]["checks"]["octoprint"] = None
				self._settings.set(["checks", "octoprint"], None, defaults=dummy_defaults)

	def _clean_settings_check(self, key, data, defaults, delete=None, save=True):
		if delete is None:
			delete = []

		for k, v in data.items():
			if k in defaults and defaults[k] == data[k]:
				del data[k]

		for k in delete:
			if k in data:
				del data[k]

		dummy_defaults = dict(plugins=dict())
		dummy_defaults["plugins"][self._identifier] = dict(checks=dict())
		dummy_defaults["plugins"][self._identifier]["checks"][key] = defaults
		if len(data):
			self._settings.set(["checks", key], data, defaults=dummy_defaults)
		else:
			self._settings.set(["checks", key], None, defaults=dummy_defaults)

		if save:
			self._settings.save()

		return data

	#~~ BluePrint API

	@octoprint.plugin.BlueprintPlugin.route("/check", methods=["GET"])
	@restricted_access
	def check_for_update(self):
		if "check" in flask.request.values:
			check_targets = map(lambda x: x.strip(), flask.request.values["check"].split(","))
		else:
			check_targets = None

		if "force" in flask.request.values and flask.request.values["force"] in octoprint.settings.valid_boolean_trues:
			force = True
		else:
			force = False

		try:
			information, update_available, update_possible = self.get_current_versions(check_targets=check_targets, force=force)
			return flask.jsonify(dict(status="updatePossible" if update_available and update_possible else "updateAvailable" if update_available else "current", information=information))
		except exceptions.ConfigurationInvalid as e:
			flask.make_response("Update not properly configured, can't proceed: %s" % e.message, 500)


	@octoprint.plugin.BlueprintPlugin.route("/update", methods=["POST"])
	@restricted_access
	@admin_permission.require(403)
	def perform_update(self):
		if self._printer.is_printing() or self._printer.is_paused():
			# do not update while a print job is running
			return flask.make_response("Printer is currently printing or paused", 409)

		if not "application/json" in flask.request.headers["Content-Type"]:
			return flask.make_response("Expected content-type JSON", 400)

		json_data = flask.request.json

		if "check" in json_data:
			check_targets = map(lambda x: x.strip(), json_data["check"])
		else:
			check_targets = None

		if "force" in json_data and json_data["force"] in octoprint.settings.valid_boolean_trues:
			force = True
		else:
			force = False

		to_be_checked, checks = self.perform_updates(check_targets=check_targets, force=force)
		return flask.jsonify(dict(order=to_be_checked, checks=checks))

	#~~ Asset API

	def get_assets(self):
		return dict(
			css=["css/softwareupdate.css"],
			js=["js/softwareupdate.js"],
			less=["less/softwareupdate.less"]
		)

	##~~ TemplatePlugin API

	def get_template_configs(self):
		from flask.ext.babel import gettext
		return [
			dict(type="settings", name=gettext("Software Update"))
		]

	#~~ Updater

	def get_current_versions(self, check_targets=None, force=False):
		"""
		Retrieves the current version information for all defined check_targets. Will retrieve information for all
		available targets by default.

		:param check_targets: an iterable defining the targets to check, if not supplied defaults to all targets
		"""

		checks = self._get_configured_checks()
		if check_targets is None:
			check_targets = checks.keys()

		update_available = False
		update_possible = False
		information = dict()

		for target, check in checks.items():
			if not target in check_targets:
				continue

			try:
				populated_check = self._populated_check(target, check)
				target_information, target_update_available, target_update_possible = self._get_current_version(target, populated_check, force=force)
				if target_information is None:
					target_information = dict()
			except exceptions.UnknownCheckType:
				self._logger.warn("Unknown update check type for target {}: {}".format(target, check.get("type", "<n/a>")))
				continue

			target_information = dict_merge(dict(local=dict(name="unknown", value="unknown"), remote=dict(name="unknown", value="unknown", release_notes=None)), target_information)

			update_available = update_available or target_update_available
			update_possible = update_possible or (target_update_possible and target_update_available)

			local_name = target_information["local"]["name"]
			local_value = target_information["local"]["value"]

			release_notes = None
			if target_information and target_information["remote"] and target_information["remote"]["value"]:
				if "release_notes" in populated_check and populated_check["release_notes"]:
					release_notes = populated_check["release_notes"]
				elif "release_notes" in target_information["remote"]:
					release_notes = target_information["remote"]["release_notes"]

				if release_notes:
					release_notes = release_notes.format(octoprint_version=VERSION,
					                                     target_name=target_information["remote"]["name"],
					                                     target_version=target_information["remote"]["value"])

			information[target] = dict(updateAvailable=target_update_available,
			                           updatePossible=target_update_possible,
			                           information=target_information,
			                           displayName=populated_check["displayName"],
			                           displayVersion=populated_check["displayVersion"].format(octoprint_version=VERSION, local_name=local_name, local_value=local_value),
			                           check=populated_check,
			                           releaseNotes=release_notes)

		if self._version_cache_dirty:
			self._save_version_cache()
		return information, update_available, update_possible

	def _get_check_hash(self, check):
		hash = hashlib.md5()
		hash.update(repr(check))
		return hash.hexdigest()

	def _get_current_version(self, target, check, force=False):
		"""
		Determines the current version information for one target based on its check configuration.
		"""

		current_hash = self._get_check_hash(check)
		if target in self._version_cache and not force:
			data = self._version_cache[target]
			if data["hash"] == current_hash and data["timestamp"] + self._version_cache_ttl >= time.time() > data["timestamp"]:
				# we also check that timestamp < now to not get confused too much by clock changes
				return data["information"], data["available"], data["possible"]

		information = dict()
		update_available = False

		try:
			version_checker = self._get_version_checker(target, check)
			information, is_current = version_checker.get_latest(target, check)
			if information is not None and not is_current:
				update_available = True
		except exceptions.UnknownCheckType:
			self._logger.warn("Unknown check type %s for %s" % (check["type"], target))
			update_possible = False
		except:
			self._logger.exception("Could not check %s for updates" % target)
			update_possible = False
		else:
			try:
				updater = self._get_updater(target, check)
				update_possible = updater.can_perform_update(target, check)
			except:
				update_possible = False

		self._version_cache[target] = dict(timestamp=time.time(),
		                                   hash=current_hash,
		                                   information=information,
		                                   available=update_available,
		                                   possible=update_possible)
		self._version_cache_dirty = True
		return information, update_available, update_possible

	def _send_client_message(self, message_type, data=None):
		self._plugin_manager.send_plugin_message("softwareupdate", dict(type=message_type, data=data))

	def perform_updates(self, check_targets=None, force=False):
		"""
		Performs the updates for the given check_targets. Will update all possible targets by default.

		:param check_targets: an iterable defining the targets to update, if not supplied defaults to all targets
		"""

		checks = self._get_configured_checks()
		populated_checks = dict()
		for target, check in checks.items():
			try:
				populated_checks[target] = self._populated_check(target, check)
			except exceptions.UnknownCheckType:
				self._logger.debug("Ignoring unknown check type for target {}".format(target))
			except:
				self._logger.exception("Error while populating check prior to update for target {}".format(target))

		if check_targets is None:
			check_targets = populated_checks.keys()
		to_be_updated = sorted(set(check_targets) & set(populated_checks.keys()))
		if "octoprint" in to_be_updated:
			to_be_updated.remove("octoprint")
			tmp = ["octoprint"] + to_be_updated
			to_be_updated = tmp

		updater_thread = threading.Thread(target=self._update_worker, args=(populated_checks, to_be_updated, force))
		updater_thread.daemon = False
		updater_thread.start()

		return to_be_updated, dict((key, check["displayName"] if "displayName" in check else key) for key, check in populated_checks.items() if key in to_be_updated)

	def _update_worker(self, checks, check_targets, force):

		restart_type = None

		try:
			self._update_in_progress = True

			target_results = dict()
			error = False

			### iterate over all configured targets

			for target in check_targets:
				if not target in checks:
					continue
				check = checks[target]

				if "enabled" in check and not check["enabled"]:
					continue

				if not target in check_targets:
					continue

				target_error, target_result = self._perform_update(target, check, force)
				error = error or target_error
				if target_result is not None:
					target_results[target] = target_result

					if "restart" in check:
						target_restart_type = check["restart"]
					elif "pip" in check:
						target_restart_type = "octoprint"

					# if our update requires a restart we have to determine which type
					if restart_type is None or (restart_type == "octoprint" and target_restart_type == "environment"):
						restart_type = target_restart_type

		finally:
			# we might have needed to update the config, so we'll save that now
			self._settings.save()

			# also, we are now longer updating
			self._update_in_progress = False

		if error:
			# if there was an unignorable error, we just return error
			self._send_client_message("error", dict(results=target_results))

		else:
			self._save_version_cache()

			# otherwise the update process was a success, but we might still have to restart
			if restart_type is not None and restart_type in ("octoprint", "environment"):
				# one of our updates requires a restart of either type "octoprint" or "environment". Let's see if
				# we can actually perform that

				if restart_type == "octoprint":
					restart_command = self._settings.global_get(["server", "commands", "serverRestartCommand"])
				elif restart_type == "environment":
					restart_command = self._settings.global_get(["server", "commands", "systemRestartCommand"])

				if restart_command is not None:
					self._send_client_message("restarting", dict(restart_type=restart_type, results=target_results))
					try:
						self._perform_restart(restart_command)
					except exceptions.RestartFailed:
						self._send_client_message("restart_failed", dict(restart_type=restart_type, results=target_results))
				else:
					# we don't have this restart type configured, we'll have to display a message that a manual
					# restart is needed
					self._send_client_message("restart_manually", dict(restart_type=restart_type, results=target_results))
			else:
				self._send_client_message("success", dict(results=target_results))

	def _perform_update(self, target, check, force):
		information, update_available, update_possible = self._get_current_version(target, check)

		if not update_available and not force:
			return False, None

		if not update_possible:
			self._logger.warn("Cannot perform update for %s, update type is not fully configured" % target)
			return False, None

		# determine the target version to update to
		target_version = information["remote"]["value"]
		target_error = False

		### The actual update procedure starts here...

		try:
			self._logger.info("Starting update of %s to %s..." % (target, target_version))
			self._send_client_message("updating", dict(target=target, version=target_version))
			updater = self._get_updater(target, check)
			if updater is None:
				raise exceptions.UnknownUpdateType()

			update_result = updater.perform_update(target, check, target_version)
			target_result = ("success", update_result)
			self._logger.info("Update of %s to %s successful!" % (target, target_version))

		except exceptions.UnknownUpdateType:
			self._logger.warn("Update of %s can not be performed, unknown update type" % target)
			self._send_client_message("update_failed", dict(target=target, version=target_version, reason="Unknown update type"))
			return False, None

		except Exception as e:
			self._logger.exception("Update of %s can not be performed" % target)
			if not "ignorable" in check or not check["ignorable"]:
				target_error = True

			if isinstance(e, exceptions.UpdateError):
				target_result = ("failed", e.data)
				self._send_client_message("update_failed", dict(target=target, version=target_version, reason=e.data))
			else:
				target_result = ("failed", None)
				self._send_client_message("update_failed", dict(target=target, version=target_version, reason="unknown"))

		else:
			# make sure that any external changes to config.yaml are loaded into the system
			self._settings.load()

			# persist the new version if necessary for check type
			if check["type"] == "github_commit":
				dummy_default = dict(plugins=dict())
				dummy_default["plugins"][self._identifier] = dict(checks=dict())
				dummy_default["plugins"][self._identifier]["checks"][target] = dict(current=None)
				self._settings.set(["checks", target, "current"], target_version, defaults=dummy_default)

				# we have to save here (even though that makes us save quite often) since otherwise the next
				# load will overwrite our changes we just made
				self._settings.save()

			del self._version_cache[target]
			self._version_cache_dirty = True

		return target_error, target_result

	def _perform_restart(self, restart_command):
		"""
		Performs a restart using the supplied restart_command.
		"""

		self._logger.info("Restarting...")
		try:
			util.execute(restart_command)
		except exceptions.ScriptError as e:
			self._logger.exception("Error while restarting")
			self._logger.warn("Restart stdout:\n%s" % e.stdout)
			self._logger.warn("Restart stderr:\n%s" % e.stderr)
			raise exceptions.RestartFailed()

	def _populated_check(self, target, check):
		if not "type" in check:
			raise exceptions.UnknownCheckType()

		result = dict(check)

		if target == "octoprint":
			from flask.ext.babel import gettext
			result["displayName"] = check.get("displayName", gettext("OctoPrint"))
			result["displayVersion"] = check.get("displayVersion", "{octoprint_version}")

			if check["type"] == "github_commit":
				result["current"] = REVISION if REVISION else "unknown"
			else:
				result["current"] = VERSION
		else:
			result["displayName"] = check.get("displayName", target)
			result["displayVersion"] = check.get("displayVersion", check.get("current", "unknown"))
			if check["type"] in ("github_commit"):
				result["current"] = check.get("current", None)
			else:
				result["current"] = check.get("current", check.get("displayVersion", None))

		return result

	def _get_version_checker(self, target, check):
		"""
		Retrieves the version checker to use for given target and check configuration. Will raise an UnknownCheckType
		if version checker cannot be determined.
		"""

		if not "type" in check:
			raise exceptions.ConfigurationInvalid("no check type defined")

		check_type = check["type"]
		if check_type == "github_release":
			return version_checks.github_release
		elif check_type == "github_commit":
			return version_checks.github_commit
		elif check_type == "git_commit":
			return version_checks.git_commit
		elif check_type == "commandline":
			return version_checks.commandline
		elif check_type == "python_checker":
			return version_checks.python_checker
		else:
			raise exceptions.UnknownCheckType()

	def _get_updater(self, target, check):
		"""
		Retrieves the updater for the given target and check configuration. Will raise an UnknownUpdateType if updater
		cannot be determined.
		"""

		if "update_script" in check:
			return updaters.update_script
		elif "pip" in check:
			if not "pip_command" in check and self._settings.get(["pip_command"]) is not None:
				check["pip_command"] = self._settings.get(["pip_command"])
			return updaters.pip
		elif "python_updater" in check:
			return updaters.python_updater
		else:
			raise exceptions.UnknownUpdateType()

__plugin_name__ = "Software Update"
__plugin_author__ = "Gina Häußge"
__plugin_url__ = "https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update"
__plugin_description__ = "Allows receiving update notifications and performing updates of OctoPrint and plugins"
__plugin_license__ = "AGPLv3"
def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = SoftwareUpdatePlugin()

	global __plugin_helpers__
	__plugin_helpers__ = dict(
		version_checks=version_checks,
		updaters=updaters,
		exceptions=exceptions,
		util=util
	)


