__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2024 The OctoPrint Project - Released under terms of the AGPLv3 License"


import hashlib
import logging
from enum import Enum

from octoprint.schema import BaseModel


class Result(Enum):
    OK: str = "ok"
    WARNING: str = "warning"
    ISSUE: str = "issue"


class CheckResult(BaseModel):
    result: Result = Result.OK
    context: dict = {}

    @property  # TODO: Turn this into a computed field once Python 3.7 is dropped
    def hash(self) -> str:
        hash = hashlib.sha1()
        hash.update(self.model_dump_json().encode())
        return hash.hexdigest()


OK_RESULT = CheckResult()


class HealthCheck:
    key: str = "dummy"

    def __init__(self, settings: dict = None):
        self._logger = logging.getLogger("octoprint.plugins.healthcheck." + self.key)
        if settings is None:
            settings = {}
        self._settings = settings

    def update_settings(self, settings: dict = None) -> None:
        if settings is None:
            settings = {}
        self._settings = settings

    def perform_check(self, force: bool = False) -> CheckResult:
        return CheckResult()
