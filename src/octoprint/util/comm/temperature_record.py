# -*- coding: utf-8 -*-

class TemperatureRecord(object):
	def __init__(self):
		self._tools = dict()
		self._bed = (None, None)
		self._chamber = (None, None)

	def copy_from(self, other):
		self._tools = other.tools
		self._bed = other.bed

	def set_tool(self, tool, actual=None, target=None):
		current = self._tools.get(tool, (None, None))
		self._tools[tool] = self._to_new_tuple(current, actual, target)

	def set_bed(self, actual=None, target=None):
		current = self._bed
		self._bed = self._to_new_tuple(current, actual, target)

	def set_chamber(self, actual=None, target=None):
		current = self._chamber
		self._chamber = self._to_new_tuple(current, actual, target)

	@property
	def tools(self):
		return dict(self._tools)

	@property
	def bed(self):
		return self._bed

	@property
	def chamber(self):
		return self._chamber

	def as_script_dict(self):
		result = dict()

		tools = self.tools
		for tool, data in tools.items():
			result[tool] = dict(actual=data[0], target=data[1])

		bed = self.bed
		result["b"] = dict(actual=bed[0], target=bed[1])

		chamber = self.chamber
		result["c"] = dict(actual=chamber[0], target=chamber[1])

		return result

	@classmethod
	def _to_new_tuple(cls, current, actual, target):
		if current is None or not isinstance(current,
											 tuple) or len(current) != 2:
			current = (None, None)

		if actual is None and target is None:
			return current

		old_actual, old_target = current

		if actual is None:
			return old_actual, target
		elif target is None:
			return actual, old_target
		else:
			return actual, target
