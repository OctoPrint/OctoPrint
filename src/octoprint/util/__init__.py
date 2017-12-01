# coding=utf-8
from __future__ import absolute_import, division, print_function

"""
This module bundles commonly used utility methods or helper classes that are used in multiple places within
OctoPrint's source code.
"""

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import os
import traceback
import sys
import re
import tempfile
import logging
import shutil
import threading
from functools import wraps
import warnings
import contextlib
import collections

try:
	import queue
except ImportError:
	import Queue as queue

from past.builtins import basestring

logger = logging.getLogger(__name__)

def warning_decorator_factory(warning_type):
	def specific_warning(message, stacklevel=1, since=None, includedoc=None, extenddoc=False):
		def decorator(func):
			@wraps(func)
			def func_wrapper(*args, **kwargs):
				# we need to increment the stacklevel by one because otherwise we'll get the location of our
				# func_wrapper in the log, instead of our caller (which is the real caller of the wrapped function)
				warnings.warn(message, warning_type, stacklevel=stacklevel + 1)
				return func(*args, **kwargs)

			if includedoc is not None and since is not None:
				docstring = "\n.. deprecated:: {since}\n   {message}\n\n".format(since=since, message=includedoc)
				if extenddoc and hasattr(func_wrapper, "__doc__") and func_wrapper.__doc__ is not None:
					docstring = func_wrapper.__doc__ + "\n" + docstring
				func_wrapper.__doc__ = docstring

			return func_wrapper

		return decorator
	return specific_warning

deprecated = warning_decorator_factory(DeprecationWarning)
"""
A decorator for deprecated methods. Logs a deprecation warning via Python's `:mod:`warnings` module including the
supplied ``message``. The call stack level used (for adding the source location of the offending call to the
warning) can be overridden using the optional ``stacklevel`` parameter. If both ``since`` and ``includedoc`` are
provided, a deprecation warning will also be added to the function's docstring by providing or extending its ``__doc__``
property.

Arguments:
    message (string): The message to include in the deprecation warning.
    stacklevel (int): Stack level for including the caller of the offending method in the logged warning. Defaults to 1,
        meaning the direct caller of the method. It might make sense to increase this in case of the function call
        happening dynamically from a fixed position to not shadow the real caller (e.g. in case of overridden
        ``getattr`` methods).
    includedoc (string): Message about the deprecation to include in the wrapped function's docstring.
    extenddoc (boolean): If True the original docstring of the wrapped function will be extended by the deprecation
        message, if False (default) it will be replaced with the deprecation message.
    since (string): Version since when the function was deprecated, must be present for the docstring to get extended.

Returns:
    function: The wrapped function with the deprecation warnings in place.
"""

pending_deprecation = warning_decorator_factory(PendingDeprecationWarning)
"""
A decorator for methods pending deprecation. Logs a pending deprecation warning via Python's `:mod:`warnings` module
including the supplied ``message``. The call stack level used (for adding the source location of the offending call to
the warning) can be overridden using the optional ``stacklevel`` parameter. If both ``since`` and ``includedoc`` are
provided, a deprecation warning will also be added to the function's docstring by providing or extending its ``__doc__``
property.

Arguments:
    message (string): The message to include in the deprecation warning.
    stacklevel (int): Stack level for including the caller of the offending method in the logged warning. Defaults to 1,
        meaning the direct caller of the method. It might make sense to increase this in case of the function call
        happening dynamically from a fixed position to not shadow the real caller (e.g. in case of overridden
        ``getattr`` methods).
    extenddoc (boolean): If True the original docstring of the wrapped function will be extended by the deprecation
        message, if False (default) it will be replaced with the deprecation message.
    includedoc (string): Message about the deprecation to include in the wrapped function's docstring.
    since (string): Version since when the function was deprecated, must be present for the docstring to get extended.

Returns:
    function: The wrapped function with the deprecation warnings in place.
"""

def get_formatted_size(num):
	"""
	Formats the given byte count as a human readable rounded size expressed in the most pressing unit among B(ytes),
	K(ilo)B(ytes), M(ega)B(ytes), G(iga)B(ytes) and T(era)B(ytes), with one decimal place.

	Based on http://stackoverflow.com/a/1094933/2028598

	Arguments:
	    num (int): The byte count to format

	Returns:
	    string: The formatted byte count.
	"""

	for x in ["B","KB","MB","GB"]:
		if num < 1024.0:
			return "%3.1f%s" % (num, x)
		num /= 1024.0
	return "%3.1f%s" % (num, "TB")


def is_allowed_file(filename, extensions):
	"""
	Determines if the provided ``filename`` has one of the supplied ``extensions``. The check is done case-insensitive.

	Arguments:
	    filename (string): The file name to check against the extensions.
	    extensions (list): The extensions to check against, a list of strings

	Return:
	    boolean: True if the file name's extension matches one of the allowed extensions, False otherwise.
	"""

	return "." in filename and filename.rsplit(".", 1)[1].lower() in map(str.lower, extensions)


def get_formatted_timedelta(d):
	"""
	Formats a timedelta instance as "HH:MM:ss" and returns the resulting string.

	Arguments:
	    d (datetime.timedelta): The timedelta instance to format

	Returns:
	    string: The timedelta formatted as "HH:MM:ss"
	"""

	if d is None:
		return None
	hours = d.days * 24 + d.seconds // 3600
	minutes = (d.seconds % 3600) // 60
	seconds = d.seconds % 60
	return "%02d:%02d:%02d" % (hours, minutes, seconds)


def get_formatted_datetime(d):
	"""
	Formats a datetime instance as "YYYY-mm-dd HH:MM" and returns the resulting string.

	Arguments:
	    d (datetime.datetime): The datetime instance to format

	Returns:
	    string: The datetime formatted as "YYYY-mm-dd HH:MM"
	"""

	if d is None:
		return None

	return d.strftime("%Y-%m-%d %H:%M")


def get_class(name):
	"""
	Retrieves the class object for a given fully qualified class name.

	Arguments:
	    name (string): The fully qualified class name, including all modules separated by ``.``

	Returns:
	    type: The class if it could be found.

	Raises:
	    ImportError
	"""

	import importlib

	mod_name, cls_name = name.rsplit(".", 1)
	m = importlib.import_module(mod_name)
	try:
		return getattr(m, cls_name)
	except AttributeError:
		raise ImportError("No module named " + name)


def get_exception_string():
	"""
	Retrieves the exception info of the last raised exception and returns it as a string formatted as
	``<exception type>: <exception message> @ <source file>:<function name>:<line number>``.

	Returns:
	    string: The formatted exception information.
	"""

	locationInfo = traceback.extract_tb(sys.exc_info()[2])[0]
	return "%s: '%s' @ %s:%s:%d" % (str(sys.exc_info()[0].__name__), str(sys.exc_info()[1]), os.path.basename(locationInfo[0]), locationInfo[2], locationInfo[1])


@deprecated("get_free_bytes has been deprecated and will be removed in the future",
            includedoc="Replaced by `psutil.disk_usage <http://pythonhosted.org/psutil/#psutil.disk_usage>`_.",
            since="1.2.5")
def get_free_bytes(path):
	import psutil
	return psutil.disk_usage(path).free


def get_dos_filename(input, existing_filenames=None, extension=None, whitelisted_extensions=None, **kwargs):
	"""
	Converts the provided input filename to a 8.3 DOS compatible filename. If ``existing_filenames`` is provided, the
	conversion result will be guaranteed not to collide with any of the filenames provided thus.

	Uses :func:`find_collision_free_name` internally.

	Arguments:
	    input (string): The original filename incl. extension to convert to the 8.3 format.
	    existing_filenames (list): A list of existing filenames with which the generated 8.3 name must not collide.
	        Optional.
	    extension (string): The .3 file extension to use for the generated filename. If not provided, the extension of
	        the provided ``filename`` will simply be truncated to 3 characters.
	    whitelisted_extensions (list): A list of extensions on ``input`` that will be left as-is instead of
	        exchanging for ``extension``.
	    kwargs (dict): Additional keyword arguments to provide to :func:`find_collision_free_name`.

	Returns:
	    string: A 8.3 compatible translation of the original filename, not colliding with the optionally provided
	        ``existing_filenames`` and with the provided ``extension`` or the original extension shortened to
	        a maximum of 3 characters.

	Raises:
	    ValueError: No 8.3 compatible name could be found that doesn't collide with the provided ``existing_filenames``.

	Examples:

	    >>> get_dos_filename("test1234.gco")
	    u'test1234.gco'
	    >>> get_dos_filename("test1234.gcode")
	    u'test1234.gco'
	    >>> get_dos_filename("test12345.gco")
	    u'test12~1.gco'
	    >>> get_dos_filename("test1234.fnord", extension="gco")
	    u'test1234.gco'
	    >>> get_dos_filename("auto0.g", extension="gco")
	    u'auto0.gco'
	    >>> get_dos_filename("auto0.g", extension="gco", whitelisted_extensions=["g"])
	    u'auto0.g'
	    >>> get_dos_filename(None)
	    >>> get_dos_filename("foo")
	    u'foo'
	"""

	if input is None:
		return None

	if existing_filenames is None:
		existing_filenames = []

	if extension is not None:
		extension = extension.lower()

	if whitelisted_extensions is None:
		whitelisted_extensions = []

	filename, ext = os.path.splitext(input)

	ext = ext.lower()
	ext = ext[1:] if ext.startswith(".") else ext
	if ext in whitelisted_extensions or extension is None:
		extension = ext

	return find_collision_free_name(filename, extension, existing_filenames, **kwargs)


def find_collision_free_name(filename, extension, existing_filenames, max_power=2):
	"""
	Tries to find a collision free translation of "<filename>.<extension>" to the 8.3 DOS compatible format,
	preventing collisions with any of the ``existing_filenames``.

	First strips all of ``."/\\[]:;=,`` from the filename and extensions, converts them to lower case and truncates
	the ``extension`` to a maximum length of 3 characters.

	If the filename is already equal or less than 8 characters in length after that procedure and "<filename>.<extension>"
	are not contained in the ``existing_files``, that concatenation will be returned as the result.

	If not, the following algorithm will be applied to try to find a collision free name::

	    set counter := power := 1
	    while counter < 10^max_power:
	        set truncated := substr(filename, 0, 6 - power + 1) + "~" + counter
	        set result := "<truncated>.<extension>"
	        if result is collision free:
	            return result
	        counter++
	        if counter >= 10 ** power:
	            power++
	    raise ValueError

	This will basically -- for a given original filename of ``some_filename`` and an extension of ``gco`` -- iterate
	through names of the format ``some_f~1.gco``, ``some_f~2.gco``, ..., ``some_~10.gco``, ``some_~11.gco``, ...,
	``<prefix>~<n>.gco`` for ``n`` less than 10 ^ ``max_power``, returning as soon as one is found that is not colliding.

	Arguments:
	    filename (string): The filename without the extension to convert to 8.3.
	    extension (string): The extension to convert to 8.3 -- will be truncated to 3 characters if it's longer than
	        that.
	    existing_filenames (list): A list of existing filenames to prevent name collisions with.
	    max_power (int): Limits the possible attempts of generating a collision free name to 10 ^ ``max_power``
	        variations. Defaults to 2, so the name generation will maximally reach ``<name>~99.<ext>`` before
	        aborting and raising an exception.

	Returns:
	    string: A 8.3 representation of the provided original filename, ensured to not collide with the provided
	        ``existing_filenames``

	Raises:
	    ValueError: No collision free name could be found.

	Examples:

	    >>> find_collision_free_name("test1234", "gco", [])
	    u'test1234.gco'
	    >>> find_collision_free_name("test1234", "gcode", [])
	    u'test1234.gco'
	    >>> find_collision_free_name("test12345", "gco", [])
	    u'test12~1.gco'
	    >>> find_collision_free_name("test 123", "gco", [])
	    u'test_123.gco'
	    >>> find_collision_free_name("test1234", "g o", [])
	    u'test1234.g_o'
	    >>> find_collision_free_name("test12345", "gco", ["test12~1.gco"])
	    u'test12~2.gco'
	    >>> many_files = ["test12~{}.gco".format(x) for x in range(10)[1:]]
	    >>> find_collision_free_name("test12345", "gco", many_files)
	    u'test1~10.gco'
	    >>> many_more_files = many_files + ["test1~{}.gco".format(x) for x in range(10, 99)]
	    >>> find_collision_free_name("test12345", "gco", many_more_files)
	    u'test1~99.gco'
	    >>> many_more_files_plus_one = many_more_files + ["test1~99.gco"]
	    >>> find_collision_free_name("test12345", "gco", many_more_files_plus_one)
	    Traceback (most recent call last):
	    ...
	    ValueError: Can't create a collision free filename
	    >>> find_collision_free_name("test12345", "gco", many_more_files_plus_one, max_power=3)
	    u'test~100.gco'

	"""

	if not isinstance(filename, unicode):
		filename = unicode(filename)
	if not isinstance(extension, unicode):
		extension = unicode(extension)

	def make_valid(text):
		return re.sub(r"\s+", "_", text.translate({ord(i):None for i in ".\"/\\[]:;=,"})).lower()

	filename = make_valid(filename)
	extension = make_valid(extension)
	extension = extension[:3] if len(extension) > 3 else extension

	full_name_format = u"{filename}.{extension}" if extension else u"{filename}"

	result = full_name_format.format(filename=filename,
	                                 extension=extension)
	if len(filename) <= 8 and not result in existing_filenames:
		# early exit
		return result

	counter = 1
	power = 1
	prefix_format = u"{segment}~{counter}"
	while counter < (10 ** max_power):
		prefix = prefix_format.format(segment=filename[:(6 - power + 1)], counter=str(counter))
		result = full_name_format.format(filename=prefix,
		                                 extension=extension)
		if result not in existing_filenames:
			return result
		counter += 1
		if counter >= 10 ** power:
			power += 1

	raise ValueError("Can't create a collision free filename")


def silent_remove(file):
	"""
	Silently removes a file. Does not raise an error if the file doesn't exist.

	Arguments:
	    file (string): The path of the file to be removed
	"""

	try:
		os.remove(file)
	except OSError:
		pass


def sanitize_ascii(line):
	if not isinstance(line, basestring):
		raise ValueError("Expected either str or unicode but got {} instead".format(line.__class__.__name__ if line is not None else None))
	return to_unicode(line, encoding="ascii", errors="replace").rstrip()


def filter_non_ascii(line):
	"""
	Filter predicate to test if a line contains non ASCII characters.

	Arguments:
	    line (string): The line to test

	Returns:
	    boolean: True if the line contains non ASCII characters, False otherwise.
	"""

	try:
		to_str(to_unicode(line, encoding="ascii"), encoding="ascii")
		return False
	except ValueError:
		return True


def to_str(s_or_u, encoding="utf-8", errors="strict"):
	"""Make sure ``s_or_u`` is a str."""
	if isinstance(s_or_u, unicode):
		return s_or_u.encode(encoding, errors=errors)
	else:
		return s_or_u


def to_unicode(s_or_u, encoding="utf-8", errors="strict"):
	"""Make sure ``s_or_u`` is a unicode string."""
	if isinstance(s_or_u, str):
		return s_or_u.decode(encoding, errors=errors)
	else:
		return s_or_u


def chunks(l, n):
	"""
	Yield successive n-sized chunks from l.

	Taken from http://stackoverflow.com/a/312464/2028598
	"""
	for i in range(0, len(l), n):
		yield l[i:i+n]


def is_running_from_source():
	root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
	return os.path.isdir(os.path.join(root, "src")) and os.path.isfile(os.path.join(root, "setup.py"))


def dict_merge(a, b, leaf_merger=None):
	"""
	Recursively deep-merges two dictionaries.

	Taken from https://www.xormedia.com/recursively-merge-dictionaries-in-python/

	Example::

	    >>> a = dict(foo="foo", bar="bar", fnord=dict(a=1))
	    >>> b = dict(foo="other foo", fnord=dict(b=2, l=["some", "list"]))
	    >>> expected = dict(foo="other foo", bar="bar", fnord=dict(a=1, b=2, l=["some", "list"]))
	    >>> dict_merge(a, b) == expected
	    True
	    >>> dict_merge(a, None) == a
	    True
	    >>> dict_merge(None, b) == b
	    True
	    >>> dict_merge(None, None) == dict()
	    True
	    >>> def leaf_merger(a, b):
	    ...     if isinstance(a, list) and isinstance(b, list):
	    ...         return a + b
	    ...     raise ValueError()
	    >>> result = dict_merge(dict(l1=[3, 4], l2=[1], a="a"), dict(l1=[1, 2], l2="foo", b="b"), leaf_merger=leaf_merger)
	    >>> result.get("l1") == [3, 4, 1, 2]
	    True
	    >>> result.get("l2") == "foo"
	    True
	    >>> result.get("a") == "a"
	    True
	    >>> result.get("b") == "b"
	    True

	Arguments:
	    a (dict): The dictionary to merge ``b`` into
	    b (dict): The dictionary to merge into ``a``
	    leaf_merger (callable): An optional callable to use to merge leaves (non-dict values)

	Returns:
	    dict: ``b`` deep-merged into ``a``
	"""

	from copy import deepcopy

	if a is None:
		a = dict()
	if b is None:
		b = dict()

	if not isinstance(b, dict):
		return b
	result = deepcopy(a)
	for k, v in b.items():
		if k in result and isinstance(result[k], dict):
			result[k] = dict_merge(result[k], v, leaf_merger=leaf_merger)
		else:
			merged = None
			if k in result and callable(leaf_merger):
				try:
					merged = leaf_merger(result[k], v)
				except ValueError:
					# can't be merged by leaf merger
					pass

			if merged is None:
				merged = deepcopy(v)

			result[k] = merged
	return result


def dict_sanitize(a, b):
	"""
	Recursively deep-sanitizes ``a`` based on ``b``, removing all keys (and
	associated values) from ``a`` that do not appear in ``b``.

	Example::

	    >>> a = dict(foo="foo", bar="bar", fnord=dict(a=1, b=2, l=["some", "list"]))
	    >>> b = dict(foo=None, fnord=dict(a=None, b=None))
	    >>> expected = dict(foo="foo", fnord=dict(a=1, b=2))
	    >>> dict_sanitize(a, b) == expected
	    True
	    >>> dict_clean(a, b) == expected
	    True

	Arguments:
	    a (dict): The dictionary to clean against ``b``.
	    b (dict): The dictionary containing the key structure to clean from ``a``.

	Results:
	    dict: A new dict based on ``a`` with all keys (and corresponding values) found in ``b`` removed.
	"""

	from copy import deepcopy
	if not isinstance(b, dict):
		return a

	result = deepcopy(a)
	for k, v in a.items():
		if not k in b:
			del result[k]
		elif isinstance(v, dict):
			result[k] = dict_sanitize(v, b[k])
		else:
			result[k] = deepcopy(v)
	return result
dict_clean = deprecated("dict_clean has been renamed to dict_sanitize",
                        includedoc="Replaced by :func:`dict_sanitize`")(dict_sanitize)


def dict_minimal_mergediff(source, target):
	"""
	Recursively calculates the minimal dict that would be needed to be deep merged with
	a in order to produce the same result as deep merging a and b.

	Example::

	    >>> a = dict(foo=dict(a=1, b=2), bar=dict(c=3, d=4))
	    >>> b = dict(bar=dict(c=3, d=5), fnord=None)
	    >>> c = dict_minimal_mergediff(a, b)
	    >>> c == dict(bar=dict(d=5), fnord=None)
	    True
	    >>> dict_merge(a, c) == dict_merge(a, b)
	    True

	Arguments:
	    source (dict): Source dictionary
	    target (dict): Dictionary to compare to source dictionary and derive diff for

	Returns:
	    dict: The minimal dictionary to deep merge on ``source`` to get the same result
	        as deep merging ``target`` on ``source``.
	"""

	if not isinstance(source, dict) or not isinstance(target, dict):
		raise ValueError("source and target must be dictionaries")

	if source == target:
		# shortcut: if both are equal, we return an empty dict as result
		return dict()

	from copy import deepcopy

	all_keys = set(source.keys() + target.keys())
	result = dict()
	for k in all_keys:
		if k not in target:
			# key not contained in b => not contained in result
			continue

		if k in source:
			# key is present in both dicts, we have to take a look at the value
			value_source = source[k]
			value_target = target[k]

			if value_source != value_target:
				# we only need to look further if the values are not equal

				if isinstance(value_source, dict) and isinstance(value_target, dict):
					# both are dicts => deeper down it goes into the rabbit hole
					result[k] = dict_minimal_mergediff(value_source, value_target)
				else:
					# new b wins over old a
					result[k] = deepcopy(value_target)

		else:
			# key is new, add it
			result[k] = deepcopy(target[k])
	return result


def dict_contains_keys(keys, dictionary):
	"""
	Recursively deep-checks if ``dictionary`` contains all keys found in ``keys``.

	Example::

	    >>> positive = dict(foo="some_other_bar", fnord=dict(b=100))
	    >>> negative = dict(foo="some_other_bar", fnord=dict(b=100, d=20))
	    >>> dictionary = dict(foo="bar", fnord=dict(a=1, b=2, c=3))
	    >>> dict_contains_keys(positive, dictionary)
	    True
	    >>> dict_contains_keys(negative, dictionary)
	    False

	Arguments:
	    a (dict): The dictionary to check for the keys from ``b``.
	    b (dict): The dictionary whose keys to check ``a`` for.

	Returns:
	    boolean: True if all keys found in ``b`` are also present in ``a``, False otherwise.
	"""

	if not isinstance(keys, dict) or not isinstance(dictionary, dict):
		return False

	for k, v in keys.items():
		if not k in dictionary:
			return False
		elif isinstance(v, dict):
			if not dict_contains_keys(v, dictionary[k]):
				return False

	return True


class fallback_dict(dict):
	def __init__(self, custom, *fallbacks):
		self.custom = custom
		self.fallbacks = fallbacks

	def __getitem__(self, item):
		for dictionary in self._all():
			if item in dictionary:
				return dictionary[item]
		raise KeyError()

	def __setitem__(self, key, value):
		self.custom[key] = value

	def __delitem__(self, key):
		for dictionary in self._all():
			if key in dictionary:
				del dictionary[key]

	def keys(self):
		result = set()
		for dictionary in self._all():
			result += dictionary.keys()
		return result

	def _all(self):
		return [self.custom] + list(self.fallbacks)



def dict_filter(dictionary, filter_function):
	"""
	Filters a dictionary with the provided filter_function

	Example::

	    >>> data = dict(key1="value1", key2="value2", other_key="other_value", foo="bar", bar="foo")
	    >>> dict_filter(data, lambda k, v: k.startswith("key")) == dict(key1="value1", key2="value2")
	    True
	    >>> dict_filter(data, lambda k, v: v.startswith("value")) == dict(key1="value1", key2="value2")
	    True
	    >>> dict_filter(data, lambda k, v: k == "foo" or v == "foo") == dict(foo="bar", bar="foo")
	    True
	    >>> dict_filter(data, lambda k, v: False) == dict()
	    True
	    >>> dict_filter(data, lambda k, v: True) == data
	    True
	    >>> dict_filter(None, lambda k, v: True)
	    Traceback (most recent call last):
	        ...
	    AssertionError
	    >>> dict_filter(data, None)
	    Traceback (most recent call last):
	        ...
	    AssertionError

	Arguments:
	    dictionary (dict): The dictionary to filter
	    filter_function (callable): The filter function to apply, called with key and
	        value of an entry in the dictionary, must return ``True`` for values to
	        keep and ``False`` for values to strip

	Returns:
	    dict: A shallow copy of the provided dictionary, stripped of the key-value-pairs
	        for which the ``filter_function`` returned ``False``
	"""
	assert isinstance(dictionary, dict)
	assert callable(filter_function)
	return dict((k, v) for k, v in dictionary.items() if filter_function(k, v))


# Source: http://stackoverflow.com/a/6190500/562769
class DefaultOrderedDict(collections.OrderedDict):
	def __init__(self, default_factory=None, *a, **kw):

		if default_factory is not None and not callable(default_factory):
			raise TypeError('first argument must be callable')
		collections.OrderedDict.__init__(self, *a, **kw)
		self.default_factory = default_factory

	def __getitem__(self, key):
		try:
			return collections.OrderedDict.__getitem__(self, key)
		except KeyError:
			return self.__missing__(key)

	def __missing__(self, key):
		if self.default_factory is None:
			raise KeyError(key)
		self[key] = value = self.default_factory()
		return value

	def __reduce__(self):
		if self.default_factory is None:
			args = tuple()
		else:
			args = self.default_factory,
		return type(self), args, None, None, self.items()

	def copy(self):
		return self.__copy__()

	def __copy__(self):
		return type(self)(self.default_factory, self)

	def __deepcopy__(self, memo):
		import copy
		return type(self)(self.default_factory,
		                  copy.deepcopy(self.items()))

	# noinspection PyMethodOverriding
	def __repr__(self):
		return 'OrderedDefaultDict(%s, %s)' % (self.default_factory,
		                                       collections.OrderedDict.__repr__(self))


class Object(object):
	pass

def interface_addresses(family=None):
	"""
	Retrieves all of the host's network interface addresses.
	"""

	import netifaces
	if not family:
		family = netifaces.AF_INET

	for interface in netifaces.interfaces():
		try:
			ifaddresses = netifaces.ifaddresses(interface)
		except:
			continue
		if family in ifaddresses:
			for ifaddress in ifaddresses[family]:
				if not ifaddress["addr"].startswith("169.254."):
					yield ifaddress["addr"]

def address_for_client(host, port, timeout=3.05):
	"""
	Determines the address of the network interface on this host needed to connect to the indicated client host and port.
	"""

	for address in interface_addresses():
		try:
			if server_reachable(host, port, timeout=timeout, proto="udp", source=address):
				return address
		except:
			continue

def server_reachable(host, port, timeout=3.05, proto="tcp", source=None):
	"""
	Checks if a server is reachable

	Args:
		host (str): host to check against
		port (int): port to check against
		timeout (float): timeout for check
		proto (str): ``tcp`` or ``udp``
		source (str): optional, socket used for check will be bound against this address if provided

	Returns:
		boolean: True if a connection to the server could be opened, False otherwise
	"""

	import socket

	if proto not in ("tcp", "udp"):
		raise ValueError("proto must be either 'tcp' or 'udp'")

	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM if proto == "udp" else socket.SOCK_STREAM)
		sock.settimeout(timeout)
		if source is not None:
			sock.bind((source, 0))
		sock.connect((host, port))
		return True
	except:
		return False

@contextlib.contextmanager
def atomic_write(filename, mode="w+b", prefix="tmp", suffix="", permissions=0o644, max_permissions=0o777):
	if os.path.exists(filename):
		permissions |= os.stat(filename).st_mode
	permissions &= max_permissions

	temp_config = tempfile.NamedTemporaryFile(mode=mode, prefix=prefix, suffix=suffix, delete=False)
	try:
		yield temp_config
	finally:
		temp_config.close()
	os.chmod(temp_config.name, permissions)
	shutil.move(temp_config.name, filename)


@contextlib.contextmanager
def tempdir(ignore_errors=False, onerror=None, **kwargs):
	import tempfile
	import shutil

	dirpath = tempfile.mkdtemp(**kwargs)
	try:
		yield dirpath
	finally:
		shutil.rmtree(dirpath, ignore_errors=ignore_errors, onerror=onerror)


@contextlib.contextmanager
def temppath(prefix=None, suffix=""):
	import tempfile

	temp = tempfile.NamedTemporaryFile(prefix=prefix if prefix is not None else tempfile.template,
	                                   suffix=suffix,
	                                   delete=False)
	try:
		temp.close()
		yield temp.name
	finally:
		os.remove(temp.name)


def bom_aware_open(filename, encoding="ascii", mode="r", **kwargs):
	import codecs

	codec = codecs.lookup(encoding)
	encoding = codec.name

	if kwargs is None:
		kwargs = dict()

	potential_bom_attribute = "BOM_" + codec.name.replace("utf-", "utf").upper()
	if "r" in mode and hasattr(codecs, potential_bom_attribute):
		# these encodings might have a BOM, so let's see if there is one
		bom = getattr(codecs, potential_bom_attribute)

		with open(filename, "rb") as f:
			header = f.read(4)

		if header.startswith(bom):
			encoding += "-sig"

	return codecs.open(filename, encoding=encoding, mode=mode, **kwargs)


def is_hidden_path(path):
	if path is None:
		# we define a None path as not hidden here
		return False

	path = to_unicode(path)

	filename = os.path.basename(path)
	if filename.startswith(u"."):
		# filenames starting with a . are hidden
		return True

	if sys.platform == "win32":
		# if we are running on windows we also try to read the hidden file
		# attribute via the windows api
		try:
			import ctypes
			attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
			assert attrs != -1     # INVALID_FILE_ATTRIBUTES == -1
			return bool(attrs & 2) # FILE_ATTRIBUTE_HIDDEN == 2
		except (AttributeError, AssertionError):
			pass

	# if we reach that point, the path is not hidden
	return False


try:
	from glob import escape
	glob_escape = escape
except ImportError:
	# no glob.escape - we need to implement our own
	_glob_escape_check = re.compile("([*?[])")
	_glob_escape_check_bytes = re.compile(b"([*?[])")

	def glob_escape(pathname):
		"""
		Ported from Python 3.4

		See https://github.com/python/cpython/commit/fd32fffa5ada8b8be8a65bd51b001d989f99a3d3
		"""

		drive, pathname = os.path.splitdrive(pathname)
		if isinstance(pathname, bytes):
			pathname = _glob_escape_check_bytes.sub(br"[\1]", pathname)
		else:
			pathname = _glob_escape_check.sub(r"[\1]", pathname)
		return drive + pathname


try:
	import monotonic
	monotonic_time = monotonic.monotonic
except RuntimeError:
	# no source of monotonic time available, nothing left but using time.time *cringe*
	import time
	monotonic_time = time.time


def utmify(link, source=None, medium=None, name=None, term=None, content=None):
	if source is None:
		return link

	from collections import OrderedDict
	try:
		import urlparse
		from urllib import urlencode
	except ImportError:
		# python 3
		import urllib.parse as urlparse
		from urllib.parse import urlencode

	# inspired by https://stackoverflow.com/a/2506477
	parts = list(urlparse.urlparse(link))

	# parts[4] is the url query
	query = OrderedDict(urlparse.parse_qs(parts[4]))

	query["utm_source"] = source
	if medium is not None:
		query["utm_medium"] = medium
	if name is not None:
		query["utm_name"] = name
	if term is not None:
		query["utm_term"] = term
	if content is not None:
		query["utm_content"] = content

	parts[4] = urlencode(query, doseq=True)

	return urlparse.urlunparse(parts)


class RepeatedTimer(threading.Thread):
	"""
	This class represents an action that should be run repeatedly in an interval. It is similar to python's
	own :class:`threading.Timer` class, but instead of only running once the ``function`` will be run again and again,
	sleeping the stated ``interval`` in between.

	RepeatedTimers are started, as with threads, by calling their ``start()`` method. The timer can be stopped (in
	between runs) by calling the :func:`cancel` method. The interval the time waited before execution of a loop may
	not be exactly the same as the interval specified by the user.

	For example:

	.. code-block:: python

	   def hello():
	       print("Hello World!")

	   t = RepeatedTimer(1.0, hello)
	   t.start() # prints "Hello World!" every second

	Another example with dynamic interval and loop condition:

	.. code-block:: python

	   count = 0
	   maximum = 5
	   factor = 1

	   def interval():
	       global count
	       global factor
	       return count * factor

	   def condition():
	       global count
	       global maximum
	       return count <= maximum

	   def hello():
	       print("Hello World!")

	       global count
	       count += 1

	   t = RepeatedTimer(interval, hello, run_first=True, condition=condition)
	   t.start() # prints "Hello World!" 5 times, printing the first one
	             # directly, then waiting 1, 2, 3, 4s in between (adaptive interval)

	Arguments:
	    interval (float or callable): The interval between each ``function`` call, in seconds. Can also be a callable
	        returning the interval to use, in case the interval is not static.
	    function (callable): The function to call.
	    args (list or tuple): The arguments for the ``function`` call. Defaults to an empty list.
	    kwargs (dict): The keyword arguments for the ``function`` call. Defaults to an empty dict.
	    run_first (boolean): If set to True, the function will be run for the first time *before* the first wait period.
	        If set to False (the default), the function will be run for the first time *after* the first wait period.
	    condition (callable): Condition that needs to be True for loop to continue. Defaults to ``lambda: True``.
	    on_condition_false (callable): Callback to call when the timer finishes due to condition becoming false. Will
	        be called before the ``on_finish`` callback.
	    on_cancelled (callable): Callback to call when the timer finishes due to being cancelled. Will be called
	        before the ``on_finish`` callback.
	    on_finish (callable): Callback to call when the timer finishes, either due to being cancelled or since
	        the condition became false.
	    daemon (bool): daemon flag to set on underlying thread.
	"""

	def __init__(self, interval, function, args=None, kwargs=None,
	             run_first=False, condition=None, on_condition_false=None,
	             on_cancelled=None, on_finish=None, daemon=True):
		threading.Thread.__init__(self)

		if args is None:
			args = []
		if kwargs is None:
			kwargs = dict()
		if condition is None:
			condition = lambda: True

		if not callable(interval):
			self.interval = lambda: interval
		else:
			self.interval = interval

		self.function = function
		self.finished = threading.Event()
		self.args = args
		self.kwargs = kwargs
		self.run_first = run_first
		self.condition = condition

		self.on_condition_false = on_condition_false
		self.on_cancelled = on_cancelled
		self.on_finish = on_finish

		self.daemon = daemon

	def cancel(self):
		self._finish(self.on_cancelled)

	def run(self):
		while self.condition():
			if self.run_first:
				# if we are to run the function BEFORE waiting for the first time
				self.function(*self.args, **self.kwargs)

				# make sure our condition is still met before running into the downtime
				if not self.condition():
					break

			# wait, but break if we are cancelled
			self.finished.wait(self.interval())
			if self.finished.is_set():
				return

			if not self.run_first:
				# if we are to run the function AFTER waiting for the first time
				self.function(*self.args, **self.kwargs)

		# we'll only get here if the condition was false
		self._finish(self.on_condition_false)

	def _finish(self, *callbacks):
		self.finished.set()

		for callback in callbacks:
			if not callable(callback):
				continue
			callback()

		if callable(self.on_finish):
			self.on_finish()


class CountedEvent(object):

	def __init__(self, value=0, maximum=None, **kwargs):
		self._counter = 0
		self._max = kwargs.get("max", maximum)
		self._mutex = threading.Lock()
		self._event = threading.Event()

		self._internal_set(value)

	def set(self):
		with self._mutex:
			self._internal_set(self._counter + 1)

	def clear(self, completely=False):
		with self._mutex:
			if completely:
				self._internal_set(0)
			else:
				self._internal_set(self._counter - 1)

	def wait(self, timeout=None):
		self._event.wait(timeout)

	def blocked(self):
		with self._mutex:
			return self._counter == 0

	def _internal_set(self, value):
		self._counter = value
		if self._counter <= 0:
			self._counter = 0
			self._event.clear()
		else:
			if self._max is not None and self._counter > self._max:
				self._counter = self._max
			self._event.set()


class InvariantContainer(object):
	def __init__(self, initial_data=None, guarantee_invariant=None):
		from collections import Iterable
		from threading import RLock

		if guarantee_invariant is None:
			guarantee_invariant = lambda data: data

		self._data = []
		self._mutex = RLock()
		self._invariant = guarantee_invariant

		if initial_data is not None and isinstance(initial_data, Iterable):
			for item in initial_data:
				self.append(item)

	def append(self, item):
		with self._mutex:
			self._data.append(item)
			self._data = self._invariant(self._data)

	def remove(self, item):
		with self._mutex:
			self._data.remove(item)
			self._data = self._invariant(self._data)

	def __len__(self):
		return len(self._data)

	def __iter__(self):
		return self._data.__iter__()


class PrependableQueue(queue.Queue):

	def __init__(self, maxsize=0):
		queue.Queue.__init__(self, maxsize=maxsize)

	def prepend(self, item, block=True, timeout=True):
		from time import time as _time

		self.not_full.acquire()
		try:
			if self.maxsize > 0:
				if not block:
					if self._qsize() == self.maxsize:
						raise queue.Full
				elif timeout is None:
					while self._qsize() >= self.maxsize:
						self.not_full.wait()
				elif timeout < 0:
					raise ValueError("'timeout' must be a non-negative number")
				else:
					endtime = _time() + timeout
					while self._qsize() == self.maxsize:
						remaining = endtime - _time()
						if remaining <= 0.0:
							raise queue.Full
						self.not_full.wait(remaining)
			self._prepend(item)
			self.unfinished_tasks += 1
			self.not_empty.notify()
		finally:
			self.not_full.release()

	def _prepend(self, item):
		self.queue.appendleft(item)


class TypedQueue(PrependableQueue):

	def __init__(self, maxsize=0):
		PrependableQueue.__init__(self, maxsize=maxsize)
		self._lookup = set()

	def put(self, item, item_type=None, *args, **kwargs):
		PrependableQueue.put(self, (item, item_type), *args, **kwargs)

	def get(self, *args, **kwargs):
		item, _ = PrependableQueue.get(self, *args, **kwargs)
		return item

	def prepend(self, item, item_type=None, *args, **kwargs):
		PrependableQueue.prepend(self, (item, item_type), *args, **kwargs)

	def _put(self, item):
		_, item_type = item
		if item_type is not None:
			if item_type in self._lookup:
				raise TypeAlreadyInQueue(item_type, "Type {} is already in queue".format(item_type))
			else:
				self._lookup.add(item_type)

		PrependableQueue._put(self, item)

	def _get(self):
		item = PrependableQueue._get(self)
		_, item_type = item

		if item_type is not None:
			self._lookup.discard(item_type)

		return item

	def _prepend(self, item):
		_, item_type = item
		if item_type is not None:
			if item_type in self._lookup:
				raise TypeAlreadyInQueue(item_type, "Type {} is already in queue".format(item_type))
			else:
				self._lookup.add(item_type)

		PrependableQueue._prepend(self, item)

class TypeAlreadyInQueue(Exception):
	def __init__(self, t, *args, **kwargs):
		Exception.__init__(self, *args, **kwargs)
		self.type = t


class ConnectivityChecker(object):
	"""
	Regularly checks for online connectivity.

	Tries to open a connection to the provided ``host`` and ``port`` every ``interval``
	seconds and sets the ``online`` status accordingly.
	"""

	def __init__(self, interval, host, port, enabled=True, on_change=None):
		self._interval = interval
		self._host = host
		self._port = port
		self._enabled = enabled
		self._on_change = on_change

		self._logger = logging.getLogger(__name__ + ".connectivity_checker")

		# we initialize the online flag to True if we are not enabled (we don't know any better
		# but these days it's probably a sane default)
		self._online = not self._enabled

		self._check_worker = None
		self._check_mutex = threading.RLock()

		self._run()

	@property
	def online(self):
		"""Current online status, True if online, False if offline."""
		with self._check_mutex:
			return self._online

	@property
	def host(self):
		"""DNS host to query."""
		with self._check_mutex:
			return self._host

	@host.setter
	def host(self, value):
		with self._check_mutex:
			self._host = value

	@property
	def port(self):
		"""DNS port to query."""
		with self._check_mutex:
			return self._port

	@port.setter
	def port(self, value):
		with self._check_mutex:
			self._port = value

	@property
	def interval(self):
		"""Interval between consecutive automatic checks."""
		return self._interval

	@interval.setter
	def interval(self, value):
		self._interval = value

	@property
	def enabled(self):
		"""Whether the check is enabled or not."""
		return self._enabled

	@enabled.setter
	def enabled(self, value):
		with self._check_mutex:
			old_enabled = self._enabled
			self._enabled = value

			if not self._enabled:
				if self._check_worker is not None:
					self._check_worker.cancel()

				old_value = self._online
				self._online = True

				if old_value != self._online:
					self._trigger_change(old_value, self._online)

			elif self._enabled and not old_enabled:
				self._run()

	def check_immediately(self):
		"""Check immediately and return result."""
		with self._check_mutex:
			self._perform_check()
			return self.online

	def _run(self):
		from octoprint.util import RepeatedTimer

		if not self._enabled:
			return

		if self._check_worker is not None:
			self._check_worker.cancel()

		self._check_worker = RepeatedTimer(self._interval, self._perform_check,
		                                   run_first=True)
		self._check_worker.start()

	def _perform_check(self):
		if not self._enabled:
			return

		with self._check_mutex:
			self._logger.debug("Checking against {}:{} if we are online...".format(self._host, self._port))

			old_value = self._online
			self._online = server_reachable(self._host, port=self._port)

			if old_value != self._online:
				self._trigger_change(old_value, self._online)

	def _trigger_change(self, old_value, new_value):
		self._logger.info("Connectivity changed from {} to {}".format("online" if old_value else "offline",
		                                                              "online" if new_value else "offline"))
		if callable(self._on_change):
			self._on_change(old_value, new_value)
