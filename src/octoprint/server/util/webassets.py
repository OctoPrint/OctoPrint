# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <gina@octoprint.org>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import re

try:
	from urllib import parse as urlparse
except:
	import urlparse

from webassets.filter import Filter
from webassets.filter.cssrewrite.base import PatternRewriter
import webassets.filter.cssrewrite.urlpath as urlpath


def replace_url(source_url, output_url, url):
	# If path is an absolute one, keep it
	parsed = urlparse.urlparse(url)

	if not parsed.scheme and not parsed.path.startswith('/'):
		abs_source_url = urlparse.urljoin(source_url, url)

		# relpath() will not detect this case
		if urlparse.urlparse(abs_source_url).scheme:
			return abs_source_url

		# rewritten url: relative path from new location (output)
		# to location of referenced file (source + current url)
		url = urlpath.relpath(output_url, abs_source_url)

	return url


class UrlRewriter(PatternRewriter):

	def input(self, _in, out, **kw):
		source, source_path, output, output_path = \
			kw['source'], kw['source_path'], kw['output'], kw['output_path']

		self.source_path = source_path
		self.output_path = output_path
		self.source_url = self.ctx.resolver.resolve_source_to_url(
			self.ctx, source_path, source)
		self.output_url = self.ctx.resolver.resolve_output_to_url(
			self.ctx, output)

		return super(UrlRewriter, self).input(_in, out, **kw)

	def replace_url(self, url):
		return replace_url(self.source_url, self.output_url, url)


class LessImportRewrite(UrlRewriter):
	name = "less_importrewrite"

	patterns = {
		"import_rewrite": re.compile("(@import(\s+\(.*\))?\s+)\"(.*)\";")
	}

	def import_rewrite(self, m):
		import_with_options = m.group(1)
		import_url = self.replace_url(m.group(3))
		return "{import_with_options}\"{import_url}\";".format(**locals())


class SourceMapRewrite(UrlRewriter):
	name = "sourcemap_urlrewrite"

	patterns = {
		"url_rewrite": re.compile("(//#\s+sourceMappingURL=)(.*)")
	}

	def url_rewrite(self, m):
		mapping = m.group(1)
		source_url = self.replace_url(m.group(2))
		return "{mapping}{source_url}".format(**locals())


class SourceMapRemove(PatternRewriter):
	name = "sourcemap_remove"

	patterns = {
		"sourcemap_remove": re.compile("(//#\s+sourceMappingURL=)(.*)")
	}

	def sourcemap_remove(self, m):
		return ""


class JsDelimiterBundler(Filter):
	name = "js_delimiter_bundler"
	options = {}

	def input(self, _in, out, **kwargs):
		out.write(_in.read())
		out.write("\n;\n")
