# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Marc Hannappel <salandora@gmail.com>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask.json import JSONEncoder, JSONDecoder


class OctoPrintJsonEncoder(JSONEncoder):
	json_encoder = dict()
	json_multi_encoder = dict()

	def default(self, obj):
		data_types = type(obj).__mro__
		if data_types[0] in self.json_encoder:
			node = self.json_encoder[data_types[0]](obj)
		else:
			for data_type in data_types:
				if data_type in self.json_multi_encoder:
					node = self.json_multi_encoder[data_type](obj)
					break
			else:
				node = JSONEncoder.default(self, obj)

		return node

	@classmethod
	def add_encoder(cls, data_type, encoder):
		if 'json_encoder' not in cls.__dict__:
			cls.json_encoder = cls.json_encoder.copy()

		cls.json_encoder[data_type] = encoder

	@classmethod
	def add_multi_encoder(cls, data_type, encoder):
		if 'json_multi_encoder' not in cls.__dict__:
			cls.json_multi_encoder = cls.json_multi_encoder.copy()

		cls.json_multi_encoder[data_type] = encoder


class OctoPrintJsonDecoder(JSONDecoder):
	json_decoder = dict()

	def __init__(self, **kwargs):
		JSONDecoder.__init__(self, object_hook=self.dict_to_object)
		self._object_hook = kwargs.pop('object_hook') if 'object_hook' in kwargs else None

	def dict_to_object(self, d):
		inst = None
		if self._object_hook is not None:
			inst = self._object_hook(d)

		if inst is None:
			for decoder in self.json_decoder:
				inst = self.json_decoder[decoder](self, d)
				if inst is not None:
					return inst
			else:
				inst = d

		return inst

	@classmethod
	def add_decoder(cls, name, decoder):
		if 'json_decoder' not in cls.__dict__:
			cls.json_decoder = cls.json_decoder.copy()

		cls.json_decoder[name] = decoder
