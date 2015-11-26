# coding=utf-8
from __future__ import absolute_import

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os

from jinja2.loaders import FileSystemLoader, PrefixLoader, ChoiceLoader, \
	TemplateNotFound, split_template_path

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
		filter_results = map(lambda x: not os.path.exists(os.path.join(x, path)) or self.path_filter(os.path.join(x, path)),
		                     self.searchpath)
		return all(filter_results)


def get_all_template_paths(loader):
	def walk_folder(folder):
		files = []
		walk_dir = os.walk(folder, followlinks=True)
		for dirpath, dirnames, filenames in walk_dir:
			for filename in filenames:
				path = os.path.join(dirpath, filename)
				files.append(path)
		return files

	def collect_templates_for_loader(loader):
		if isinstance(loader, FilteredFileSystemLoader):
			result = []
			for folder in loader.searchpath:
				result += walk_folder(folder)
			return filter(loader.path_filter, result)

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


def get_all_asset_paths(env):
	result = []
	for bundle in env:
		for content in bundle.resolve_contents():
			try:
				if not content:
					continue
				path = content[1]
				if not os.path.isfile(path):
					continue
				result.append(path)
			except IndexError:
				# intentionally ignored
				pass
	return result
