__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from typing import Union

from octoprint.schema import BaseModel
from octoprint.vendor.with_attrs_docs import with_attrs_docs

from .access_control import AccessControlConfig
from .api import ApiConfig
from .appearance import AppearanceConfig
from .controls import CustomControl, CustomControlContainer
from .devel import DevelConfig
from .estimation import EstimationConfig
from .events import EventsConfig
from .feature import FeatureConfig
from .folder import FolderConfig
from .gcode_analysis import GcodeAnalysisConfig
from .plugins import PluginsConfig
from .printer_connection import PrinterConnectionConfig
from .printer_parameters import PrinterParametersConfig
from .printer_profiles import PrinterProfilesConfig
from .scripts import ScriptsConfig
from .server import ServerConfig
from .slicing import SlicingConfig
from .system import SystemConfig
from .temperature import TemperatureConfig
from .terminalfilters import DEFAULT_TERMINAL_FILTERS, TerminalFilterEntry
from .webcam import WebcamConfig


@with_attrs_docs
class Config(BaseModel):
    accessControl: AccessControlConfig = AccessControlConfig()
    api: ApiConfig = ApiConfig()
    appearance: AppearanceConfig = AppearanceConfig()
    controls: list[Union[CustomControl, CustomControlContainer]] = []
    devel: DevelConfig = DevelConfig()
    estimation: EstimationConfig = EstimationConfig()
    events: EventsConfig = EventsConfig()
    feature: FeatureConfig = FeatureConfig()
    folder: FolderConfig = FolderConfig()
    gcodeAnalysis: GcodeAnalysisConfig = GcodeAnalysisConfig()
    plugins: PluginsConfig = PluginsConfig()
    printerConnection: PrinterConnectionConfig = PrinterConnectionConfig()
    printerParameters: PrinterParametersConfig = PrinterParametersConfig()
    printerProfiles: PrinterProfilesConfig = PrinterProfilesConfig()
    scripts: ScriptsConfig = ScriptsConfig()
    server: ServerConfig = ServerConfig()
    slicing: SlicingConfig = SlicingConfig()
    system: SystemConfig = SystemConfig()
    temperature: TemperatureConfig = TemperatureConfig()
    terminalFilters: list[TerminalFilterEntry] = DEFAULT_TERMINAL_FILTERS
    webcam: WebcamConfig = WebcamConfig()
