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
from octoprint.events import Events
from octoprint.util.version import get_octoprint_version

from .achievements import Achievement, Achievements
from .data import Data, State, Stats, YearlyStats


class ApiAchievement(Achievement):
    logo: str = ""
    achieved: int = 0


class ApiTimezoneInfo(BaseModel):
    name: str
    offset: int


class ApiResponse(BaseModel):
    stats: Stats
    achievements: List[ApiAchievement]
    hidden_achievements: int
    current_year: YearlyStats
    available_years: List[int]
    timezone: ApiTimezoneInfo


class AchievementsPlugin(
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.BlueprintPlugin,
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

        self._year_data = None
        self._year_data_mutex = threading.Lock()

        self._get_throttled = lambda: False

        self._pause_counter = 0  # not persisted, as it depends on the current print

        self._tz = None

    def initialize(self):
        self._load_data_file()
        self._load_current_year_file()
        return super().initialize()

    def _server_timezone(self):
        return (
            datetime.datetime.utcnow().astimezone()
        )  # utcnow still needed while supporting Python 3.7

    def _now(self):
        if self._tz is None:
            import pytz

            timezone = self._settings.get(["timezone"])
            if timezone:
                try:
                    self._tz = pytz.timezone(timezone)
                except Exception:
                    self._logger.exception(
                        f"Cannot load timezone {timezone}, falling back to server timezone"
                    )
        return datetime.datetime.now(tz=self._tz)

    ##~~ Additional permissions hook

    def get_additional_permissions(self):
        return [
            {
                "key": "VIEW",
                "name": "View instance achievements & stats",
                "description": gettext(
                    "Allows to view the instance achievements & stats."
                ),
                "default_groups": [READONLY_GROUP, USER_GROUP, ADMIN_GROUP],
                "roles": ["view"],
            },
            {
                "key": "RESET",
                "name": "Reset instance achievements & stats",
                "description": gettext(
                    "Allows to reset the instance achievements & stats."
                ),
                "default_groups": [ADMIN_GROUP],
                "roles": ["reset"],
            },
        ]

    ##~~ socket emit hook

    def socket_emit_hook(self, socket, user, message, payload, *args, **kwargs):
        if (
            message != "event"
            or payload["type"] != Events.PLUGIN_ACHIEVEMENTS_ACHIEVEMENT_UNLOCKED
        ):
            return True

        return user and user.has_permission(Permissions.PLUGIN_ACHIEVEMENTS_VIEW)

    ##~~ Firmware info hook

    def firmware_info_hook(
        self, comm_instance, firmware_name, firmware_data, *args, **kwargs
    ):
        if "klipper" in firmware_name.lower():
            self._trigger_achievement(Achievements.CROSSOVER_EPISODE)

    ##~~ StartupPlugin

    def on_startup(self, *args, **kwargs):
        self._data.stats.server_starts += 1
        self._year_data.server_starts += 1

        version = get_octoprint_version()
        if self._data.stats.last_version != version.base_version:
            self._data.stats.seen_versions += 1
            self._data.stats.last_version = version.base_version

        if self._year_data.last_version != version.base_version:
            self._year_data.seen_versions += 1
            self._year_data.last_version = version.base_version

        self._recheck_plugin_count()

        if not self._has_achievement(
            Achievements.THE_WIZARD
        ) and not self._settings.get_boolean(["server", "firstRun"]):
            self._trigger_achievement(Achievements.THE_WIZARD, write=False)

        self._write_data_file()
        self._write_current_year_file()

    def on_after_startup(self):
        helpers = self._plugin_manager.get_helpers("pi_support", "get_throttled")
        if helpers and "get_throttled" in helpers:
            self._get_throttled = helpers["get_throttled"]

        return super().on_after_startup()

    ##~~ EventHandlerPlugin

    def on_event(self, event, payload, *args, **kwargs):
        changed = False
        yearly_changed = False
        now = self._now()

        if event == Events.PRINT_STARTED:
            self._pause_counter = 0
            self._data.stats.prints_started += 1
            self._year_data.prints_started += 1

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
            self._year_data.prints_started_per_weekday[now.weekday()] = (
                self._year_data.prints_started_per_weekday.get(now.weekday(), 0) + 1
            )

            ## other conditions
            throttled = self._get_throttled()
            if throttled and throttled.get("current_undervoltage"):
                self._trigger_achievement(
                    Achievements.WHAT_COULD_POSSIBLY_GO_WRONG, write=False
                )

            changed = True
            yearly_changed = True

        elif event == Events.PRINT_DONE:
            self._data.stats.prints_finished += 1
            self._data.stats.print_duration_total += payload["time"]
            self._data.stats.print_duration_finished += payload["time"]

            self._year_data.prints_finished += 1
            self._year_data.print_duration_total += payload["time"]
            self._year_data.print_duration_finished += payload["time"]

            self._data.state.consecutive_prints_cancelled_today = 0

            if payload["time"] > self._data.stats.longest_print_duration:
                self._data.stats.longest_print_duration = payload["time"]
                self._data.stats.longest_print_date = self._now().timestamp()

            if payload["time"] > self._year_data.longest_print_duration:
                self._year_data.longest_print_duration = payload["time"]
                self._year_data.longest_print_date = self._now().timestamp()

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

            lastmodified = self._file_manager.get_lastmodified(
                payload.get("origin"), payload.get("path")
            )
            loc = f"{payload['origin']}:{payload['path']}:{lastmodified}"
            if loc == self._data.state.file_last_print:
                self._data.state.consecutive_prints_of_same_file += 1
                if self._data.state.consecutive_prints_of_same_file >= 5:
                    self._trigger_achievement(Achievements.MASS_PRODUCTION, write=False)
            else:
                self._data.state.consecutive_prints_of_same_file = 1
            self._data.state.file_last_print = loc

            ## total finished print duration

            if self._data.stats.print_duration_finished >= 404 * 60 * 60:
                self._trigger_achievement(Achievements.ACHIEVEMENT_NOT_FOUND)

            changed = True
            yearly_changed = True

        elif event == Events.PRINT_FAILED or event == Events.PRINT_CANCELLED:
            self._data.stats.print_duration_total += payload["time"]
            self._year_data.print_duration_total += payload["time"]

            if Events.PRINT_CANCELLED:
                self._trigger_achievement(
                    Achievements.ALL_BEGINNINGS_ARE_HARD, write=False
                )

                if payload["progress"] > 95:
                    self._trigger_achievement(Achievements.SO_CLOSE, write=False)

                ## cancelled per day

                if now.date().isoformat() != self._data.state.date_last_cancelled_print:
                    self._data.state.date_last_cancelled_print = now.date().isoformat()
                    self._data.state.prints_cancelled_today = 0
                self._data.state.prints_cancelled_today += 1
                self._data.state.consecutive_prints_cancelled_today += 1

                if self._data.state.consecutive_prints_cancelled_today >= 10:
                    self._trigger_achievement(Achievements.ONE_OF_THOSE_DAYS, write=False)

            changed = True
            yearly_changed = True

        elif event == Events.PRINT_PAUSED:
            self._pause_counter += 1
            if self._pause_counter >= 10:
                self._trigger_achievement(Achievements.HANG_IN_THERE, write=False)

        elif event == Events.FILE_ADDED:
            if payload.get("operation") == "add":
                self._data.stats.files_uploaded += 1
                self._year_data.files_uploaded += 1

                if self._data.stats.files_uploaded >= 1000:
                    self._trigger_achievement(Achievements.THE_COLLECTOR_III)
                elif self._data.stats.files_uploaded >= 500:
                    self._trigger_achievement(Achievements.THE_COLLECTOR_II)
                elif self._data.stats.files_uploaded >= 100:
                    self._trigger_achievement(Achievements.THE_COLLECTOR_I)

                size = self._file_manager.get_size(
                    payload.get("storage"), payload.get("path")
                )
                if size > 500 * 1024 * 1024:
                    self._trigger_achievement(Achievements.HEAVY_CHONKER)

                changed = yearly_changed = True

        elif event == Events.FILE_REMOVED:
            if payload.get("operation") == "remove":
                self._data.stats.files_deleted += 1
                self._year_data.files_deleted += 1

                if self._data.stats.files_deleted >= 1000:
                    self._trigger_achievement(Achievements.CLEAN_HOUSE_III)
                elif self._data.stats.files_deleted >= 500:
                    self._trigger_achievement(Achievements.CLEAN_HOUSE_II)
                elif self._data.stats.files_deleted >= 100:
                    self._trigger_achievement(Achievements.CLEAN_HOUSE_I)

                changed = yearly_changed = True

        elif event == Events.FOLDER_ADDED:
            self._trigger_achievement(Achievements.THE_ORGANIZER)

        elif (
            hasattr(Events, "PLUGIN_BACKUP_BACKUP_CREATED")
            and event == Events.PLUGIN_BACKUP_BACKUP_CREATED
        ):
            self._trigger_achievement(Achievements.BETTER_SAFE_THAN_SORRY)

        elif (
            hasattr(Events, "PLUGIN_PLUGINMANAGER_INSTALL_PLUGIN")
            and event == Events.PLUGIN_PLUGINMANAGER_INSTALL_PLUGIN
        ):
            if payload.get("from_repo"):
                self._trigger_achievement(Achievements.ADVENTURER)
            else:
                self._trigger_achievement(Achievements.TINKERER)

            self._data.stats.plugins_installed += 1
            self._year_data.plugins_installed += 1

            self._recheck_plugin_count()

            changed = yearly_changed = True

        elif (
            hasattr(Events, "PLUGIN_PLUGINMANAGER_UNINSTALL_PLUGIN")
            and event == Events.PLUGIN_PLUGINMANAGER_UNINSTALL_PLUGIN
        ):
            self._data.stats.plugins_uninstalled += 1
            self._year_data.plugins_uninstalled += 1

            changed = yearly_changed = True

        if changed:
            self._write_data_file()

        if yearly_changed:
            self._write_current_year_file()

    ##~~ BlueprintPlugin

    def is_blueprint_csrf_protected(self):
        return True

    @octoprint.plugin.BlueprintPlugin.route("/", methods=["GET"])
    @Permissions.PLUGIN_ACHIEVEMENTS_VIEW.require(403)
    def get_data(self):
        self._now()  # make sure self._tz is set, if we have a timezone

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

        if self._tz:
            timezone_name = self._tz.zone
            timezone_offset = (
                self._tz.utcoffset(datetime.datetime.now()).total_seconds() // 60
            )
        else:
            server_timezone = self._server_timezone()
            timezone_name = server_timezone.tzname()
            timezone_offset = server_timezone.utcoffset().total_seconds() // 60

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
            current_year=self._year_data,
            available_years=self._available_years(),
            timezone=ApiTimezoneInfo(
                name=timezone_name,
                offset=timezone_offset,
            ),
        )

        return jsonify(response.dict())

    @octoprint.plugin.BlueprintPlugin.route("/year/<int:year>", methods=["GET"])
    @Permissions.PLUGIN_ACHIEVEMENTS_VIEW.require(403)
    def get_year_data(self, year):
        year_data = self._load_year_file(year=year)
        if year_data is None:
            if year == self._now().year:
                year_data = self._year_data
            else:
                abort(404)

        return jsonify(year_data.dict())

    @octoprint.plugin.BlueprintPlugin.route("/reset/achievements", methods=["POST"])
    @Permissions.PLUGIN_ACHIEVEMENTS_RESET.require(403)
    def reset_achievements(self):
        from flask import request

        from octoprint.server import NO_CONTENT

        data = request.json
        if "achievements" not in data or not isinstance(data["achievements"], list):
            abort(400, "Need list of achievements to reset")

        self._reset_achievements(*data["achievements"])
        return NO_CONTENT

    ##~~ AssetPlugin

    def get_assets(self):
        return {
            "clientjs": ["clientjs/achievements.js"],
            "js": ["js/achievements.js"],
            "less": ["less/achievements.less"],
            "css": ["css/achievements.css"],
        }

    ##~~ SettingsPlugin

    def get_settings_defaults(self):
        return {
            "timezone": "",
        }

    def on_settings_save(self, data):
        super().on_settings_save(data)
        if "timezone" in data:
            self._tz = None

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
            {
                "type": "settings",
                "name": gettext("Achievements"),
                "template": "achievements_settings.jinja2",
                "custom_bindings": True,
            },
        ]

    def get_template_vars(self):
        import pytz

        server_timezone = self._server_timezone()

        return {
            "svgs": self._generate_svg(),
            "timezones": pytz.common_timezones,
            "server_timezone": server_timezone.tzname(),
        }

    ##~~ External helpers

    def get_unlocked_achievements(self):
        return list(
            filter(
                lambda x: x is not None,
                [Achievements.get(key) for key in self._data.achievements.keys()],
            )
        )

    ##~~ Internal helpers

    def _recheck_plugin_count(self):
        changed = yearly_changed = False

        if len(self._plugin_manager.plugins) > self._data.stats.most_plugins:
            self._data.stats.most_plugins = len(self._plugin_manager.plugins)

        if len(self._plugin_manager.plugins) > self._year_data.most_plugins:
            self._year_data.most_plugins = len(self._plugin_manager.plugins)

        return changed, yearly_changed

    def _has_achievement(self, achievement):
        return achievement.key in self._data.achievements

    def _trigger_achievement(self, achievement, write=True):
        if self._has_achievement(achievement):
            return

        self._data.achievements[achievement.key] = int(self._now().timestamp())
        if write:
            self._write_data_file()

        self._year_data.achievements += 1
        self._write_current_year_file()

        self._logger.info(f"New achievement unlocked: {achievement.name}!")

        payload = achievement.dict()
        payload["type"] = "achievement"
        payload["logo"] = achievement.icon
        self._event_bus.fire(Events.PLUGIN_ACHIEVEMENTS_ACHIEVEMENT_UNLOCKED, payload)

    def _reset_achievements(self, *achievements, write=True):
        for achievement in achievements:
            if not Achievements.get(achievement):
                self._logger.error(f"Unknown achievement {achievement}")
                continue
            self._data.achievements.pop(achievement, None)
        if write:
            self._write_data_file()

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

    def _year_path(self, year=None):
        if year is None:
            year = self._now().year
        return os.path.join(self.get_plugin_data_folder(), f"{year}.json")

    def _available_years(self):
        years = []
        for entry in os.scandir(self.get_plugin_data_folder()):
            if not entry.is_file() or not entry.name.endswith(".json"):
                continue

            try:
                years.append(int(entry.name[:-5]))
            except Exception:
                # not a year file
                continue

        if not years:
            years.append(self._now().year)
        return years

    def _reset_data(self):
        self._data = Data(
            stats=Stats(
                created=self._now().timestamp(),
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

    def _reset_current_year_data(self):
        self._year_data = YearlyStats()

    def _load_current_year_file(self):
        with self._year_data_mutex:
            self._year_data = self._load_year_file()
            if self._year_data is None:
                self._logger.info(
                    "No data file for the current year found, starting with empty data"
                )
                self._reset_current_year_data()

    def _write_current_year_file(self):
        with self._year_data_mutex:
            path = self._year_path()
            self._logger.debug(f"Writing data to {path}")
            with octoprint.util.atomic_write(path, mode="wb") as f:
                f.write(
                    octoprint.util.to_bytes(
                        json.dumps(
                            self._year_data.dict(), indent=2, separators=(",", ": ")
                        )
                    )
                )

    def _load_year_file(self, year=None):
        path = self._year_path(year=year)
        if not os.path.exists(path):
            return None

        try:
            with open(path) as f:
                self._logger.info(f"Loading data for {year} from {path}")
                data = json.load(f)

            return YearlyStats(**data)
        except Exception as e:
            self._logger.exception(f"Error loading data for year {year} from {path}: {e}")
            return None


def _register_custom_events(*args, **kwargs):
    return ["achievement_unlocked"]


__plugin_name__ = "Achievements Plugin"
__plugin_author__ = "Gina Häußge"
__plugin_description__ = "Achievements & stats about your OctoPrint instance"
__plugin_disabling_discouraged__ = gettext(
    "Without this plugin you will no longer be able to earn achievements and track stats about your OctoPrint instance."
)
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = AchievementsPlugin()
__plugin_helpers__ = {
    "get_unlocked_achievements": __plugin_implementation__.get_unlocked_achievements,
    "has_achievement": __plugin_implementation__._has_achievement,
}
__plugin_hooks__ = {
    "octoprint.access.permissions": __plugin_implementation__.get_additional_permissions,
    "octoprint.comm.protocol.firmware.info": __plugin_implementation__.firmware_info_hook,
    "octoprint.events.register_custom_events": _register_custom_events,
    "octoprint.server.sockjs.emit": __plugin_implementation__.socket_emit_hook,
}
