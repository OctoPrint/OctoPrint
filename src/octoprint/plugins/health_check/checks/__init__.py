__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2024 The OctoPrint Project - Released under terms of the AGPLv3 License"


import hashlib
import logging
from enum import Enum

from pydantic import computed_field

from octoprint.schema import BaseModel


class Result(Enum):
    OK = "ok"
    INFO = "info"
    WARNING = "warning"
    ISSUE = "issue"


class CheckResult(BaseModel):
    result: Result = Result.OK
    context: dict = {}

    @computed_field
    def hash(self) -> str:
        hash = hashlib.sha1()
        hash.update(self.model_dump_json(exclude="hash").encode())
        return hash.hexdigest()


OK_RESULT = CheckResult()


class HealthCheck:
    key: str = "dummy"

    def __init__(self, settings: dict | None = None):
        self._logger = logging.getLogger("octoprint.plugins.healthcheck." + self.key)
        if settings is None:
            settings = {}
        self._settings = settings

    def update_settings(self, settings: dict | None = None) -> None:
        if settings is None:
            settings = {}
        self._settings = settings

    def perform_check(self, force: bool = False) -> CheckResult | None:
        return CheckResult()
