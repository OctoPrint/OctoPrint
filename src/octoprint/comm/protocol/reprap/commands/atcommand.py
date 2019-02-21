# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.comm.protocol.reprap.commands import Command

from octoprint.util import pp

class AtCommand(Command):

	pattern = staticmethod(lambda x: x.startswith("@"))

	@staticmethod
	def from_line(line, **kwargs):
		split = line.split(None, 1)
		if len(split) == 2:
			atcommand = split[0]
			parameters = split[1]
		else:
			atcommand = split[0]
			parameters = ""

		atcommand = atcommand[1:]

		return AtCommand(line, atcommand, parameters, **kwargs)

	def __init__(self, line, atcommand, parameters, **kwargs):
		self.atcommand = atcommand
		self.parameters = parameters
		super(AtCommand, self).__init__(line, **kwargs)

	def __repr__(self):
		return "AtCommand({!r},{!r},{!r},type={!r},tags={}".format(self.line,
		                                                           self.atcommand,
		                                                           self.parameters,
		                                                           self.type,
		                                                           pp(self.tags))

