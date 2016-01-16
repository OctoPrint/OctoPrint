# coding=utf-8
from __future__ import absolute_import, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
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
	def __init__(self, name, title, default=None):
		self.name = name
		self.title = title
		self.default = default

	def convert(self, value):
		return value

	def __repr__(self):
		return "{}(".format(self.__class__.__name__) \
		       + ", ".join(["{}={!r}".format(key, value) for key, value in self.__dict__.items() if not key.startswith("_")]) + ")"

class TextType(ParamType):
	def convert(self, value):
		if isinstance(value, bytes):
			value = value.decode("utf-8", "replace")
		return value

class IntegerType(ParamType):
	def __init__(self, name, title, min=None, max=None, default=None):
		self.min = min
		self.max = max
		ParamType.__init__(self, name, title, default=default)

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
	def __init__(self, name, title, choice_type, choices, default=None):
		self.choice_type = choice_type
		self.choices = choices
		ParamType.__init__(self, name, title, default=default)

	def convert(self, value):
		value = self.choice_type.convert(value)
		if not value in self.choices:
			raise ValueError("value {} is not a valid choice")
		return value

class SuggestionType(ParamType):
	def __init__(self, name, title, suggestion_type, suggestions, default=None):
		self.suggestion_type = suggestion_type
		self.suggestions = suggestions
		ParamType.__init__(self, name, title, default=default)

	def convert(self, value):
		value = self.suggestion_type.convert(value)
		return value

class ListType(ParamType):
	def __init__(self, name, title, item_type, default=None):
		self.item_type = item_type
		ParamType.__init__(self, name, title, default=default)

	def convert(self, value):
		if isinstance(value, unicode):
			items = map(unicode.strip, value.split(","))
		elif isinstance(value, list):
			items = value
		else:
			raise ValueError("value {!r} must be either a comma-separated string or a list".format(value))

		return map(self.item_type.convert, items)

class ConstantType(ParamType):
	def __init__(self, name, title, constant, default=None):
		ParamType.__init__(self, name, title, default=default)
		self.constant = constant
		self.default = constant

	def convert(self, value):
		return self.constant

class ConstantNameType(ConstantType):
	def __init__(self, name, title, default=None):
		ConstantType.__init__(self, name, title, constant=name, default=default)
