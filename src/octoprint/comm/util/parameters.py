# coding=utf-8
from __future__ import absolute_import, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"


def get_param_dict(data, options):
	options_by_name = dict((option.name, option) for option in options)

	result = dict()
	for key, value in data.items():
		if not key in options_by_name:
			continue
		option = options_by_name[key]
		result[key] = option.convert(value)
	return result


class ParamType(object):
	type = "generic"

	def __init__(self, name, title, default=None):
		self.name = name
		self.title = title
		self.default = default

	def as_dict(self):
		return dict(name=self.name,
		            title=self.title,
		            default=self.default,
		            type=self.type)

	def convert(self, value):
		return value

	def __repr__(self):
		return "{}(".format(self.__class__.__name__) \
		       + ", ".join(["{}={!r}".format(key, value) for key, value in self.__dict__.items() if not key.startswith("_")]) + ")"

class TextType(ParamType):
	type = "text"

	def convert(self, value):
		if isinstance(value, bytes):
			value = value.decode("utf-8", "replace")
		return value

class IntegerType(ParamType):
	type = "integer"

	def __init__(self, name, title, min=None, max=None, default=None):
		self.min = min
		self.max = max
		ParamType.__init__(self, name, title, default=default)

	def as_dict(self):
		result = ParamType.as_dict(self)
		result.update(dict(min=self.min,
		                   max=self.max))
		return result

	def convert(self, value):
		try:
			value = int(value)
		except ValueError:
			raise ValueError("value {!r} is not a valid integer".format(value))

		if self.min is not None and value < self.min:
			raise ValueError("value {} is less than minimum valid value {}".format(value, self.min))
		if self.max is not None and value > self.max:
			raise ValueError("value {} is greater than maximum valid value {}".format(value, self.max))

		return value

class ChoiceType(ParamType):
	type = "choice"

	def __init__(self, name, title, choices, default=None):
		self.choices = choices
		ParamType.__init__(self, name, title, default=default)

	def as_dict(self):
		result = ParamType.as_dict(self)
		result.update(dict(choices=map(lambda x: x.as_dict(), self.choices)))
		return result

class SuggestionType(ParamType):
	type = "suggestion"

	def __init__(self, name, title, suggestions, factory, default=None):
		self.suggestions = suggestions
		self.factory = factory
		ParamType.__init__(self, name, title, default=default)

	def as_dict(self):
		result = ParamType.as_dict(self)
		result.update(dict(suggestions=map(lambda x: x.as_dict(), self.suggestions)))
		return result

class ListType(ParamType):
	type = "list"

	def __init__(self, name, title, factory, default=None):
		self.factory = factory
		ParamType.__init__(self, name, title, default=default)

	def convert(self, value):
		if isinstance(value, unicode):
			items = map(unicode.strip, value.split(","))
		elif isinstance(value, list):
			items = value
		else:
			raise ValueError("value {!r} must be either a comma-separated string or a list".format(value))

		return map(self.factory, items)

class Value(object):
	def __init__(self, value, title=None):
		self.value = value
		self.title = title if title else value

	def as_dict(self):
		return dict(value=self.value,
		            title=self.title)
