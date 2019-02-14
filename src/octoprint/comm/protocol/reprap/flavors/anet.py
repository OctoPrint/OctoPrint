# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

from .repetier import RepetierFlavor

class AnetA8RepetierFlavor(RepetierFlavor):

	key = "aneta8repetier"
	name = "Anet A8"

	@classmethod
	def identifier(cls, firmware_name, firmware_info):
		return "anet_a8" in firmware_name.lower()

