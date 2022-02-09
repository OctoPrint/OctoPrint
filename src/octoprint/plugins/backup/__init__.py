__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import octoprint.plugin
from octoprint.access import ADMIN_GROUP
from octoprint.access.permissions import Permissions
from octoprint.events import Events
from octoprint.server import NO_CONTENT
from octoprint.server.util.flask import no_firstrun_access
from octoprint.settings import default_settings
from octoprint.util import is_hidden_path, to_bytes, yaml
from octoprint.util.pip import create_pip_caller
from octoprint.util.platform import is_os_compatible
from octoprint.util.version import (
    get_comparable_version,
    get_octoprint_version,
    get_octoprint_version_string,
    is_octoprint_compatible,
)

try:
    import zlib  # check if zlib is available
except ImportError:
    zlib = None


import json
import logging
import os
import shutil
import sys
import tempfile
import threading
import time
import traceback
import zipfile

import flask
import requests
import sarge
from flask_babel import gettext

from octoprint.plugins.pluginmanager import DEFAULT_PLUGIN_REPOSITORY
from octoprint.settings import valid_boolean_trues
from octoprint.util import get_formatted_size
from octoprint.util.text import sanitize

UNKNOWN_PLUGINS_FILE = "unknown_plugins_from_restore.json"

BACKUP_DATE_TIME_FMT = "%Y%m%d-%H%M%S"

MAX_UPLOAD_SIZE = 1024 * 1024 * 1024  # 1GB


class BackupPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.BlueprintPlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.WizardPlugin,
):

    _pip_caller = None

    # noinspection PyMissingConstructor
    def __init__(self):
        self._in_progress = []
        self._in_progress_lock = threading.RLock()

    # Additional permissions hook

    def get_additional_permissions(self):
        return [
            {
                "key": "ACCESS",
                "name": "Backup access",
                "description": gettext("Allows access to backups and restores"),
                "roles": ["access"],
                "dangerous": True,
                "default_groups": [ADMIN_GROUP],
            }
        ]

    # Socket emit hook

    def socket_emit_hook(self, socket, user, message, payload, *args, **kwargs):
        if message != "event" or payload["type"] != Events.PLUGIN_BACKUP_BACKUP_CREATED:
            return True

        return user and user.has_permission(Permissions.PLUGIN_BACKUP_ACCESS)

    ##~~ StartupPlugin

    def on_after_startup(self):
        self._clean_dir_backup(self._settings._basedir, on_log_progress=self._logger.info)

    ##~~ SettingsPlugin

    def get_settings_defaults(self):
        return {"restore_unsupported": False}

    ##~~ AssetPlugin

    def get_assets(self):
        return {
            "js": ["js/backup.js"],
            "clientjs": ["clientjs/backup.js"],
            "css": ["css/backup.css"],
            "less": ["less/backup.less"],
        }

    ##~~ TemplatePlugin

    def get_template_configs(self):
        return [
            {"type": "settings", "name": gettext("Backup & Restore")},
            {"type": "wizard", "name": gettext("Restore Backup?")},
        ]

    def get_template_vars(self):
        return {
            "max_upload_size": MAX_UPLOAD_SIZE,
            "max_upload_size_str": get_formatted_size(MAX_UPLOAD_SIZE),
        }

    ##~~ BlueprintPlugin

    @octoprint.plugin.BlueprintPlugin.route("/", methods=["GET"])
    @no_firstrun_access
    @Permissions.PLUGIN_BACKUP_ACCESS.require(403)
    def get_state(self):
        backups = self._get_backups()
        unknown_plugins = self._get_unknown_plugins()
        return flask.jsonify(
            backups=backups,
            backup_in_progress=len(self._in_progress) > 0,
            unknown_plugins=unknown_plugins,
            restore_supported=self._restore_supported(self._settings),
            max_upload_size=MAX_UPLOAD_SIZE,
        )

    @octoprint.plugin.BlueprintPlugin.route("/unknown_plugins", methods=["GET"])
    @no_firstrun_access
    @Permissions.PLUGIN_BACKUP_ACCESS.require(403)
    def get_unknown_plugins(self):
        # TODO add caching
        unknown_plugins = self._get_unknown_plugins()
        return flask.jsonify(unknown_plugins=unknown_plugins)

    @octoprint.plugin.BlueprintPlugin.route("/unknown_plugins", methods=["DELETE"])
    @no_firstrun_access
    @Permissions.PLUGIN_BACKUP_ACCESS.require(403)
    def delete_unknown_plugins(self):
        data_file = os.path.join(self.get_plugin_data_folder(), UNKNOWN_PLUGINS_FILE)
        try:
            os.remove(data_file)
        except Exception:
            pass
        return NO_CONTENT

    @octoprint.plugin.BlueprintPlugin.route("/backup", methods=["GET"])
    @no_firstrun_access
    @Permissions.PLUGIN_BACKUP_ACCESS.require(403)
    def get_backups(self):
        backups = self._get_backups()
        return flask.jsonify(backups=backups)

    @octoprint.plugin.BlueprintPlugin.route("/backup", methods=["POST"])
    @no_firstrun_access
    @Permissions.PLUGIN_BACKUP_ACCESS.require(403)
    def create_backup(self):

        data = flask.request.json
        exclude = data.get("exclude", [])
        filename = self._build_backup_filename(settings=self._settings)

        self._start_backup(exclude, filename)

        response = flask.jsonify(started=True, name=filename)
        response.status_code = 201
        return response

    @octoprint.plugin.BlueprintPlugin.route("/backup/<filename>", methods=["DELETE"])
    @no_firstrun_access
    @Permissions.PLUGIN_BACKUP_ACCESS.require(403)
    def delete_backup(self, filename):
        self._delete_backup(filename)

        return NO_CONTENT

    @octoprint.plugin.BlueprintPlugin.route("/restore", methods=["POST"])
    def perform_restore(self):
        if not Permissions.PLUGIN_BACKUP_ACCESS.can() and not self._settings.global_get(
            ["server", "firstRun"]
        ):
            flask.abort(403)

        if not self._restore_supported(self._settings):
            flask.abort(
                400,
                description="Invalid request, the restores are not "
                "supported on the underlying operating system",
            )

        input_name = "file"
        input_upload_path = (
            input_name
            + "."
            + self._settings.global_get(["server", "uploads", "pathSuffix"])
        )

        if input_upload_path in flask.request.values:
            # file to restore was uploaded
            path = flask.request.values[input_upload_path]

        elif flask.request.json and "path" in flask.request.json:
            # existing backup is supposed to be restored
            backup_folder = self.get_plugin_data_folder()
            path = os.path.realpath(
                os.path.join(backup_folder, flask.request.json["path"])
            )
            if (
                not path.startswith(backup_folder)
                or not os.path.exists(path)
                or is_hidden_path(path)
            ):
                return flask.abort(404)

        else:
            flask.abort(
                400,
                description="Invalid request, neither a file nor a path of a file to "
                "restore provided",
            )

        def on_install_plugins(plugins):
            force_user = self._settings.global_get_boolean(
                ["plugins", "pluginmanager", "pip_force_user"]
            )
            pip_args = self._settings.global_get(["plugins", "pluginmanager", "pip_args"])

            def on_log(line):
                self._logger.info(line)
                self._send_client_message("logline", {"line": line, "type": "stdout"})

            for plugin in plugins:
                octoprint_compatible = is_octoprint_compatible(
                    *plugin["compatibility"]["octoprint"]
                )
                os_compatible = is_os_compatible(plugin["compatibility"]["os"])
                compatible = octoprint_compatible and os_compatible
                if not compatible:
                    if not octoprint_compatible and not os_compatible:
                        self._logger.warning(
                            "Cannot install plugin {}, it is incompatible to this version "
                            "of OctoPrint and the underlying operating system".format(
                                plugin["id"]
                            )
                        )
                    elif not octoprint_compatible:
                        self._logger.warning(
                            "Cannot install plugin {}, it is incompatible to this version "
                            "of OctoPrint".format(plugin["id"])
                        )
                    elif not os_compatible:
                        self._logger.warning(
                            "Cannot install plugin {}, it is incompatible to the underlying "
                            "operating system".format(plugin["id"])
                        )
                    self._send_client_message(
                        "plugin_incompatible",
                        {
                            "plugin": plugin["id"],
                            "octoprint_compatible": octoprint_compatible,
                            "os_compatible": os_compatible,
                        },
                    )
                    continue

                self._logger.info("Installing plugin {}".format(plugin["id"]))
                self._send_client_message("installing_plugin", {"plugin": plugin["id"]})
                self.__class__._install_plugin(
                    plugin,
                    force_user=force_user,
                    pip_command=self._settings.global_get(
                        ["server", "commands", "localPipCommand"]
                    ),
                    pip_args=pip_args,
                    on_log=on_log,
                )

        def on_report_unknown_plugins(plugins):
            self._send_client_message("unknown_plugins", payload={"plugins": plugins})

        def on_log_progress(line):
            self._logger.info(line)
            self._send_client_message(
                "logline", payload={"line": line, "stream": "stdout"}
            )

        def on_log_error(line, exc_info=None):
            self._logger.error(line, exc_info=exc_info)
            self._send_client_message(
                "logline", payload={"line": line, "stream": "stderr"}
            )

            if exc_info is not None:
                exc_type, exc_value, exc_tb = exc_info
                output = traceback.format_exception(exc_type, exc_value, exc_tb)
                for line in output:
                    self._send_client_message(
                        "logline", payload={"line": line.rstrip(), "stream": "stderr"}
                    )

        def on_restore_start(path):
            self._send_client_message("restore_started")

        def on_restore_done(path):
            self._send_client_message("restore_done")

        def on_restore_failed(path):
            self._send_client_message("restore_failed")

        def on_invalid_backup(line):
            on_log_error(line)

        archive = tempfile.NamedTemporaryFile(delete=False)
        archive.close()
        shutil.copy(path, archive.name)
        path = archive.name

        # noinspection PyTypeChecker
        thread = threading.Thread(
            target=self._restore_backup,
            args=(path,),
            kwargs={
                "settings": self._settings,
                "plugin_manager": self._plugin_manager,
                "datafolder": self.get_plugin_data_folder(),
                "on_install_plugins": on_install_plugins,
                "on_report_unknown_plugins": on_report_unknown_plugins,
                "on_invalid_backup": on_invalid_backup,
                "on_log_progress": on_log_progress,
                "on_log_error": on_log_error,
                "on_restore_start": on_restore_start,
                "on_restore_done": on_restore_done,
                "on_restore_failed": on_restore_failed,
            },
        )
        thread.daemon = True
        thread.start()

        return flask.jsonify(started=True)

    def is_blueprint_protected(self):
        return False

    ##~~ WizardPlugin

    def is_wizard_required(self):
        return self._settings.global_get(["server", "firstRun"]) and is_os_compatible(
            ["!windows"]
        )

    def get_wizard_details(self):
        return {"required": self.is_wizard_required()}

    ##~~ tornado hook

    def route_hook(self, *args, **kwargs):
        from octoprint.server import app
        from octoprint.server.util.flask import admin_validator
        from octoprint.server.util.tornado import (
            LargeResponseHandler,
            access_validation_factory,
            path_validation_factory,
        )
        from octoprint.util import is_hidden_path

        return [
            (
                r"/download/(.*)",
                LargeResponseHandler,
                {
                    "path": self.get_plugin_data_folder(),
                    "as_attachment": True,
                    "path_validation": path_validation_factory(
                        lambda path: not is_hidden_path(path), status_code=404
                    ),
                    "access_validation": access_validation_factory(app, admin_validator),
                },
            )
        ]

    def bodysize_hook(self, current_max_body_sizes, *args, **kwargs):
        # max upload size for the restore endpoint
        return [("POST", r"/restore", MAX_UPLOAD_SIZE)]

    # Exported plugin helpers
    def create_backup_helper(self, exclude=None, filename=None):
        """
        .. versionadded:: 1.6.0

        Create a backup from a plugin or other internal call

        This helper is exported as ``create_backup`` and can be used from the plugin
        manager's ``get_helpers`` method.

        **Example**

        The following code snippet can be used from within a plugin, and will create a backup
        excluding two folders (``timelapse`` and ``uploads``)

        .. code-block:: python

            helpers = self._plugin_manager.get_helpers("backup", "create_backup")

            if helpers and "create_backup" in helpers:
                helpers["create_backup"](exclude=["timelapse", "uploads"])

        By using the ``if helpers [...]`` clause, plugins can fall back to other methods
        when they are running under versions where these helpers did not exist.


        :param list exclude: Names of data folders to exclude, defaults to None
        :param str filename: Name of backup to be created, if None (default) the backup
            name will be auto-generated. This should use a ``.zip`` extension.
        """
        if exclude is None:
            exclude = []
        if not isinstance(exclude, list):
            exclude = list(exclude)

        self._start_backup(exclude, filename=filename)

    def delete_backup_helper(self, filename):
        """
        .. versionadded:: 1.6.0

        Delete the specified backup from a plugin or other internal call

        This helper is exported as ``delete_backup`` and can be used through the plugin
        manager's ``get_helpers`` method.

        **Example**
        The following code snippet can be used from within a plugin, and will attempt to
        delete the backup named ``ExampleBackup.zip``.

        .. code-block:: python

            helpers = self._plugin_manager.get_helpers("backup", "delete_backup")

            if helpers and "delete_backup" in helpers:
                helpers["delete_backup"]("ExampleBackup.zip")

        By using the ``if helpers [...]`` clause, plugins can fall back to other methods
        when they are running under versions where these helpers did not exist.

        .. warning::

            This method will fail silently if the backup does not exist, and so
            it is recommended that you make sure the name comes from a verified source,
            for example the name from the events or other helpers.

        :param str filename: The name of the backup to delete
        """
        self._delete_backup(filename)

    ##~~ CLI hook

    def cli_commands_hook(self, cli_group, pass_octoprint_ctx, *args, **kwargs):
        import click

        @click.command("backup")
        @click.option(
            "--exclude",
            multiple=True,
            help="Identifiers of data folders to exclude, e.g. 'uploads' to exclude uploads or "
            "'timelapse' to exclude timelapses.",
        )
        @click.option(
            "--path",
            type=click.Path(),
            default=None,
            help="Specify full path to backup file to be created",
        )
        def backup_command(exclude, path):
            """
            Creates a new backup.
            """

            settings = octoprint.plugin.plugin_settings_for_settings_plugin(
                "backup", self, settings=cli_group.settings
            )

            if path is not None:
                datafolder, filename = os.path.split(os.path.abspath(path))
            else:
                filename = self._build_backup_filename(settings=settings)
                datafolder = os.path.join(settings.getBaseFolder("data"), "backup")

            if not os.path.isdir(datafolder):
                os.makedirs(datafolder)

            click.echo(f"Creating backup at {filename}, please wait...")
            self._create_backup(
                filename,
                exclude=exclude,
                settings=settings,
                plugin_manager=cli_group.plugin_manager,
                datafolder=datafolder,
            )
            click.echo("Done.")
            click.echo(f"Backup located at {os.path.join(datafolder, filename)}")

        @click.command("restore")
        @click.argument("path")
        def restore_command(path):
            """
            Restores an existing backup from the backup zip provided as argument.

            OctoPrint does not need to run for this to proceed.
            """
            settings = octoprint.plugin.plugin_settings_for_settings_plugin(
                "backup", self, settings=cli_group.settings
            )
            plugin_manager = cli_group.plugin_manager

            datafolder = os.path.join(settings.getBaseFolder("data"), "backup")
            if not os.path.isdir(datafolder):
                os.makedirs(datafolder)

            # register plugin manager plugin setting overlays
            plugin_info = plugin_manager.get_plugin_info("pluginmanager")
            if plugin_info and plugin_info.implementation:
                default_settings_overlay = {"plugins": {}}
                default_settings_overlay["plugins"][
                    "pluginmanager"
                ] = plugin_info.implementation.get_settings_defaults()
                settings.add_overlay(default_settings_overlay, at_end=True)

            if not os.path.isabs(path):
                datafolder = os.path.join(settings.getBaseFolder("data"), "backup")
                if not os.path.isdir(datafolder):
                    os.makedirs(datafolder)
                path = os.path.join(datafolder, path)

            if not os.path.exists(path):
                click.echo(f"Backup {path} does not exist", err=True)
                sys.exit(-1)

            archive = tempfile.NamedTemporaryFile(delete=False)
            archive.close()
            shutil.copy(path, archive.name)
            path = archive.name

            def on_install_plugins(plugins):
                if not plugins:
                    return

                force_user = settings.global_get_boolean(
                    ["plugins", "pluginmanager", "pip_force_user"]
                )
                pip_args = settings.global_get(["plugins", "pluginmanager", "pip_args"])

                def log(line):
                    click.echo(f"\t{line}")

                for plugin in plugins:
                    octoprint_compatible = is_octoprint_compatible(
                        *plugin["compatibility"]["octoprint"]
                    )
                    os_compatible = is_os_compatible(plugin["compatibility"]["os"])
                    compatible = octoprint_compatible and os_compatible
                    if not compatible:
                        if not octoprint_compatible and not os_compatible:
                            click.echo(
                                "Cannot install plugin {}, it is incompatible to this version of "
                                "OctoPrint and the underlying operating system".format(
                                    plugin["id"]
                                )
                            )
                        elif not octoprint_compatible:
                            click.echo(
                                "Cannot install plugin {}, it is incompatible to this version of "
                                "OctoPrint".format(plugin["id"])
                            )
                        elif not os_compatible:
                            click.echo(
                                "Cannot install plugin {}, it is incompatible to the underlying "
                                "operating system".format(plugin["id"])
                            )
                        continue

                    click.echo("Installing plugin {}".format(plugin["id"]))
                    self.__class__._install_plugin(
                        plugin,
                        force_user=force_user,
                        pip_command=settings.global_get(
                            ["server", "commands", "localPipCommand"]
                        ),
                        pip_args=pip_args,
                        on_log=log,
                    )

            def on_report_unknown_plugins(plugins):
                if not plugins:
                    return

                click.echo(
                    "The following plugins were not found in the plugin repository. You'll need to install them manually."
                )
                for plugin in plugins:
                    click.echo(
                        "\t{} (Homepage: {})".format(
                            plugin["name"], plugin["url"] if plugin["url"] else "?"
                        )
                    )

            def on_log_progress(line):
                click.echo(line)

            def on_log_error(line, exc_info=None):
                click.echo(line, err=True)

                if exc_info is not None:
                    exc_type, exc_value, exc_tb = exc_info
                    output = traceback.format_exception(exc_type, exc_value, exc_tb)
                    for line in output:
                        click.echo(line.rstrip(), err=True)

            if self._restore_backup(
                path,
                settings=settings,
                plugin_manager=plugin_manager,
                datafolder=datafolder,
                on_install_plugins=on_install_plugins,
                on_report_unknown_plugins=on_report_unknown_plugins,
                on_log_progress=on_log_progress,
                on_log_error=on_log_error,
                on_invalid_backup=on_log_error,
            ):
                click.echo(f"Restored from {path}")
            else:
                click.echo(f"Restoring from {path} failed", err=True)

        return [backup_command, restore_command]

    ##~~ helpers

    def _start_backup(self, exclude, filename=None):
        if filename is None:
            filename = self._build_backup_filename(settings=self._settings)

        def on_backup_start(name, temporary_path, exclude):
            self._logger.info(
                "Creating backup zip at {} (excluded: {})...".format(
                    temporary_path, ",".join(exclude) if len(exclude) else "-"
                )
            )

            with self._in_progress_lock:
                self._in_progress.append(name)
                self._send_client_message("backup_started", payload={"name": name})

        def on_backup_done(name, final_path, exclude):
            with self._in_progress_lock:
                self._in_progress.remove(name)
                self._send_client_message("backup_done", payload={"name": name})

            self._logger.info("... done creating backup zip.")

            self._event_bus.fire(
                Events.PLUGIN_BACKUP_BACKUP_CREATED,
                {"name": name, "path": final_path, "excludes": exclude},
            )

        def on_backup_error(name, exc_info):
            with self._in_progress_lock:
                try:
                    self._in_progress.remove(name)
                except ValueError:
                    # we'll ignore that
                    pass

            self._send_client_message(
                "backup_error", payload={"name": name, "error": f"{exc_info[1]}"}
            )
            self._logger.error("Error while creating backup zip", exc_info=exc_info)

        thread = threading.Thread(
            target=self._create_backup,
            args=(filename,),
            kwargs={
                "exclude": exclude,
                "settings": self._settings,
                "plugin_manager": self._plugin_manager,
                "logger": self._logger,
                "datafolder": self.get_plugin_data_folder(),
                "on_backup_start": on_backup_start,
                "on_backup_done": on_backup_done,
                "on_backup_error": on_backup_error,
            },
        )
        thread.daemon = True
        thread.start()

    def _delete_backup(self, filename):
        """
        Delete the backup specified
        Args:
            filename (str): Name of backup to delete
        """
        backup_folder = self.get_plugin_data_folder()
        full_path = os.path.realpath(os.path.join(backup_folder, filename))
        if (
            full_path.startswith(backup_folder)
            and os.path.exists(full_path)
            and not is_hidden_path(full_path)
        ):
            try:
                os.remove(full_path)
            except Exception:
                self._logger.exception(f"Could not delete {filename}")
                raise

    def _get_backups(self):
        backups = []
        for entry in os.scandir(self.get_plugin_data_folder()):
            if is_hidden_path(entry.path):
                continue
            if not entry.is_file():
                continue
            if not entry.name.endswith(".zip"):
                continue

            backups.append(
                {
                    "name": entry.name,
                    "date": entry.stat().st_mtime,
                    "size": entry.stat().st_size,
                    "url": flask.url_for("index")
                    + "plugin/backup/download/"
                    + entry.name,
                }
            )
        return backups

    def _get_unknown_plugins(self):
        data_file = os.path.join(self.get_plugin_data_folder(), UNKNOWN_PLUGINS_FILE)
        if os.path.exists(data_file):
            try:
                with open(data_file, encoding="utf-8") as f:
                    unknown_plugins = json.load(f)

                assert isinstance(unknown_plugins, list)
                assert all(
                    map(
                        lambda x: isinstance(x, dict)
                        and "key" in x
                        and "name" in x
                        and "url" in x,
                        unknown_plugins,
                    )
                )

                installed_plugins = self._plugin_manager.plugins
                unknown_plugins = list(
                    filter(lambda x: x["key"] not in installed_plugins, unknown_plugins)
                )
                if not unknown_plugins:
                    # no plugins left uninstalled, delete data file
                    try:
                        os.remove(data_file)
                    except Exception:
                        self._logger.exception(
                            "Error while deleting list of unknown plugins at {}".format(
                                data_file
                            )
                        )

                return unknown_plugins
            except Exception:
                self._logger.exception(
                    "Error while reading list of unknown plugins from {}".format(
                        data_file
                    )
                )
                try:
                    os.remove(data_file)
                except Exception:
                    self._logger.exception(
                        "Error while deleting list of unknown plugins at {}".format(
                            data_file
                        )
                    )

        return []

    @classmethod
    def _clean_dir_backup(cls, basedir, on_log_progress=None):
        basedir_backup = basedir + ".bck"

        if os.path.exists(basedir_backup):

            def remove_bck():
                if callable(on_log_progress):
                    on_log_progress(
                        "Found config folder backup from prior restore, deleting it..."
                    )
                shutil.rmtree(basedir_backup)
                if callable(on_log_progress):
                    on_log_progress("... deleted.")

            thread = threading.Thread(target=remove_bck)
            thread.daemon = True
            thread.start()

    @classmethod
    def _get_disk_size(cls, path, ignored=None):
        if ignored is None:
            ignored = []

        if path in ignored:
            return 0

        total = 0
        for entry in os.scandir(path):
            if entry.is_dir():
                total += cls._get_disk_size(entry.path, ignored=ignored)
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
        except Exception:
            logger.exception(
                f"Error while fetching the plugin repository data from {url}"
            )
            return {}

        from octoprint.plugins.pluginmanager import map_repository_entry

        return {plugin["id"]: plugin for plugin in map(map_repository_entry, r.json())}

    @classmethod
    def _install_plugin(
        cls, plugin, force_user=False, pip_command=None, pip_args=None, on_log=None
    ):
        if pip_args is None:
            pip_args = []

        if on_log is None:
            on_log = logging.getLogger(__name__).info

        # prepare pip caller
        def log(prefix, *lines):
            for line in lines:
                on_log(f"{prefix} {line.rstrip()}")

        def log_call(*lines):
            log(">", *lines)

        def log_stdout(*lines):
            log("<", *lines)

        def log_stderr(*lines):
            log("!", *lines)

        if cls._pip_caller is None:
            cls._pip_caller = create_pip_caller(
                command=pip_command, force_user=force_user
            )

        cls._pip_caller.on_log_call = log_call
        cls._pip_caller.on_log_stdout = log_stdout
        cls._pip_caller.on_log_stderr = log_stderr

        # install plugin
        pip = ["install", sarge.shell_quote(plugin["archive"]), "--no-cache-dir"]

        if plugin.get("follow_dependency_links"):
            pip.append("--process-dependency-links")

        if force_user:
            pip.append("--user")

        if pip_args:
            pip += pip_args

        cls._pip_caller.execute(*pip)

    @classmethod
    def _create_backup(
        cls,
        name,
        exclude=None,
        settings=None,
        plugin_manager=None,
        logger=None,
        datafolder=None,
        on_backup_start=None,
        on_backup_done=None,
        on_backup_error=None,
    ):
        if logger is None:
            logger = logging.getLogger(__name__)

        exclude_by_default = (
            "generated",
            "logs",
            "watched",
        )

        try:
            if exclude is None:
                exclude = []
            if not isinstance(exclude, list):
                exclude = list(exclude)

            if "timelapse" in exclude:
                exclude.append("timelapse_tmp")

            current_excludes = list(exclude)
            additional_excludes = list()
            plugin_data = settings.global_get_basefolder("data")
            for plugin, hook in plugin_manager.get_hooks(
                "octoprint.plugin.backup.additional_excludes"
            ).items():
                try:
                    additional = hook(current_excludes)
                    if isinstance(additional, list):
                        if "." in additional:
                            current_excludes.append(os.path.join("data", plugin))
                            additional_excludes.append(os.path.join(plugin_data, plugin))
                        else:
                            current_excludes += map(
                                lambda x: os.path.join("data", plugin, x), additional
                            )
                            additional_excludes += map(
                                lambda x: os.path.join(plugin_data, plugin, x), additional
                            )
                except Exception:
                    logger.exception(
                        f"Error while retrieving additional excludes "
                        f"from plugin {name}",
                        extra={"plugin": plugin},
                    )

            configfile = settings._configfile
            basedir = settings._basedir

            temporary_path = os.path.join(datafolder, f".{name}")
            final_path = os.path.join(datafolder, name)

            own_folder = datafolder
            defaults = [os.path.join(basedir, "config.yaml"),] + [
                os.path.join(basedir, folder)
                for folder in default_settings["folder"].keys()
            ]

            # check how many bytes we are about to backup
            size = os.stat(configfile).st_size
            for folder in default_settings["folder"].keys():
                if folder in exclude or folder in exclude_by_default:
                    continue
                size += cls._get_disk_size(
                    settings.global_get_basefolder(folder),
                    ignored=[
                        own_folder,
                    ],
                )
            size += cls._get_disk_size(
                basedir,
                ignored=defaults
                + [
                    own_folder,
                ],
            )

            # since we can't know the compression ratio beforehand, we assume we need the same amount of space
            if not cls._free_space(os.path.dirname(temporary_path), size):
                raise InsufficientSpace()

            compression = zipfile.ZIP_DEFLATED if zlib else zipfile.ZIP_STORED

            if callable(on_backup_start):
                on_backup_start(name, temporary_path, exclude)

            with zipfile.ZipFile(
                temporary_path, mode="w", compression=compression, allowZip64=True
            ) as zip:

                def add_to_zip(source, target, ignored=None):
                    if ignored is None:
                        ignored = []

                    if source in ignored:
                        return

                    if os.path.isdir(source):
                        for entry in os.scandir(source):
                            add_to_zip(
                                entry.path,
                                os.path.join(target, entry.name),
                                ignored=ignored,
                            )
                    elif os.path.isfile(source):
                        zip.write(source, arcname=target)

                # add metadata
                metadata = {
                    "version": get_octoprint_version_string(),
                    "excludes": exclude,
                }
                zip.writestr("metadata.json", json.dumps(metadata))

                # backup current config file
                add_to_zip(
                    configfile,
                    "basedir/config.yaml",
                    ignored=[
                        own_folder,
                    ],
                )

                # backup configured folder paths
                for folder in default_settings["folder"].keys():
                    if folder in exclude or folder in exclude_by_default:
                        continue

                    add_to_zip(
                        settings.global_get_basefolder(folder),
                        "basedir/" + folder.replace("_", "/"),
                        ignored=[
                            own_folder,
                        ]
                        + additional_excludes,
                    )

                # backup anything else that might be lying around in our basedir
                add_to_zip(
                    basedir,
                    "basedir",
                    ignored=defaults
                    + [
                        own_folder,
                    ]
                    + additional_excludes,
                )

                # add list of installed plugins
                helpers = plugin_manager.get_helpers(
                    "pluginmanager", "generate_plugins_json"
                )
                if helpers and "generate_plugins_json" in helpers:
                    plugins = helpers["generate_plugins_json"](
                        settings=settings, plugin_manager=plugin_manager
                    )

                    if len(plugins):
                        zip.writestr("plugin_list.json", json.dumps(plugins))

            shutil.move(temporary_path, final_path)

            if callable(on_backup_done):
                on_backup_done(name, final_path, exclude)

        except Exception as exc:  # noqa: F841
            # TODO py3: use the exception, not sys.exc_info()
            if callable(on_backup_error):
                exc_info = sys.exc_info()
                try:
                    on_backup_error(name, exc_info)
                finally:
                    del exc_info
            raise

    @classmethod
    def _restore_backup(
        cls,
        path,
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
        on_restore_failed=None,
    ):
        if not cls._restore_supported(settings):
            if callable(on_log_error):
                on_log_error("Restore is not supported on this operating system")
            if callable(on_restore_failed):
                on_restore_failed(path)
            return False

        restart_command = settings.global_get(
            ["server", "commands", "serverRestartCommand"]
        )

        basedir = settings._basedir
        cls._clean_dir_backup(basedir, on_log_progress=on_log_progress)

        repo_url = settings.global_get(["plugins", "pluginmanager", "repository"])
        if not repo_url:
            repo_url = DEFAULT_PLUGIN_REPOSITORY

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
                        on_invalid_backup("Not an OctoPrint backup, lacks metadata.json")
                    if callable(on_restore_failed):
                        on_restore_failed(path)
                    return False

                metadata_bytes = zip.read(metadata_zipinfo)
                metadata = json.loads(metadata_bytes)

                backup_version = get_comparable_version(metadata["version"], cut=1)
                if backup_version > get_octoprint_version(cut=1):
                    if callable(on_invalid_backup):
                        on_invalid_backup(
                            "Backup is from a newer version of OctoPrint and cannot be applied"
                        )
                    if callable(on_restore_failed):
                        on_restore_failed(path)
                    return False

                # unzip to temporary folder
                temp = tempfile.mkdtemp()
                try:
                    if callable(on_log_progress):
                        on_log_progress(f"Unpacking backup to {temp}...")

                    abstemp = os.path.abspath(temp)
                    dirs = {}
                    for member in zip.infolist():
                        abspath = os.path.abspath(os.path.join(temp, member.filename))
                        if abspath.startswith(abstemp):
                            date_time = time.mktime(member.date_time + (0, 0, -1))

                            zip.extract(member, temp)

                            if os.path.isdir(abspath):
                                dirs[abspath] = date_time
                            else:
                                os.utime(abspath, (date_time, date_time))

                    # set time on folders
                    for abspath, date_time in dirs.items():
                        os.utime(abspath, (date_time, date_time))

                    # sanity check
                    configfile = os.path.join(temp, "basedir", "config.yaml")
                    if not os.path.exists(configfile):
                        if callable(on_invalid_backup):
                            on_invalid_backup("Backup lacks config.yaml")
                        if callable(on_restore_failed):
                            on_restore_failed(path)
                        return False

                    configdata = yaml.load_from_file(path=configfile)

                    userfile = os.path.join(temp, "basedir", "users.yaml")
                    if not os.path.exists(userfile):
                        if callable(on_invalid_backup):
                            on_invalid_backup("Backup lacks users.yaml")
                        if callable(on_restore_failed):
                            on_restore_failed(path)
                        return False

                    if callable(on_log_progress):
                        on_log_progress("Unpacked")

                    # install available plugins
                    plugins = []
                    plugin_list_file = os.path.join(temp, "plugin_list.json")
                    if os.path.exists(plugin_list_file):
                        with open(os.path.join(temp, "plugin_list.json"), "rb") as f:
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
                                on_log_progress(
                                    "Known and installable plugins: {}".format(
                                        ", ".join(map(lambda x: x["id"], known_plugins))
                                    )
                                )
                            if unknown_plugins:
                                on_log_progress(
                                    "Unknown plugins: {}".format(
                                        ", ".join(
                                            map(lambda x: x["key"], unknown_plugins)
                                        )
                                    )
                                )

                        if callable(on_install_plugins):
                            on_install_plugins(known_plugins)

                        if callable(on_report_unknown_plugins):
                            on_report_unknown_plugins(unknown_plugins)

                    # move config data
                    basedir_backup = basedir + ".bck"
                    basedir_extracted = os.path.join(temp, "basedir")

                    if callable(on_log_progress):
                        on_log_progress(f"Renaming {basedir} to {basedir_backup}...")
                    shutil.move(basedir, basedir_backup)

                    try:
                        if callable(on_log_progress):
                            on_log_progress(f"Moving {basedir_extracted} to {basedir}...")
                        shutil.move(basedir_extracted, basedir)
                    except Exception:
                        if callable(on_log_error):
                            on_log_error(
                                "Error while restoring config data",
                                exc_info=sys.exc_info(),
                            )
                            on_log_error("Rolling back old config data")

                        shutil.move(basedir_backup, basedir)

                        if callable(on_restore_failed):
                            on_restore_failed(path)
                        return False

                    if unknown_plugins:
                        if callable(on_log_progress):
                            on_log_progress("Writing info file about unknown plugins")

                        if not os.path.isdir(datafolder):
                            os.makedirs(datafolder)

                        unknown_plugins_path = os.path.join(
                            datafolder, UNKNOWN_PLUGINS_FILE
                        )
                        try:
                            with open(unknown_plugins_path, mode="wb") as f:
                                f.write(to_bytes(json.dumps(unknown_plugins)))
                        except Exception:
                            if callable(on_log_error):
                                on_log_error(
                                    "Could not persist list of unknown plugins to {}".format(
                                        unknown_plugins_path
                                    ),
                                    exc_info=sys.exc_info(),
                                )

                finally:
                    if callable(on_log_progress):
                        on_log_progress("Removing temporary unpacked folder")
                    shutil.rmtree(temp)

        except Exception:
            exc_info = sys.exc_info()
            try:
                if callable(on_log_error):
                    on_log_error("Error while running restore", exc_info=exc_info)
                if callable(on_restore_failed):
                    on_restore_failed(path)
            finally:
                del exc_info
            return False

        finally:
            # remove zip
            if callable(on_log_progress):
                on_log_progress("Removing temporary zip")
            os.remove(path)

        # restart server
        if not restart_command:
            restart_command = (
                configdata.get("server", {})
                .get("commands", {})
                .get("serverRestartCommand")
            )

        if restart_command:
            import sarge

            if callable(on_log_progress):
                on_log_progress("Restarting...")
            if callable(on_restore_done):
                on_restore_done(path)

            try:
                sarge.run(restart_command, close_fds=True, async_=True)
            except Exception:
                if callable(on_log_error):
                    on_log_error(
                        f"Error while restarting via command {restart_command}",
                        exc_info=sys.exc_info(),
                    )
                    on_log_error("Please restart OctoPrint manually")
                return False

        else:
            if callable(on_restore_done):
                on_restore_done(path)
            if callable(on_log_error):
                on_log_error(
                    "No restart command configured. Please restart OctoPrint manually."
                )

        return True

    @classmethod
    def _build_backup_filename(cls, settings):
        if settings.global_get(["appearance", "name"]) == "":
            backup_prefix = "octoprint"
        else:
            backup_prefix = settings.global_get(["appearance", "name"])
        backup_prefix = sanitize(backup_prefix)
        return "{}-backup-{}.zip".format(
            backup_prefix, time.strftime(BACKUP_DATE_TIME_FMT)
        )

    @classmethod
    def _restore_supported(cls, settings):
        return (
            is_os_compatible(["!windows"])
            and not settings.get_boolean(["restore_unsupported"])
            and os.environ.get("OCTOPRINT_BACKUP_RESTORE_UNSUPPORTED", False)
            not in valid_boolean_trues
        )

    def _send_client_message(self, message, payload=None):
        if payload is None:
            payload = {}
        payload["type"] = message
        self._plugin_manager.send_plugin_message(self._identifier, payload)


class InsufficientSpace(Exception):
    pass


def _register_custom_events(*args, **kwargs):
    return ["backup_created"]


__plugin_name__ = "Backup & Restore"
__plugin_author__ = "Gina Häußge"
__plugin_description__ = "Backup & restore your OctoPrint settings and data"
__plugin_disabling_discouraged__ = gettext(
    "Without this plugin you will no longer be able to backup "
    "& restore your OctoPrint settings and data."
)
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = BackupPlugin()
__plugin_hooks__ = {
    "octoprint.server.http.routes": __plugin_implementation__.route_hook,
    "octoprint.server.http.bodysize": __plugin_implementation__.bodysize_hook,
    "octoprint.cli.commands": __plugin_implementation__.cli_commands_hook,
    "octoprint.access.permissions": __plugin_implementation__.get_additional_permissions,
    "octoprint.events.register_custom_events": _register_custom_events,
    "octoprint.server.sockjs.emit": __plugin_implementation__.socket_emit_hook,
}
__plugin_helpers__ = {
    "create_backup": __plugin_implementation__.create_backup_helper,
    "delete_backup": __plugin_implementation__.delete_backup_helper,
}
