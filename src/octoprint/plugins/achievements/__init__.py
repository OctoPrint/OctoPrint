__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2023 The OctoPrint Project - Released under terms of the AGPLv3 License"


import datetime
import json
import os
import threading
from typing import List

from flask import abort, jsonify
from flask_babel import gettext
from pydantic import BaseModel

import octoprint.plugin
import octoprint.util
from octoprint.access import ADMIN_GROUP, READONLY_GROUP, USER_GROUP
from octoprint.access.permissions import Permissions
from octoprint.util.version import get_octoprint_version

from .achievements import Achievement, Achievements
from .data import Data, State, Stats


class ApiAchievement(Achievement):
    logo: str = ""
    achieved: int = 0


class ApiResponse(BaseModel):
    stats: Stats
    achievements: List[ApiAchievement]
    hidden_achievements: int


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

        self._pause_counter = 0  # not persisted, as it depends on the current print

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
        now = datetime.datetime.now()

        if event == Events.PRINT_STARTED:
            self._pause_counter = 0
            self._data.stats.prints_started += 1

            ## specific dates

            if now.month == 3 and now.day == 21:
                self._trigger_achievement(Achievements.HAPPY_BIRTHDAY_FOOSEL, write=False)
            elif now.month == 10 and now.day == 31:
                self._trigger_achievement(Achievements.SPOOKY, write=False)
            elif now.month == 12 and now.day >= 1 and now.day <= 24:
                self._trigger_achievement(Achievements.SANTAS_LITTLE_HELPER, write=False)
            elif now.month == 12 and now.day == 25:
                self._trigger_achievement(
                    Achievements.HAPPY_BIRTHDAY_OCTOPRINT, write=False
                )

            ## specific times

            if 23 <= now.hour or now.hour < 3:
                self._trigger_achievement(Achievements.NIGHT_OWL, write=False)
            elif 3 <= now.hour < 7:
                self._trigger_achievement(Achievements.EARLY_BIRD, write=False)

            ## specific weekdays

            if now.weekday() == 4:  # friday
                self._trigger_achievement(Achievements.TGIF, write=False)

            if now.weekday() >= 5:  # weekend
                if self._data.state.date_last_weekend_print:
                    last_weekend_print = datetime.date.fromisoformat(
                        self._data.state.date_last_weekend_print
                    )
                    last_saturday = now.date() - datetime.timedelta(
                        days=now.weekday() + 2
                    )
                    last_sunday = last_saturday + datetime.timedelta(days=1)
                    if last_saturday <= last_weekend_print <= last_sunday:
                        self._data.state.consecutive_weekend_prints += 1
                        if self._data.state.consecutive_weekend_prints == 4:
                            self._trigger_achievement(
                                Achievements.WEEKEND_WARRIOR, write=False
                            )
                self._data.state.date_last_weekend_print = now.date().isoformat()

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

            ## print count

            if self._data.stats.prints_finished >= 1000:
                self._trigger_achievement(Achievements.THE_MANUFACTURER_III)
            elif self._data.stats.prints_finished >= 100:
                self._trigger_achievement(Achievements.THE_MANUFACTURER_II)
            elif self._data.stats.prints_finished >= 10:
                self._trigger_achievement(Achievements.THE_MANUFACTURER_I)

            ## print duration

            if payload["time"] > 24 * 60 * 60:
                self._trigger_achievement(Achievements.MARATHON, write=False)
            if payload["time"] > 12 * 60 * 60:
                self._trigger_achievement(Achievements.HALF_MARATHON, write=False)
            if payload["time"] < 10 * 60:
                self._trigger_achievement(Achievements.SPRINT, write=False)

            ## prints per day

            if now.date().isoformat() != self._data.state.date_last_print:
                self._data.state.date_last_print = now.date().isoformat()
                self._data.state.prints_today = 0
            self._data.state.prints_today += 1
            if self._data.state.prints_today >= 10:
                self._trigger_achievement(Achievements.CANT_GET_ENOUGH, write=False)

            ## consecutive prints of same file

            loc = f"{payload['origin']}:{payload['path']}"
            if loc == self._data.state.file_last_print:
                self._data.state.consecutive_prints_of_same_file += 1
                if self._data.state.consecutive_prints_of_same_file >= 5:
                    self._trigger_achievement(Achievements.MASS_PRODUCTION, write=False)
            else:
                self._data.state.consecutive_prints_of_same_file = 1
            self._data.state.file_last_print = loc

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
            self._trigger_achievement(Achievements.THE_ORGANIZER)

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
            ApiAchievement(
                achieved=self._data.achievements.get(a.key, 0),
                logo=a.icon,
                **a.dict(),
            )
            for a in Achievements.all()
            if not a.hidden or self._has_achievement(a)
        ]
        achievements.sort(key=lambda a: a.name)

        response = ApiResponse(
            stats=self._data.stats,
            achievements=achievements,
            hidden_achievements=len(
                [
                    achievement
                    for achievement in Achievements.all()
                    if achievement.hidden and not self._has_achievement(achievement)
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
                "template": "achievements_about_achievements.jinja2",
                "custom_bindings": True,
            },
            {
                "type": "about",
                "name": gettext("Instance Stats"),
                "template": "achievements_about_stats.jinja2",
                "custom_bindings": True,
            },
        ]

    def get_template_vars(self):
        return {"svgs": self._generate_svg()}

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
        payload["logo"] = achievement.icon
        self._plugin_manager.send_plugin_message(self._identifier, payload)

    def _generate_svg(self):
        import os
        from xml.dom.minidom import parse

        svg = """
<svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" style="display: none;">
<defs>
"""
        for entry in os.scandir(os.path.join(os.path.dirname(__file__), "static", "img")):
            if not entry.is_file() or not entry.name.endswith(".svg"):
                continue

            try:
                dom = parse(entry.path)
                paths = dom.getElementsByTagName("path")
                if len(paths):
                    svg += (
                        f"<g id='achievement-logo-{entry.name[:-4]}'>"
                        + "".join([path.toxml() for path in paths])
                        + "</g>"
                    )
            except Exception:
                continue

        svg += """
</defs>
</svg>
"""

        return svg

    @property
    def _data_path(self):
        return os.path.join(self.get_plugin_data_folder(), "data.json")

    def _reset_data(self):
        self._data = Data(
            stats=Stats(
                created=datetime.datetime.now().timestamp(),
                created_version=get_octoprint_version().base_version,
            ),
            achievements={},
            state=State(),
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
