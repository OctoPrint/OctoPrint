__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"


def get_param_dict(data, options):
    options_by_name = dict((option.name, option) for option in options)

    result = {}
    for key, value in data.items():
        if key not in options_by_name:
            continue
        option = options_by_name[key]
        result[key] = option.convert(value)
    return result


class ParamType(object):
    type = "generic"

    def __init__(
        self,
        name,
        title,
        default=None,
        advanced=False,
        expert=False,
        warning=False,
        labels=None,
        help=None,
    ):
        if labels is None:
            labels = []

        self.name = name
        self.title = title
        self.default = default
        self.advanced = advanced
        self.expert = expert
        self.warning = warning
        self.labels = labels
        self.help = help

    def as_dict(self):
        return {
            "name": self.name,
            "title": self.title,
            "default": self.default,
            "advanced": self.advanced,
            "expert": self.expert,
            "warning": self.warning,
            "labels": self.labels,
            "help": self.help,
            "type": self.type,
        }

    def convert(self, value):
        return value

    def __repr__(self):
        return (
            "{}(".format(self.__class__.__name__)
            + ", ".join(
                [
                    "{}={!r}".format(key, value)
                    for key, value in self.__dict__.items()
                    if not key.startswith("_")
                ]
            )
            + ")"
        )


class TextType(ParamType):
    type = "text"

    def convert(self, value):
        if isinstance(value, bytes):
            value = value.decode("utf-8", "replace")
        return value


class IntegerType(ParamType):
    type = "integer"

    def __init__(self, name, title, min=None, max=None, unit=None, **kwargs):
        self.min = min
        self.max = max
        self.unit = unit
        ParamType.__init__(self, name, title, **kwargs)

    def as_dict(self):
        result = ParamType.as_dict(self)
        result.update({"min": self.min, "max": self.max, "unit": self.unit})
        return result

    def convert(self, value):
        try:
            value = int(value)
        except ValueError:
            raise ValueError("value {!r} is not a valid integer".format(value))

        if self.min is not None and value < self.min:
            raise ValueError(
                "value {} is less than minimum valid value {}".format(value, self.min)
            )
        if self.max is not None and value > self.max:
            raise ValueError(
                "value {} is greater than maximum valid value {}".format(value, self.max)
            )

        return value


class FloatType(ParamType):
    type = "float"

    def __init__(self, name, title, min=None, max=None, unit=None, **kwargs):
        self.min = min
        self.max = max
        self.unit = unit
        ParamType.__init__(self, name, title, **kwargs)

    def as_dict(self):
        result = ParamType.as_dict(self)
        result.update({"min": self.min, "max": self.max, "unit": self.unit})
        return result

    def convert(self, value):
        try:
            value = float(value)
        except ValueError:
            raise ValueError("value {!r} is not a valid float".format(value))

        if self.min is not None and value < self.min:
            raise ValueError(
                "value {} is less than minimum valid value {}".format(value, self.min)
            )
        if self.max is not None and value > self.max:
            raise ValueError(
                "value {} is greater than maximum valid value {}".format(value, self.max)
            )

        return value


class BooleanType(ParamType):
    type = "boolean"

    def convert(self, value):
        try:
            value = bool(value)
        except ValueError:
            raise ValueError("value {!r} is not a valid boolean".format(value))

        return value


class ChoiceType(ParamType):
    type = "choice"

    def __init__(self, name, title, choices, **kwargs):
        self.choices = choices
        ParamType.__init__(self, name, title, **kwargs)

    def as_dict(self):
        result = ParamType.as_dict(self)
        result.update({"choices": list(map(lambda x: x.as_dict(), self.choices))})
        return result


class SmallChoiceType(ChoiceType):
    type = "smallchoice"


class GroupChoiceType(ChoiceType):
    type = "groupchoice"

    def __init__(self, name, title, choices, group, defaults=None, **kwargs):
        if defaults is None:
            defaults = {}

        ChoiceType.__init__(self, name, title, choices, **kwargs)

        self.group = group
        self.defaults = defaults

    def as_dict(self):
        result = ChoiceType.as_dict(self)
        result["group"] = self.group.as_dict()
        result["defaults"] = self.defaults
        return result


class SuggestionType(ParamType):
    type = "suggestion"

    def __init__(self, name, title, suggestions, factory, **kwargs):
        self.suggestions = suggestions
        self.factory = factory
        ParamType.__init__(self, name, title, **kwargs)

    def as_dict(self):
        result = ParamType.as_dict(self)
        result.update({"suggestions": list(map(lambda x: x.as_dict(), self.suggestions))})
        return result


class ListType(ParamType):
    type = "list"

    def __init__(self, name, title, factory=None, **kwargs):
        if factory is None:
            factory = lambda x: x

        self.factory = factory
        ParamType.__init__(self, name, title, **kwargs)

    def convert(self, value):
        if isinstance(value, str):
            items = map(str.strip, value.split(","))
        elif isinstance(value, list):
            items = value
        else:
            raise ValueError(
                "value {!r} must be either a comma-separated string or a list".format(
                    value
                )
            )

        return list(map(self.factory, items))


class SmallListType(ListType):
    type = "smalllist"


class ParamGroup(ParamType):
    type = "group"

    def __init__(self, name, title, params, **kwargs):
        ParamType.__init__(self, name, title, **kwargs)
        self.params = params

    def as_dict(self):
        result = ParamType.as_dict(self)
        result["params"] = [x.as_dict() for x in self.params]
        return result

    def convert(self, value):
        if not isinstance(value, dict):
            raise ValueError("value {!r} must be a dict".format(value))
        return dict((k, v.convert()) for k, v in value.items())


class Value(object):
    def __init__(self, value, title=None, warning=False, labels=None, help=None):
        if labels is None:
            labels = []

        self.value = value
        self.title = title if title else value
        self.warning = warning
        self.labels = labels
        self.help = help

    def as_dict(self):
        return {
            "value": self.value,
            "title": self.title,
            "warning": self.warning,
            "labels": self.labels,
            "help": self.help,
        }
