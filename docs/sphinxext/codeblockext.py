# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'The MIT License <http://opensource.org/licenses/MIT>'
__copyright__ = "Copyright (C) 2015 Gina Häußge - Released under terms of the MIT License"

from sphinx.directives.code import CodeBlock

import sphinx.highlighting
from sphinx.highlighting import PygmentsBridge
from sphinx.ext import doctest
from sphinx.util.texescape import tex_hl_escape_map_new

from docutils.nodes import General, FixedTextElement, literal_block, container
from docutils.parsers.rst import directives

from six import text_type

from pygments import highlight
from pygments.filters import VisibleWhitespaceFilter, ErrorToken
from pygments.lexers.python import PythonConsoleLexer
from pygments.util import ClassNotFound

def _merge_dict(a, b):
	"""
	Little helper to merge two dicts a and b on the fly.
	"""
	result = dict(a)
	result.update(b)
	return result

class literal_block_ext(General, FixedTextElement):
	"""
	Custom node which is basically the same as a :class:`literal_block`, just with whitespace support and introduced
	in order to be able to have a custom visitor.
	"""

	@classmethod
	def from_literal_block(cls, block):
		"""
		Factory method constructing an instance exactly copying all attributes over from ``block`` and settings a
		custom ``tagname``.
		"""
		new = literal_block_ext()
		for a in ("attributes", "basic_attributes", "child_text_separator", "children", "document", "known_attributes",
		          "line", "list_attributes", "local_attributes", "parent", "rawsource", "source"):
			setattr(new, a, getattr(block, a))
		new.tagname = "literal_block_ext"
		return new

class CodeBlockExt(CodeBlock):
	"""
	This is basically an extension of a regular :class:`CodeBlock` directive which just supports an additional option
	``whitespace`` which if present will enable (together with everything else in here) to render whitespace in
	code blocks.
	"""

	option_spec = _merge_dict(CodeBlock.option_spec, dict(whitespace=directives.flag))

	def run(self):
		# get result from parent implementation
		code_block = CodeBlock.run(self)

		def find_and_wrap_literal_block(node):
			"""
			Recursive method to turn all literal blocks located within a node into :class:`literal_block_ext`.
			"""

			if isinstance(node, container):
				# container node => handle all children
				children = []
				for child in node.children:
					children.append(find_and_wrap_literal_block(child))
				node.children = children
				return node

			elif isinstance(node, literal_block):
				# literal block => replace it
				return self._wrap_literal_block(node)

			else:
				# no idea what that is => leave it alone
				return node

		# replace all created literal_blocks with literal_block_ext instances
		return map(find_and_wrap_literal_block, code_block)

	def _wrap_literal_block(self, node):
		literal = literal_block_ext.from_literal_block(node)
		literal["whitespace"] = "whitespace" in self.options
		return literal

class PygmentsBridgeExt(object):
	"""
	Wrapper for :class:`PygmentsBridge`, delegates everything to the wrapped ``bridge`` but :method:`highlight_block`,
	which calls the parent implementation for lexer selection, then
	"""

	def __init__(self, bridge, whitespace):
		self._bridge = bridge
		self._whitespace = whitespace

	def __getattr__(self, item):
		return getattr(self._bridge, item)

	def highlight_block(self, source, lang, opts=None, warn=None, force=False, **kwargs):
		if not self._whitespace:
			return self._bridge.highlight_block(source, lang, opts=opts, warn=warn, force=force, **kwargs)

		# We are still here => we need to basically do everything the parent implementation does (and does so in a very
		# inextensible way...), but inject the whitespace filter into the used lexer just before the highlighting run
		# and remove it afterwards so the lexer can be safely reused.
		#
		# For this we define a context manager that will allow us to wrap a lexer and modify its filters on the fly to
		# include the whitespace filter.

		class whitespace(object):
			def __init__(self, lexer):
				self._lexer = lexer
				self._orig_filters = lexer.filters
				self._orig_tabsize = lexer.tabsize

			def __enter__(self):
				new_filters = list(self._orig_filters)
				new_filters.append(VisibleWhitespaceFilter(spaces=True, tabs=True, tabsize=self._lexer.tabsize))
				self._lexer.filters = new_filters
				self._lexer.tabsize = 0
				return self._lexer

			def __exit__(self, type, value, traceback):
				self._lexer.filters = self._orig_filters
				self._lexer.tabsize = self._orig_tabsize

		# Then a ton of copy-pasted code follows. Sadly, we need to do this since we have no way to inject ourselves
		# into the highlighting call otherwise - lexer selection and actual call are tightly coupled in the original
		# "highlight_block" method, with no means for external code to inject different functionality.
		#
		# Unless otherwise marked ("MODIFIED"), any code in this method after this line is copied verbatim from the
		# implementation of sphinx.highlighting.PygmentsBridge, released under the Simplified BSD License, the copyright
		# lies with the respective authors.

		if not isinstance(source, text_type):
			source = source.decode()

		# find out which lexer to use
		if lang in ('py', 'python'):
			if source.startswith('>>>'):
				# interactive session
				lexer = sphinx.highlighting.lexers['pycon']
			elif not force:
				# maybe Python -- try parsing it
				if self.try_parse(source):
					lexer = sphinx.highlighting.lexers['python']
				else:
					lexer = sphinx.highlighting.lexers['none']
			else:
				lexer = sphinx.highlighting.lexers['python']
		elif lang in ('python3', 'py3') and source.startswith('>>>'):
			# for py3, recognize interactive sessions, but do not try parsing...
			lexer = sphinx.highlighting.lexers['pycon3']
		elif lang == 'guess':
			try:
				lexer = sphinx.highlighting.guess_lexer(source)
			except Exception:
				lexer = sphinx.highlighting.lexers['none']
		else:
			if lang in sphinx.highlighting.lexers:
				lexer = sphinx.highlighting.lexers[lang]
			else:
				try:
					lexer = sphinx.highlighting.lexers[lang] = sphinx.highlighting.get_lexer_by_name(lang, **opts or {})
				except ClassNotFound:
					if warn:
						warn('Pygments lexer name %r is not known' % lang)
						lexer = sphinx.highlighting.lexers['none']
					else:
						raise
				else:
					lexer.add_filter('raiseonerror')

		if not isinstance(source, text_type):
			source = source.decode()

		# trim doctest options if wanted
		if isinstance(lexer, PythonConsoleLexer) and self._bridge.trim_doctest_flags:
			source = doctest.blankline_re.sub('', source)
			source = doctest.doctestopt_re.sub('', source)

		# highlight via Pygments
		formatter = self._bridge.get_formatter(**kwargs)
		try:
			# MODIFIED: replaced by whitespace wrapped call
			with whitespace(lexer) as l:
				hlsource = highlight(source, l, formatter)
			# /MODIFIED
		except ErrorToken:
			# this is most probably not the selected language,
			# so let it pass unhighlighted

			# MODIFIED: replaced by whitespace wrapped call
			with whitespace(sphinx.highlighting.lexers["none"]) as l:
				hlsource = highlight(source, l, formatter)
			# /MODIFIED
		if self._bridge.dest == 'html':
			return hlsource
		else:
			if not isinstance(hlsource, text_type):  # Py2 / Pygments < 1.6
				hlsource = hlsource.decode()
			return hlsource.translate(tex_hl_escape_map_new)


class whitespace_highlighter(object):
	"""
	Context manager for adapting the used highlighter on a translator for a given node's whitespace properties.
	"""
	def __init__(self, translator, node):
		self.translator = translator
		self.node = node

		self._orig_highlighter = self.translator.highlighter

	def __enter__(self):
		whitespace = self.node["whitespace"] if "whitespace" in self.node else False
		if whitespace:
			self.translator.highlighter = PygmentsBridgeExt(self._orig_highlighter, whitespace)
		return self.translator

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.translator.highlighter = self._orig_highlighter


def visit_literal_block_ext(translator, node):
	"""
	When our custom code block is visited, we temporarily exchange the highlighter used in the translator, call the
	visitor for regular literal blocks, then switch back again.
	"""
	with whitespace_highlighter(translator, node):
		translator.visit_literal_block(node)


def depart_literal_block_ext(translator, node):
	"""
	Just call the depart function for regular literal blocks.
	"""
	with whitespace_highlighter(translator, node):
		translator.depart_literal_block(node)


def setup(app):
	# custom directive
	app.add_directive("code-block-ext", CodeBlockExt)

	# custom node type
	handler = (visit_literal_block_ext, depart_literal_block_ext)
	app.add_node(literal_block_ext, html=handler, latex=handler, text=handler)

	return dict(version="0.1")