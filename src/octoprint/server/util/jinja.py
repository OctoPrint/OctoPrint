# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

from jinja2 import nodes
from jinja2.ext import Extension

import logging

class ExceptionHandlerExtension(Extension):
	tags = {"try"}

	def __init__(self, environment):
		super(ExceptionHandlerExtension, self).__init__(environment)
		self._logger = logging.getLogger(__name__)

	def parse(self, parser):
		token = parser.stream.next()
		lineno = token.lineno
		filename = parser.name
		error = parser.parse_expression()

		args = [error, nodes.Const(filename), nodes.Const(lineno)]
		try:
			body = parser.parse_statements(["name:endtry"], drop_needle=True)
			node = nodes.CallBlock(self.call_method("_handle_body", args),
			                       [], [], body).set_lineno(lineno)
		except Exception as e:
			# that was expected
			self._logger.exception("Caught exception while parsing template")
			node = nodes.CallBlock(self.call_method("_handle_error", [nodes.Const(self._format_error(error, e, filename, lineno))]),
			                       [], [], []).set_lineno(lineno)

		return node

	def _handle_body(self, error, filename, lineno, caller):
		try:
			return caller()
		except Exception as e:
			self._logger.exception("Caught exception while compiling template {filename} at line {lineno}".format(**locals()))
			error_string = self._format_error(error, e, filename, lineno)
			return error_string if error_string else ""

	def _handle_error(self, error, caller):
		return error if error else ""

	def _format_error(self, error, exception, filename, lineno):
		if not error:
			return ""

		try:
			return error.format(exception=exception, filename=filename, lineno=lineno)
		except:
			self._logger.exception("Error while compiling exception output for template {filename} at line {lineno}".format(**locals()))
			return "Unknown error"

trycatch = ExceptionHandlerExtension
