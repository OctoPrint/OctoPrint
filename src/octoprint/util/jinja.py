__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import os

from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.loaders import (
    BaseLoader,
    ChoiceLoader,
    FileSystemLoader,
    PrefixLoader,
    TemplateNotFound,
    split_template_path,
)
from webassets import Bundle


class FilteredFileSystemLoader(FileSystemLoader):
    """
    Jinja2 ``FileSystemLoader`` subclass that allows filtering templates.

    Only such templates will be accessible for whose paths the provided
    ``path_filter`` filter function returns True.

    ``path_filter`` will receive the actual path on disc and should behave just
    like callables provided to Python's internal ``filter`` function, returning
    ``True`` if the path is cleared and ``False`` if it is supposed to be removed
    from results and hence ``filter(path_filter, iterable)`` should be
    equivalent to ``[item for item in iterable if path_filter(item)]``.

    If ``path_filter`` is not set or not a ``callable``, the loader will
    behave just like the regular Jinja2 ``FileSystemLoader``.
    """

    def __init__(self, searchpath, path_filter=None, **kwargs):
        FileSystemLoader.__init__(self, searchpath, **kwargs)
        self.path_filter = path_filter

    def get_source(self, environment, template):
        if callable(self.path_filter):
            pieces = split_template_path(template)
            if not self._combined_filter(os.path.join(*pieces)):
                raise TemplateNotFound(template)

        return FileSystemLoader.get_source(self, environment, template)

    def list_templates(self):
        result = FileSystemLoader.list_templates(self)

        if callable(self.path_filter):
            result = sorted(filter(self._combined_filter, result))

        return result

    def _combined_filter(self, path):
        filter_results = map(
            lambda x: not os.path.exists(os.path.join(x, path))
            or self.path_filter(os.path.join(x, path)),
            self.searchpath,
        )
        return all(filter_results)


class SelectedFilesLoader(BaseLoader):
    def __init__(self, files, encoding="utf-8"):
        self.files = files
        self.encoding = encoding

    def get_source(self, environment, template):
        if template not in self.files:
            raise TemplateNotFound(template)

        from jinja2.loaders import open_if_exists

        path = self.files[template]
        f = open_if_exists(path)
        if f is None:
            raise TemplateNotFound(template)
        try:
            contents = f.read().decode(self.encoding)
        finally:
            f.close()

        mtime = os.path.getmtime(path)

        def uptodate():
            try:
                return os.path.getmtime(path) == mtime
            except OSError:
                return False

        return contents, path, uptodate

    def list_templates(self):
        return self.files.keys()


class SelectedFilesWithConversionLoader(SelectedFilesLoader):
    def __init__(self, files, encoding="utf-8", conversion=None):
        SelectedFilesLoader.__init__(self, files, encoding=encoding)
        self.conversion = conversion

    def get_source(self, environment, template):
        contents = SelectedFilesLoader.get_source(self, environment, template)
        if callable(self.conversion):
            contents = self.conversion(contents[0]), contents[1], contents[2]
        return contents


class PrefixChoiceLoader(BaseLoader):
    def __init__(self, loader):
        self.loader = loader

    def get_source(self, environment, template):
        for prefix in sorted(self.loader.mapping.keys()):
            try:
                return self.loader.mapping[prefix].get_source(environment, template)
            except TemplateNotFound:
                pass

        raise TemplateNotFound(template)


class WarningLoader(BaseLoader):
    """
    Logs a warning if the loader is used to successfully load a template.
    """

    def __init__(self, loader, warning_message):
        self.loader = loader
        self.warning_message = warning_message

    def get_source(self, environment, template):
        import logging

        try:
            contents, filename, uptodate = self.loader.get_source(environment, template)
            logging.getLogger(__name__).warning(
                self.warning_message.format(template=template, filename=filename)
            )
            return contents, filename, uptodate
        except TemplateNotFound:
            raise


def get_all_template_paths(loader):
    def walk_folder(folder):
        files = []
        walk_dir = os.walk(folder, followlinks=True)
        for dirpath, _, filenames in walk_dir:
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                files.append(path)
        return files

    def collect_templates_for_loader(loader):
        if isinstance(loader, SelectedFilesLoader):
            import copy

            return copy.copy(list(loader.files.values()))

        elif isinstance(loader, FilteredFileSystemLoader):
            result = []
            for folder in loader.searchpath:
                result += walk_folder(folder)
            return list(filter(loader.path_filter, result))

        elif isinstance(loader, FileSystemLoader):
            result = []
            for folder in loader.searchpath:
                result += walk_folder(folder)
            return result

        elif isinstance(loader, PrefixLoader):
            result = []
            for subloader in loader.mapping.values():
                result += collect_templates_for_loader(subloader)
            return result

        elif isinstance(loader, ChoiceLoader):
            result = []
            for subloader in loader.loaders:
                result += collect_templates_for_loader(subloader)
            return result

        return []

    return collect_templates_for_loader(loader)


def get_all_asset_paths(env, verifyExist=True):
    result = []

    def get_paths(bundle):
        r = []
        for content in bundle.resolve_contents():
            try:
                if not content:
                    continue
                if isinstance(content[1], Bundle):
                    r += get_paths(content[1])
                else:
                    path = content[1]
                    if verifyExist is True and not os.path.isfile(path):
                        continue
                    r.append(path)
            except IndexError:
                # intentionally ignored
                pass
        return r

    for bundle in env:
        result += get_paths(bundle)
    return result


class ExceptionHandlerExtension(Extension):
    tags = {"try"}

    def __init__(self, environment):
        super().__init__(environment)
        self._logger = logging.getLogger(__name__)

    def parse(self, parser):
        token = next(parser.stream)
        lineno = token.lineno
        filename = parser.name
        error = parser.parse_expression()

        args = [error, nodes.Const(filename), nodes.Const(lineno)]
        try:
            body = parser.parse_statements(["name:endtry"], drop_needle=True)
            node = nodes.CallBlock(
                self.call_method("_handle_body", args), [], [], body
            ).set_lineno(lineno)
        except Exception as e:
            # that was expected
            self._logger.exception("Caught exception while parsing template")
            node = nodes.CallBlock(
                self.call_method(
                    "_handle_error",
                    [nodes.Const(self._format_error(error, e, filename, lineno))],
                ),
                [],
                [],
                [],
            ).set_lineno(lineno)

        return node

    def _handle_body(self, error, filename, lineno, caller):
        try:
            return caller()
        except Exception as e:
            self._logger.exception(
                f"Caught exception while compiling template {filename} at line {lineno}"
            )
            error_string = self._format_error(error, e, filename, lineno)
            return error_string if error_string else ""

    def _handle_error(self, error, caller):
        return error if error else ""

    def _format_error(self, error, exception, filename, lineno):
        if not error:
            return ""

        try:
            return error.format(exception=exception, filename=filename, lineno=lineno)
        except Exception:
            self._logger.exception(
                f"Error while compiling exception output for template {filename} at line {lineno}"
            )
            return "Unknown error"


trycatch = ExceptionHandlerExtension


class MarkdownFilter:
    def __init__(self, app, **markdown_options):
        self._markdown_options = markdown_options
        app.jinja_env.filters.setdefault("markdown", self)

    def __call__(self, stream):
        from markdown import Markdown
        from markupsafe import Markup

        # Markdown is not thread safe
        markdown = Markdown(**self._markdown_options)
        return Markup(markdown.convert(stream))
