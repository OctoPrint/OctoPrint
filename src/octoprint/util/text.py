__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2020 The OctoPrint Project - Released under terms of the AGPLv3 License"

import re

from emoji import demojize

from octoprint.util import to_unicode
from octoprint.vendor.awesome_slugify import Slugify

_UNICODE_VARIATIONS = re.compile("[\ufe00-\ufe0f]", re.U)
_SLUGIFIES = {}


def demojify(text):
    text = to_unicode(text)
    text = remove_unicode_variations(text)
    return demojize(text, delimiters=("", ""))


def sanitize(text, safe_chars="-_.", demoji=True):
    """
    Sanitizes text by running it through slugify and optionally emoji translating.

    Examples:

    >>> sanitize("Hello World!")
    'Hello-World'
    >>> sanitize("Hello World!", safe_chars="-_. ")
    'Hello World'
    >>> sanitize("\u2764")
    'red_heart'
    >>> sanitize("\u2764\ufe00")
    'red_heart'
    >>> sanitize("\u2764", demoji=False)
    ''

    Args:
        text: the text to sanitize
        safe_chars: characters to consider safe and to keep after sanitization
        demoji: whether to also convert emoji to text

    Returns: the sanitized text
    """
    slugify = _SLUGIFIES.get(safe_chars)
    if slugify is None:
        slugify = Slugify()
        slugify.safe_chars = safe_chars
        _SLUGIFIES[safe_chars] = slugify

    text = to_unicode(text)
    if demoji:
        text = demojify(text)
    return slugify(text)


def remove_unicode_variations(text):
    return _UNICODE_VARIATIONS.sub("", text)


_OLD_FORMAT_REGEX = re.compile(
    r"%\([a-zA-Z0-9_]+\)[#0\- +]*\d*(\.[0-9]+)?[hlL]?[diouxXeEfFgGcrs]"
)
# '%(' + name + ')' + opt(conversion_flags) + opt(min_field_width) + opt(precision) + opt(length_mod) + conversion_type
#
# conversion_flags: '#', '0', '-', ' ', '+'
# min_field_width: \d+
# precision: '.' + \d+
# length_mod: 'h' | 'l' | 'L'
# conversion_type: 'd' | 'i' | 'o' | 'u' | 'x' | 'X' | 'e' | 'E' | 'f' | 'F' | 'g' | 'G' | 'c' | 'r' | 's'
#
# we ignore stuff without a named placeholder as well as parameterized width and precision
#
# see https://docs.python.org/2/library/stdtypes.html#string-formatting


def has_old_style_formatting(text: str) -> bool:
    """
    Checks whether ``text`` contains old ``%(foo)s`` style formatting.

    Examples:

    >>> has_old_style_formatting("test {foo!s} bar")
    False
    >>> has_old_style_formatting("G1 X%(x)s F%(feedrate)s")
    True
    >>> has_old_style_formatting("G1 X%(x)f F%(feedrate)f")
    True
    >>> has_old_style_formatting("G1 X%(x)f F%(feedrate)lf")
    True
    >>> has_old_style_formatting("G1 X%(x)f F%(feedrate)0f")
    True
    >>> has_old_style_formatting("G1 X%(x)f F%(feedrate)+f")
    True
    >>> has_old_style_formatting("G1 X%(x)f F%(feedrate)-f")
    True
    >>> has_old_style_formatting("G1 X%(x)f F%(feedrate).2f")
    True
    >>> has_old_style_formatting("foo %(fnord)10s bar")
    True
    >>> has_old_style_formatting("foo %(fnord)-10s bar")
    True
    >>> has_old_style_formatting("foo %(fnord).5s bar")
    True
    >>> has_old_style_formatting("foo %(fnord)-10.5s bar")
    True
    >>> has_old_style_formatting("foo %(fnord)06.2f bar")
    True
    >>> has_old_style_formatting("foo %(fnord)+d bar")
    True
    >>> has_old_style_formatting("foo %% bar")
    True

    Args:
        text: The text to check

    Returns:
        ``True`` if old style formatting was found, ``False`` otherwise
    """
    return "%%" in text or _OLD_FORMAT_REGEX.search(text) is not None
