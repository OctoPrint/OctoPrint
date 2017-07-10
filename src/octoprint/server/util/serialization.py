# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Marc Hannappel <salandora@gmail.com>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask.json import JSONEncoder, JSONDecoder

class OctoPrintJsonEncoder:
	json_encoder = dict()
	json_multi_encoder = dict()

	class Encoder(JSONEncoder):
		def default(self, obj):
			for data_type, func in OctoPrintJsonEncoder.json_encoder.items():
				if isinstance(obj, data_type):
					node = func(obj)
					break
			else:
				for data_type, func in OctoPrintJsonEncoder.json_multi_encoder.items():
					if isinstance(obj, data_type):
						node = func(obj)
						break
				else:
					node = JSONEncoder.default(self, obj)

			return node

	def add_encoder(self, data_type, encoder):
		OctoPrintJsonEncoder.json_encoder[data_type] = encoder

	def add_multi_encoder(self, data_type, encoder):
		OctoPrintJsonEncoder.json_multi_encoder[data_type] = encoder


class OctoPrintJsonDecoder:
	json_decoder = dict()

	class Decoder(JSONDecoder):
		def __init__(self, **kwargs):
			JSONDecoder.__init__(self, object_hook=self.dict_to_object)
			self._object_hook = kwargs.pop('object_hook', None)

		def dict_to_object(self, d):
			inst = None
			if self._object_hook is not None:
				inst = self._object_hook(d)

			if inst is None:
				for decoder in OctoPrintJsonDecoder.json_decoder:
					inst = OctoPrintJsonDecoder.json_decoder[decoder](self, d)
					if inst is not None:
						return inst
				else:
					inst = d

			return inst

	def add_decoder(self, name, decoder):
		OctoPrintJsonDecoder.json_decoder[name] = decoder
