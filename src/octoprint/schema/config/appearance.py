__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from enum import Enum
from typing import List

from pydantic import BaseModel

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
    navbar: List[str] = [
        "settings",
        "systemmenu",
        "plugin_announcements",
        "plugin_logging_seriallog",
        "plugin_logging_plugintimingslog",
        "plugin_pi_support",
        "login",
    ]
    """Order of navbar items."""

    sidebar: List[str] = [
        "plugin_firmware_check_warning",
        "plugin_firmware_check_info",
        "connection",
        "state",
        "files",
    ]
    """Order of sidebar items."""

    tab: List[str] = [
        "temperature",
        "control",
        "plugin_gcodeviewer",
        "terminal",
        "timelapse",
    ]
    """Order of tabs."""

    settings: List[str] = [
        "section_printer",
        "serial",
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

    usersettings: List[str] = ["access", "interface"]
    """Order of user settings."""

    wizard: List[str] = [
        "plugin_softwareupdate_update",
        "plugin_backup",
        "plugin_corewizard_acl",
        "plugin_corewizard_onlinecheck",
    ]
    """Order of wizards."""

    about: List[str] = [
        "about",
        "plugin_pi_support",
        "supporters",
        "authors",
        "changelog",
        "license",
        "thirdparty",
        "plugin_pluginmanager",
    ]
    """Order of about dialog items."""

    generic: List[str] = []
    """Order of generic items."""


@with_attrs_docs
class ComponentDisabledConfig(BaseModel):
    navbar: List[str] = []
    """Disabled navbar items."""
    sidebar: List[str] = []
    """Disabled sidebar items."""
    tab: List[str] = []
    """Disabled tabs."""
    settings: List[str] = []
    """Disabled settings."""
    usersettings: List[str] = []
    """Disabled user settings."""
    wizard: List[str] = []
    """Disabled wizards."""
    about: List[str] = []
    """Disabled about dialog items."""
    generic: List[str] = []
    """Disabled generic items."""


@with_attrs_docs
class ComponentConfig(BaseModel):
    order: ComponentOrderConfig = ComponentOrderConfig()
    """Defines the order of the components within their respective containers."""

    disabled: ComponentDisabledConfig = ComponentDisabledConfig()
    """Disabled components per container. If a component is included here it will not be included in OctoPrint's UI at all. Note that this might mean that critical functionality will not be available if no replacement is registered."""


@with_attrs_docs
class AppearanceConfig(BaseModel):
    name: str = ""
    """Use this to give your OctoPrint instance a name. It will be displayed in the title bar (as "<Name> [OctoPrint]") and in the navigation bar (as "OctoPrint: <>")"""

    color: ColorEnum = "default"
    """Use this to color the navigation bar."""

    colorTransparent: bool = False
    """Makes the color of the navigation bar "transparent". In case your printer uses acrylic for its frame 😉."""

    colorIcon: bool = True

    defaultLanguage: str = "_default"
    """Default language of OctoPrint. If left unset OctoPrint will try to match up available languages with the user's browser settings."""

    showFahrenheitAlso: bool = False

    fuzzyTimes: bool = True

    closeModalsWithClick: bool = True

    showInternalFilename: bool = True
    """Show the internal filename in the files sidebar, if necessary."""

    components: ComponentConfig = ComponentConfig()
    """Configures the order and availability of the UI components."""
