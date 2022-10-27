__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from enum import Enum
from typing import List, Optional, Union

from octoprint.schema import BaseModel
from octoprint.vendor.with_attrs_docs import with_attrs_docs


class LayoutEnum(str, Enum):
    horizontal = "horizontal"
    vertical = "vertical"


class ControlSliderInputConfig(BaseModel):
    min: int = 0
    """Minimum value of the slider."""

    max: int = 255
    """Maximum value of the slider."""

    step: int = 1
    """Step size per slider tick."""


class ControlInputConfig(BaseModel):
    name: str
    """Name to display for the input field."""

    parameter: str
    """Internal parameter name for the input field, used as a placeholder in `command`/`commands`."""

    default: Union[str, int, float, bool]
    """Default value for the input field."""

    slider: Optional[ControlSliderInputConfig] = None
    """If this attribute is included, instead of an input field a slider control will be rendered."""


@with_attrs_docs
class ContainerConfig(BaseModel):
    children: "List[Union[ContainerConfig, ControlConfig]]" = []
    """A list of children controls or containers contained within this container."""

    name: Optional[str] = None
    """A name to display above the container, basically a section header."""

    layout: LayoutEnum = LayoutEnum.vertical
    """The layout to use for laying out the contained children, either from top to bottom (`vertical`) or from left to right (`horizontal`)."""


@with_attrs_docs
class ControlConfig(BaseModel):
    name: str
    """The name of the control, will be displayed either on the button if it's a control sending a command or as a label for controls which only display output."""

    command: Optional[str] = None
    """A single GCODE command to send to the printer. Will be rendered as a button which sends the command to the printer upon click. The button text will be the value of the `name` attribute. Mutually exclusive with `commands` and `script`. The rendered button be disabled if the printer is currently offline or printing or alternatively if the requirements defined via the `enabled` attribute are not met."""

    commands: Optional[List[str]] = None
    """A list of GCODE commands to send to the printer. Will be rendered as a button which sends the commands to the printer upon click. The button text will be the value of the `name` attribute. Mutually exclusive with `command` and `script`. The rendered button will be disabled if the printer is currently offline or printing or alternatively if the requirements defined via the `enabled` attribute are not met."""

    script: Optional[str] = None
    """The name of a full blown [GCODE script]() to send to the printer. Will be rendered as a button which sends the script to the printer upon click. The button text will be the value of the `name` attribute. Mutually exclusive with `command` and `commands`. The rendered button will be disabled if the printer is currently offline or printing or alternatively if the requirements defined via the `enabled` attribute are not met. Values of input parameters will be available in the template context under the `parameter` variable (e.g. an input parameter `speed` will be available in the script template as `parameter.speed`). On top of that all other variables defined in the [GCODE template context]() will be available."""

    javascript: Optional[str] = None
    """A JavaScript snippet to be executed when the button rendered for `command` or `commands` is clicked. This allows to override the direct sending of the command or commands to the printer with more sophisticated behaviour. The JavaScript snippet is `eval`'d and processed in a context where the control it is part of is provided as local variable `data` and the `ControlViewModel` is available as `self`."""

    additionalClasses: Optional[str] = None
    """Additional classes to apply to the button of a `command`, `commands`, `script` or `javascript` control, other than the default `btn`. Can be used to visually style the button, e.g. set to `btn-danger` to turn the button red."""

    enabled: Optional[str] = None
    """A JavaScript snippet returning either `true` or `false` determining whether the control should be enabled or not. This allows to override the default logic for the enable state of the control (disabled if printer is offline). The JavaScript snippet is `eval`'d and processed in a context where the control it is part of is provided as local variable `data` and the `ControlViewModel` is available as `self`."""

    input: Optional[List[ControlInputConfig]] = []
    """A list of definitions of input parameters for a `command` or `commands`, to be rendered as additional input fields. `command`/`commands` may contain placeholders to be replaced by the values obtained from the user for the defined input fields."""

    regex: Optional[str] = None
    """A [regular expression <re-syntax>](https://docs.python.org/3/library/re.html#regular-expression-syntax) to match against lines received from the printer to retrieve information from it (e.g. specific output). Together with `template` this allows rendition of received data from the printer within the UI."""

    template: Optional[str] = None
    r"""A template to use for rendering the match of `regex`. May contain placeholders in [Python Format String Syntax](https://docs.python.org/3/library/string.html#formatstrings) for either named groups within the regex (e.g. `Temperature: {temperature}` for a regex `T:\s*(?P<temperature>\d+(\.\d*)`) or positional groups within the regex (e.g. `Position: X={0}, Y={1}, Z={2}, E={3}` for a regex `X:([0-9.]+) Y:([0-9.]+) Z:([0-9.]+) E:([0-9.]+)`)."""

    confirm: Optional[str] = None
    """A text to display to the user to confirm his button press. Can be used with sensitive custom controls like changing EEPROM values in order to prevent accidental clicks. The text will be displayed in a confirmation dialog."""
