# coding=utf-8
from __future__ import absolute_import, unicode_literals, print_function, \
	division

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"


from octoprint.comm.protocol.reprap.flavors import ReprapGcodeFlavor

class MarlinFlavor(ReprapGcodeFlavor):

	key = "marlin"

class BqMarlinFlavor(MarlinFlavor):

	key = "bqmarlin"

	long_running_commands = MarlinFlavor.long_running_commands + ["G92", "M800", "M801"]

	@classmethod
	def comm_ignore_ok(cls, line, lower_line, state):
		return lower_line.startswith("echo:enqueueing")

