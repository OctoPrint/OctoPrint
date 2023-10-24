__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2023 The OctoPrint Project - Released under terms of the AGPLv3 License"


import datetime
import json
import os
import threading
from typing import Dict, List

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

    prints_started_per_weekday: Dict[int, int] = {}
    """Number of prints started per weekday."""

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
    achievements: Dict[str, int]


class Achievement(BaseModel):
    key: str = ""
    name: str = ""
    description: str = ""
    hidden: bool = False
    nag: bool = False


class AchievedAchievement(Achievement):
    achieved: int


class ApiResponse(BaseModel):
    stats: InstanceStats
    achievements: List[Achievement]
    hidden_achievements: int


class AchievementsMetaClass(type):
    achievements = {}

    def __new__(mcs, name, bases, args):
        cls = type.__new__(mcs, name, bases, args)

        for key, value in args.items():
            if isinstance(value, Achievement):
                value.key = key.lower()
                mcs.achievements[key] = value

        return cls

    def all(cls):
        return cls.achievements.values()


class Achievements(metaclass=AchievementsMetaClass):
    THE_WIZARD = Achievement(
        name="The Wizard",
        description="Complete the first run setup wizard.",
    )

    ONE_SMALL_STEP_FOR_MAN = Achievement(
        name="That's One Small Step For Man", description="Finish your first print."
    )

    ALL_BEGINNINGS_ARE_HARD = Achievement(
        name="All Beginnings Are Hard", description="Cancel your first print."
    )

    ONE_OF_THOSE_DAYS = Achievement(
        name="Must Be One Of Those Days",
        description="Cancel ten consecutive prints.",
    )

    ADVENTURER = Achievement(
        name="The Adventurer",
        description="Install a plugin.",
    )

    TINKERER = Achievement(
        name="The Tinkerer",
        description="Install a plugin from a URL.",
    )

    BETTER_SAFE_THAN_SORRY = Achievement(
        name="Better Safe Than Sorry",
        description="Create a backup.",
    )

    CLEAN_HOUSE_I = Achievement(
        name="Clean House I",
        description="Delete one hundred files.",
        hidden=True,
    )

    CLEAN_HOUSE_II = Achievement(
        name="Clean House II",
        description="Delete five hundred files.",
        hidden=True,
    )

    CLEAN_HOUSE_III = Achievement(
        name="Clean House III",
        description="Delete one thousand files.",
        hidden=True,
    )

    THE_COLLECTOR_I = Achievement(
        name="The Collector I",
        description="Upload one hundred files.",
        hidden=True,
        nag=True,
    )

    THE_COLLECTOR_II = Achievement(
        name="The Collector II",
        description="Upload five hundred files.",
        hidden=True,
        nag=True,
    )

    THE_COLLECTOR_III = Achievement(
        name="The Collector III",
        description="Upload one thousand files.",
        hidden=True,
        nag=True,
    )

    THE_HOUSEKEEPER = Achievement(
        name="The Housekeeper",
        description="Create a folder.",
        hidden=True,
    )

    HANG_IN_THERE = Achievement(
        name="Hang In There!",
        description="Pause the same print ten times.",
        hidden=True,
    )

    CROSSOVER_EPISODE = Achievement(
        name="What Is This, A Crossover Episode?",
        description="Connect to a printer running Klipper.",
        hidden=True,
    )

    HAPPY_BIRTHDAY_FOOSEL = Achievement(
        name="Happy Birthday, foosel",
        description="Start a print on foosel's birthday.",
        hidden=True,
    )

    HAPPY_BIRTHDAY_OCTOPRINT = Achievement(
        name="Happy Birthday, OctoPrint",
        description="Start a print on OctoPrint's birthday.",
        hidden=True,
    )

    EARLY_BIRD = Achievement(
        name="Early Bird",
        description="Start a print between 03:00 and 07:00.",
        hidden=True,
    )

    NIGHT_OWL = Achievement(
        name="Night Owl",
        description="Start a print between 23:00 and 03:00.",
        hidden=True,
    )

    TGIF = Achievement(
        name="TGIF",
        description="Start a print on a Friday.",
    )

    MARATHON = Achievement(
        name="Marathon",
        description="Finish a print that took longer than 24 hours.",
        nag=True,
    )

    HALF_MARATHON = Achievement(
        name="Half Marathon",
        description="Finish a print that took longer than 12 hours.",
        nag=True,
    )

    SPRINT = Achievement(
        name="Sprint",
        description="Finish a print that took less than 10 minutes.",
    )

    CANT_GET_ENOUGH = Achievement(
        name="Can't Get Enough",
        description="Finish ten prints in one day.",
        nag=True,
    )

    SANTAS_LITTLE_HELPER = Achievement(
        name="Santa's Little Helper",
        description="Start a print between December 1st and December 24th.",
        hidden=True,
    )

    SO_CLOSE = Achievement(
        name="So Close",
        description="Cancel a print job at 95% progress or more.",
    )

    HEAVY_CHONKER = Achievement(
        name="Heavy Chonker",
        description="Upload a GCODE file larger than 500MB.",
    )

    THE_MANUFACTURER_I = Achievement(
        name="The Manufacturer I", description="Finish 10 prints.", nag=True
    )

    THE_MANUFACTURER_II = Achievement(
        name="The Manufacturer II",
        description="Finish 100 prints.",
        hidden=True,
        nag=True,
    )

    THE_MANUFACTURER_III = Achievement(
        name="The Manufacturer I",
        description="Finish 1000 prints.",
        hidden=True,
        nag=True,
    )

    WEEKEND_WARRIOR = Achievement(
        name="Weekend Warrior",
        description="Print on four consecutive weekends.",
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
        self._today = None
        self._prints_today = 0

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

        self._today = datetime.datetime.now().date()

        self._write_data_file()

    ##~~ EventHandlerPlugin

    def on_event(self, event, payload, *args, **kwargs):
        from octoprint.events import Events

        changed = False
        now = datetime.datetime.now()

        if event == Events.PRINT_STARTED:
            self._pause_counter = 0
            self._data.stats.prints_started += 1

            if now.month == 3 and now.day == 21:
                self._trigger_achievement(Achievements.HAPPY_BIRTHDAY_FOOSEL, write=False)
            elif now.month == 12 and now.day >= 1 and now.day <= 24:
                self._trigger_achievement(Achievements.SANTAS_LITTLE_HELPER, write=False)
            elif now.month == 12 and now.day == 25:
                self._trigger_achievement(
                    Achievements.HAPPY_BIRTHDAY_OCTOPRINT, write=False
                )

            if 23 <= now.hour or now.hour < 3:
                self._trigger_achievement(Achievements.NIGHT_OWL, write=False)
            elif 3 <= now.hour < 7:
                self._trigger_achievement(Achievements.EARLY_BIRD, write=False)

            if now.weekday() == 4:
                self._trigger_achievement(Achievements.TGIF, write=False)

            self._data.stats.prints_started_per_weekday[now.weekday()] = (
                self._data.stats.prints_started_per_weekday.get(now.weekday(), 0) + 1
            )

            changed = True

        elif event == Events.PRINT_DONE:
            self._data.stats.prints_finished += 1
            self._data.stats.print_duration_total += payload["time"]
            self._data.stats.print_duration_finished += payload["time"]

            if payload["time"] > self._data.stats.longest_print_duration:
                self._data.stats.longest_print_duration = payload["time"]
                self._data.stats.longest_print_date = datetime.datetime.now().timestamp()

            self._trigger_achievement(Achievements.ONE_SMALL_STEP_FOR_MAN, write=False)

            if self._data.stats.prints_finished >= 1000:
                self._trigger_achievement(Achievements.THE_MANUFACTURER_III)
            elif self._data.stats.prints_finished >= 100:
                self._trigger_achievement(Achievements.THE_MANUFACTURER_II)
            elif self._data.stats.prints_finished >= 10:
                self._trigger_achievement(Achievements.THE_MANUFACTURER_I)

            if payload["time"] > 24 * 60 * 60:
                self._trigger_achievement(Achievements.MARATHON, write=False)
            if payload["time"] > 12 * 60 * 60:
                self._trigger_achievement(Achievements.HALF_MARATHON, write=False)
            if payload["time"] < 10 * 60:
                self._trigger_achievement(Achievements.SPRINT, write=False)

            if now.date() != self._today:
                self._today = now.date()
                self._prints_today = 0
            self._prints_today += 1
            if self._prints_today >= 10:
                self._trigger_achievement(Achievements.CANT_GET_ENOUGH, write=False)

            changed = True

        elif event == Events.PRINT_FAILED or event == Events.PRINT_CANCELLED:
            self._data.stats.print_duration_total += payload["time"]

            if Events.PRINT_CANCELLED:
                self._trigger_achievement(
                    Achievements.ALL_BEGINNINGS_ARE_HARD, write=False
                )

                if payload["progress"] > 95:
                    self._trigger_achievement(Achievements.SO_CLOSE, write=False)

            changed = True

        elif event == Events.PRINT_PAUSED:
            self._pause_counter += 1
            if self._pause_counter >= 10:
                self._trigger_achievement(Achievements.HANG_IN_THERE, write=False)

        elif event == Events.FILE_ADDED:
            if payload.get("operation") == "add":
                self._data.stats.files_uploaded += 1
                if self._data.stats.files_uploaded >= 1000:
                    self._trigger_achievement(Achievements.THE_COLLECTOR_III)
                elif self._data.stats.files_uploaded >= 500:
                    self._trigger_achievement(Achievements.THE_COLLECTOR_II)
                elif self._data.stats.files_uploaded >= 100:
                    self._trigger_achievement(Achievements.THE_COLLECTOR_I)

                if payload.get("size", 0) > 500 * 1024 * 1024:
                    self._trigger_achievement(Achievements.HEAVY_CHONKER)

        elif event == Events.FILE_REMOVED:
            if payload.get("operation") == "remove":
                self._data.stats.files_deleted += 1
                if self._data.stats.files_deleted >= 1000:
                    self._trigger_achievement(Achievements.CLEAN_HOUSE_III)
                elif self._data.stats.files_deleted >= 500:
                    self._trigger_achievement(Achievements.CLEAN_HOUSE_II)
                elif self._data.stats.files_deleted >= 100:
                    self._trigger_achievement(Achievements.CLEAN_HOUSE_I)

        elif event == Events.FOLDER_ADDED:
            self._trigger_achievement(Achievements.THE_HOUSEKEEPER)

        elif event == Events.PLUGIN_BACKUP_BACKUP_CREATED:
            self._trigger_achievement(Achievements.BETTER_SAFE_THAN_SORRY)

        elif event == Events.PLUGIN_PLUGINMANAGER_INSTALL_PLUGIN:
            if payload.get("from_repo"):
                self._trigger_achievement(Achievements.ADVENTURER)
            else:
                self._trigger_achievement(Achievements.TINKERER)

        if changed:
            self._write_data_file()

    ##~~ SimpleApiPlugin

    def on_api_get(self, request, *args, **kwargs):
        if not Permissions.PLUGIN_ACHIEVEMENTS_VIEW.can():
            abort(403)

        achievements = [
            AchievedAchievement(
                **achievement.dict(), achieved=self._data.achievements[achievement.key]
            )
            if self._has_achievement(achievement)
            else achievement
            for achievement in Achievements.all()
        ]

        response = ApiResponse(
            stats=self._data.stats,
            achievements=sorted(
                [
                    achievement
                    for achievement in achievements
                    if not achievement.hidden
                    or isinstance(achievement, AchievedAchievement)
                ],
                key=lambda a: a.name,
            ),
            hidden_achievements=len(
                [
                    achievement
                    for achievement in achievements
                    if achievement.hidden
                    and not isinstance(achievement, AchievedAchievement)
                ]
            ),
        )

        return jsonify(response.dict())

    ##~~ AssetPlugin

    def get_assets(self):
        return {
            "clientjs": ["clientjs/achievements.js"],
            "js": ["js/achievements.js"],
            "less": ["less/achievements.less"],
            "css": ["css/achievements.css"],
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

        payload = achievement.dict()
        payload["type"] = "achievement"
        self._plugin_manager.send_plugin_message(self._identifier, payload)

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
