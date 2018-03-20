# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"


import collections
import frozendict

class JsonEncoding(object):

	encoders = collections.OrderedDict()

	@classmethod
	def add_encoder(cls, type, encoder):
		cls.encoders[type] = encoder

	@classmethod
	def encode(cls, obj):
		for type, encoder in cls.encoders.items():
			if isinstance(obj, type):
				return encoder(obj)
		raise TypeError

JsonEncoding.add_encoder(frozendict.frozendict, lambda obj: dict(obj))
