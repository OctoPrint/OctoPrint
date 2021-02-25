__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import re
import string

from octoprint.comm.protocol.reprap.commands import Command
from octoprint.util import pp


class GcodeCommand(Command):

    pattern = staticmethod(lambda x: GcodeCommand.command_regex.match(x))

    command_regex = re.compile(
        r"^\s*((?P<GM>[GM](?P<number>\d+))(\\.(?P<subcode>\d+))?|(?P<T>T(?P<tool>\d+))|(?P<F>F(?P<feedrate>\d+)))"
    )
    parameter_regex = re.compile(
        r"(?P<key>[A-Z])((?P<value>[-+]?[0-9]*\.?[0-9]+)(?!\d)|(\s|$))"
    )

    possible_params = tuple(string.ascii_lowercase) + (
        "subcode",
        "param",
        "tool",
        "feedrate",
        "original",
    )

    @staticmethod
    def from_line(line, **kwargs):
        if isinstance(line, GcodeCommand):
            return line

        tags = kwargs.get("tags")
        if tags is None:
            tags = set()

        command_type = kwargs.get("type")

        line = line.strip()
        code = ""

        args = {"original": line, "type": command_type, "tags": tags}

        match = GcodeCommand.command_regex.match(line)

        if match is None:
            # not a gcode command
            return Command.from_line(line, **kwargs)

        if match.group("GM"):
            code = match.group("GM")

            if match.group("subcode"):
                args["subcode"] = int(match.group("subcode"))

            if match.group(0) != line:
                rest = line[len(match.group(0)) :]

                while True:
                    matched_param = GcodeCommand.parameter_regex.search(rest)
                    if not matched_param:
                        break

                    key = matched_param.group("key").lower()
                    if matched_param.group("value"):
                        value = matched_param.group("value")
                        if "." in value:
                            value = float(value)
                        else:
                            value = int(value)
                    else:
                        value = True
                    args[key] = value
                    rest = rest[: matched_param.start()] + rest[matched_param.end() :]

                rest = rest.lstrip()
                if rest:
                    args["param"] = rest

        elif match.group("T"):
            code = "T"
            args["tool"] = int(match.group("tool"))

        elif match.group("F"):
            code = "F"
            args["feedrate"] = int(match.group("feedrate"))

        return GcodeCommand(code, **args)

    def __init__(self, code, **kwargs):
        self.code = code

        self.subcode = kwargs.pop("subcode", None)
        self.tool = kwargs.pop("tool", None)
        self.feedrate = kwargs.pop("feedrate", None)
        self.param = kwargs.pop("param", None)
        self.original = kwargs.pop("original", None)

        command_type = kwargs.pop("type", None)
        tags = kwargs.pop("tags", None)

        self.args = kwargs

        if self.original is None:
            line = self._to_line()
        else:
            line = self.original

        super().__init__(line, type=command_type, tags=tags)

        self._repr = self._to_repr()

    def with_args(self, **kwargs):
        args = {
            "subcode": self.subcode,
            "tool": self.tool,
            "feedrate": self.feedrate,
            "param": self.param,
            "type": self.type,
            "tags": self.tags,
        }
        args.update(self.args)

        args.update(kwargs)

        return GcodeCommand(self.code, **args)

    def __getattr__(self, item):
        if len(item) == 1:
            return self.args.get(item, None)
        raise AttributeError("'GcodeCommand' object has no attribute '{}'".format(item))

    def __repr__(self):
        return self._repr

    def _to_line(self):
        attr = []
        for key in string.ascii_lowercase:
            value = self.args.get(key, None)
            if value is not None:
                if value is True:
                    attr.append(key.upper())
                else:
                    attr.append("{}{!r}".format(key.upper(), value))
        attribute_str = " ".join(attr)
        return "{}{}{}".format(
            self.code.upper(),
            " " + attribute_str if attribute_str else "",
            " " + self.param if self.param else "",
        )

    def _to_repr(self):
        args = [
            k + "=" + repr(getattr(self, k))
            for k in self.possible_params
            if getattr(self, k, None) is not None
        ]
        return "GcodeCommand({!r}{},type={!r},tags={})".format(
            self.code, "," + ",".join(args) if args else "", self.type, pp(self.tags)
        )
