__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.schema import BaseModel
from octoprint.vendor.with_attrs_docs import with_attrs_docs


@with_attrs_docs
class PrinterParametersConfig(BaseModel):
    pauseTriggers: list[str] = []
