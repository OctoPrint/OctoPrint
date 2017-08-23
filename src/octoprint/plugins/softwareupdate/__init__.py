# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import octoprint.plugin

import flask
import os
import threading
import time
import logging
import logging.handlers
import hashlib
import traceback

from concurrent import futures

from . import version_checks, updaters, exceptions, util, cli

from flask.ext.babel import gettext

from octoprint.server.util.flask import restricted_access, with_revalidation_checking, check_etag
from octoprint.server import admin_permission, VERSION, REVISION, BRANCH
from octoprint.util import dict_merge, to_unicode
import octoprint.settings


##~~ Plugin


class SoftwareUpdatePlugin(octoprint.plugin.BlueprintPlugin,
                           octoprint.plugin.SettingsPlugin,
                           octoprint.plugin.AssetPlugin,
                           octoprint.plugin.TemplatePlugin,
                           octoprint.plugin.StartupPlugin,
                           octoprint.plugin.WizardPlugin,
                           octoprint.plugin.EventHandlerPlugin):

	COMMIT_TRACKING_TYPES = ("github_commit", "bitbucket_commit")

	def __init__(self):
		self._update_in_progress = False
		self._configured_checks_mutex = threading.Lock()
		self._configured_checks = None
		self._refresh_configured_checks = False

		self._get_versions_mutex = threading.RLock()
		self._get_versions_data = None
		self._get_versions_data_ready = threading.Event()

		self._version_cache = dict()
		self._version_cache_ttl = 0
		self._version_cache_path = None
		self._version_cache_dirty = False
		self._version_cache_timestamp = None

		self._console_logger = None

	def initialize(self):
		self._console_logger = logging.getLogger("octoprint.plugins.softwareupdate.console")

		self._version_cache_ttl = self._settings.get_int(["cache_ttl"]) * 60
		self._version_cache_path = os.path.join(self.get_plugin_data_folder(), "versioncache.yaml")
		self._load_version_cache()

		def refresh_checks(name, plugin):
			self._refresh_configured_checks = True
			self._send_client_message("update_versions")

		self._plugin_lifecycle_manager.add_callback("enabled", refresh_checks)
		self._plugin_lifecycle_manager.add_callback("disabled", refresh_checks)

	def on_startup(self, host, port):
		console_logging_handler = logging.handlers.RotatingFileHandler(self._settings.get_plugin_logfile_path(postfix="console"), maxBytes=2*1024*1024)
		console_logging_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
		console_logging_handler.setLevel(logging.DEBUG)

		self._console_logger.addHandler(console_logging_handler)
		self._console_logger.setLevel(logging.DEBUG)
		self._console_logger.propagate = False

	def on_after_startup(self):
		# refresh cache now if necessary so it's faster once the user connects to the instance - but decouple it from
		# the server startup
		def fetch_data():
			self.get_current_versions()

		thread = threading.Thread(target=fetch_data)
		thread.daemon = True
		thread.start()

	def _get_configured_checks(self):
		with self._configured_checks_mutex:
			if self._refresh_configured_checks or self._configured_checks is None:
				self._refresh_configured_checks = False
				self._configured_checks = self._settings.get(["checks"], merged=True)

				update_check_hooks = self._plugin_manager.get_hooks("octoprint.plugin.softwareupdate.check_config")
				check_providers = self._settings.get(["check_providers"], merged=True)
				effective_configs = dict()

				for name, hook in update_check_hooks.items():
					try:
						hook_checks = hook()
					except:
						self._logger.exception("Error while retrieving update information from plugin {name}".format(**locals()))
					else:
						for key, default_config in hook_checks.items():
							if key in effective_configs or key == "octoprint":
								if key == name:
									self._logger.warn("Software update hook {} provides check for itself but that was already registered by {} - overwriting that third party registration now!".format(name, check_providers.get(key, "unknown hook")))
								else:
									self._logger.warn("Software update hook {} tried to overwrite config for check {} but that was already configured elsewhere".format(name, key))
									continue

							check_providers[key] = name

							yaml_config = dict()
							effective_config = default_config
							if key in self._configured_checks:
								yaml_config = self._configured_checks[key]
								effective_config = dict_merge(default_config, yaml_config)

								# Make sure there's nothing persisted in that check that shouldn't be persisted
								#
								# This used to be part of the settings migration (version 2) due to a bug - it can't
								# stay there though since it interferes with manual entries to the checks not
								# originating from within a plugin. Hence we do that step now here.
								if "type" not in effective_config or effective_config["type"] not in self.COMMIT_TRACKING_TYPES:
									deletables = ["current", "displayVersion"]
								else:
									deletables = []
								self._clean_settings_check(key, yaml_config, default_config, delete=deletables, save=False)

							if effective_config:
								effective_configs[key] = effective_config
							else:
								self._logger.warn("Update for {} is empty or None, ignoring it".format(key))

				# finally set all our internal representations to our processed results
				for key, config in effective_configs.items():
					self._configured_checks[key] = config

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
			timestamp = os.stat(self._version_cache_path).st_mtime
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
				self._version_cache_timestamp = timestamp
				self._logger.info("Loaded version cache from disk")
			except:
				self._logger.exception("Error parsing in version cache data")

	def _save_version_cache(self):
		import yaml
		from octoprint.util import atomic_write
		from octoprint._version import get_versions

		octoprint_version = get_versions()["version"]
		self._version_cache["__version"] = octoprint_version

		with atomic_write(self._version_cache_path, max_permissions=0o666) as file_obj:
			yaml.safe_dump(self._version_cache, stream=file_obj, default_flow_style=False, indent="  ", allow_unicode=True)

		self._version_cache_dirty = False
		self._version_cache_timestamp = time.time()
		self._logger.info("Saved version cache to disk")

	#~~ SettingsPlugin API

	def get_settings_defaults(self):
		update_script = os.path.join(self._basefolder, "scripts", "update-octoprint.py")
		return {
			"checks": {
				"octoprint": {
					"type": "github_release",
					"user": "foosel",
					"repo": "OctoPrint",
					"update_script": "{{python}} \"{update_script}\" --branch={{branch}} --force={{force}} \"{{folder}}\" {{target}}".format(update_script=update_script),
					"restart": "octoprint",
					"stable_branch": dict(branch="master", commitish=["master"], name="Stable"),
					"prerelease_branches": [dict(branch="rc/maintenance",
					                             commitish=["rc/maintenance"],             # maintenance RCs
					                             name="Maintenance RCs"),
					                        dict(branch="rc/devel",
					                             commitish=["rc/maintenance", "rc/devel"], # devel & maintenance RCs
					                             name="Devel RCs")]
				},
			},
			"pip_command": None,
			"check_providers": {},

			"cache_ttl": 24 * 60,

			"notify_users": True
		}

	def on_settings_load(self):
		data = dict(octoprint.plugin.SettingsPlugin.on_settings_load(self))
		if "checks" in data:
			del data["checks"]

		if "check_providers" in data:
			del data["check_providers"]

		checks = self._get_configured_checks()
		if "octoprint" in checks:
			data["octoprint_checkout_folder"] = self._get_octoprint_checkout_folder(checks=checks)
			data["octoprint_type"] = checks["octoprint"].get("type", None)

			try:
				data["octoprint_method"] = self._get_update_method("octoprint", checks["octoprint"])
			except exceptions.UnknownUpdateType:
				data["octoprint_method"] = "unknown"

			stable_branch = None
			prerelease_branches = []
			branch_mappings = []
			if "stable_branch" in checks["octoprint"]:
				branch_mappings.append(checks["octoprint"]["stable_branch"])
				stable_branch = checks["octoprint"]["stable_branch"]["branch"]
			if "prerelease_branches" in checks["octoprint"]:
				for mapping in checks["octoprint"]["prerelease_branches"]:
					branch_mappings.append(mapping)
					prerelease_branches.append(mapping["branch"])
			data["octoprint_branch_mappings"] = branch_mappings

			data["octoprint_release_channel"] = stable_branch
			if checks["octoprint"].get("prerelease", False):
				channel = checks["octoprint"].get("prerelease_channel", BRANCH)
				if channel in prerelease_branches:
					data["octoprint_release_channel"] = channel

		else:
			data["octoprint_checkout_folder"] = None
			data["octoprint_type"] = None
			data["octoprint_branch_mappings"] = []

		return data

	def on_settings_save(self, data):
		for key in self.get_settings_defaults():
			if key in ("checks", "cache_ttl", "notify_user", "octoprint_checkout_folder", "octoprint_type", "octoprint_release_channel"):
				continue
			if key in data:
				self._settings.set([key], data[key])

		if "cache_ttl" in data:
			self._settings.set_int(["cache_ttl"], data["cache_ttl"])
		self._version_cache_ttl = self._settings.get_int(["cache_ttl"]) * 60

		if "notify_users" in data:
			self._settings.set_boolean(["notify_users"], data["notify_users"])

		checks = self._get_configured_checks()
		if "octoprint" in checks:
			check = checks["octoprint"]
			update_type = check.get("type", None)
			checkout_folder = check.get("checkout_folder", None)
			update_folder = check.get("update_folder", None)
			prerelease = check.get("prerelease", False)
			prerelease_channel = check.get("prerelease_channel", None)
		else:
			update_type = checkout_folder = update_folder = prerelease_channel = None
			prerelease = False

		defaults = dict(
			plugins=dict(softwareupdate=dict(
				checks=dict(
					octoprint=dict(
						type=update_type,
						checkout_folder=checkout_folder,
						update_folder=update_folder,
						prerelease=prerelease,
						prerelease_channel=prerelease_channel
					)
				)
			))
		)

		updated_octoprint_check_config = False

		if "octoprint_checkout_folder" in data:
			self._settings.set(["checks", "octoprint", "checkout_folder"], data["octoprint_checkout_folder"], defaults=defaults, force=True)
			if update_folder and data["octoprint_checkout_folder"]:
				self._settings.set(["checks", "octoprint", "update_folder"], None, defaults=defaults, force=True)
			updated_octoprint_check_config = True

		if "octoprint_type" in data and data["octoprint_type"] in ("github_release", "git_commit"):
			self._settings.set(["checks", "octoprint", "type"], data["octoprint_type"], defaults=defaults, force=True)
			updated_octoprint_check_config = True

		if updated_octoprint_check_config:
			self._refresh_configured_checks = True
			try:
				del self._version_cache["octoprint"]
			except KeyError:
				pass
			self._version_cache_dirty = True

		if "octoprint_release_channel" in data:
			prerelease_branches = self._settings.get(["checks", "octoprint", "prerelease_branches"])
			if prerelease_branches and data["octoprint_release_channel"] in [x["branch"] for x in prerelease_branches]:
				self._settings.set(["checks", "octoprint", "prerelease"], True, defaults=defaults, force=True)
				self._settings.set(["checks", "octoprint", "prerelease_channel"], data["octoprint_release_channel"], defaults=defaults, force=True)
				self._refresh_configured_checks = True
			else:
				self._settings.set(["checks", "octoprint", "prerelease"], False, defaults=defaults, force=True)
				self._settings.set(["checks", "octoprint", "prerelease_channel"], None, defaults=defaults, force=True)
				self._refresh_configured_checks = True

	def get_settings_version(self):
		return 5

	def on_settings_migrate(self, target, current=None):

		if current == 4:
			# config version 4 didn't correctly remove the old settings for octoprint_restart_command
			# and environment_restart_command

			self._settings.set(["environment_restart_command"], None)
			self._settings.set(["octoprint_restart_command"], None)

		if current is None or current < 5:
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
			# accidentally persisted data off the checks.
			#
			# We used to do the same processing for the plugin entries too here, but that interfered
			# with manual configuration entries. Stuff got deleted that wasn't supposed to be deleted.
			#
			# The problem is that we don't know if an entry we are looking at and which didn't come through
			# a plugin hook is simply an entry from a now uninstalled/unactive plugin, or if it was something
			# manually configured by the user. So instead of just blindly removing anything that doesn't
			# come from a plugin here we instead clean up anything that indeed comes from a plugin
			# during run time and leave everything else as is in the hopes that will not cause trouble.
			#
			# We still handle the "octoprint" entry here though.

			configured_checks = self._settings.get(["checks"], incl_defaults=False)
			if configured_checks is not None and "octoprint" in configured_checks:
				octoprint_check = dict(configured_checks["octoprint"])
				if "type" not in octoprint_check or octoprint_check["type"] not in self.COMMIT_TRACKING_TYPES:
					deletables=["current", "displayName", "displayVersion"]
				else:
					deletables=[]
				self._clean_settings_check("octoprint", octoprint_check, self.get_settings_defaults()["checks"]["octoprint"], delete=deletables, save=False)

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
		if not data:
			# nothing to do
			return data

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

		force = flask.request.values.get("force", "false") in octoprint.settings.valid_boolean_trues

		def view():
			try:
				information, update_available, update_possible = self.get_current_versions(check_targets=check_targets, force=force)
				return flask.jsonify(dict(status="updatePossible" if update_available and update_possible else "updateAvailable" if update_available else "current",
				                          information=information,
				                          timestamp=self._version_cache_timestamp))
			except exceptions.ConfigurationInvalid as e:
				return flask.make_response("Update not properly configured, can't proceed: %s" % e.message, 500)

		def etag():
			checks = self._get_configured_checks()

			targets = check_targets
			if targets is None:
				targets = checks.keys()

			import hashlib
			hash = hashlib.sha1()

			targets = sorted(targets)
			for target in targets:
				current_hash = self._get_check_hash(checks.get(target, dict()))
				if target in self._version_cache and not force:
					data = self._version_cache[target]
					hash.update(current_hash)
					hash.update(str(data["timestamp"] + self._version_cache_ttl >= time.time() > data["timestamp"]))
					hash.update(repr(data["information"]))
					hash.update(str(data["available"]))
					hash.update(str(data["possible"]))
					hash.update(str(data.get("online", None)))

			hash.update(",".join(targets))
			hash.update(str(self._version_cache_timestamp))
			hash.update(str(self._connectivity_checker.online))
			return hash.hexdigest()

		def condition():
			return check_etag(etag())

		return with_revalidation_checking(etag_factory=lambda *args, **kwargs: etag(),
		                                  condition=lambda *args, **kwargs: condition(),
		                                  unless=lambda: force)(view)()


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

	##~~ WizardPlugin API

	def is_wizard_required(self):
		checks = self._get_configured_checks()
		check = checks.get("octoprint", None)
		checkout_folder = self._get_octoprint_checkout_folder(checks=checks)
		return check and "update_script" in check and not checkout_folder

	##~~ EventHandlerPlugin API

	def on_event(self, event, payload):
		from octoprint.events import Events
		if event != Events.CONNECTIVITY_CHANGED or not payload or not payload.get("new", False):
			return

		thread = threading.Thread(target=self.get_current_versions)
		thread.daemon = True
		thread.start()

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

		# we don't want to do the same work twice, so let's use a lock
		if self._get_versions_mutex.acquire(False):
			self._get_versions_data_ready.clear()
			try:
				futures_to_result = dict()
				online = self._connectivity_checker.check_immediately()
				self._logger.debug("Looks like we are {}".format("online" if online else "offline"))

				with futures.ThreadPoolExecutor(max_workers=5) as executor:
					for target, check in checks.items():
						if not target in check_targets:
							continue

						if not check:
							continue

						try:
							populated_check = self._populated_check(target, check)
							future = executor.submit(self._get_current_version, target, populated_check, force=force)
							futures_to_result[future] = (target, populated_check)
						except exceptions.UnknownCheckType:
							self._logger.warn("Unknown update check type for target {}: {}".format(target,
							                                                                       check.get("type",
							                                                                                 "<n/a>")))
							continue
						except:
							self._logger.exception("Could not check {} for updates".format(target))
							continue

					for future in futures.as_completed(futures_to_result):

						target, populated_check = futures_to_result[future]
						if future.exception() is not None:
							self._logger.error("Could not check {} for updates, error: {!r}".format(target,
							                                                                        future.exception()))
							continue

						target_information, target_update_available, target_update_possible, target_online, target_error = future.result()

						target_information = dict_merge(dict(local=dict(name="?", value="?"),
						                                     remote=dict(name="?", value="?",
						                                                 release_notes=None),
						                                     needs_online=True), target_information)

						update_available = update_available or target_update_available
						update_possible = update_possible or (target_update_possible and target_update_available)

						local_name = target_information["local"]["name"]
						local_value = target_information["local"]["value"]

						release_notes = None
						if target_information and target_information["remote"] and target_information["remote"][
							"value"]:
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
						                           displayVersion=populated_check["displayVersion"].format(octoprint_version=VERSION,
						                                                                                   local_name=local_name,
						                                                                                   local_value=local_value),
						                           releaseNotes=release_notes,
						                           online=target_online,
						                           error=target_error)

				if self._version_cache_dirty:
					self._save_version_cache()

				self._get_versions_data = information, update_available, update_possible
				self._get_versions_data_ready.set()
			finally:
				self._get_versions_mutex.release()

		else: # something's already in progress, let's wait for it to complete and use its result
			self._get_versions_data_ready.wait()
			information, update_available, update_possible = self._get_versions_data

		return information, update_available, update_possible

	def _get_check_hash(self, check):
		def dict_to_sorted_repr(d):
			lines = []
			for key in sorted(d.keys()):
				value = d[key]
				if isinstance(value, dict):
					lines.append("{!r}: {}".format(key, dict_to_sorted_repr(value)))
				else:
					lines.append("{!r}: {!r}".format(key, value))

			return "{" + ", ".join(lines) + "}"

		hash = hashlib.md5()
		hash.update(dict_to_sorted_repr(check))
		return hash.hexdigest()

	def _get_current_version(self, target, check, force=False, online=None):
		"""
		Determines the current version information for one target based on its check configuration.
		"""

		current_hash = self._get_check_hash(check)
		if online is None:
			online = self._connectivity_checker.online
		if target in self._version_cache and not force:
			data = self._version_cache[target]
			if data["hash"] == current_hash \
					and data["timestamp"] + self._version_cache_ttl >= time.time() > data["timestamp"] \
					and data.get("online", None) == online:
				# we also check that timestamp < now to not get confused too much by clock changes
				return data["information"], data["available"], data["possible"], data["online"], data.get("error", None)

		information = dict()
		update_available = False
		error = None

		try:
			version_checker = self._get_version_checker(target, check)
			information, is_current = version_checker.get_latest(target, check, online=online)
			if information is not None and not is_current:
				update_available = True
		except exceptions.CannotCheckOffline:
			update_possible = False
			information["needs_online"] = True
		except exceptions.UnknownCheckType:
			self._logger.warn("Unknown check type %s for %s" % (check["type"], target))
			update_possible = False
			error = "unknown_check"
		except exceptions.NetworkError:
			self._logger.warn("Could not check %s for updates due to a network error" % target)
			update_possible = False
			error = "network"
		except:
			self._logger.exception("Could not check %s for updates" % target)
			update_possible = False
			error = "unknown"
		else:
			try:
				updater = self._get_updater(target, check)
				update_possible = updater.can_perform_update(target, check, online=online)
			except:
				update_possible = False

		self._version_cache[target] = dict(timestamp=time.time(),
		                                   hash=current_hash,
		                                   information=information,
		                                   available=update_available,
		                                   possible=update_possible,
		                                   online=online,
		                                   error=error)
		self._version_cache_dirty = True
		return information, update_available, update_possible, online, error

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

		check_data = dict((key, check["displayName"] if "displayName" in check else key) for key, check in populated_checks.items() if key in to_be_updated)
		return to_be_updated, check_data

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
					else:
						target_restart_type = None

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

				restart_command = None
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
		online = self._connectivity_checker.online

		information, update_available, update_possible, _, _ = self._get_current_version(target, check, online=online)

		if not update_available and not force:
			return False, None

		if not update_possible:
			self._logger.warn("Cannot perform update for %s, update type is not fully configured" % target)
			return False, None

		# determine the target version to update to
		target_version = information["remote"]["value"]
		target_error = False

		### The actual update procedure starts here...

		populated_check = self._populated_check(target, check)
		try:
			self._logger.info("Starting update of %s to %s..." % (target, target_version))
			self._send_client_message("updating", dict(target=target, version=target_version, name=populated_check["displayName"]))
			updater = self._get_updater(target, check)
			if updater is None:
				raise exceptions.UnknownUpdateType()

			update_result = updater.perform_update(target, populated_check, target_version, log_cb=self._log, online=online)
			target_result = ("success", update_result)
			self._logger.info("Update of %s to %s successful!" % (target, target_version))

		except exceptions.UnknownUpdateType:
			self._logger.warn("Update of %s can not be performed, unknown update type" % target)
			self._send_client_message("update_failed", dict(target=target, version=target_version, name=populated_check["displayName"], reason="Unknown update type"))
			return False, None

		except exceptions.CannotUpdateOffline:
			self._logger.warn("Update of %s can not be performed, it's not marked as 'offline' capable but we are apparently offline right now" % target)
			self._send_client_message("update_failed", dict(target=target, version=target_version, name=populated_check["displayName"], reason="No internet connection"))

		except Exception as e:
			self._logger.exception("Update of %s can not be performed" % target)
			if not "ignorable" in populated_check or not populated_check["ignorable"]:
				target_error = True

			if isinstance(e, exceptions.UpdateError):
				target_result = ("failed", e.data)
				self._send_client_message("update_failed", dict(target=target, version=target_version, name=populated_check["displayName"], reason=e.data))
			else:
				target_result = ("failed", None)
				self._send_client_message("update_failed", dict(target=target, version=target_version, name=populated_check["displayName"], reason="unknown"))

		else:
			# make sure that any external changes to config.yaml are loaded into the system
			self._settings.load()

			# persist the new version if necessary for check type
			if check["type"] in self.COMMIT_TRACKING_TYPES:
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
			util.execute(restart_command, evaluate_returncode=False, async=True)
		except exceptions.ScriptError as e:
			self._logger.exception("Error while restarting via command {}".format(restart_command))
			self._logger.warn("Restart stdout:\n{}".format(e.stdout))
			self._logger.warn("Restart stderr:\n{}".format(e.stderr))
			raise exceptions.RestartFailed()

	def _populated_check(self, target, check):
		if not "type" in check:
			raise exceptions.UnknownCheckType()

		result = dict(check)

		if target == "octoprint":
			from flask.ext.babel import gettext

			result["displayName"] = to_unicode(check.get("displayName"), errors="replace")
			if result["displayName"] is None:
				# displayName missing or set to None
				result["displayName"] = to_unicode(gettext("OctoPrint"), errors="replace")

			result["displayVersion"] = to_unicode(check.get("displayVersion"), errors="replace")
			if result["displayVersion"] is None:
				# displayVersion missing or set to None
				result["displayVersion"] = u"{octoprint_version}"

			stable_branch = "master"
			release_branches = []
			if "stable_branch" in check:
				release_branches.append(check["stable_branch"]["branch"])
				stable_branch = check["stable_branch"]["branch"]
			if "prerelease_branches" in check:
				release_branches += [x["branch"] for x in check["prerelease_branches"]]
			result["released_version"] = not release_branches or BRANCH in release_branches

			if check["type"] in self.COMMIT_TRACKING_TYPES:
				result["current"] = REVISION if REVISION else "unknown"
			else:
				result["current"] = VERSION

				if check["type"] == "github_release" and (check.get("prerelease", None) or BRANCH != stable_branch):
					# we are tracking github releases and are either also tracking prerelease OR are currently installed
					# from something that is not the stable (master) branch => we need to change some parameters

					# we compare versions fully, not just the base so that we see a difference
					# between RCs + stable for the same version release
					result["force_base"] = False

					if check.get("update_script", None):
						# if we are using the update_script, we need to set our update_branch

						if check.get("prerelease", None):
							# we are tracking prereleases => we want to be on the correct prerelease channel/branch
							channel = check.get("prerelease_channel", None)
							if channel:
								# if we have a release channel, we also set our update_branch here to our release channel
								# in case it's not already set
								result["update_branch"] = check.get("update_branch", channel)

						else:
							# we are not tracking prereleases, but aren't on the stable branch either => switch back
							# to stable branch on update
							result["update_branch"] = check.get("update_branch", stable_branch)

						# we also force an exact version
						result["force_exact_version"] = True

						if BRANCH != result.get("prerelease_channel"):
							# we force python unequality check here because that will also allow us to
							# downgrade on a prerelease channel change (rc/devel => rc/maintenance)
							#
							# we detect channel changes by comparing the current branch with the target
							# branch of the release channel - unequality means we might have to handle
							# a downgrade
							result["release_compare"] = "python_unequal"

		else:
			result["displayName"] = to_unicode(check.get("displayName"), errors="replace")
			if result["displayName"] is None:
				# displayName missing or None
				result["displayName"] = to_unicode(target, errors="replace")

			result["displayVersion"] = to_unicode(check.get("displayVersion", check.get("current")), errors="replace")
			if result["displayVersion"] is None:
				# displayVersion AND current missing or None
				result["displayVersion"] = u"unknown"

			if check["type"] in self.COMMIT_TRACKING_TYPES:
				result["current"] = check.get("current", None)
			else:
				result["current"] = check.get("current", check.get("displayVersion", None))

		if "pip" in result:
			if not "pip_command" in check and self._settings.get(["pip_command"]) is not None:
				result["pip_command"] = self._settings.get(["pip_command"])

		return result

	def _log(self, lines, prefix=None, stream=None, strip=True):
		if strip:
			lines = map(lambda x: x.strip(), lines)

		self._send_client_message("loglines", data=dict(loglines=[dict(line=line, stream=stream) for line in lines]))
		for line in lines:
			self._console_logger.debug(u"{} {}".format(prefix, line))

	def _send_client_message(self, message_type, data=None):
		self._plugin_manager.send_plugin_message(self._identifier, dict(type=message_type, data=data))

	def _get_version_checker(self, target, check):
		"""
		Retrieves the version checker to use for given target and check configuration. Will raise an UnknownCheckType
		if version checker cannot be determined.
		"""

		if not "type" in check:
			raise exceptions.ConfigurationInvalid("no check type defined")

		check_type = check["type"]
		method = getattr(version_checks, check_type)
		if method is None:
			raise exceptions.UnknownCheckType()
		else:
			return method

	def _get_update_method(self, target, check, valid_methods=None):
		"""
		Determines the update method for the given target and check.

		If ``valid_methods`` is provided, determine method must be contained
		therein to be considered valid.

		Raises an ``UnknownUpdateType`` exception if method cannot be determined
		or validated.
		"""

		method = None
		if "method" in check:
			method = check["method"]
		else:
			if "update_script" in check:
				method = "update_script"
			elif "pip" in check:
				method = "pip"
			elif "python_updater" in check:
				method = "python_updater"

		if method is None or (valid_methods and not method in valid_methods):
			raise exceptions.UnknownUpdateType()

		return method

	def _get_updater(self, target, check):
		"""
		Retrieves the updater for the given target and check configuration. Will raise an UnknownUpdateType if updater
		cannot be determined.
		"""

		mapping = dict(update_script=updaters.update_script,
		               pip=updaters.pip,
		               python_updater=updaters.python_updater)

		method = self._get_update_method(target, check, valid_methods=mapping.keys())
		return mapping[method]

	def _get_octoprint_checkout_folder(self, checks=None):
		if checks is None:
			checks = self._get_configured_checks()

		if not "octoprint" in checks:
			return None

		if "checkout_folder" in checks["octoprint"]:
			return checks["octoprint"]["checkout_folder"]
		elif "update_folder" in checks["octoprint"]:
			return checks["octoprint"]["update_folder"]

		return None


__plugin_name__ = "Software Update"
__plugin_author__ = "Gina Häußge"
__plugin_url__ = "http://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html"
__plugin_description__ = "Allows receiving update notifications and performing updates of OctoPrint and plugins"
__plugin_disabling_discouraged__ = gettext("Without this plugin OctoPrint will no longer be able to "
                                           "update itself or any of your installed plugins which might put "
                                           "your system at risk.")
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

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.cli.commands": cli.commands
	}


