# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.comm.protocol.reprap.commands import Command
from octoprint.util import PrependableQueue, TypeAlreadyInQueue, CountedEvent

# noinspection PyCompatibility
from past.builtins import basestring

import contextlib
import copy
import logging
import threading

try:
	# noinspection PyCompatibility
	import queue
except Exception:
	# noinspection PyCompatibility
	import Queue as queue

regex_float_pattern = "[-+]?[0-9]*\.?[0-9]+"
regex_positive_float_pattern = "[+]?[0-9]*\.?[0-9]+"
regex_int_pattern = "\d+"


def strip_comment(line):
	if not ";" in line:
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


def process_gcode_line(line, offsets=None, current_tool=None):
	line = strip_comment(line).strip()
	if not len(line):
		return None

	# if offsets is not None:
	#	line = apply_temperature_offsets(line, offsets, current_tool=current_tool)

	return line


def normalize_command_handler_result(command, handler_results, tags_to_add=None):
	"""
	Normalizes a command handler result.

	Handler results can be either ``None``, a single result entry or a list of result
	entries.

	``None`` results are ignored, the provided ``command``, ``command_type``,
	``gcode``, ``subcode`` and ``tags`` are returned in that case (as single-entry list with
	one 5-tuple as entry).

	Single result entries are either:

	  * a single string defining a replacement ``command``
	  * a 1-tuple defining a replacement ``command``
	  * a 2-tuple defining a replacement ``command`` and ``command_type``
	  * a 3-tuple defining a replacement ``command`` and ``command_type`` and additional ``tags`` to set

	A ``command`` that is ``None`` will lead to the entry being ignored for
	the normalized result.

	The method returns a list of normalized result entries. Normalized result
	entries always are a 4-tuple consisting of ``command``, ``command_type``,
	``gcode`` and ``subcode``, the latter three being allowed to be ``None``. The list may
	be empty in which case the command is to be suppressed.

	Examples:
	    >>> normalize_command_handler_result("M105", None, "M105", None, None, None)
	    [(u'M105', None, u'M105', None, None)]
	    >>> normalize_command_handler_result("M105", None, "M105", None, None, "M110")
	    [(u'M110', None, u'M110', None, None)]
	    >>> normalize_command_handler_result("M105", None, "M105", None, None, ["M110"])
	    [(u'M110', None, u'M110', None, None)]
	    >>> normalize_command_handler_result("M105", None, "M105", None, None, ["M110", "M117 Foobar"])
	    [(u'M110', None, u'M110', None, None), (u'M117 Foobar', None, u'M117', None, None)]
	    >>> normalize_command_handler_result("M105", None, "M105", None, None, [("M110",), "M117 Foobar"])
	    [(u'M110', None, u'M110', None, None), (u'M117 Foobar', None, u'M117', None, None)]
	    >>> normalize_command_handler_result("M105", None, "M105", None, None, [("M110", "lineno_reset"), "M117 Foobar"])
	    [(u'M110', u'lineno_reset', u'M110', None, None), (u'M117 Foobar', None, u'M117', None, None)]
	    >>> normalize_command_handler_result("M105", None, "M105", None, None, [])
	    []
	    >>> normalize_command_handler_result("M105", None, "M105", None, None, ["M110", None])
	    [(u'M110', None, u'M110', None, None)]
	    >>> normalize_command_handler_result("M105", None, "M105", None, None, [("M110",), (None, "ignored")])
	    [(u'M110', None, u'M110', None, None)]
	    >>> normalize_command_handler_result("M105", None, "M105", None, None, [("M110",), ("M117 Foobar", "display_message"), ("tuple", "of", "unexpected", "length"), ("M110", "lineno_reset")])
	    [(u'M110', None, u'M110', None, None), (u'M117 Foobar', u'display_message', u'M117', None, None), (u'M110', u'lineno_reset', u'M110', None, None)]
	    >>> normalize_command_handler_result("M105", None, "M105", None, {"tag1", "tag2"}, ["M110", "M117 Foobar"])
	    [(u'M110', None, u'M110', None, set([u'tag1', u'tag2'])), (u'M117 Foobar', None, u'M117', None, set([u'tag1', u'tag2']))]
	    >>> normalize_command_handler_result("M105", None, "M105", None, {"tag1", "tag2"}, ["M110", "M105", "M117 Foobar"], tags_to_add={"tag3"})
	    [(u'M110', None, u'M110', None, set([u'tag1', u'tag2', u'tag3'])), (u'M105', None, u'M105', None, set([u'tag1', u'tag2'])), (u'M117 Foobar', None, u'M117', None, set([u'tag1', u'tag2', u'tag3']))]
	    >>> normalize_command_handler_result("M105", None, "M105", None, {"tag1", "tag2"}, ["M110", ("M105", "temperature_poll"), "M117 Foobar"], tags_to_add={"tag3"})
	    [(u'M110', None, u'M110', None, set([u'tag1', u'tag2', u'tag3'])), (u'M105', u'temperature_poll', u'M105', None, set([u'tag1', u'tag2', u'tag3'])), (u'M117 Foobar', None, u'M117', None, set([u'tag1', u'tag2', u'tag3']))]

	Arguments:
	    command (Command): The command for which the handler result was
	        generated
	    handler_results: The handler result(s) to normalized. Can be either
	        a single result entry or a list of result entries.
	    tags_to_add (set of unicode or None): List of tags to add to expanded result
	        entries

	Returns:
	    (list) - A list of normalized handler result entries, which are
	        ``Command`` instances
	"""

	original = command

	if handler_results is None:
		# handler didn't return anything, we'll just continue
		return [original]

	if not isinstance(handler_results, list):
		handler_results = [handler_results, ]

	result = []
	for handler_result in handler_results:
		# we iterate over all handler result entries and process each one
		# individually here

		if handler_result is None:
			# entry is None, we'll ignore that entry and continue
			continue

		if command.tags:
			# copy the tags
			tags = set(command.tags)

		def expand_tags(tags, tags_to_add):
			tags = tags.copy()
			if tags_to_add and isinstance(tags_to_add, set):
				tags |= tags_to_add
			return tags

		if isinstance(handler_result, basestring):
			# entry is just a string, replace command with it
			if handler_result != original.line:
				# command changed, swap it
				command = Command.from_line(handler_result, type=original.type,
				                            tags=expand_tags(original.tags, tags_to_add))
			result.append(command)

		elif isinstance(handler_result, Command):
			if handler_result != original:
				command = copy.copy(handler_result)
				command.tags = expand_tags(original.tags, tags_to_add)
			result.append(command)

		elif isinstance(handler_result, tuple):
			# entry is a tuple, extract command and command_type
			hook_result_length = len(handler_result)

			command_type = original.type
			command_tags = original.tags

			if hook_result_length == 1:
				# handler returned just the command
				command_line, = handler_result
			elif hook_result_length == 2:
				# handler returned command and command_type
				command_line, command_type = handler_result
			elif hook_result_length == 3:
				# handler returned command, command type and additional tags
				command_line, command_type, command_tags = handler_result
			else:
				# handler returned a tuple of an unexpected length, ignore
				# and continue
				continue

			if command_line is None:
				# command is None, ignore it and continue
				continue

			if command_line != original.line or command_type != original.type:
				# command or command_type changed, tags need to be rewritten
				command_tags = expand_tags(command_tags, tags_to_add)

			result.append(Command.from_line(command_line, type=command_type, tags=command_tags))

		# reset to original
		command, command_type, gcode, subcode, tags = original

	return result


class SendToken(CountedEvent):

	def __init__(self, value=0, maximum=None, **kwargs):
		super(SendToken, self).__init__(value=value, maximum=maximum, **kwargs)
		self._ignored = 0

	def set(self, ignore=False):
		with self._mutex:
			if ignore:
				self._ignored += 1
			self._internal_set(self._counter + 1)

	def clear(self, completely=False):
		with self._mutex:
			if completely:
				self._internal_set(0)
				self._ignored = 0
			else:
				if self._ignored > 0:
					self._ignored -= 1
					self._internal_set(self._counter - 1)
				self._internal_set(self._counter - 1)


class LineHistory(object):
	def __init__(self, max=None):
		self.max = max

		self._lines = []
		self._mutex = threading.RLock()
		self._line_number_lookup = dict()

	@property
	def lines(self):
		with self._mutex:
			return [x[0] for x in self._lines]

	def append(self, line, line_number=None):
		with self._mutex:
			self._lines.append((line, line_number))
			if line_number is not None:
				self._line_number_lookup[line_number] = line
			self._cleanup()

	def clear(self):
		with self._mutex:
			self._lines = []
			self._line_number_lookup = dict()

	def __len__(self):
		with self._mutex:
			return len(self._lines)

	def __getitem__(self, line_number):
		with self._mutex:
			return self._line_number_lookup[line_number]

	def __contains__(self, line_number):
		with self._mutex:
			return line_number in self._line_number_lookup

	def __iter__(self):
		return iter(self.lines)

	def _cleanup(self):
		if len(self._lines) <= self.max:
			return

		while len(self._lines) > self.max:
			_, line_number = self._lines.pop(0)
			if line_number is not None:
				try:
					del self._line_number_lookup[line_number]
				except KeyError:
					pass


class PositionRecord(object):
	_standard_attrs = {"x", "y", "z", "e", "f", "t"}

	@classmethod
	def valid_e(cls, attr):
		if not attr.startswith("e"):
			return False

		try:
			int(attr[1:])
		except Exception:
			return False

		return True

	def __init__(self, *args, **kwargs):
		attrs = self._standard_attrs | set([key for key in kwargs if self.valid_e(key)])
		for attr in attrs:
			setattr(self, attr, kwargs.get(attr))

	def copy_from(self, other):
		# make sure all standard attrs and attrs from other are set
		attrs = self._standard_attrs | set([key for key in dir(other) if self.valid_e(key)])
		for attr in attrs:
			setattr(self, attr, getattr(other, attr))

		# delete attrs other doesn't have
		attrs = set([key for key in dir(self) if self.valid_e(key)]) - attrs
		for attr in attrs:
			delattr(self, attr)

	def as_dict(self):
		attrs = self._standard_attrs | set([key for key in dir(self) if self.valid_e(key)])
		return dict((attr, getattr(self, attr)) for attr in attrs)


class TemperatureRecord(object):
	def __init__(self):
		self._tools = dict()
		self._bed = (None, None)

	def copy_from(self, other):
		self._tools = other.tools
		self._bed = other.bed

	def set_tool(self, tool, actual=None, target=None):
		current = self._tools.get(tool, (None, None))
		self._tools[tool] = self._to_new_tuple(current, actual, target)

	def set_bed(self, actual=None, target=None):
		current = self._bed
		self._bed = self._to_new_tuple(current, actual, target)

	@property
	def tools(self):
		return dict(self._tools)

	@property
	def bed(self):
		return self._bed

	def as_dict(self):
		result = dict()

		tools = self.tools
		for tool, data in tools.items():
			result["tool{}".format(tool)] = dict(actual=data[0],
			                                     target=data[1])

		bed = self.bed
		result["bed"] = dict(actual=bed[0],
		                     target=bed[1])

		return result

	def as_script_dict(self):
		result = self.as_dict()

		# backwards compatibility
		tools = self.tools
		for tool, data in tools.items():
			result[tool] = dict(actual=data[0],
			                    target=data[1])

		bed = self.bed
		result["b"] = dict(actual=bed[0],
		                   target=bed[1])

		return result

	@classmethod
	def _to_new_tuple(cls, current, actual, target):
		if current is None or not isinstance(current, tuple) or len(current) != 2:
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
