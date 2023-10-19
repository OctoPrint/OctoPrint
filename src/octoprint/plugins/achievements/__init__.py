__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2023 The OctoPrint Project - Released under terms of the AGPLv3 License"


import datetime
import json
import os
import threading

from flask import abort, jsonify
from flask_babel import gettext
from pydantic import BaseModel

import octoprint.plugin
import octoprint.util
from octoprint.access import ADMIN_GROUP, READONLY_GROUP, USER_GROUP
from octoprint.access.permissions import Permissions
from octoprint.util.version import get_octoprint_version


class InstanceStats(BaseModel):
    created: int = 0
    """Timestamp of when stats collection was started."""

    created_version: str = ""
    """Version of OctoPrint when stats collection was started."""

    last_version: str = ""
    """Version of OctoPrint during last start, used for keeping track of updates."""

    seen_versions: int = 0
    """Number of different versions seen."""

    server_starts: int = 0
    """Number of times OctoPrint was started."""

    prints_started: int = 0
    """Number of prints started."""

    prints_cancelled: int = 0
    """Number of prints cancelled."""

    prints_errored: int = 0
    """Number of prints errored."""

    prints_finished: int = 0
    """Number of prints finished."""

    print_duration_total: float = 0
    """Total print duration."""

    print_duration_cancelled: float = 0
    """Total print duration of cancelled prints."""

    print_duration_errored: float = 0
    """Total print duration of errored prints."""

    print_duration_finished: float = 0
    """Total print duration of finished prints."""

    longest_print_duration: float = 0
    """Duration of longest print."""

    longest_print_date: int = 0
    """Timestamp of longest print."""

    files_uploaded: int = 0
    """Number of files uploaded."""

    files_deleted: int = 0
    """Number of files deleted."""


class Data(BaseModel):
    stats: InstanceStats
    achievements: dict[str, int]


class Achievement(BaseModel):
    key: str = ""
    name: str = ""
    description: str = ""


class AchievementsMetaClass(type):
    achievements = {}

    def __new__(mcs, name, bases, args):
        cls = type.__new__(mcs, name, bases, args)

        for key, value in args.items():
            if isinstance(value, Achievement):
                value.key = key.lower()
                mcs.achievements[key] = value

        return cls


class Achievements(metaclass=AchievementsMetaClass):
    THE_WIZARD = Achievement(
        name="The wizard",
        description="Complete the first run setup wizard.",
    )

    HANG_IN_THERE = Achievement(
        name="Hang in there!",
        description="Pause the same print ten times.",
    )

    ONE_SMALL_STEP_FOR_MAN = Achievement(
        name="That's one small step for man", description="Finish your first print."
    )

    ALL_BEGINNINGS_ARE_HARD = Achievement(
        name="All beginnings are hard", description="Cancel your first print."
    )

    CROSSOVER_EPISODE = Achievement(
        name="What is this, a crossover episode?",
        description="Connect to a printer running Klipper.",
    )

    ADVENTURER = Achievement(
        name="Adventurer",
        description="Install a plugin.",
    )

    TINKERER = Achievement(
        name="Tinkerer",
        description="Install a plugin from a URL.",
    )

    BETTER_SAFE_THAN_SORRY = Achievement(
        name="Better safe than sorry",
        description="Create a backup.",
    )


class AchievementsPlugin(
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.TemplatePlugin,
):
    def __init__(self):
        super().__init__()
        self._data = None
        self._data_mutex = threading.Lock()

        self._pause_counter = 0

    def initialize(self):
        self._load_data_file()
        return super().initialize()

    ##~~ Additional permissions hook

    def get_additional_permissions(self):
        return [
            {
                "key": "VIEW",
                "name": "View instance achievements & stats",
                "description": gettext(
                    "Allows to view the instance achievements & stats."
                ),
                "default_groups": [[READONLY_GROUP, USER_GROUP, ADMIN_GROUP]],
                "roles": ["view"],
            }
        ]

    ##~ StartupPlugin

    def on_startup(self, *args, **kwargs):
        self._data.stats.server_starts += 1

        version = get_octoprint_version()
        if self._data.stats.last_version != version.base_version:
            self._data.stats.seen_versions += 1
            self._data.stats.last_version = version.base_version

        if not self._has_achievement(
            Achievements.THE_WIZARD
        ) and not self._settings.get_boolean(["server", "firstRun"]):
            self._trigger_achievement(Achievements.THE_WIZARD, write=False)

        self._write_data_file()

    ##~~ EventHandlerPlugin

    def on_event(self, event, payload, *args, **kwargs):
        from octoprint.events import Events

        changed = False

        if event == Events.PRINT_STARTED:
            self._pause_counter = 0
            self._data.stats.prints_started += 1
            changed = True

        elif event == Events.PRINT_DONE:
            self._data.stats.prints_finished += 1
            self._data.stats.print_duration_total += payload["time"]
            self._data.stats.print_duration_finished += payload["time"]

            if payload["time"] > self._data.stats.longest_print_duration:
                self._data.stats.longest_print_duration = payload["time"]
                self._data.stats.longest_print_date = datetime.datetime.now().timestamp()

            self._trigger_achievement(Achievements.ONE_SMALL_STEP_FOR_MAN, write=False)

            changed = True

        elif event == Events.PRINT_FAILED or event == Events.PRINT_CANCELLED:
            self._data.stats.print_duration_total += payload["time"]

            if Events.PRINT_CANCELLED:
                self._trigger_achievement(
                    Achievements.ALL_BEGINNINGS_ARE_HARD, write=False
                )

            changed = True

        elif event == Events.PRINT_PAUSED:
            self._pause_counter += 1
            if self._pause_counter >= 10:
                self._trigger_achievement(Achievements.HANG_IN_THERE, write=False)

        elif event == Events.PLUGIN_BACKUP_BACKUP_CREATED:
            self._trigger_achievement(Achievements.BETTER_SAFE_THAN_SORRY)

        elif event == Events.PLUGIN_PLUGINMANAGER_INSTALL_PLUGIN:
            self._trigger_achievement(Achievements.ADVENTURER)

        if changed:
            self._write_data_file()

    ##~~ SimpleApiPlugin

    def on_api_get(self, request, *args, **kwargs):
        if not Permissions.PLUGIN_ACHIEVEMENTS_VIEW.can():
            abort(403)
        return jsonify(self._data.dict())

    ##~~ AssetPlugin

    def get_assets(self):
        return {
            "clientjs": ["clientjs/achievements.js"],
            "js": ["js/achievements.js"],
        }

    ##~~ TemplatePlugin

    def get_template_configs(self):
        return [
            {
                "type": "about",
                "name": gettext("Achievements"),
                "template": "achievements_about.jinja2",
                "custom_bindings": True,
            },
        ]

    ##~~ Internal helpers

    def _has_achievement(self, achievement):
        return achievement.key in self._data.achievements

    def _trigger_achievement(self, achievement, write=True):
        if self._has_achievement(achievement):
            return

        self._data.achievements[achievement.key] = int(
            datetime.datetime.now().timestamp()
        )
        if write:
            self._write_data_file()

        self._logger.info(f"New achievement unlocked: {achievement.name}!")

        # TODO: trigger notification

    @property
    def _data_path(self):
        return os.path.join(self.get_plugin_data_folder(), "data.json")

    def _reset_data(self):
        self._data = Data(
            stats=InstanceStats(
                created=datetime.datetime.now().timestamp(),
                created_version=get_octoprint_version().base_version,
            ),
            achievements={},
        )

    def _load_data_file(self):
        path = self._data_path

        with self._data_mutex:
            if not os.path.exists(path):
                self._logger.info("No data file found, starting with empty data")
                self._reset_data()
                return

            try:
                with open(path) as f:
                    self._logger.info(f"Loading data from {path}")
                    data = json.load(f)

                self._data = Data(**data)
            except Exception as e:
                self._logger.exception(f"Error loading data from {path}: {e}")
                self._logger.error("Starting with empty data")
                self._reset_data()

    def _write_data_file(self):
        with self._data_mutex:
            self._logger.debug(f"Writing data to {self._data_path}")
            with octoprint.util.atomic_write(self._data_path, mode="wb") as f:
                f.write(
                    octoprint.util.to_bytes(
                        json.dumps(self._data.dict(), indent=2, separators=(",", ": "))
                    )
                )


__plugin_name__ = "Achievements Plugin"
__plugin_author__ = "Gina Häußge"
__plugin_description__ = "Achievements & stats about your OctoPrint instance"
__plugin_disabling_discouraged__ = gettext(
    "Without this plugin you will no longer be able to earn achievements and track stats about your OctoPrint instance."
)
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = AchievementsPlugin()
__plugin_hooks__ = {
    "octoprint.access.permissions": __plugin_implementation__.get_additional_permissions
}
