__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021 The OctoPrint Project - Released under terms of the AGPLv3 License"


def strip_comment(line):
    if ";" not in line:
        # shortcut
        return line

    escaped = False
    result = []
    for c in line:
        if c == ";" and not escaped:
            break
        result += c
        escaped = (c == "\\") and not escaped
    return "".join(result).strip()
