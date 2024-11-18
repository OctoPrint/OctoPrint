import datetime
import sys
import time

import requests

from octoprint import __version__ as octoprint_version
from octoprint.util.version import get_python_version_string

from . import CheckResult, HealthCheck, Result


class PythonEolHealthCheck(HealthCheck):
    key = "python_eol"

    MAX_MONTHS_UNTIL = 12

    def __init__(self, settings):
        super().__init__(settings)

        from octoprint.server import connectivityChecker

        self._connectivity_checker = connectivityChecker
        self._cache = None
        self._timestamp = None

    def perform_check(self, force=False):
        data = self._get_eol_data(force=force)
        today_obj = datetime.date.today()
        today = today_obj.isoformat()

        major = sys.version_info.major
        major_minor = f"{sys.version_info.major}.{sys.version_info.minor}"

        # major, major_minor = ("3", "3.7")  # for testing

        for python in (
            major,
            major_minor,
        ):
            if python in data:
                data = data[python]

                date_obj = datetime.date.fromisoformat(data["date"])
                months_until = (date_obj - today_obj).total_seconds() / (
                    30 * 24 * 60 * 60
                )
                if months_until > self.MAX_MONTHS_UNTIL:
                    continue

                soon = today < data["date"]
                context = {
                    "version": get_python_version_string(),
                    "date": data["date"],
                    "soon": soon,
                }
                if "last_octoprint" in data:
                    context["last_octoprint"] = data["last_octoprint"]

                result = Result.ISSUE
                if soon:
                    result = Result.WARNING
                return CheckResult(result=result, context=context)

    def _get_eol_data(self, force=False):
        url = self._settings.get("url")
        ttl = self._settings.get("ttl")
        fallback = self._settings.get("fallback")

        if any(x is None for x in (url, ttl, fallback)):
            return None

        if (
            self._cache is None
            or self._timestamp is None
            or self._timestamp + ttl < time.time()
            or force
        ):
            if self._connectivity_checker.online:
                try:
                    r = requests.get(
                        url,
                        headers={"User-Agent": f"OctoPrint/{octoprint_version}"},
                        timeout=(3.05, 7),
                    )
                    r.raise_for_status()
                    self._cache = r.json()
                    self._timestamp = time.time()
                    self._logger.info(f"Fetched Python EOL data from {url}")
                except Exception:
                    self._logger.exception(
                        "Could not fetch Python EOL data, falling back to defaults"
                    )
                    self._cache = fallback
                    self._timestamp = time.time()

            else:
                self._logger.info(
                    "Could not fetch Python EOL data, we are offline, falling back to defaults"
                )
                self._cache = fallback
                self._timestamp = time.time()

        return self._cache
