__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.util import deprecated

from . import serializing  # noqa: F401
from .encoding import JsonEncoding, dumps, loads  # noqa: F401

dump = deprecated(
    "dump has been renamed to dumps, please adjust your implementation",
    includedoc="dump has been renamed to dumps",
    since="1.8.0",
)(dumps)
