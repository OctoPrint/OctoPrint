__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import copy
import logging
import os
import sys
import threading

import psutil

from octoprint.plugin import EnvironmentDetectionPlugin
from octoprint.util import yaml
from octoprint.util.platform import get_os
from octoprint.util.version import get_python_version_string


class EnvironmentDetector:
    def __init__(self, plugin_manager):
        self._plugin_manager = plugin_manager

        self._cache = None
        self._cache_lock = threading.RLock()

        self._logger = logging.getLogger(__name__)

        try:
            self._environment_plugins = self._plugin_manager.get_implementations(
                EnvironmentDetectionPlugin
            )
        except Exception:
            # just in case, see #3100...
            self._logger.exception(
                "There was an error fetching EnvironmentDetectionPlugins from the plugin manager"
            )
            self._environment_plugins = []

    @property
    def environment(self):
        with self._cache_lock:
            if self._cache is None:
                self.run_detection()
            return copy.deepcopy(self._cache)

    def run_detection(self, notify_plugins=True):
        try:
            environment = {}
            environment["os"] = self._detect_os()
            environment["python"] = self._detect_python()
            environment["hardware"] = self._detect_hardware()

            plugin_result = self._detect_from_plugins()
            if plugin_result:
                environment["plugins"] = plugin_result

            with self._cache_lock:
                self._cache = environment

            if notify_plugins:
                self.notify_plugins()

            return environment
        except Exception:
            self._logger.exception("Unexpected error while detecting environment")
            with self._cache_lock:
                self._cache = {}
                return self._cache

    def _detect_os(self):
        return {
            "id": get_os(),
            "platform": sys.platform,
            "bits": 64 if sys.maxsize > 2**32 else 32,
        }

    def _detect_python(self):
        result = {"version": "unknown", "pip": "unknown"}

        # determine python version
        try:
            result["version"] = get_python_version_string()
        except Exception:
            self._logger.exception("Error detecting python version")

        # determine if we are running from a virtual environment
        try:
            if hasattr(sys, "real_prefix") or (
                hasattr(sys, "base_prefix")
                and os.path.realpath(sys.prefix) != os.path.realpath(sys.base_prefix)
            ):
                result["virtualenv"] = sys.prefix
        except Exception:
            self._logger.exception(
                "Error detecting whether we are running in a virtual environment"
            )

        # try to find pip version
        try:
            import pkg_resources

            result["pip"] = pkg_resources.get_distribution("pip").version
        except Exception:
            self._logger.exception("Error detecting pip version")

        return result

    def _detect_hardware(self):
        result = {"cores": "unknown", "freq": "unknown", "ram": "unknown"}

        try:
            cores = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            ram = psutil.virtual_memory()
            if cores:
                result["cores"] = cores
            if cpu_freq and hasattr(cpu_freq, "max"):
                result["freq"] = cpu_freq.max
            if ram and hasattr(ram, "total"):
                result["ram"] = ram.total
        except Exception:
            self._logger.exception("Error while detecting hardware environment")

        return result

    def _detect_from_plugins(self):
        result = {}

        for implementation in self._environment_plugins:
            try:
                additional = implementation.get_additional_environment()
                if (
                    additional is not None
                    and isinstance(additional, dict)
                    and len(additional)
                ):
                    result[implementation._identifier] = additional
            except Exception:
                self._logger.exception(
                    "Error while fetching additional "
                    "environment data from plugin {}".format(implementation._identifier),
                    extra={"plugin": implementation._identifier},
                )

        return result

    def log_detected_environment(self, only_to_handler=None):
        def _log(message, level=logging.INFO):
            if only_to_handler is not None:
                import octoprint.logging

                octoprint.logging.log_to_handler(
                    self._logger, only_to_handler, level, message, []
                )
            else:
                self._logger.log(level, message)

        try:
            _log(self._format())
        except Exception:
            self._logger.exception("Error logging detected environment")

    def _format(self):
        with self._cache_lock:
            if self._cache is None:
                self.run_detection()
            environment = copy.deepcopy(self._cache)

        dumped_environment = yaml.dump(environment, pretty=True).strip()
        environment_lines = "\n".join(
            map(lambda x: f"|  {x}", dumped_environment.split("\n"))
        )
        return "Detected environment is Python {} under {} ({}). Details:\n{}".format(
            environment["python"]["version"],
            environment["os"]["id"].title(),
            environment["os"]["platform"],
            environment_lines,
        )

    def notify_plugins(self):
        with self._cache_lock:
            if self._cache is None:
                self.run_detection(notify_plugins=False)
            environment = copy.deepcopy(self._cache)

        for implementation in self._environment_plugins:
            try:
                implementation.on_environment_detected(environment)
            except Exception:
                self._logger.exception(
                    "Error while sending environment "
                    "detection result to plugin {}".format(implementation._identifier)
                )
