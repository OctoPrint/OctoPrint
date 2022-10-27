__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from pydantic import BaseModel

from octoprint.vendor.with_attrs_docs import with_attrs_docs


@with_attrs_docs
class PrintTimeEstimationConfig(BaseModel):
    statsWeighingUntil: float = 0.5
    """Until which percentage to do a weighted mixture of statistical duration (analysis or past prints) with the result from the calculated estimate if that's already available. Utilized to compensate for the fact that the earlier in a print job, the least accuracy even a stable calculated estimate provides."""

    validityRange: float = 0.15
    """Range the assumed percentage (based on current estimated statistical, calculated or mixed total vs elapsed print time so far) needs to be around the actual percentage for the result to be used."""

    forceDumbFromPercent: float = 0.3
    """If no estimate could be calculated until this percentage and no statistical data is available, use dumb linear estimate. Value between 0 and 1.0."""

    forceDumbAfterMin: float = 30.0
    """If no estimate could be calculated until this many minutes into the print and no statistical data is available, use dumb linear estimate."""

    stableThreshold: int = 60
    """Average fluctuation between individual calculated estimates to consider in stable range. Seconds of difference."""


@with_attrs_docs
class EstimationConfig(BaseModel):
    printTime: PrintTimeEstimationConfig = PrintTimeEstimationConfig()
    """Parameters for the print time estimation during an ongoing print job."""
