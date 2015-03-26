# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'The MIT License <http://opensource.org/licenses/MIT>'
__copyright__ = "Copyright (C) 2015 Gina Häußge - Released under terms of the MIT License"


import codecs
import urllib2

from sphinx.directives import LiteralInclude, dedent_lines

cache = dict()

class OnlineIncludeDirective(LiteralInclude):

	def read_with_encoding(self, filename, document, codec_info, encoding):
		global cache

		f = None
		try:
			if not self.arguments[0] in cache:
				f = codecs.StreamReaderWriter(urllib2.urlopen(self.arguments[0]), codec_info[2],
				                              codec_info[3], 'strict')
				lines = f.readlines()
				cache[self.arguments[0]] = lines
			else:
				lines = cache[self.arguments[0]]

			lines = dedent_lines(lines, self.options.get('dedent'))
			return lines
		except (IOError, OSError, urllib2.URLError):
			return [document.reporter.warning(
				'Include file %r not found or reading it failed' % self.arguments[0],
				line=self.lineno)]
		except UnicodeError:
			return [document.reporter.warning(
				'Encoding %r used for reading included file %r seems to '
				'be wrong, try giving an :encoding: option' %
				(encoding, self.arguments[0]))]
		finally:
			if f is not None:
				f.close()

def visit_onlineinclude(translator, node):
	translator.visit_literal_block(node)

def depart_onlineinclude(translator, node):
	translator.depart_literal_block(node)

def setup(app):
	app.add_directive("onlineinclude", OnlineIncludeDirective)

	handler = (visit_onlineinclude, depart_onlineinclude)
	app.add_node(OnlineIncludeDirective, html=handler, latex=handler, text=handler)