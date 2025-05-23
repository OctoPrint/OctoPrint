__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2020 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging
import threading
import time

from octoprint.util.net import resolve_host, server_reachable


class ConnectivityChecker:
    """
    Regularly checks for online connectivity.

    Tries to open a connection to the provided ``host`` and ``port`` every ``interval``
    seconds and sets the ``online`` status accordingly.

    If a ``name``is provided, also tries to resolve that name to a valid IP address
    during connectivity check and only set ``online`` to ``True`` if that succeeds as well.
    """

    def __init__(
        self,
        interval,
        host,
        port,
        name=None,
        enabled=True,
        force_offline=False,
        on_change=None,
    ):
        self._interval = interval
        self._host = host
        self._port = port
        self._name = name
        self._enabled = enabled
        self._force_offline = force_offline
        self._on_change = on_change

        self._logger = logging.getLogger(__name__ + ".connectivity_checker")

        self._connection_working = not self._enabled and not self._force_offline
        self._resolution_working = (
            not self._enabled or self._name is None
        ) and not self._force_offline

        self._check_worker = None
        self._check_mutex = threading.RLock()

        self._run()

    @property
    def online(self):
        """Current online status, True if online, False if offline."""
        with self._check_mutex:
            return self._online

    @property
    def _online(self):
        if self._force_offline:
            return False
        return self._connection_working and self._resolution_working

    @property
    def forced_offlined(self):
        return self._force_offline

    @property
    def host(self):
        """DNS host to query."""
        with self._check_mutex:
            return self._host

    @host.setter
    def host(self, value):
        with self._check_mutex:
            self._host = value

    @property
    def port(self):
        """DNS port to query."""
        with self._check_mutex:
            return self._port

    @port.setter
    def port(self, value):
        with self._check_mutex:
            self._port = value

    @property
    def name(self):
        with self._check_mutex:
            return self._name

    @name.setter
    def name(self, value):
        with self._check_mutex:
            self._name = value

    @property
    def interval(self):
        """Interval between consecutive automatic checks."""
        return self._interval

    @interval.setter
    def interval(self, value):
        self._interval = value

    @property
    def enabled(self):
        """Whether the check is enabled or not."""
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        with self._check_mutex:
            old_enabled = self._enabled
            self._enabled = value

            if not self._enabled:
                if self._check_worker is not None:
                    self._check_worker.cancel()

                old_value = self._online
                self._connection_working = self._resolution_working = True

                if old_value != self._online:
                    self._trigger_change(old_value, self._online)

            elif self._enabled and not old_enabled:
                self._run()

    def check_immediately(self):
        """Check immediately and return result."""
        with self._check_mutex:
            self._perform_check()
            return self.online

    def log_full_report(self):
        if not self._enabled:
            self._logger.info(
                "Connectivity check is disabled, assuming we are online and have functional name resolution"
            )
            return

        with self._check_mutex:
            self._logger.info(
                "Connectivity state is currently: {}".format(
                    self._map_online(self.online)
                )
            )
            self.log_details()

    def log_details(self):
        self._logger.info(
            "Connecting to {}:{} is {}".format(
                self._host,
                self._port,
                self._map_working(self._connection_working),
            )
        )
        if self._name:
            self._logger.info(
                "Resolving {} is {}".format(
                    self._name,
                    self._map_working(self._resolution_working),
                )
            )

    def as_dict(self):
        result = {
            "online": self.online,
            "enabled": self.enabled,
            "connection_ok": self._connection_working,
            "connection_check": f"{self._host}:{self._port}",
        }
        if self._name:
            result.update(
                resolution_ok=self._resolution_working, resolution_check=self._name
            )
        return result

    def _run(self):
        from octoprint.util import RepeatedTimer

        if not self._enabled:
            return

        if self._check_worker is not None:
            self._check_worker.cancel()

        self._check_worker = RepeatedTimer(
            self._interval, self._perform_check, run_first=True
        )
        self._check_worker.start()

    def _perform_check(self):
        if not self._enabled:
            return

        with self._check_mutex:
            self._logger.debug(
                "Checking against {}:{} if we are online...".format(
                    self._host, self._port
                )
            )

            old_value = self._online

            for _ in range(3):
                connection_working = server_reachable(self._host, port=self._port)

                if self._name:
                    if connection_working:
                        self._logger.debug(f"Checking if we can resolve {self._name}...")
                        resolution_working = len(resolve_host(self._name)) > 0
                    else:
                        resolution_working = False
                else:
                    resolution_working = True

                if not (connection_working and resolution_working):
                    # retry up to 3 times
                    time.sleep(1.0)
                    continue

                # all good
                break

            self._connection_working = connection_working
            self._resolution_working = resolution_working
            new_value = self._online

            if old_value != new_value:
                self._trigger_change(old_value, new_value)

    def _trigger_change(self, old_value, new_value):
        self._log_change_report(old_value, new_value, include_details=not new_value)
        if callable(self._on_change):
            self._on_change(
                old_value,
                new_value,
                connection_working=self._connection_working,
                resolution_working=self._resolution_working,
            )

    def _log_change_report(self, old_value, new_value, include_details=False):
        self._logger.info(
            "Connectivity changed from {} to {}".format(
                self._map_online(old_value),
                self._map_online(new_value),
            )
        )
        if include_details:
            self.log_details()

    def _map_working(self, value):
        return "working" if value else "not working"

    def _map_online(self, value):
        return "online" if value else "offline"
