# coding=utf-8
"""
This module bundles commonly used utility methods or helper classes that are used in multiple places withing
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

	Taken from http://stackoverflow.com/a/452981/2028598.

	Arguments:
	    name (string): The fully qualified class name, including all modules separated by ``.``

	Returns:
	    type: The class if it could be found.

	Raises:
	    AttributeError: The class could not be found.
	"""

	parts = name.split(".")
	module = ".".join(parts[:-1])
	m = __import__(module)
	for comp in parts[1:]:
		m = getattr(m, comp)
	return m


def get_exception_string():
	"""
	Retrieves the exception info of the last raised exception and returns it as a string formatted as
	``<exception type>: <exception message> @ <source file>:<function name>:<line number>``.

	Returns:
	    string: The formatted exception information.
	"""

	locationInfo = traceback.extract_tb(sys.exc_info()[2])[0]
	return "%s: '%s' @ %s:%s:%d" % (str(sys.exc_info()[0].__name__), str(sys.exc_info()[1]), os.path.basename(locationInfo[0]), locationInfo[2], locationInfo[1])


def get_free_bytes(path):
	"""
	Retrieves the number of free bytes on the partition ``path`` is located at and returns it. Works on both Windows and
	Unix/Linux.

	Taken from http://stackoverflow.com/a/2372171/2028598

	Arguments:
	    path (string): The path for which to check the remaining partition space.

	Returns:
	    int: The amount of bytes still left on the partition.
	"""

	path = os.path.abspath(path)
	if sys.platform == "win32":
		import ctypes
		freeBytes = ctypes.c_ulonglong(0)
		ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(path), None, None, ctypes.pointer(freeBytes))
		return freeBytes.value
	else:
		st = os.statvfs(path)
		return st.f_bavail * st.f_frsize


def get_dos_filename(origin, existing_filenames=None, extension=None, **kwargs):
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
	    kwargs (dict): Additional keyword arguments to provide to :func:`find_collision_free_name`.

	Returns:
	    string: A 8.3 compatible translation of the original filename, not colliding with the optionally provided
	        ``existing_filenames`` and with the provided ``extension`` or the original extension shortened to
	        a maximum of 3 characters.

	Raises:
	    ValueError: No 8.3 compatible name could be found that doesn't collide with the provided ``existing_filenames``.
	"""

	if origin is None:
		return None

	if existing_filenames is None:
		existing_filenames = []

	filename, ext = os.path.splitext(origin)
	if extension is None:
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
	"""

	# TODO unit test!

	if not isinstance(filename, unicode):
		filename = unicode(filename)
	if not isinstance(extension, unicode):
		extension = unicode(extension)

	def make_valid(text):
		return re.sub(r"\s+", "_", text.translate({ord(i):None for i in ".\"/\\[]:;=,"})).lower()

	filename = make_valid(filename)
	extension = make_valid(extension)
	extension = extension[:3] if len(extension) > 3 else extension

	if len(filename) <= 8 and not filename + "." + extension in existing_filenames:
		# early exit
		return filename + "." + extension

	counter = 1
	power = 1
	while counter < (10 ** max_power):
		result = filename[:(6 - power + 1)] + "~" + str(counter) + "." + extension
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


def dict_merge(a, b):
	"""
	Recursively deep-merges two dictionaries.

	Taken from https://www.xormedia.com/recursively-merge-dictionaries-in-python/

	Arguments:
	    a (dict): The dictionary to merge ``b`` into
	    b (dict): The dictionary to merge into ``a``

	Returns:
	    dict: ``b`` deep-merged into ``a``
	"""

	from copy import deepcopy

	if not isinstance(b, dict):
		return b
	result = deepcopy(a)
	for k, v in b.iteritems():
		if k in result and isinstance(result[k], dict):
			result[k] = dict_merge(result[k], v)
		else:
			result[k] = deepcopy(v)
	return result


def dict_clean(a, b):
	"""
	Recursively deep-cleans ``b`` from ``a``, removing all keys and corresponding values from ``a`` that appear in
	``b``.

	Arguments:
	    a (dict): The dictionary to clean from ``b``.
	    b (dict): The dictionary to clean ``b`` from.

	Results:
	    dict: A new dict based on ``a`` with all keys (and corresponding values) found in ``b`` removed.
	"""

	from copy import deepcopy
	if not isinstance(b, dict):
		return a

	result = deepcopy(a)
	for k, v in a.iteritems():
		if not k in b:
			del result[k]
		elif isinstance(v, dict):
			result[k] = dict_clean(v, b[k])
		else:
			result[k] = deepcopy(v)
	return result


def dict_contains_keys(a, b):
	"""
	Recursively deep-checks if ``a`` contains all keys found in ``b``.

	Example::

	    >>> dict_contains_keys(dict(foo="bar", fnord=dict(a=1, b=2, c=3)), dict(foo="some_other_bar", fnord=dict(b=100)))
	    True
	    >>> dict_contains_keys(dict(foo="bar", fnord=dict(a=1, b=2, c=3)), dict(foo="some_other_bar", fnord=dict(b=100, d=20)))
	    False

	Arguments:
	    a (dict): The dictionary to check for the keys from ``b``.
	    b (dict): The dictionary whose keys to check ``a`` for.

	Returns:
	    boolean: True if all keys found in ``b`` are also present in ``a``, False otherwise.
	"""

	if not isinstance(a, dict) or not isinstance(b, dict):
		return False

	for k, v in a.iteritems():
		if not k in b:
			return False
		elif isinstance(v, dict):
			if not dict_contains_keys(v, b[k]):
				return False

	return True

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

def address_for_client(host, port):
	"""
	Determines the address of the network interface on this host needed to connect to the indicated client host and port.
	"""

	import socket

	for address in interface_addresses():
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			sock.bind((address, 0))
			sock.connect((host, port))
			return address
		except:
			continue

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
	    daemon (bool): daemon flag to set on underlying thread.
	"""

	def __init__(self, interval, function, args=None, kwargs=None, run_first=False, condition=None, daemon=True):
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
		self.daemon = daemon

	def cancel(self):
		self.finished.set()

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
				break

			if not self.run_first:
				# if we are to run the function AFTER waiting for the first time
				self.function(*self.args, **self.kwargs)

		# make sure we set our finished event so we can detect that the loop was finished
		self.finished.set()


class CountedEvent(object):

	def __init__(self, value=0, max=None, name=None):
		logger_name = __name__ + ".CountedEvent" + (".{name}".format(name=name) if name is not None else "")
		self._logger = logging.getLogger(logger_name)

		self._counter = 0
		self._max = max
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
		self._logger.debug("New counter value: {value}".format(value=value))
		self._counter = value
		if self._counter <= 0:
			self._counter = 0
			self._event.clear()
			self._logger.debug("Cleared event")
		else:
			if self._max is not None and self._counter > self._max:
				self._counter = self._max
			self._event.set()
			self._logger.debug("Set event")


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
