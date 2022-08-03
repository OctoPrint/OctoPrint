from __future__ import annotations

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "The MIT License <http://opensource.org/licenses/MIT>"
__copyright__ = "Copyright (C) 2015 Gina Häußge - Released under terms of the MIT License"


import codecs
from contextlib import closing
from typing import Any

import requests
from sphinx.directives.code import (
    LiteralInclude,
    LiteralIncludeReader,
    container_wrapper,
    dedent_lines,
    logger,
    nodes,
    parselinenos,
)
from sphinx.util.nodes import set_source_info

cache = {}


class OnlineIncludeReader(LiteralIncludeReader):
    def read_file(self, filename: str, location: Any = None) -> list[str]:

        global cache
        try:
            if filename in cache:
                lines = cache[filename]
            else:
                with closing(requests.get(filename, stream=True)) as r:
                    r.encoding = self.encoding
                    lines = r.text.splitlines(True)
                    cache[filename] = lines

            if "tab-width" in self.options:
                lines = [line.expandtabs(self.options["tab-width"]) for line in lines]

            return lines
        except OSError:
            raise OSError("Include file %r not found or reading it failed" % filename)
        except UnicodeError:
            raise UnicodeError(
                "Encoding %r used for reading included file %r seems to "
                "be wrong, try giving an :encoding: option" % (self.encoding, filename)
            )


class OnlineIncludeDirective(LiteralInclude):
    def run(self) -> list[nodes.Node]:
        document = self.state.document
        if not document.settings.file_insertion_enabled:
            return [
                document.reporter.warning("File insertion disabled", line=self.lineno)
            ]
        # convert options['diff'] to absolute path
        if "diff" in self.options:
            _, path = self.env.relfn2path(self.options["diff"])
            self.options["diff"] = path

        try:
            location = self.state_machine.get_source_and_line(self.lineno)
            url = self.arguments[0]

            reader = OnlineIncludeReader(url, self.options, self.config)
            text, lines = reader.read(location=location)

            retnode = nodes.literal_block(text, text, source=url)
            set_source_info(self, retnode)
            if self.options.get("diff"):  # if diff is set, set udiff
                retnode["language"] = "udiff"
            elif "language" in self.options:
                retnode["language"] = self.options["language"]
            retnode["linenos"] = (
                "linenos" in self.options
                or "lineno-start" in self.options
                or "lineno-match" in self.options
            )
            retnode["classes"] += self.options.get("class", [])
            extra_args = retnode["highlight_args"] = {}
            if "emphasize-lines" in self.options:
                hl_lines = parselinenos(self.options["emphasize-lines"], lines)
                if any(i >= lines for i in hl_lines):
                    logger.warning(
                        "line number spec is out of range(1-%d): %r"
                        % (lines, self.options["emphasize-lines"]),
                        location=location,
                    )
                extra_args["hl_lines"] = [x + 1 for x in hl_lines if x < lines]
            extra_args["linenostart"] = reader.lineno_start

            if "caption" in self.options:
                caption = self.options["caption"] or self.arguments[0]
                retnode = container_wrapper(self, retnode, caption)

            # retnode will be note_implicit_target that is linked from caption and numref.
            # when options['name'] is provided, it should be primary ID.
            self.add_name(retnode)

            return [retnode]
        except Exception as exc:
            return [document.reporter.warning(str(exc), line=self.lineno)]


def visit_onlineinclude(translator, node):
    translator.visit_literal_block(node)


def depart_onlineinclude(translator, node):
    translator.depart_literal_block(node)


def setup(app):
    app.add_directive("onlineinclude", OnlineIncludeDirective)

    handler = (visit_onlineinclude, depart_onlineinclude)
    app.add_node(OnlineIncludeDirective, html=handler, latex=handler, text=handler)
