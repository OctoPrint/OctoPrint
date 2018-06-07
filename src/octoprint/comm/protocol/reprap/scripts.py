# coding=utf-8
from __future__ import absolute_import, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"


from octoprint.comm.scripts import Script
from octoprint.comm.protocol.reprap.util import process_gcode_line

class GcodeScript(Script):

	def render(self, context=None):
		script = super(GcodeScript, self).render(context)
		return filter(lambda x: x is not None and x.strip() != "",
		              map(lambda x: process_gcode_line(x),
		                  script))
