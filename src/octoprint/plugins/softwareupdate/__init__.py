# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import copy
import hashlib
import io
import logging
import logging.handlers
import os
import threading
import time

# noinspection PyCompatibility
from concurrent import futures

import flask
import requests
from flask_babel import gettext

import octoprint.plugin
import octoprint.settings
from octoprint.access import ADMIN_GROUP, USER_GROUP
from octoprint.access.permissions import Permissions
from octoprint.server import BRANCH, NO_CONTENT, REVISION, VERSION
from octoprint.server.util.flask import (
    check_etag,
    no_firstrun_access,
    with_revalidation_checking,
)
from octoprint.util import dict_merge, get_formatted_size, to_unicode
from octoprint.util.pip import create_pip_caller
from octoprint.util.version import get_comparable_version, get_python_version_string

from . import cli, exceptions, updaters, util, version_checks

# OctoPi 0.15+
MINIMUM_PYTHON = "2.7.9"
MINIMUM_SETUPTOOLS = "39.0.1"
MINIMUM_PIP = "9.0.3"


##~~ Plugin


class SoftwareUpdatePlugin(
    octoprint.plugin.BlueprintPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.WizardPlugin,
    octoprint.plugin.EventHandlerPlugin,
):

    COMMIT_TRACKING_TYPES = ("github_commit", "bitbucket_commit")
    CURRENT_TRACKING_TYPES = COMMIT_TRACKING_TYPES + ("etag", "lastmodified", "jsondata")

    OCTOPRINT_RESTART_TYPES = ("pip", "single_file_plugin")

    DATA_FORMAT_VERSION = "v4"

    CHECK_OVERLAY_KEY = "softwareupdate_check_overlay"

    # noinspection PyMissingConstructor
    def __init__(self):
        self._update_in_progress = False
        self._configured_checks_mutex = threading.Lock()
        self._configured_checks = None
        self._refresh_configured_checks = False

        self._get_versions_mutex = threading.RLock()
        self._get_versions_data = None
        self._get_versions_data_ready = threading.Event()

        self._version_cache = {}
        self._version_cache_ttl = 0
        self._version_cache_path = None
        self._version_cache_dirty = False
        self._version_cache_timestamp = None

        self._overlay_cache = {}
        self._overlay_cache_ttl = 0
        self._overlay_cache_timestamp = None

        self._environment_supported = True
        self._environment_versions = {}
        self._environment_ready = threading.Event()

        self._storage_sufficient = True
        self.storage_info = {}

        self._console_logger = None

        self._get_throttled = lambda: False

    def initialize(self):
        self._console_logger = logging.getLogger(
            "octoprint.plugins.softwareupdate.console"
        )

        self._version_cache_ttl = self._settings.get_int(["cache_ttl"]) * 60
        self._version_cache_path = os.path.join(
            self.get_plugin_data_folder(), "versioncache.yaml"
        )
        self._load_version_cache()

        self._overlay_cache_ttl = self._settings.get_int(["check_overlay_ttl"]) * 60

        def refresh_checks(name, plugin):
            self._refresh_configured_checks = True
            self._send_client_message("update_versions")

        self._plugin_lifecycle_manager.add_callback("enabled", refresh_checks)
        self._plugin_lifecycle_manager.add_callback("disabled", refresh_checks)

    # Additional permissions hook

    def get_additional_permissions(self):
        return [
            {
                "key": "CHECK",
                "name": "Check",
                "description": gettext("Allows to check for software updates"),
                "roles": ["check"],
                "default_groups": [USER_GROUP],
            },
            {
                "key": "UPDATE",
                "name": "Update",
                "description": gettext("Allows to perform software updates"),
                "default_groups": [ADMIN_GROUP],
                "roles": ["update"],
                "dangerous": True,
            },
            {
                "key": "CONFIGURE",
                "name": "Configure",
                "description": gettext("Allows to configure software update"),
                "default_groups": [ADMIN_GROUP],
                "roles": ["configure"],
                "dangerous": True,
            },
        ]

    def on_startup(self, host, port):
        console_logging_handler = logging.handlers.RotatingFileHandler(
            self._settings.get_plugin_logfile_path(postfix="console"),
            maxBytes=2 * 1024 * 1024,
            encoding="utf-8",
        )
        console_logging_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        console_logging_handler.setLevel(logging.DEBUG)

        self._console_logger.addHandler(console_logging_handler)
        self._console_logger.setLevel(logging.DEBUG)
        self._console_logger.propagate = False

        helpers = self._plugin_manager.get_helpers("pi_support", "get_throttled")
        if helpers and "get_throttled" in helpers:
            self._get_throttled = helpers["get_throttled"]
            if self._settings.get_boolean(["ignore_throttled"]):
                self._logger.warning(
                    "!!! THROTTLE STATE IGNORED !!! You have configured the Software Update plugin to ignore an active throttle state of the underlying system. You might run into stability issues or outright corrupt your install. Consider fixing the throttling issue instead of suppressing it."
                )

    def on_after_startup(self):
        self._check_environment()
        self._check_storage()
        self.get_current_versions()

    def _get_configured_checks(self):
        with self._configured_checks_mutex:
            if (
                self._refresh_configured_checks
                or self._configured_checks is None
                or self._check_overlays_stale
            ):

                self._refresh_configured_checks = False

                overlays = self._get_check_overlays()
                self._configured_checks = self._settings.get(["checks"], merged=True)

                update_check_hooks = self._plugin_manager.get_hooks(
                    "octoprint.plugin.softwareupdate.check_config"
                )
                check_providers = {}

                effective_configs = {}

                for name, hook in update_check_hooks.items():
                    try:
                        hook_checks = hook()
                    except Exception:
                        self._logger.exception(
                            "Error while retrieving update information "
                            "from plugin {name}".format(**locals()),
                            extra={"plugin": name},
                        )
                    else:
                        for key, default_config in hook_checks.items():
                            if key in effective_configs or key == "octoprint":
                                if key == name:
                                    self._logger.warning(
                                        "Software update hook {} provides check for itself but that was already registered by {} - overwriting that third party registration now!".format(
                                            name, check_providers.get(key, "unknown hook")
                                        )
                                    )
                                else:
                                    self._logger.warning(
                                        "Software update hook {} tried to overwrite config for check {} but that was already configured elsewhere".format(
                                            name, key
                                        )
                                    )
                                    continue

                            check_providers[key] = name

                            yaml_config = {}
                            effective_config = copy.deepcopy(default_config)

                            if key in overlays:
                                effective_config = dict_merge(
                                    default_config, overlays[key]
                                )

                            if key in self._configured_checks:
                                yaml_config = self._configured_checks[key]
                                effective_config = dict_merge(
                                    effective_config, yaml_config, in_place=True
                                )

                                # Make sure there's nothing persisted in that check that shouldn't be persisted
                                #
                                # This used to be part of the settings migration (version 2) due to a bug - it can't
                                # stay there though since it interferes with manual entries to the checks not
                                # originating from within a plugin. Hence we do that step now here.
                                if (
                                    "type" not in effective_config
                                    or effective_config["type"]
                                    not in self.CURRENT_TRACKING_TYPES
                                ):
                                    deletables = ["current", "displayVersion"]
                                else:
                                    deletables = []
                                self._clean_settings_check(
                                    key,
                                    yaml_config,
                                    default_config,
                                    delete=deletables,
                                    save=False,
                                )

                            if effective_config:
                                effective_configs[key] = effective_config
                            else:
                                self._logger.warning(
                                    "Update for {} is empty or None, ignoring it".format(
                                        key
                                    )
                                )

                # finally set all our internal representations to our processed results
                for key, config in effective_configs.items():
                    self._configured_checks[key] = config

                # we only want to process checks that came from plugins for
                # which the plugins are still installed and enabled
                config_checks = self._settings.get(["checks"])
                plugin_and_not_enabled = (
                    lambda k: k in check_providers
                    and check_providers[k] not in self._plugin_manager.enabled_plugins
                )
                obsolete_plugin_checks = list(
                    filter(plugin_and_not_enabled, config_checks.keys())
                )
                for key in obsolete_plugin_checks:
                    self._logger.debug(
                        "Check for key {} was provided by plugin {} that's no longer available, ignoring it".format(
                            key, check_providers[key]
                        )
                    )
                    del self._configured_checks[key]

            return self._configured_checks

    def _check_environment(self):
        import pkg_resources

        local_pip = create_pip_caller(
            command=self._settings.global_get(["server", "commands", "localPipCommand"])
        )

        # check python and setuptools version
        versions = {
            "python": get_python_version_string(),
            "setuptools": pkg_resources.get_distribution("setuptools").version,
            "pip": local_pip.version_string,
        }
        supported = (
            get_comparable_version(versions["python"])
            >= get_comparable_version(MINIMUM_PYTHON)
            and get_comparable_version(versions["setuptools"])
            >= get_comparable_version(MINIMUM_SETUPTOOLS)
            and get_comparable_version(versions["pip"])
            >= get_comparable_version(MINIMUM_PIP)
        )

        self._environment_supported = supported
        self._environment_versions = versions
        self._environment_ready.set()

    def _check_storage(self):
        import distutils.sysconfig
        import tempfile

        import psutil

        storage_info = {}
        paths = {
            "python": distutils.sysconfig.get_python_lib(),
            "plugins": self._settings.global_get_basefolder("plugins"),
            "temp": tempfile.gettempdir(),
        }

        for key, path in paths.items():
            info = {"path": path, "free": None}

            try:
                data = psutil.disk_usage(path)
                info["free"] = data.free
            except Exception:
                self._logger.exception(
                    "Error while determining disk usage of {}".format(path)
                )
                continue

            storage_info[key] = info

        if len(storage_info):
            free_storage = min(*list(map(lambda x: x["free"], storage_info.values())))
        else:
            free_storage = None

        self._storage_sufficient = (
            free_storage is None
            or free_storage
            >= self._settings.get_int(["minimum_free_storage"]) * 1024 * 1024
        )
        self._storage_info = storage_info

        self._logger.info(
            "Minimum free storage across all update relevant locations is {}. "
            "That is considered {} for updating.".format(
                get_formatted_size(free_storage)
                if free_storage is not None
                else "unknown",
                "sufficient" if self._storage_sufficient else "insufficient",
            )
        )

    @property
    def _check_overlays_stale(self):
        return (
            self._overlay_cache is None
            or self._overlay_cache_timestamp is None
            or self._overlay_cache_timestamp + self._overlay_cache_ttl < time.time()
        )

    def _get_check_overlays(self, force=False):
        if self._check_overlays_stale or force:
            if self._connectivity_checker.online:
                # reload from URL
                url = self._settings.get(["check_overlay_url"])
                self._logger.info("Fetching check overlays from {}".format(url))
                try:
                    r = requests.get(url, timeout=3.1)
                    r.raise_for_status()
                    data = r.json()
                except Exception as exc:
                    self._logger.error(
                        "Could not fetch check overlay from {}: {}".format(url, exc)
                    )
                    self._overlay_cache = {}
                else:
                    self._overlay_cache = data

            else:
                self._logger.info("Not fetching check overlays, we are offline")
                self._overlay_cache = {}

            self._overlay_cache_timestamp = time.time()

            default_overlay = {}
            defaults = self.get_settings_defaults()
            for key in defaults["checks"]:
                if key in self._overlay_cache:
                    default_overlay[key] = self._overlay_cache[key]

            self._settings.remove_overlay(self.CHECK_OVERLAY_KEY)
            if default_overlay:
                self._settings.add_overlay(
                    {"checks": default_overlay}, key=self.CHECK_OVERLAY_KEY
                )

        return self._overlay_cache

    def _load_version_cache(self):
        if not os.path.isfile(self._version_cache_path):
            return

        import yaml

        try:
            with io.open(self._version_cache_path, "rt", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            timestamp = os.stat(self._version_cache_path).st_mtime
        except Exception:
            self._logger.exception("Error while loading version cache from disk")
        else:
            try:
                if not isinstance(data, dict):
                    self._logger.info(
                        "Version cache was created in a different format, not using it"
                    )
                    return

                if "__version" in data:
                    data_version = data["__version"]
                else:
                    self._logger.info(
                        "Can't determine version of OctoPrint version cache was created for, not using it"
                    )
                    return

                from octoprint._version import get_versions

                octoprint_version = get_versions()["version"]
                if data_version != octoprint_version:
                    self._logger.info(
                        "Version cache was created for another version of OctoPrint, not using it"
                    )
                    return

                self._version_cache = data
                self._version_cache_dirty = False
                self._version_cache_timestamp = timestamp
                self._logger.info("Loaded version cache from disk")
            except Exception:
                self._logger.exception("Error parsing in version cache data")

    def _save_version_cache(self):
        import yaml

        from octoprint._version import get_versions
        from octoprint.util import atomic_write

        octoprint_version = get_versions()["version"]
        self._version_cache["__version"] = octoprint_version

        with atomic_write(
            self._version_cache_path, mode="wt", max_permissions=0o666
        ) as file_obj:
            yaml.safe_dump(
                self._version_cache,
                stream=file_obj,
                default_flow_style=False,
                indent=2,
                allow_unicode=True,
            )

        self._version_cache_dirty = False
        self._version_cache_timestamp = time.time()
        self._logger.info("Saved version cache to disk")

    def _invalidate_version_cache(self, target):
        self._refresh_configured_checks = True
        try:
            del self._version_cache[target]
        except KeyError:
            pass
        self._version_cache_dirty = True

    # ~~ SettingsPlugin API

    def get_settings_defaults(self):
        update_script = os.path.join(self._basefolder, "scripts", "update-octoprint.py")
        default_update_script = (
            '{{python}} "{update_script}" --branch={{branch}} '
            '--force={{force}} "{{folder}}" {{target}}'.format(
                update_script=update_script
            )
        )

        return {
            "checks": {
                "octoprint": {
                    "type": "github_release",
                    "user": "foosel",
                    "repo": "OctoPrint",
                    "method": "pip",
                    "pip": "https://github.com/OctoPrint/OctoPrint/archive/{target_version}.zip",
                    "update_script": default_update_script,
                    "restart": "octoprint",
                    "stable_branch": {
                        "branch": "master",
                        "commitish": ["master"],
                        "name": "Stable",
                    },
                    "prerelease_branches": [
                        {
                            "branch": "rc/maintenance",
                            "commitish": ["rc/maintenance"],  # maintenance RCs
                            "name": "Maintenance RCs",
                        },
                        {
                            "branch": "rc/devel",
                            "commitish": [
                                "rc/maintenance",
                                "rc/devel",
                            ],  # devel & maintenance RCs
                            "name": "Devel RCs",
                        },
                    ],
                },
            },
            "pip_command": None,
            "cache_ttl": 24 * 60,
            "notify_users": True,
            "ignore_throttled": False,
            "minimum_free_storage": 150,
            "check_overlay_url": "https://plugins.octoprint.org/update_check_overlay.json",
            "check_overlay_ttl": 6 * 60,
            "credentials": {
                "github": None,
                "bitbucket_user": None,
                "bitbucket_password": None,
            },
        }

    def on_settings_load(self):
        # ensure we don't persist check configs we receive on the API
        data = dict(octoprint.plugin.SettingsPlugin.on_settings_load(self))
        if "checks" in data:
            del data["checks"]

        checks = self._get_configured_checks()

        # ~~ octoprint check settings

        if "octoprint" in checks:
            data["octoprint_checkout_folder"] = self._get_octoprint_checkout_folder(
                checks=checks
            )
            data["octoprint_tracked_branch"] = self._get_octoprint_tracked_branch(
                checks=checks
            )
            data["octoprint_pip_target"] = self._get_octoprint_pip_target(checks=checks)
            data["octoprint_type"] = checks["octoprint"].get("type", None)

            try:
                data["octoprint_method"] = self._get_update_method(
                    "octoprint", checks["octoprint"]
                )
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

        # ~~ pip check settings

        data["pip_enable_check"] = "pip" in checks

        return data

    def get_settings_restricted_paths(self):
        return {"never": [["credentials"]]}

    def on_settings_save(self, data):
        # ~~ plugin settings

        for key in self.get_settings_defaults():
            if key in (
                "checks",
                "cache_ttl",
                "check_overlay_ttl",
                "notify_user",
                "minimum_free_storage",
                "octoprint_checkout_folder",
                "octoprint_type",
                "octoprint_release_channel",
            ):
                continue
            if key in data:
                self._settings.set([key], data[key])

        if "cache_ttl" in data:
            self._settings.set_int(["cache_ttl"], data["cache_ttl"])
        self._version_cache_ttl = self._settings.get_int(["cache_ttl"]) * 60

        if "check_overlay_ttl" in data:
            self._settings.set_int(["check_overlay_ttl"], data["check_overlay_ttl"])
        self._overlay_cache_ttl = self._settings.get_int(["check_overlay_ttl"]) * 60

        if "notify_users" in data:
            self._settings.set_boolean(["notify_users"], data["notify_users"])

        if "minimum_free_storage" in data:
            self._settings.set_int(["minimum_free_storage"], data["minimum_free_storage"])
            self._check_storage()

        # ~~ octoprint check settings

        updated_octoprint_check_config = False

        if "octoprint_checkout_folder" in data:
            if data["octoprint_checkout_folder"]:
                # force=True as that path is not part of the default config
                self._settings.set(
                    ["checks", "octoprint", "checkout_folder"],
                    data["octoprint_checkout_folder"],
                    force=True,
                )
                if self._settings.get(["checks", "octoprint", "update_folder"]):
                    self._settings.remove(["checks", "octoprint", "update_folder"])
            else:
                self._settings.remove(["checks", "octoprint", "checkout_folder"])
            updated_octoprint_check_config = True

        if "octoprint_type" in data:
            octoprint_type = data["octoprint_type"]

            if octoprint_type == "github_release":
                self._settings.set(["checks", "octoprint", "type"], octoprint_type)
                self._settings.set(["checks", "octoprint", "method"], "pip")
                updated_octoprint_check_config = True

            elif octoprint_type == "github_commit":
                self._settings.set(["checks", "octoprint", "type"], octoprint_type)
                self._settings.set(["checks", "octoprint", "method"], "pip")
                updated_octoprint_check_config = True

            elif octoprint_type == "git_commit":
                self._settings.set(["checks", "octoprint", "type"], octoprint_type)
                self._settings.set(["checks", "octoprint", "method"], "update_script")
                updated_octoprint_check_config = True

        if "octoprint_tracked_branch" in data:
            if data["octoprint_tracked_branch"]:
                # force=True as that path is not part of the default config
                self._settings.set(
                    ["checks", "octoprint", "branch"],
                    data["octoprint_tracked_branch"],
                    force=True,
                )
            else:
                self._settings.remove(["checks", "octoprint", "branch"])
            updated_octoprint_check_config = True

        if "octoprint_pip_target" in data:
            self._settings.set(
                ["checks", "octoprint", "pip"], data["octoprint_pip_target"]
            )
            updated_octoprint_check_config = True

        if "octoprint_release_channel" in data:
            prerelease_branches = self._settings.get(
                ["checks", "octoprint", "prerelease_branches"]
            )
            if prerelease_branches and data["octoprint_release_channel"] in [
                x["branch"] for x in prerelease_branches
            ]:
                # force=True as those paths are not part of the default config
                self._settings.set(
                    ["checks", "octoprint", "prerelease"], True, force=True
                )
                self._settings.set(
                    ["checks", "octoprint", "prerelease_channel"],
                    data["octoprint_release_channel"],
                    force=True,
                )
            else:
                self._settings.remove(["checks", "octoprint", "prerelease"])
                self._settings.remove(["checks", "octoprint", "prerelease_channel"])
            updated_octoprint_check_config = True

        if updated_octoprint_check_config:
            self._invalidate_version_cache("octoprint")

        # ~~ pip check settings

        update_pip_check_config = False

        if "pip_enable_check" in data:
            pip_enable_check = (
                data["pip_enable_check"] in octoprint.settings.valid_boolean_trues
            )
            pip_check_currently_enabled = "pip" in self._settings.get(
                ["checks"], merged=True
            )

            if pip_enable_check != pip_check_currently_enabled:
                if pip_enable_check:
                    # force=True as that path is not part of the default config
                    self._settings.set(
                        ["checks", "pip"],
                        {
                            "type": "pypi_release",
                            "package": "pip",
                            "pip": "pip=={target_version}",
                        },
                        force=True,
                    )
                else:
                    self._settings.remove(["checks", "pip"])
                update_pip_check_config = True

        if update_pip_check_config:
            self._invalidate_version_cache("pip")

    def get_settings_version(self):
        return 9

    def on_settings_migrate(self, target, current=None):

        if current is None or current < 6:
            # up until & including config version 5 we didn't set the method parameter for the octoprint check
            # configuration

            configured_checks = self._settings.get(["checks"], incl_defaults=False)
            if configured_checks is not None and "octoprint" in configured_checks:
                octoprint_check = dict(configured_checks["octoprint"])

                if (
                    "method" not in octoprint_check
                    and octoprint_check.get("type") == "git_commit"
                ):
                    defaults = {
                        "plugins": {
                            "softwareupdate": {"checks": {"octoprint": {"method": "pip"}}}
                        }
                    }
                    self._settings.set(
                        ["checks", "octoprint", "method"],
                        "update_script",
                        defaults=defaults,
                    )

        if current == 4:
            # config version 4 didn't correctly remove the old settings for octoprint_restart_command
            # and environment_restart_command

            self._settings.set(["environment_restart_command"], None)
            self._settings.set(["octoprint_restart_command"], None)

        if current is None or current < 5:
            # config version 4 and higher moves octoprint_restart_command and
            # environment_restart_command to the core configuration

            # current plugin commands
            configured_octoprint_restart_command = self._settings.get(
                ["octoprint_restart_command"]
            )
            configured_environment_restart_command = self._settings.get(
                ["environment_restart_command"]
            )

            # current global commands
            configured_system_restart_command = self._settings.global_get(
                ["server", "commands", "systemRestartCommand"]
            )
            configured_server_restart_command = self._settings.global_get(
                ["server", "commands", "serverRestartCommand"]
            )

            # only set global commands if they are not yet set
            if (
                configured_system_restart_command is None
                and configured_environment_restart_command is not None
            ):
                self._settings.global_set(
                    ["server", "commands", "systemRestartCommand"],
                    configured_environment_restart_command,
                )
            if (
                configured_server_restart_command is None
                and configured_octoprint_restart_command is not None
            ):
                self._settings.global_set(
                    ["server", "commands", "serverRestartCommand"],
                    configured_octoprint_restart_command,
                )

            # delete current plugin commands from config
            self._settings.set(["environment_restart_command"], None)
            self._settings.set(["octoprint_restart_command"], None)

        if current is None or current == 2 or current == 8:
            # No config version and config version 2 and 8 need the same fix, stripping
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
                if (
                    "type" not in octoprint_check
                    or octoprint_check["type"] not in self.CURRENT_TRACKING_TYPES
                ):
                    deletables = ["current", "displayName", "displayVersion"]
                else:
                    deletables = []
                self._clean_settings_check(
                    "octoprint",
                    octoprint_check,
                    self.get_settings_defaults()["checks"]["octoprint"],
                    delete=deletables,
                    save=False,
                )

        elif current == 1:
            # config version 1 had the error that the octoprint check got accidentally
            # included in checks["octoprint"], leading to recursion and hence to
            # yaml parser errors

            configured_checks = self._settings.get(["checks"], incl_defaults=False)
            if configured_checks is None:
                return

            if (
                "octoprint" in configured_checks
                and "octoprint" in configured_checks["octoprint"]
            ):
                # that's a circular reference, back to defaults
                dummy_defaults = {"plugins": {}}
                dummy_defaults["plugins"][self._identifier] = {"checks": {}}
                dummy_defaults["plugins"][self._identifier]["checks"]["octoprint"] = None
                self._settings.set(["checks", "octoprint"], None, defaults=dummy_defaults)

        if current is None or current < 8:
            # remove check_providers again
            self._settings.remove(["check_providers"])

    def _clean_settings_check(self, key, data, defaults, delete=None, save=True):
        if not data:
            # nothing to do
            return data

        if delete is None:
            delete = []

        for k in data:
            if k in defaults and defaults[k] == data[k]:
                delete.append(k)

        for k in delete:
            if k in data:
                del data[k]

        dummy_defaults = {"plugins": {}}
        dummy_defaults["plugins"][self._identifier] = {"checks": {}}
        dummy_defaults["plugins"][self._identifier]["checks"][key] = defaults
        if len(data):
            self._settings.set(["checks", key], data, defaults=dummy_defaults)
        else:
            self._settings.remove(["checks", key], defaults=dummy_defaults)

        if save:
            self._settings.save()

        return data

    # ~~ BluePrint API

    @octoprint.plugin.BlueprintPlugin.route("/check", methods=["GET"])
    @no_firstrun_access
    @Permissions.PLUGIN_SOFTWAREUPDATE_CHECK.require(403)
    def check_for_update(self):
        request_data = flask.request.values

        if "targets" in request_data or "check" in request_data:
            check_targets = list(
                map(
                    lambda x: x.strip(),
                    request_data.get("targets", request_data.get("check", "")).split(","),
                )
            )
        else:
            check_targets = None

        force = (
            request_data.get("force", "false") in octoprint.settings.valid_boolean_trues
        )

        def view():
            self._environment_ready.wait(timeout=30.0)

            try:
                (
                    information,
                    update_available,
                    update_possible,
                ) = self.get_current_versions(check_targets=check_targets, force=force)

                storage = list()
                for key, name in (
                    ("python", gettext("Python package installation folder")),
                    ("plugins", gettext("Plugin folder")),
                    ("temp", gettext("System temporary files")),
                ):
                    data = self._storage_info.get(key)
                    if not data:
                        continue

                    s = {"name": name}
                    s.update(**data)
                    storage.append(s)

                status = "current"
                if self._update_in_progress:
                    status = "inProgress"
                elif (
                    update_available
                    and update_possible
                    and self._environment_supported
                    and self._storage_sufficient
                ):
                    status = "updatePossible"
                elif update_available:
                    status = "updateAvailable"

                return flask.jsonify(
                    {
                        "status": status,
                        "information": information,
                        "timestamp": self._version_cache_timestamp,
                        "environment": {
                            "supported": self._environment_supported,
                            "versions": [
                                {
                                    "name": gettext("Python"),
                                    "current": self._environment_versions.get(
                                        "python", "unknown"
                                    ),
                                    "minimum": MINIMUM_PYTHON,
                                },
                                {
                                    "name": gettext("pip"),
                                    "current": self._environment_versions.get(
                                        "pip", "unknown"
                                    ),
                                    "minimum": MINIMUM_PIP,
                                },
                                {
                                    "name": gettext("setuptools"),
                                    "current": self._environment_versions.get(
                                        "setuptools", "unknown"
                                    ),
                                    "minimum": MINIMUM_SETUPTOOLS,
                                },
                            ],
                        },
                        "storage": {
                            "sufficient": self._storage_sufficient,
                            "free": storage,
                        },
                    }
                )
            except exceptions.ConfigurationInvalid as e:
                return flask.make_response(
                    "Update not properly configured, can't proceed: {}".format(e), 500
                )

        def etag():
            checks = self._get_configured_checks()

            targets = check_targets
            if targets is None:
                targets = checks.keys()

            hash = hashlib.sha1()

            def hash_update(value):
                value = value.encode("utf-8")
                hash.update(value)

            targets = sorted(targets)
            for target in targets:
                current_hash = self._get_check_hash(checks.get(target, {}))
                if target in self._version_cache and not force:
                    data = self._version_cache[target]
                    hash_update(current_hash)
                    hash_update(
                        str(
                            data["timestamp"] + self._version_cache_ttl
                            >= time.time()
                            > data["timestamp"]
                        )
                    )
                    hash_update(repr(data["information"]))
                    hash_update(str(data["available"]))
                    hash_update(str(data["possible"]))
                    hash_update(str(data.get("online", None)))

            hash_update(",".join(targets))

            hash_update(str(self._environment_supported))
            hash_update(str(self._version_cache_timestamp))
            hash_update(str(self._overlay_cache_timestamp))
            hash_update(str(self._connectivity_checker.online))
            hash_update(str(self._update_in_progress))
            hash_update(self.DATA_FORMAT_VERSION)
            return hash.hexdigest()

        def condition():
            return check_etag(etag())

        return with_revalidation_checking(
            etag_factory=lambda *args, **kwargs: etag(),
            condition=lambda *args, **kwargs: condition(),
            unless=lambda: force or self._check_overlays_stale,
        )(view)()

    @octoprint.plugin.BlueprintPlugin.route("/update", methods=["POST"])
    @no_firstrun_access
    @Permissions.PLUGIN_SOFTWAREUPDATE_UPDATE.require(403)
    def perform_update(self):
        throttled = self._get_throttled()
        if (
            throttled
            and isinstance(throttled, dict)
            and throttled.get("current_issue", False)
            and not self._settings.get_boolean(["ignore_throttled"])
        ):
            # currently throttled, we refuse to run
            return flask.make_response(
                "System is currently throttled, refusing to update "
                "anything due to possible stability issues",
                409,
            )

        if self._printer.is_printing() or self._printer.is_paused():
            # do not update while a print job is running
            return flask.make_response("Printer is currently printing or paused", 409)

        if not self._environment_supported:
            return flask.make_response(
                "Direct updates are not supported in this Python environment", 409
            )

        if not self._storage_sufficient:
            return flask.make_response("Not enough free disk space for updating", 409)

        if "application/json" not in flask.request.headers["Content-Type"]:
            return flask.make_response("Expected content-type JSON", 400)

        json_data = flask.request.get_json(silent=True)
        if json_data is None:
            return flask.make_response("Invalid JSON", 400)

        if "targets" in json_data or "checks" in json_data:
            targets = list(
                map(
                    lambda x: x.strip(),
                    json_data.get("targets", json_data.get("check", [])),
                )
            )
        else:
            targets = None

        force = json_data.get("force", "false") in octoprint.settings.valid_boolean_trues

        to_be_checked, checks = self.perform_updates(targets=targets, force=force)
        return flask.jsonify({"order": to_be_checked, "checks": checks})

    @octoprint.plugin.BlueprintPlugin.route("/configure", methods=["POST"])
    @no_firstrun_access
    @Permissions.PLUGIN_SOFTWAREUPDATE_CONFIGURE.require(403)
    def configure_update(self):
        json_data = flask.request.get_json(silent=True)
        if json_data is None:
            return flask.make_response("Invalid JSON", 400)

        checks = self._get_configured_checks()

        settings_dirty = False
        for target, data in json_data.items():
            if target not in checks:
                continue

            try:
                populated_check = self._populated_check(target, checks[target])
            except exceptions.UnknownCheckType:
                self._logger.debug(
                    "Ignoring unknown check type for target {}".format(target)
                )
                continue
            except Exception:
                self._logger.exception(
                    "Error while populating check prior to configuration for target {}".format(
                        target
                    )
                )
                continue

            patch = {}

            # switched release channel
            if "channel" in data:
                if (
                    populated_check["type"] == "github_release"
                    and "stable_branch" in populated_check
                    and "prerelease_branches" in populated_check
                ):
                    valid_channel = data["channel"] == populated_check[
                        "stable_branch"
                    ].get("branch") or any(
                        map(
                            lambda x: data["channel"] == x.get("branch"),
                            populated_check["prerelease_branches"],
                        )
                    )
                    prerelease = data["channel"] != populated_check["stable_branch"].get(
                        "branch"
                    )

                    if valid_channel:
                        patch["prerelease"] = prerelease
                        patch["prerelease_channel"] = data["channel"]

            # disable/enable check
            if "disabled" in data:
                patch["disabled"] = (
                    data["disabled"] in octoprint.settings.valid_boolean_trues
                )

            # do we have changes to apply?
            if patch:
                current = self._settings.get(["checks", target], incl_defaults=False)
                updated = dict_merge(current, patch)
                self._settings.set(
                    ["checks", target],
                    updated,
                    defaults={"plugins": {"softwareupdate": {"checks": {target: {}}}}},
                )

                settings_dirty = True
                self._invalidate_version_cache(target)

        if settings_dirty:
            self._settings.save()

        return NO_CONTENT

    def is_blueprint_protected(self):
        return False

    # ~~ Asset API

    def get_assets(self):
        return {
            "css": ["css/softwareupdate.css"],
            "js": ["js/softwareupdate.js"],
            "clientjs": ["clientjs/softwareupdate.js"],
            "less": ["less/softwareupdate.less"],
        }

    ##~~ TemplatePlugin API

    def get_template_configs(self):
        from flask_babel import gettext

        return [{"type": "settings", "name": gettext("Software Update")}]

    ##~~ WizardPlugin API

    def is_wizard_required(self):
        checks = self._get_configured_checks()
        check = checks.get("octoprint", None)
        checkout_folder = self._get_octoprint_checkout_folder(checks=checks)
        return (
            check
            and "method" in check
            and check["method"] == "update_script"
            and not checkout_folder
        )

    ##~~ EventHandlerPlugin API

    def on_event(self, event, payload):
        from octoprint.events import Events

        if (
            event != Events.CONNECTIVITY_CHANGED
            or not payload
            or not payload.get("new", False)
        ):
            return

        thread = threading.Thread(target=self.get_current_versions)
        thread.daemon = True
        thread.start()

    # ~~ Updater

    def get_current_versions(self, check_targets=None, force=False):
        """
        Retrieves the current version information for all defined check_targets. Will retrieve information for all
        available targets by default.

        :param check_targets: an iterable defining the targets to check, if not supplied defaults to all targets
        """

        if force:
            self._get_check_overlays(force=True)

        checks = self._get_configured_checks()
        if check_targets is None:
            check_targets = list(checks.keys())

        update_available = False
        update_possible = False
        information = {}

        credentials = self._settings.get(["credentials"], merged=True)

        # we don't want to do the same work twice, so let's use a lock
        if self._get_versions_mutex.acquire(False):
            self._get_versions_data_ready.clear()
            try:
                futures_to_result = {}
                online = self._connectivity_checker.check_immediately()
                self._logger.debug(
                    "Looks like we are {}".format("online" if online else "offline")
                )

                with futures.ThreadPoolExecutor(max_workers=5) as executor:
                    for target, check in checks.items():
                        if target not in check_targets:
                            continue

                        if not check:
                            continue

                        try:
                            populated_check = self._populated_check(target, check)
                            future = executor.submit(
                                self._get_current_version,
                                target,
                                populated_check,
                                force=force,
                                credentials=credentials,
                            )
                            futures_to_result[future] = (target, populated_check)
                        except exceptions.UnknownCheckType:
                            self._logger.warning(
                                "Unknown update check type for target {}: {}".format(
                                    target, check.get("type", "<n/a>")
                                )
                            )
                            continue
                        except Exception:
                            self._logger.exception(
                                "Could not check {} for updates".format(target)
                            )
                            continue

                    for future in futures.as_completed(futures_to_result):

                        target, populated_check = futures_to_result[future]
                        if future.exception() is not None:
                            self._logger.error(
                                "Could not check {} for updates, error: {!r}".format(
                                    target, future.exception()
                                )
                            )
                            continue

                        (
                            target_information,
                            target_update_available,
                            target_update_possible,
                            target_online,
                            target_error,
                        ) = future.result()
                        target_update_possible = (
                            target_update_possible and self._environment_supported
                        )

                        target_information = dict_merge(
                            {
                                "local": {"name": "?", "value": "?"},
                                "remote": {
                                    "name": "?",
                                    "value": "?",
                                    "release_notes": None,
                                },
                                "needs_online": True,
                            },
                            target_information,
                        )

                        target_disabled = populated_check.get("disabled", False)
                        update_available = update_available or (
                            target_update_available and not target_disabled
                        )
                        update_possible = update_possible or (
                            target_update_possible
                            and target_update_available
                            and not target_disabled
                        )

                        local_name = target_information["local"]["name"]
                        local_value = target_information["local"]["value"]

                        release_notes = None
                        if (
                            target_information
                            and target_information["remote"]
                            and target_information["remote"]["value"]
                        ):
                            if (
                                "release_notes" in populated_check
                                and populated_check["release_notes"]
                            ):
                                release_notes = populated_check["release_notes"]
                            elif "release_notes" in target_information["remote"]:
                                release_notes = target_information["remote"][
                                    "release_notes"
                                ]

                            if release_notes:
                                release_notes = release_notes.format(
                                    octoprint_version=VERSION,
                                    target_name=target_information["remote"]["name"],
                                    target_version=target_information["remote"]["value"],
                                )

                        information[target] = {
                            "updateAvailable": target_update_available,
                            "updatePossible": target_update_possible,
                            "information": target_information,
                            "displayName": populated_check["displayName"],
                            "displayVersion": populated_check["displayVersion"].format(
                                octoprint_version=VERSION,
                                local_name=local_name,
                                local_value=local_value,
                            ),
                            "releaseNotes": release_notes,
                            "online": target_online,
                            "error": target_error,
                            "disabled": target_disabled,
                            "releaseChannels": {},
                        }

                        if (
                            populated_check["type"] == "github_release"
                            and "stable_branch" in populated_check
                            and "prerelease_branches" in populated_check
                        ):
                            # target supports release channels via github branches and releases
                            def to_release_channel(branch_info):
                                return {
                                    "name": branch_info["name"],
                                    "channel": branch_info["branch"],
                                }

                            stable_channel = populated_check["stable_branch"]["branch"]
                            current_channel = populated_check.get("prerelease_channel")
                            release_channels = [
                                to_release_channel(populated_check["stable_branch"]),
                            ] + list(
                                map(
                                    to_release_channel,
                                    populated_check["prerelease_branches"],
                                )
                            )
                            information[target]["releaseChannels"] = {
                                "available": release_channels,
                                "current": current_channel
                                if current_channel
                                else stable_channel,
                                "stable": stable_channel,
                            }

                        if "released_version" in populated_check:
                            information[target]["releasedVersion"] = populated_check[
                                "released_version"
                            ]

                if self._version_cache_dirty:
                    self._save_version_cache()

                self._get_versions_data = information, update_available, update_possible
                self._get_versions_data_ready.set()
            finally:
                self._get_versions_mutex.release()

        else:  # something's already in progress, let's wait for it to complete and use its result
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

        def hash_update(value):
            value = value.encode("utf-8")
            hash.update(value)

        hash_update(dict_to_sorted_repr(check))
        return hash.hexdigest()

    def _get_current_version(
        self, target, check, force=False, online=None, credentials=None
    ):
        """
        Determines the current version information for one target based on its check configuration.
        """

        current_hash = self._get_check_hash(check)
        if online is None:
            online = self._connectivity_checker.online
        if target in self._version_cache and not force:
            data = self._version_cache[target]
            if (
                data["hash"] == current_hash
                and data["timestamp"] + self._version_cache_ttl
                >= time.time()
                > data["timestamp"]
                and data.get("online", None) == online
            ):
                # we also check that timestamp < now to not get confused too much by clock changes
                return (
                    data["information"],
                    data["available"],
                    data["possible"],
                    data["online"],
                    data.get("error", None),
                )

        information = {}
        update_available = False
        error = None

        try:
            version_checker = self._get_version_checker(target, check)
            information, is_current = version_checker.get_latest(
                target, check, online=online, credentials=credentials
            )
            if information is not None:
                if (
                    is_current
                    and check["type"] in self.CURRENT_TRACKING_TYPES
                    and check["current"] is None
                ):
                    self._persist_check_current(
                        target, check, information["remote"]["value"]
                    )
                    del self._version_cache[target]
                    self._version_cache_dirty = True
                elif not is_current:
                    update_available = True
        except exceptions.CannotCheckOffline:
            update_possible = False
            information["needs_online"] = True
        except exceptions.UnknownCheckType:
            self._logger.warning(
                "Unknown check type {} for {}".format(check["type"], target)
            )
            update_possible = False
            error = "unknown_check"
        except exceptions.NetworkError:
            self._logger.warning(
                "Could not check {} for updates due to a network error".format(target)
            )
            update_possible = False
            error = "network"
        except exceptions.RateLimitCheckError as exc:
            self._logger.warning(
                "Could not check {} for updates due to running into a rate limit: {}".format(
                    target, exc
                )
            )
            update_possible = False
            error = "ratelimit"
        except exceptions.CheckError:
            self._logger.warning(
                "Could not check {} for updates due to a check error".format(target)
            )
            update_possible = False
            error = "check"
        except Exception:
            self._logger.exception("Could not check {} for updates".format(target))
            update_possible = False
            error = "unknown"
        else:
            try:
                updater = self._get_updater(target, check)
                update_possible = updater.can_perform_update(target, check, online=online)
            except Exception:
                self._logger.exception(
                    "Error while checking if {} can be updated".format(target)
                )
                update_possible = False

        disabled = check.get("disabled", False)

        self._version_cache[target] = {
            "timestamp": time.time(),
            "hash": current_hash,
            "information": information,
            "available": update_available,
            "possible": update_possible,
            "online": online,
            "error": error,
            "disabled": disabled,
        }
        self._version_cache_dirty = True
        return information, update_available, update_possible, online, error

    def perform_updates(self, force=False, **kwargs):
        """
        Performs the updates for the given check_targets. Will update all possible targets by default.

        :param targets: an iterable defining the targets to update, if not supplied defaults to all targets
        """

        if not self._environment_supported:
            self._logger.error("Direct updates are unsupported in this environment")
            return [], {}

        if not self._storage_sufficient:
            self._logger.error("Not enough free disk space for updating")
            return [], {}

        targets = kwargs.get("targets", kwargs.get("check_targets", None))

        checks = self._get_configured_checks()
        populated_checks = {}
        for target, check in checks.items():
            try:
                populated_checks[target] = self._populated_check(target, check)
            except exceptions.UnknownCheckType:
                self._logger.debug(
                    "Ignoring unknown check type for target {}".format(target)
                )
            except Exception:
                self._logger.exception(
                    "Error while populating check prior to update for target {}".format(
                        target
                    )
                )

        if targets is None:
            targets = populated_checks.keys()
        to_be_updated = sorted(set(targets) & set(populated_checks.keys()))
        if "octoprint" in to_be_updated:
            to_be_updated.remove("octoprint")
            tmp = ["octoprint"] + to_be_updated
            to_be_updated = tmp
        if "pip" in to_be_updated:
            to_be_updated.remove("pip")
            tmp = ["pip"] + to_be_updated
            to_be_updated = tmp

        updater_thread = threading.Thread(
            target=self._update_worker, args=(populated_checks, to_be_updated, force)
        )
        updater_thread.daemon = False
        updater_thread.start()

        check_data = dict(
            (key, check["displayName"] if "displayName" in check else key)
            for key, check in populated_checks.items()
            if key in to_be_updated
        )
        return to_be_updated, check_data

    def _update_worker(self, checks, check_targets, force):

        restart_type = None

        credentials = self._settings.get(["credentials"], merged=True)

        try:
            self._update_in_progress = True

            target_results = {}
            error = False

            ### iterate over all configured targets

            for target in check_targets:
                if target not in checks:
                    continue
                check = checks[target]

                if "enabled" in check and not check["enabled"]:
                    continue

                if target not in check_targets:
                    continue

                target_error, target_result = self._perform_update(
                    target, check, force, credentials=credentials
                )
                error = error or target_error
                if target_result is not None:
                    target_results[target] = target_result

                    if "restart" in check:
                        target_restart_type = check["restart"]
                    elif (
                        "pip" in check
                        or check.get("method") in self.OCTOPRINT_RESTART_TYPES
                    ):
                        target_restart_type = "octoprint"
                    else:
                        target_restart_type = None

                    # if our update requires a restart we have to determine which type
                    if restart_type is None or (
                        restart_type == "octoprint"
                        and target_restart_type == "environment"
                    ):
                        restart_type = target_restart_type

        finally:
            # we might have needed to update the config, so we'll save that now
            self._settings.save()

            # also, we are now longer updating
            self._update_in_progress = False

        if error:
            # if there was an unignorable error, we just return error
            self._send_client_message("error", {"results": target_results})

        else:
            self._save_version_cache()

            # otherwise the update process was a success, but we might still have to restart
            if restart_type is not None and restart_type in ("octoprint", "environment"):
                # one of our updates requires a restart of either type "octoprint" or "environment". Let's see if
                # we can actually perform that

                restart_command = None
                if restart_type == "octoprint":
                    restart_command = self._settings.global_get(
                        ["server", "commands", "serverRestartCommand"]
                    )
                elif restart_type == "environment":
                    restart_command = self._settings.global_get(
                        ["server", "commands", "systemRestartCommand"]
                    )

                if restart_command:
                    self._send_client_message(
                        "restarting",
                        {"restart_type": restart_type, "results": target_results},
                    )
                    try:
                        self._perform_restart(restart_command)
                    except exceptions.RestartFailed:
                        self._send_client_message(
                            "restart_failed",
                            {"restart_type": restart_type, "results": target_results},
                        )
                else:
                    # we don't have this restart type configured, we'll have to display a message that a manual
                    # restart is needed
                    self._send_client_message(
                        "restart_manually",
                        {"restart_type": restart_type, "results": target_results},
                    )
            else:
                self._send_client_message("success", {"results": target_results})

    def _perform_update(self, target, check, force, credentials=None):
        online = self._connectivity_checker.online

        information, update_available, update_possible, _, _ = self._get_current_version(
            target, check, online=online, credentials=credentials
        )

        if not update_available and not force:
            return False, None

        if not update_possible:
            self._logger.warning(
                "Cannot perform update for %s, update type is not fully configured"
                % target
            )
            return False, None

        # determine the target version to update to
        target_version = information["remote"]["value"]
        target_error = False
        target_result = None

        def trigger_event(success, **additional_payload):
            from octoprint.events import Events

            if success:
                # noinspection PyUnresolvedReferences
                event = Events.PLUGIN_SOFTWAREUPDATE_UPDATE_SUCCEEDED
            else:
                # noinspection PyUnresolvedReferences
                event = Events.PLUGIN_SOFTWAREUPDATE_UPDATE_FAILED

            payload = copy.copy(additional_payload)
            payload.update(
                {
                    "target": target,
                    "from_version": information["local"]["value"],
                    "to_version": target_version,
                }
            )

            self._event_bus.fire(event, payload=payload)

        ### The actual update procedure starts here...

        populated_check = self._populated_check(target, check)
        try:
            self._logger.info("Starting update of %s to %s..." % (target, target_version))
            self._send_client_message(
                "updating",
                {
                    "target": target,
                    "version": target_version,
                    "name": populated_check["displayName"],
                },
            )
            updater = self._get_updater(target, check)
            if updater is None:
                raise exceptions.UnknownUpdateType()

            update_result = updater.perform_update(
                target, populated_check, target_version, log_cb=self._log, online=online
            )
            target_result = ("success", update_result)
            self._logger.info("Update of %s to %s successful!" % (target, target_version))
            trigger_event(True)

        except exceptions.UnknownUpdateType:
            self._logger.warning(
                "Update of %s can not be performed, unknown update type" % target
            )
            self._send_client_message(
                "update_failed",
                {
                    "target": target,
                    "version": target_version,
                    "name": populated_check["displayName"],
                    "reason": "Unknown update type",
                },
            )
            return False, None

        except exceptions.CannotUpdateOffline:
            self._logger.warning(
                "Update of %s can not be performed, it's not marked as 'offline' capable but we are apparently offline right now"
                % target
            )
            self._send_client_message(
                "update_failed",
                {
                    "target": target,
                    "version": target_version,
                    "name": populated_check["displayName"],
                    "reason": "No internet connection",
                },
            )

        except Exception as e:
            self._logger.exception(
                "Update of %s can not be performed, please also check plugin_softwareupdate_console.log for possible causes of this"
                % target
            )
            trigger_event(False)

            if "ignorable" not in populated_check or not populated_check["ignorable"]:
                target_error = True

            if isinstance(e, exceptions.UpdateError):
                target_result = ("failed", e.data)
                self._send_client_message(
                    "update_failed",
                    {
                        "target": target,
                        "version": target_version,
                        "name": populated_check["displayName"],
                        "reason": e.data,
                    },
                )
            else:
                target_result = ("failed", None)
                self._send_client_message(
                    "update_failed",
                    {
                        "target": target,
                        "version": target_version,
                        "name": populated_check["displayName"],
                        "reason": "unknown",
                    },
                )

        else:
            # make sure that any external changes to config.yaml are loaded into the system
            self._settings.load()

            # persist the new version if necessary for check type
            self._persist_check_current(target, check, target_version)

            del self._version_cache[target]
            self._version_cache_dirty = True

        return target_error, target_result

    def _persist_check_current(self, target, check, current):
        if check["type"] not in self.CURRENT_TRACKING_TYPES:
            return

        self._settings.load()

        dummy_default = {"plugins": {}}
        dummy_default["plugins"][self._identifier] = {"checks": {}}
        dummy_default["plugins"][self._identifier]["checks"][target] = {"current": None}
        self._settings.set(["checks", target, "current"], current, defaults=dummy_default)

        # we have to save here (even though that makes us save quite often) since otherwise the next
        # load will overwrite our changes we just made
        self._settings.save()

        check["current"] = current

    def _perform_restart(self, restart_command):
        """
        Performs a restart using the supplied restart_command.
        """

        self._logger.info("Restarting...")
        try:
            util.execute(restart_command, evaluate_returncode=False, do_async=True)
        except exceptions.ScriptError as e:
            self._logger.exception(
                "Error while restarting via command {}".format(restart_command)
            )
            self._logger.warning("Restart stdout:\n{}".format(e.stdout))
            self._logger.warning("Restart stderr:\n{}".format(e.stderr))
            raise exceptions.RestartFailed()

    def _populated_check(self, target, check):
        from flask_babel import gettext

        if "type" not in check:
            raise exceptions.UnknownCheckType()

        result = dict(check)

        if target == "octoprint":

            from octoprint.util.version import (
                is_released_octoprint_version,
                is_stable_octoprint_version,
            )

            displayName = check.get("displayName")
            if displayName is None:
                # displayName missing or set to None
                displayName = gettext("OctoPrint")
            result["displayName"] = to_unicode(displayName, errors="replace")

            displayVersion = check.get("displayVersion")
            if displayVersion is None:
                # displayVersion missing or set to None
                displayVersion = "{octoprint_version}"
            result["displayVersion"] = to_unicode(displayVersion, errors="replace")

            stable_branch = "master"
            release_branches = []
            if "stable_branch" in check:
                release_branches.append(check["stable_branch"]["branch"])
                stable_branch = check["stable_branch"]["branch"]
            if "prerelease_branches" in check:
                release_branches += [x["branch"] for x in check["prerelease_branches"]]
            result["released_version"] = is_released_octoprint_version()

            if check["type"] in self.COMMIT_TRACKING_TYPES:
                result["current"] = REVISION if REVISION else "unknown"
            else:
                result["current"] = VERSION

                if check["type"] == "github_release" and (
                    check.get("prerelease", None) or not is_stable_octoprint_version()
                ):
                    # we are tracking github releases and are either also tracking prerelease OR are currently running
                    # a non stable version => we need to change some parameters

                    # we compare versions fully, not just the base so that we see a difference
                    # between RCs + stable for the same version release
                    result["force_base"] = False

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
                        result["update_branch"] = check.get(
                            "update_branch", stable_branch
                        )

                    if check.get("update_script", None):
                        # we force an exact version & python unequality check, to be able to downgrade
                        result["force_exact_version"] = True
                        result["release_compare"] = "python_unequal"
                    elif check.get("pip", None):
                        # we force python unequality check for pip installs, to be able to downgrade
                        result["release_compare"] = "python_unequal"
                        result["pip_command"] = check.get(
                            "pip_command",
                            self._settings.global_get(
                                ["server", "commands", "localPipCommand"]
                            ),
                        )

        elif target == "pip":
            import pkg_resources

            displayName = check.get("displayName")
            if displayName is None:
                # displayName missing or set to None
                displayName = gettext("pip")
            result["displayName"] = to_unicode(displayName, errors="replace")

            displayVersion = check.get("displayVersion")
            if displayVersion is None:
                # displayVersion missing or set to None
                distribution = pkg_resources.get_distribution("pip")
                if distribution:
                    displayVersion = distribution.version
            result["displayVersion"] = to_unicode(displayVersion, errors="replace")

            result["pip_command"] = check.get(
                "pip_command",
                self._settings.global_get(["server", "commands", "localPipCommand"]),
            )

        else:
            result["displayName"] = to_unicode(check.get("displayName"), errors="replace")
            if result["displayName"] is None:
                # displayName missing or None
                result["displayName"] = to_unicode(target, errors="replace")

            result["displayVersion"] = to_unicode(
                check.get("displayVersion", check.get("current")), errors="replace"
            )
            if result["displayVersion"] is None:
                # displayVersion AND current missing or None
                result["displayVersion"] = "unknown"

            if check["type"] in self.CURRENT_TRACKING_TYPES:
                result["current"] = check.get("current", None)
            else:
                result["current"] = check.get(
                    "current", check.get("displayVersion", None)
                )

        if "pip" in result:
            if (
                "pip_command" not in check
                and self._settings.get(["pip_command"]) is not None
            ):
                result["pip_command"] = self._settings.get(["pip_command"])

        return result

    def _log(self, lines, prefix=None, stream=None, strip=True):
        if strip:
            lines = list(map(lambda x: x.strip(), lines))

        self._send_client_message(
            "loglines",
            data={"loglines": [{"line": line, "stream": stream} for line in lines]},
        )
        for line in lines:
            self._console_logger.debug("{} {}".format(prefix, line))

    def _send_client_message(self, message_type, data=None):
        self._plugin_manager.send_plugin_message(
            self._identifier, {"type": message_type, "data": data}
        )

    def _get_version_checker(self, target, check):
        """
        Retrieves the version checker to use for given target and check configuration. Will raise an UnknownCheckType
        if version checker cannot be determined.
        """

        if "type" not in check:
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

        if method is None or (valid_methods and method not in valid_methods):
            raise exceptions.UnknownUpdateType()

        return method

    def _get_updater(self, target, check):
        """
        Retrieves the updater for the given target and check configuration. Will raise an UnknownUpdateType if updater
        cannot be determined.
        """

        method = self._get_update_method(target, check)
        if method is None:
            raise exceptions.UnknownUpdateType()

        updater = getattr(updaters, method)
        if updater is None:
            raise exceptions.UnknownUpdateType()

        return updater

    def _get_octoprint_checkout_folder(self, checks=None):
        if checks is None:
            checks = self._get_configured_checks()

        if "octoprint" not in checks:
            return None

        if "checkout_folder" in checks["octoprint"]:
            return checks["octoprint"]["checkout_folder"]
        elif "update_folder" in checks["octoprint"]:
            return checks["octoprint"]["update_folder"]

        return None

    def _get_octoprint_tracked_branch(self, checks=None):
        if checks is None:
            checks = self._get_configured_checks()

        if "octoprint" not in checks:
            return None

        return checks["octoprint"].get("branch")

    def _get_octoprint_pip_target(self, checks=None):
        if checks is None:
            checks = self._get_configured_checks()

        if "octoprint" not in checks:
            return None

        return checks["octoprint"].get("pip")


def _register_custom_events(*args, **kwargs):
    return ["update_succeeded", "update_failed"]


__plugin_name__ = "Software Update"
__plugin_author__ = "Gina Häußge"
__plugin_url__ = "http://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html"
__plugin_description__ = "Allows receiving update notifications and performing updates of OctoPrint and plugins"
__plugin_disabling_discouraged__ = gettext(
    "Without this plugin OctoPrint will no longer be able to "
    "update itself or any of your installed plugins which might put "
    "your system at risk."
)
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = SoftwareUpdatePlugin()

    global __plugin_helpers__
    __plugin_helpers__ = {
        "version_checks": version_checks,
        "updaters": updaters,
        "exceptions": exceptions,
        "util": util,
    }

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.cli.commands": cli.commands,
        "octoprint.events.register_custom_events": _register_custom_events,
        "octoprint.access.permissions": __plugin_implementation__.get_additional_permissions,
    }
