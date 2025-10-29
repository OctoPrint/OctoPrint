__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from enum import Enum

from octoprint.schema import BaseModel
from octoprint.vendor.with_attrs_docs import with_attrs_docs


class ColorEnum(str, Enum):
    red = "red"
    orange = "orange"
    yellow = "yellow"
    green = "green"
    blue = "blue"
    violet = "violet"
    default = "default"


@with_attrs_docs
class ComponentOrderConfig(BaseModel):
    navbar: list[str] = [
        "settings",
        "systemmenu",
        "plugin_announcements",
        "plugin_logging_seriallog",
        "plugin_logging_plugintimingslog",
        "plugin_pi_support",
        "plugin_health_check",
        "login",
    ]
    """Order of navbar items."""

    sidebar: list[str] = [
        "plugin_firmware_check_warning",
        "plugin_firmware_check_info",
        "connection",
        "state",
        "files",
    ]
    """Order of sidebar items."""

    tab: list[str] = [
        "temperature",
        "control",
        "plugin_gcodeviewer",
        "terminal",
        "timelapse",
    ]
    """Order of tabs."""

    settings: list[str] = [
        "section_printer",
        "plugin_serial_connector",
        "printerprofiles",
        "temperatures",
        "terminalfilters",
        "gcodescripts",
        "section_features",
        "features",
        "webcam",
        "accesscontrol",
        "plugin_gcodeviewer",
        "api",
        "plugin_appkeys",
        "section_octoprint",
        "server",
        "folders",
        "appearance",
        "plugin_logging",
        "plugin_pluginmanager",
        "plugin_softwareupdate",
        "plugin_announcements",
        "plugin_eventmanager",
        "plugin_backup",
        "plugin_tracking",
        "plugin_errortracking",
        "plugin_pi_support",
    ]
    """Order of settings."""

    usersettings: list[str] = ["access", "interface"]
    """Order of user settings."""

    wizard: list[str] = [
        "plugin_softwareupdate_update",
        "plugin_backup",
        "plugin_corewizard_acl",
        "plugin_corewizard_onlinecheck",
    ]
    """Order of wizards."""

    about: list[str] = [
        "about",
        "plugin_pi_support",
        "supporters",
        "authors",
        "changelog",
        "license",
        "thirdparty",
        "plugin_pluginmanager",
        "plugin_achievements",
        "plugin_achievements_2",
        "systeminfo",
    ]
    """Order of about dialog items."""

    generic: list[str] = []
    """Order of generic items."""


@with_attrs_docs
class ComponentDisabledConfig(BaseModel):
    navbar: list[str] = []
    """Disabled navbar items."""
    sidebar: list[str] = []
    """Disabled sidebar items."""
    tab: list[str] = []
    """Disabled tabs."""
    settings: list[str] = []
    """Disabled settings."""
    usersettings: list[str] = []
    """Disabled user settings."""
    wizard: list[str] = []
    """Disabled wizards."""
    about: list[str] = []
    """Disabled about dialog items."""
    generic: list[str] = []
    """Disabled generic items."""


@with_attrs_docs
class ComponentConfig(BaseModel):
    order: ComponentOrderConfig = ComponentOrderConfig()
    """Defines the order of the components within their respective containers."""

    disabled: ComponentDisabledConfig = ComponentDisabledConfig()
    """Disabled components per container. If a component is included here it will not be included in OctoPrint's UI at all. Note that this might mean that critical functionality will not be available if no replacement is registered."""


class ThumbnailAlignmentEnum(str, Enum):
    left = "left"
    right = "right"
    center = "center"


@with_attrs_docs
class ThumbnailConfig(BaseModel):
    filelistEnabled: bool = True
    """Whether to display thumbnails for printables on the file list, if available."""

    filelistScale: int = 25
    """Percentage of file list width to use for thumbnail. Note that if the image is smaller, it won't be scaled up."""

    filelistAlignment: ThumbnailAlignmentEnum = ThumbnailAlignmentEnum.left
    """Alignment of thumbnail in file list."""

    filelistPreview: bool = False
    """Whether to enable a preview popover with the full thumbnail size when hovering over the thumbnail in the file list."""

    stateEnabled: bool = True
    """Whether to display thumbnails for printable on the state panel, if available."""

    stateScale: int = 75
    """Percentage of state panel width to use for thumbnail. Note that if the image is smaller, it won't be scaled up."""


@with_attrs_docs
class AppearanceConfig(BaseModel):
    name: str = ""
    """Use this to give your OctoPrint instance a name. It will be displayed in the title bar (as "<Name> [OctoPrint]") and in the navigation bar (as "OctoPrint: <>")"""

    color: ColorEnum = ColorEnum.default
    """Use this to color the navigation bar."""

    colorTransparent: bool = False
    """Makes the color of the navigation bar "transparent". In case your printer uses acrylic for its frame 😉."""

    colorIcon: bool = True

    defaultLanguage: str = "_default"
    """Default language of OctoPrint. If left unset OctoPrint will try to match up available languages with the user's browser settings."""

    showFahrenheitAlso: bool = False
    """Show temperatures in Celsius as well as in Fahrenheit."""

    fuzzyTimes: bool = True
    """Display fuzzy times for print time estimations."""

    closeModalsWithClick: bool = True
    """Allow closing modals with a click outside of them."""

    showInternalFilename: bool = True
    """Show the internal filename in the files sidebar, if necessary."""

    components: ComponentConfig = ComponentConfig()
    """Configures the order and availability of the UI components."""

    thumbnails: ThumbnailConfig = ThumbnailConfig()
    """Configured how thumbnails are shown in the UI"""
