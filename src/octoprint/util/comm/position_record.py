# -*- coding: utf-8 -*-

class PositionRecord(object):
	_standard_attrs = {"x", "y", "z", "e", "f", "t"}

	@classmethod
	def valid_e(cls, attr):
		if not attr.startswith("e"):
			return False

		try:
			int(attr[1:])
		except ValueError:
			return False

		return True

	def __init__(self, *args, **kwargs):
		attrs = self._standard_attrs | set(
			key for key in kwargs if self.valid_e(key))
		for attr in attrs:
			setattr(self, attr, kwargs.get(attr))

	def copy_from(self, other):
		# make sure all standard attrs and attrs from other are set
		attrs = self._standard_attrs | set(
			key for key in dir(other) if self.valid_e(key))
		for attr in attrs:
			setattr(self, attr, getattr(other, attr))

		# delete attrs other doesn't have
		attrs = set(key for key in dir(self) if self.valid_e(key)) - attrs
		for attr in attrs:
			delattr(self, attr)

	def as_dict(self):
		attrs = self._standard_attrs | set(
			key for key in dir(self) if self.valid_e(key))
		return dict((attr, getattr(self, attr)) for attr in attrs)
