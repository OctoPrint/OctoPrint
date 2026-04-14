__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.schema import BaseModel


class TerminalFilterEntry(BaseModel):
    name: str
    """The name of the filter."""

    regex: str
    """The regular expression to match. Use `JavaScript regular expressions <https://developer.mozilla.org/en/docs/Web/JavaScript/Guide/Regular_Expressions>`_."""


DEFAULT_TERMINAL_FILTERS = [
    TerminalFilterEntry(
        name="Suppress temperature messages",
        regex=r"((Send:|>>>)\s+(N\d+\s+)?M105)|((Recv:|<<<)\s+(ok\s+([PBN]\d+\s+)*)?([BCLPR]|T\d*):-?\d+)",
    ),
    TerminalFilterEntry(
        name="Suppress SD status messages",
        regex=r"((Send:|>>>)\s+(N\d+\s+)?M27)|((Recv:|<<<)\s+SD printing byte)|((Recv:|<<<)\s+Not SD printing)",
    ),
    TerminalFilterEntry(
        name="Suppress position messages",
        regex=r"((Send:|>>>)\s+(N\d+\s+)?M114)|((Recv:|<<<)\s+(ok\s+)?X:[+-]?([0-9]*[.])?[0-9]+\s+Y:[+-]?([0-9]*[.])?[0-9]+\s+Z:[+-]?([0-9]*[.])?[0-9]+\s+E\d*:[+-]?([0-9]*[.])?[0-9]+).*",
    ),
    TerminalFilterEntry(name="Suppress wait responses", regex=r"(Recv:|<<<)\s+wait"),
    TerminalFilterEntry(
        name="Suppress processing responses",
        regex=r"(Recv:|<<<)\s+(echo:\s*)?busy:\s*processing",
    ),
]
