# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import os
import octoprint.plugin
import octoprint.events
from octoprint.settings import settings


class SlicingProfile(object):
	def __init__(self, slicer, name, data, display_name=None, description=None):
		self.slicer = slicer
		self.name = name
		self.data = data
		self.display_name = display_name
		self.description = description


class TemporaryProfile(object):
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
		except:
			pass


class SlicingCancelled(BaseException):
	pass


class SlicingManager(object):
	def __init__(self, profile_path):
		self._profile_path = profile_path

		self._slicers = dict()
		self._slicer_names = dict()
		self._load_slicers()

		self._progress_callbacks = []
		self._last_progress_report = None

	def register_progress_callback(self, callback):
		self._progress_callbacks.append(callback)

	def unregister_progress_callback(self, callback):
		self._progress_callbacks.remove(callback)

	def _load_slicers(self):
		plugins = octoprint.plugin.plugin_manager().get_implementations(octoprint.plugin.SlicerPlugin)
		for name, plugin in plugins.items():
			if plugin.is_slicer_configured():
				self._slicers[plugin.get_slicer_properties()["type"]] = plugin

	@property
	def slicing_enabled(self):
		return len(self.configured_slicers) > 0

	@property
	def registered_slicers(self):
		return self._slicers.keys()

	@property
	def configured_slicers(self):
		return map(lambda slicer: slicer.get_slicer_properties()["type"], filter(lambda slicer: slicer.is_slicer_configured(), self._slicers.values()))

	@property
	def default_slicer(self):
		slicer_name = settings().get(["slicing", "defaultSlicer"])
		if slicer_name in self.configured_slicers:
			return slicer_name
		else:
			return None

	def get_slicer(self, slicer, require_configured=True):
		return self._slicers[slicer] if slicer in self._slicers and (not require_configured or self._slicers[slicer].is_slicer_configured()) else None

	def slice(self, slicer_name, source_path, dest_path, profile_name, callback, callback_args=None, callback_kwargs=None, overrides=None, on_progress=None, on_progress_args=None, on_progress_kwargs=None):
		if callback_args is None:
			callback_args = ()
		if callback_kwargs is None:
			callback_kwargs = dict()

		if not slicer_name in self.configured_slicers:
			if not slicer_name in self.registered_slicers:
				error = "No such slicer: {slicer_name}".format(**locals())
			else:
				error = "Slicer not configured: {slicer_name}".format(**locals())
			callback_kwargs.update(dict(_error=error))
			callback(*callback_args, **callback_kwargs)
			return False, error

		slicer = self.get_slicer(slicer_name)

		def slicer_worker(slicer, model_path, machinecode_path, profile_name, overrides, callback, callback_args, callback_kwargs):
			try:
				slicer_name = slicer.get_slicer_properties()["type"]
				with self.temporary_profile(slicer_name, name=profile_name, overrides=overrides) as profile_path:
					ok, result = slicer.do_slice(
						model_path,
						machinecode_path=machinecode_path,
						profile_path=profile_path,
						on_progress=on_progress,
						on_progress_args=on_progress_args,
						on_progress_kwargs=on_progress_kwargs
					)

				if not ok:
					callback_kwargs.update(dict(_error=result))
			except SlicingCancelled:
				callback_kwargs.update(dict(_cancelled=True))
			finally:
				callback(*callback_args, **callback_kwargs)

		import threading
		slicer_worker_thread = threading.Thread(target=slicer_worker,
		                                        args=(slicer, source_path, dest_path, profile_name, overrides, callback, callback_args, callback_kwargs))
		slicer_worker_thread.daemon = True
		slicer_worker_thread.start()
		return True, None

	def cancel_slicing(self, slicer_name, source_path, dest_path):
		if not slicer_name in self.registered_slicers:
			return
		slicer = self.get_slicer(slicer_name)
		slicer.cancel_slicing(dest_path)

	def load_profile(self, slicer, name):
		if not slicer in self.registered_slicers:
			return None

		try:
			path = self.get_profile_path(slicer, name, must_exist=True)
		except IOError:
			return None
		return self._load_profile_from_path(slicer, path)

	def save_profile(self, slicer, name, profile, overrides=None, allow_overwrite=True, display_name=None, description=None):
		if not slicer in self.registered_slicers:
			return

		if not isinstance(profile, SlicingProfile):
			if isinstance(profile, dict):
				profile = SlicingProfile(slicer, name, profile, display_name=display_name, description=description)
			else:
				raise ValueError("profile must be a SlicingProfile")
		else:
			profile.slicer = slicer
			profile.name = name
			if display_name is not None:
				profile.display_name = display_name
			if description is not None:
				profile.description = description

		path = self.get_profile_path(slicer, name)
		self._save_profile_to_path(slicer, path, profile, overrides=overrides, allow_overwrite=allow_overwrite)
		return profile

	def temporary_profile(self, slicer, name=None, overrides=None):
		if not slicer in self.registered_slicers:
			return None

		profile = self._get_default_profile(slicer)
		if name:
			try:
				profile = self.load_profile(slicer, name)
			except IOError:
				profile = self._get_default_profile(slicer)
			else:
				if profile is None:
					profile = self._get_default_profile(slicer)

		return TemporaryProfile(self.get_slicer(slicer).save_slicer_profile, profile, overrides=overrides)

	def delete_profile(self, slicer, name):
		if not slicer in self.registered_slicers:
			return None

		path = self.get_profile_path(slicer, name)
		if not os.path.exists(path) or not os.path.isfile(path):
			return
		os.remove(path)

	def all_profiles(self, slicer):
		if not slicer in self.registered_slicers:
			return None

		profiles = dict()
		slicer_profile_path = self.get_slicer_profile_path(slicer)
		for entry in os.listdir(slicer_profile_path):
			if not entry.endswith(".profile") or entry.startswith("."):
				# we are only interested in profiles and no hidden files
				continue

			path = os.path.join(slicer_profile_path, entry)
			profile_name = entry[:-len(".profile")]

			profiles[profile_name] = self._load_profile_from_path(slicer, path)
		return profiles

	def get_slicer_profile_path(self, slicer):
		if not slicer in self.registered_slicers:
			return None

		path = os.path.join(self._profile_path, slicer)
		if not os.path.exists(path):
			os.makedirs(path)
		return path

	def get_profile_path(self, slicer, name, must_exist=False):
		if not slicer in self.registered_slicers:
			return None

		if not name:
			return None

		name = self._sanitize(name)

		path = os.path.join(self.get_slicer_profile_path(slicer), "{name}.profile".format(name=name))
		if not os.path.realpath(path).startswith(self._profile_path):
			raise IOError("Path to profile {name} tried to break out of allows sub path".format(**locals()))
		if must_exist and not (os.path.exists(path) and os.path.isfile(path)):
			raise IOError("Profile {name} doesn't exist".format(**locals()))
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

	def _load_profile_from_path(self, slicer, path):
		return self.get_slicer(slicer).get_slicer_profile(path)

	def _save_profile_to_path(self, slicer, path, profile, allow_overwrite=True, overrides=None):
		self.get_slicer(slicer).save_slicer_profile(path, profile, allow_overwrite=allow_overwrite, overrides=overrides)

	def _get_default_profile(self, slicer):
		default_profiles = settings().get(["slicing", "defaultProfiles"])
		if default_profiles and slicer in default_profiles:
			try:
				return self.load_profile(slicer, default_profiles[slicer])
			except:
				pass

		return self.get_slicer(slicer).get_slicer_default_profile()


