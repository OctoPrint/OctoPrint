# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.comm.protocol.reprap.flavors.generic import GenericFlavor

class MarlinFlavor(GenericFlavor):

	key = "marlin"
	name = "Marlin"

class BqMarlinFlavor(MarlinFlavor):

	key = "bqmarlin"
	name = "Marlin: BQ variant"

	long_running_commands = MarlinFlavor.long_running_commands + ["G92", "M800", "M801"]

class PrusaMarlinFlavor(MarlinFlavor):

	key = "prusamarlin"
	name = "Marlin: Prusa variant"
