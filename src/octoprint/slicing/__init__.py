# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

"""
In this module the slicing support of OctoPrint is encapsulated.

.. autoclass:: SlicingProfile
   :members:

.. autoclass:: TemporaryProfile
   :members:

.. autoclass:: SlicingManager
   :members:
"""

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import os

try:
	from os import scandir
except ImportError:
	from scandir import scandir

import octoprint.plugin
import octoprint.events
import octoprint.util
from octoprint.settings import settings

import logging

from .exceptions import UnknownSlicer, SlicerNotConfigured, SlicingCancelled, \
		ProfileAlreadyExists, ProfileException, CouldNotDeleteProfile, UnknownProfile


class SlicingProfile(object):
	"""
	A wrapper for slicing profiles, both meta data and actual profile data.

	Arguments:
	    slicer (str): Identifier of the slicer this profile belongs to.
	    name (str): Identifier of this slicing profile.
	    data (object): Profile data, actual structure depends on individual slicer implementation.
	    display_name (str): Displayable name for this slicing profile.
	    description (str): Description of this slicing profile.
	    default (bool): Whether this is the default slicing profile for the slicer.
	"""

	def __init__(self, slicer, name, data, display_name=None, description=None, default=False):
		self.slicer = slicer
		self.name = name
		self.data = data
		self.display_name = display_name
		self.description = description
		self.default = default


class TemporaryProfile(object):
	"""
	A wrapper for a temporary slicing profile to be used for a slicing job, based on a :class:`SlicingProfile` with
	optional ``overrides`` applied through the supplied ``save_profile`` method.

	Usage example:

	.. code-block:: python

	   temporary = TemporaryProfile(my_slicer.save_slicer_profile, my_default_profile,
	                                overrides=my_overrides)
	   with (temporary) as profile_path:
	       my_slicer.do_slice(..., profile_path=profile_path, ...)

	Arguments:
	    save_profile (callable): Method to use for saving the temporary profile, also responsible for applying the
	        supplied ``overrides``. This will be called according to the method signature of
	        :meth:`~octoprint.plugin.SlicerPlugin.save_slicer_profile`.
	    profile (SlicingProfile): The profile from which to derive the temporary profile.
	    overrides (dict): Optional overrides to apply to the ``profile`` for creation of the temporary profile.
	"""

	def __init__(self, save_profile, profile, overrides=None):
		self.save_profile = save_profile
		self.profile = profile
		self.overrides = overrides

	def __enter__(self):
		import tempfile
		temp_profile = tempfile.NamedTemporaryFile(prefix="slicing-profile-temp-", suffix=".profile", delete=False)
		temp_profile.close()

		self.temp_path = temp_profile.name
		self.save_profile(self.temp_path, self.profile, overrides=self.overrides)
		return self.temp_path

	def __exit__(self, type, value, traceback):
		import os
		try:
			os.remove(self.temp_path)
		except Exception:
			pass


class SlicingManager(object):
	"""
	The :class:`SlicingManager` is responsible for managing available slicers and slicing profiles.

	Arguments:
	    profile_path (str): Absolute path to the base folder where all slicing profiles are stored.
	    printer_profile_manager (~octoprint.printer.profile.PrinterProfileManager): :class:`~octoprint.printer.profile.PrinterProfileManager`
	       instance to use for accessing available printer profiles, most importantly the currently selected one.
	"""

	def __init__(self, profile_path, printer_profile_manager):
		self._logger = logging.getLogger(__name__)

		self._profile_path = profile_path
		self._printer_profile_manager = printer_profile_manager

		self._slicers = dict()
		self._slicer_names = dict()

	def initialize(self):
		"""
		Initializes the slicing manager by loading and initializing all available
		:class:`~octoprint.plugin.SlicerPlugin` implementations.
		"""
		self.reload_slicers()

	def reload_slicers(self):
		"""
		Retrieves all registered :class:`~octoprint.plugin.SlicerPlugin` implementations and registers them as
		available slicers.
		"""
		plugins = octoprint.plugin.plugin_manager().get_implementations(octoprint.plugin.SlicerPlugin)
		slicers = dict()
		for plugin in plugins:
			try:
				slicers[plugin.get_slicer_properties()["type"]] = plugin
			except Exception:
				self._logger.exception("Error while getting properties from slicer {}, ignoring it".format(plugin._identifier),
				                       extra=dict(plugin=plugin._identifier))
				continue
		self._slicers = slicers

	@property
	def slicing_enabled(self):
		"""
		Returns:
		    (boolean) True if there is at least one configured slicer available, False otherwise.
		"""
		return len(self.configured_slicers) > 0

	@property
	def registered_slicers(self):
		"""
		Returns:
		    (list of str) Identifiers of all available slicers.
		"""
		return list(self._slicers.keys())

	@property
	def configured_slicers(self):
		"""
		Returns:
		    (list of str) Identifiers of all available configured slicers.
		"""
		return list(map(lambda slicer: slicer.get_slicer_properties()["type"], filter(lambda slicer: slicer.is_slicer_configured(), self._slicers.values())))

	@property
	def default_slicer(self):
		"""
		Retrieves the default slicer.

		Returns:
		    (str) The identifier of the default slicer or ``None`` if the default slicer is not registered in the
		        system.
		"""
		slicer_name = settings().get(["slicing", "defaultSlicer"])
		if slicer_name in self.registered_slicers:
			return slicer_name
		else:
			return None

	def get_slicer(self, slicer, require_configured=True):
		"""
		Retrieves the slicer named ``slicer``. If ``require_configured`` is set to True (the default) an exception
		will be raised if the slicer is not yet configured.

		Arguments:
		    slicer (str): Identifier of the slicer to return
		    require_configured (boolean): Whether to raise an exception if the slicer has not been configured yet (True,
		        the default), or also return an unconfigured slicer (False).

		Raises:
		    ~octoprint.slicing.exceptions.UnknownSlicer: The ``slicer`` is unknown.
		    ~octoprint.slicing.exceptions.SlicerNotConfigured: The ``slicer`` is not yet configured and ``require_configured`` was set to True.
		"""

		if not slicer in self._slicers:
			raise UnknownSlicer(slicer)

		if require_configured and not self._slicers[slicer].is_slicer_configured():
			raise SlicerNotConfigured(slicer)

		return self._slicers[slicer]

	def slice(self, slicer_name, source_path, dest_path, profile_name, callback,
	          callback_args=None, callback_kwargs=None, overrides=None,
	          on_progress=None, on_progress_args=None, on_progress_kwargs=None, printer_profile_id=None, position=None):
		"""
		Slices ``source_path`` to ``dest_path`` using slicer ``slicer_name`` and slicing profile ``profile_name``.
		Since slicing happens asynchronously, ``callback`` will be called when slicing has finished (either successfully
		or not), with ``callback_args`` and ``callback_kwargs`` supplied.

		If ``callback_args`` is left out, an empty argument list will be assumed for the callback. If ``callback_kwargs``
		is left out, likewise an empty keyword argument list will be assumed for the callback. Note that in any case
		the callback *must* support being called with the following optional keyword arguments:

		_analysis
		    If the slicer returned analysis data of the created machine code as part of its slicing result, this keyword
		    argument will contain that data.
		_error
		    If there was an error while slicing this keyword argument will contain the error message as returned from
		    the slicer.
		_cancelled
		    If the slicing job was cancelled this keyword argument will be set to True.

		Additionally callees may specify ``overrides`` for the specified slicing profile, e.g. a different extrusion
		temperature than defined in the profile or a different layer height.

		With ``on_progress``, ``on_progress_args`` and ``on_progress_kwargs``, callees may specify a callback plus
		arguments and keyword arguments to call upon progress reports from the slicing job. The progress callback will
		be called with a keyword argument ``_progress`` containing the current slicing progress as a value between 0
		and 1 plus all additionally specified args and kwargs.

		If a different printer profile than the currently selected one is to be used for slicing, its id can be provided
		via the keyword argument ``printer_profile_id``.

		If the ``source_path`` is to be a sliced at a different position than the print bed center, this ``position`` can
		be supplied as a dictionary defining the ``x`` and ``y`` coordinate in print bed coordinates of the model's center.

		Arguments:
		    slicer_name (str): The identifier of the slicer to use for slicing.
		    source_path (str): The absolute path to the source file to slice.
		    dest_path (str): The absolute path to the destination file to slice to.
		    profile_name (str): The name of the slicing profile to use.
		    callback (callable): A callback to call after slicing has finished.
		    callback_args (list or tuple): Arguments of the callback to call after slicing has finished. Defaults to
		        an empty list.
		    callback_kwargs (dict): Keyword arguments for the callback to call after slicing has finished, will be
		        extended by ``_analysis``, ``_error`` or ``_cancelled`` as described above! Defaults to an empty
		        dictionary.
		    overrides (dict): Overrides for the printer profile to apply.
		    on_progress (callable): Callback to call upon slicing progress.
		    on_progress_args (list or tuple): Arguments of the progress callback. Defaults to an empty list.
		    on_progress_kwargs (dict): Keyword arguments of the progress callback, will be extended by ``_progress``
		        as described above! Defaults to an empty dictionary.
		    printer_profile_id (str): Identifier of the printer profile for which to slice, if another than the
		        one currently selected is to be used.
		    position (dict): Dictionary containing the ``x`` and ``y`` coordinate in the print bed's coordinate system
		        of the sliced model's center. If not provided the model will be positioned at the print bed's center.
		        Example: ``dict(x=10,y=20)``.

		Raises:
		    ~octoprint.slicing.exceptions.UnknownSlicer: The slicer specified via ``slicer_name`` is unknown.
		    ~octoprint.slicing.exceptions.SlicerNotConfigured: The slice specified via ``slicer_name`` is not configured yet.
		"""

		if callback_args is None:
			callback_args = ()
		if callback_kwargs is None:
			callback_kwargs = dict()

		if not slicer_name in self.configured_slicers:
			if not slicer_name in self.registered_slicers:
				error = "No such slicer: {slicer_name}".format(**locals())
				exc = UnknownSlicer(slicer_name)
			else:
				error = "Slicer not configured: {slicer_name}".format(**locals())
				exc = SlicerNotConfigured(slicer_name)
			callback_kwargs.update(dict(_error=error, _exc=exc))
			callback(*callback_args, **callback_kwargs)
			raise exc

		slicer = self.get_slicer(slicer_name)

		printer_profile = None
		if printer_profile_id is not None:
			printer_profile = self._printer_profile_manager.get(printer_profile_id)

		if printer_profile is None:
			printer_profile = self._printer_profile_manager.get_current_or_default()

		def slicer_worker(slicer, model_path, machinecode_path, profile_name, overrides, printer_profile, position, callback, callback_args, callback_kwargs):
			try:
				slicer_name = slicer.get_slicer_properties()["type"]
				with self._temporary_profile(slicer_name, name=profile_name, overrides=overrides) as profile_path:
					ok, result = slicer.do_slice(
						model_path,
						printer_profile,
						machinecode_path=machinecode_path,
						profile_path=profile_path,
						position=position,
						on_progress=on_progress,
						on_progress_args=on_progress_args,
						on_progress_kwargs=on_progress_kwargs
					)

				if not ok:
					callback_kwargs.update(dict(_error=result))
				elif result is not None and isinstance(result, dict) and "analysis" in result:
					callback_kwargs.update(dict(_analysis=result["analysis"]))
			except SlicingCancelled:
				callback_kwargs.update(dict(_cancelled=True))
			finally:
				callback(*callback_args, **callback_kwargs)

		import threading
		slicer_worker_thread = threading.Thread(target=slicer_worker,
		                                        args=(slicer, source_path, dest_path, profile_name, overrides, printer_profile, position, callback, callback_args, callback_kwargs))
		slicer_worker_thread.daemon = True
		slicer_worker_thread.start()

	def cancel_slicing(self, slicer_name, source_path, dest_path):
		"""
		Cancels the slicing job on slicer ``slicer_name`` from ``source_path`` to ``dest_path``.

		Arguments:
		    slicer_name (str): Identifier of the slicer on which to cancel the job.
		    source_path (str): The absolute path to the source file being sliced.
		    dest_path (str): The absolute path to the destination file being sliced to.

		Raises:
		    ~octoprint.slicing.exceptions.UnknownSlicer: The slicer specified via ``slicer_name`` is unknown.
		"""

		slicer = self.get_slicer(slicer_name)
		slicer.cancel_slicing(dest_path)

	def load_profile(self, slicer, name, require_configured=True):
		"""
		Loads the slicing profile for ``slicer`` with the given profile ``name`` and returns it. If it can't be loaded
		due to an :class:`IOError` ``None`` will be returned instead.

		If ``require_configured`` is True (the default) a :class:`SlicerNotConfigured` exception will be raised
		if the indicated ``slicer`` has not yet been configured.

		Returns:
		    SlicingProfile: The requested slicing profile or None if it could not be loaded.

		Raises:
		    ~octoprint.slicing.exceptions.UnknownSlicer: The slicer specified via ``slicer`` is unknown.
		    ~octoprint.slicing.exceptions.SlicerNotConfigured: The slicer specified via ``slicer`` has not yet been configured and
		        ``require_configured`` was True.
		    ~octoprint.slicing.exceptions.UnknownProfile: The profile for slicer ``slicer`` named ``name`` does not exist.
		"""

		if not slicer in self.registered_slicers:
			raise UnknownSlicer(slicer)

		try:
			path = self.get_profile_path(slicer, name, must_exist=True)
		except IOError:
			return None
		return self._load_profile_from_path(slicer, path, require_configured=require_configured)

	def save_profile(self, slicer, name, profile, overrides=None, allow_overwrite=True, display_name=None, description=None):
		"""
		Saves the slicer profile ``profile`` for slicer ``slicer`` under name ``name``.

		``profile`` may be either a :class:`SlicingProfile` or a :class:`dict`.

		If it's a :class:`SlicingProfile`, its :attr:`~SlicingProfile.slicer``, :attr:`~SlicingProfile.name` and - if
		provided - :attr:`~SlicingProfile.display_name` and :attr:`~SlicingProfile.description` attributes will be
		overwritten with the supplied values.

		If it's a :class:`dict`, a new :class:`SlicingProfile` instance will be created with the supplied meta data and
		the profile data as the :attr:`~SlicingProfile.data` attribute.

		.. note::

		   If the profile is the first profile to be saved for the slicer, it will automatically be marked as default.

		Arguments:
		    slicer (str): Identifier of the slicer for which to save the ``profile``.
		    name (str): Identifier under which to save the ``profile``.
		    profile (SlicingProfile or dict): The :class:`SlicingProfile` or a :class:`dict` containing the profile
		        data of the profile the save.
		    overrides (dict): Overrides to apply to the ``profile`` before saving it.
		    allow_overwrite (boolean): If True (default) if a profile for the same ``slicer`` of the same ``name``
		        already exists, it will be overwritten. Otherwise an exception will be thrown.
		    display_name (str): The name to display to the user for the profile.
		    description (str): A description of the profile.

		Returns:
		    SlicingProfile: The saved profile (including the applied overrides).

		Raises:
		    ValueError: The supplied ``profile`` is neither a :class:`SlicingProfile` nor a :class:`dict`.
		    ~octoprint.slicing.exceptions.UnknownSlicer: The slicer ``slicer`` is unknown.
		    ~octoprint.slicing.exceptions.ProfileAlreadyExists: A profile with name ``name`` already exists for ``slicer`` and ``allow_overwrite`` is
		        False.
		"""
		if not slicer in self.registered_slicers:
			raise UnknownSlicer(slicer)

		if not isinstance(profile, SlicingProfile):
			if isinstance(profile, dict):
				profile = SlicingProfile(slicer, name, profile, display_name=display_name, description=description)
			else:
				raise ValueError("profile must be a SlicingProfile or a dict")
		else:
			profile.slicer = slicer
			profile.name = name
			if display_name is not None:
				profile.display_name = display_name
			if description is not None:
				profile.description = description

		first_profile = len(self.all_profiles(slicer, require_configured=False)) == 0

		path = self.get_profile_path(slicer, name)
		is_overwrite = os.path.exists(path)

		if is_overwrite and not allow_overwrite:
			raise ProfileAlreadyExists(slicer, profile.name)

		self._save_profile_to_path(slicer, path, profile, overrides=overrides, allow_overwrite=allow_overwrite)

		payload = dict(slicer=slicer,
		               profile=name)
		event = octoprint.events.Events.SLICING_PROFILE_MODIFIED if is_overwrite else octoprint.events.Events.SLICING_PROFILE_ADDED
		octoprint.events.eventManager().fire(event, payload)

		if first_profile:
			# enforce the first profile we add for this slicer  is set as default
			self.set_default_profile(slicer, name)

		return profile

	def _temporary_profile(self, slicer, name=None, overrides=None):
		if not slicer in self.registered_slicers:
			raise UnknownSlicer(slicer)

		profile = self._get_default_profile(slicer)
		if name:
			try:
				profile = self.load_profile(slicer, name)
			except (UnknownProfile, IOError):
				# in that case we'll use the default profile
				pass

		return TemporaryProfile(self.get_slicer(slicer).save_slicer_profile, profile, overrides=overrides)

	def delete_profile(self, slicer, name):
		"""
		Deletes the profile ``name`` for the specified ``slicer``.

		If the profile does not exist, nothing will happen.

		Arguments:
		    slicer (str): Identifier of the slicer for which to delete the profile.
		    name (str): Identifier of the profile to delete.

		Raises:
		    ~octoprint.slicing.exceptions.UnknownSlicer: The slicer ``slicer`` is unknown.
		    ~octoprint.slicing.exceptions.CouldNotDeleteProfile: There was an error while deleting the profile.
		"""

		if not slicer in self.registered_slicers:
			raise UnknownSlicer(slicer)

		if not name:
			raise ValueError("name must be set")

		try:
			try:
				path = self.get_profile_path(slicer, name, must_exist=True)
			except UnknownProfile:
				return
			os.remove(path)
		except ProfileException as e:
			raise e
		except Exception as e:
			raise CouldNotDeleteProfile(slicer, name, cause=e)
		else:
			octoprint.events.eventManager().fire(octoprint.events.Events.SLICING_PROFILE_DELETED, dict(slicer=slicer, profile=name))

	def set_default_profile(self, slicer, name, require_configured=False,
	                        require_exists=True):
		"""
		Sets the given profile as default profile for the slicer.

		Arguments:
		    slicer (str): Identifier of the slicer for which to set the default
		        profile.
		    name (str): Identifier of the profile to set as default.
		    require_configured (bool): Whether the slicer needs to be configured
		        for the action to succeed. Defaults to false. Will raise a
		        SlicerNotConfigured error if true and the slicer has not been
		        configured yet.
		    require_exists (bool): Whether the profile is required to exist in
		        order to be set as default. Defaults to true. Will raise a
		        UnknownProfile error if true and the profile is unknown.

		Raises:
		    ~octoprint.slicing.exceptions.UnknownSlicer: The slicer ``slicer``
		        is unknown
		    ~octoprint.slicing.exceptions.SlicerNotConfigured: The slicer ``slicer``
		        has not yet been configured and ``require_configured`` was true.
		    ~octoprint.slicing.exceptions.UnknownProfile: The profile ``name``
		        was unknown for slicer ``slicer`` and ``require_exists`` was
		        true.
		"""
		if not slicer in self.registered_slicers:
			raise UnknownSlicer(slicer)
		if require_configured and not slicer in self.configured_slicers:
			raise SlicerNotConfigured(slicer)

		if not name:
			raise ValueError("name must be set")

		if require_exists and not name in self.all_profiles(slicer, require_configured=require_configured):
			raise UnknownProfile(slicer, name)

		default_profiles = settings().get(["slicing", "defaultProfiles"])
		if not default_profiles:
			default_profiles = dict()
		default_profiles[slicer] = name
		settings().set(["slicing", "defaultProfiles"], default_profiles)
		settings().save(force=True)

	def all_profiles(self, slicer, require_configured=False):
		"""
		Retrieves all profiles for slicer ``slicer``.

		If ``require_configured`` is set to True (default is False), only will return the profiles if the ``slicer``
		is already configured, otherwise a :class:`SlicerNotConfigured` exception will be raised.

		Arguments:
		    slicer (str): Identifier of the slicer for which to retrieve all slicer profiles
		    require_configured (boolean): Whether to require the slicer ``slicer`` to be already configured (True)
		        or not (False, default). If False and the slicer is not yet configured, a :class:`~octoprint.slicing.exceptions.SlicerNotConfigured`
		        exception will be raised.

		Returns:
		    dict of SlicingProfile: A dict of all :class:`SlicingProfile` instances available for the slicer ``slicer``, mapped by the identifier.

		Raises:
		    ~octoprint.slicing.exceptions.UnknownSlicer: The slicer ``slicer`` is unknown.
		    ~octoprint.slicing.exceptions.SlicerNotConfigured: The slicer ``slicer`` is not configured and ``require_configured`` was True.
		"""

		if not slicer in self.registered_slicers:
			raise UnknownSlicer(slicer)
		if require_configured and not slicer in self.configured_slicers:
			raise SlicerNotConfigured(slicer)

		slicer_profile_path = self.get_slicer_profile_path(slicer)
		return self.get_slicer(slicer, require_configured=False).get_slicer_profiles(slicer_profile_path)

	def profiles_last_modified(self, slicer):
		"""
		Retrieves the last modification date of ``slicer``'s profiles.

		Args:
		    slicer (str): the slicer for which to retrieve the last modification date

		Returns:
		    (float) the time stamp of the last modification of the slicer's profiles
		"""

		if not slicer in self.registered_slicers:
			raise UnknownSlicer(slicer)

		slicer_profile_path = self.get_slicer_profile_path(slicer)
		return self.get_slicer(slicer, require_configured=False).get_slicer_profiles_lastmodified(slicer_profile_path)

	def get_slicer_profile_path(self, slicer):
		"""
		Retrieves the path where the profiles for slicer ``slicer`` are stored.

		Arguments:
		    slicer (str): Identifier of the slicer for which to retrieve the path.

		Returns:
		    str: The absolute path to the folder where the slicer's profiles are stored.

		Raises:
		    ~octoprint.slicing.exceptions.UnknownSlicer: The slicer ``slicer`` is unknown.
		"""

		if not slicer in self.registered_slicers:
			raise UnknownSlicer(slicer)

		path = os.path.join(self._profile_path, slicer)
		if not os.path.exists(path):
			os.makedirs(path)
		return path

	def get_profile_path(self, slicer, name, must_exist=False):
		"""
		Retrieves the path to the profile named ``name`` for slicer ``slicer``.

		If ``must_exist`` is set to True (defaults to False) a :class:`UnknownProfile` exception will be raised if the
		profile doesn't exist yet.

		Arguments:
		    slicer (str): Identifier of the slicer to which the profile belongs to.
		    name (str): Identifier of the profile for which to retrieve the path.
		    must_exist (boolean): Whether the path must exist (True) or not (False, default).

		Returns:
		    str: The absolute path to the profile identified by ``name`` for slicer ``slicer``.

		Raises:
		    ~octoprint.slicing.exceptions.UnknownSlicer: The slicer ``slicer`` is unknown.
		    ~octoprint.slicing.exceptions.UnknownProfile: The profile named ``name`` doesn't exist and ``must_exist`` was True.
		"""

		if not slicer in self.registered_slicers:
			raise UnknownSlicer(slicer)

		if not name:
			raise ValueError("name must be set")

		name = self._sanitize(name)

		path = os.path.join(self.get_slicer_profile_path(slicer), "{name}.profile".format(name=name))
		if not os.path.realpath(path).startswith(os.path.realpath(self._profile_path)):
			raise IOError("Path to profile {name} tried to break out of allows sub path".format(**locals()))
		if must_exist and not (os.path.exists(path) and os.path.isfile(path)):
			raise UnknownProfile(slicer, name)
		return path

	def _sanitize(self, name):
		if name is None:
			return None

		if "/" in name or "\\" in name:
			raise ValueError("name must not contain / or \\")

		import string
		valid_chars = "-_.() {ascii}{digits}".format(ascii=string.ascii_letters, digits=string.digits)
		sanitized_name = ''.join(c for c in name if c in valid_chars)
		sanitized_name = sanitized_name.replace(" ", "_")
		return sanitized_name

	def _load_profile_from_path(self, slicer, path, require_configured=False):
		profile = self.get_slicer(slicer, require_configured=require_configured).get_slicer_profile(path)
		default_profiles = settings().get(["slicing", "defaultProfiles"])
		if default_profiles and slicer in default_profiles:
			profile.default = default_profiles[slicer] == profile.name
		return profile

	def _save_profile_to_path(self, slicer, path, profile, allow_overwrite=True, overrides=None, require_configured=False):
		self.get_slicer(slicer, require_configured=require_configured).save_slicer_profile(path, profile, allow_overwrite=allow_overwrite, overrides=overrides)

	def _get_default_profile(self, slicer):
		default_profiles = settings().get(["slicing", "defaultProfiles"])
		if default_profiles and slicer in default_profiles:
			try:
				return self.load_profile(slicer, default_profiles[slicer])
			except (UnknownProfile, IOError):
				# in that case we'll use the slicers predefined default profile
				pass

		return self.get_slicer(slicer).get_slicer_default_profile()
