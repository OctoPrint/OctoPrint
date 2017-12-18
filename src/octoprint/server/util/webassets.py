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

from webassets.bundle import Bundle
from webassets.merge import MemoryHunk, BaseHunk
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
		source = kwargs.get("source", "n/a")

		out.write("// source: " + source + "\n")
		out.write(_in.read())
		out.write("\n;\n")


class ChainedHunk(BaseHunk):
	def __init__(self, *hunks):
		self._hunks = hunks

	def mtime(self):
		pass

	def data(self):
		result = u""
		for hunk in self._hunks:
			if isinstance(hunk, tuple) and len(hunk) == 2:
				hunk, f = hunk
			else:
				f = lambda x: x
			result += f(hunk.data())
		return result


_PLUGIN_BUNDLE_WRAPPER_PREFIX = \
u"""// JS assets for plugin {plugin}
(function () {{
    try {{
        """
_PLUGIN_BUNDLE_WRAPPER_SUFFIX = \
u"""
    }} catch (error) {{
        log.error("Error in JS assets for plugin {plugin}:", (error.stack || error));
    }}
}})();
"""
class JsPluginBundle(Bundle):
	def __init__(self, plugin, *args, **kwargs):
		Bundle.__init__(self, *args, **kwargs)
		self.plugin = plugin

	def _merge_and_apply(self, ctx, output, force, parent_debug=None,
	                     parent_filters=None, extra_filters=None,
	                     disable_cache=None):
		hunk = Bundle._merge_and_apply(self, ctx, output, force, parent_debug=parent_debug,
		                               parent_filters=parent_filters, extra_filters=extra_filters,
		                               disable_cache=disable_cache)

		return ChainedHunk(MemoryHunk(_PLUGIN_BUNDLE_WRAPPER_PREFIX.format(plugin=self.plugin)),
		                   (hunk, lambda x: x.replace("\n", "\n        ")),
		                   MemoryHunk(_PLUGIN_BUNDLE_WRAPPER_SUFFIX.format(plugin=self.plugin)))
