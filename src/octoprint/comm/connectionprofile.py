# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2019 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging
import os
import io

try:
	from os import scandir
except ImportError:
	from scandir import scandir

from octoprint.settings import settings
from octoprint.util import is_hidden_path


class ConnectionProfile(object):

	def __init__(self, id, name=None, printer_profile=None, protocol=None, protocol_parameters=None, transport=None, transport_parameters=None, **kwargs):
		self.id = id
		self.name = name if name is not None else id
		self.printer_profile = printer_profile
		self.protocol = protocol
		self.protocol_parameters = protocol_parameters
		self.transport = transport
		self.transport_parameters = transport_parameters

	@classmethod
	def from_dict(cls, data):
		identifier = data.pop("id")
		return ConnectionProfile(identifier, **data)

	def as_dict(self):
		return dict(id=self.id,
		            name=self.name,
		            printer_profile=self.printer_profile,
		            protocol=self.protocol,
		            protocol_parameters=self.protocol_parameters,
		            transport=self.transport,
		            transport_parameters=self.transport_parameters)


class ConnectionProfileManager(object):

	@classmethod
	def to_profile(cls, data):
		return ConnectionProfile.from_dict(data)

	def __init__(self):
		self._current = None
		self._folder = settings().getBaseFolder("connectionProfiles")
		self._logger = logging.getLogger(__name__)

	def select(self, identifier):
		self._current = self.get(identifier)
		if self._current is None:
			self._logger.error("Profile {} is invalid, cannot select".format(identifier))
			return False
		return True

	def deselect(self):
		self._current = None

	@property
	def current(self):
		return self._current

	def get_all(self):
		return self._load_all()

	def get(self, identifier):
		try:
			if self.exists(identifier):
				return self._load_from_path(self._get_profile_path(identifier))
			else:
				return None
		except InvalidProfileError:
			return None

	def remove(self, identifier):
		return self._remove_from_path(self._get_profile_path(identifier))

	def save(self, profile, allow_overwrite=False, make_default=False):
		self._save_to_path(self._get_profile_path(profile.id),
		                   profile,
		                   allow_overwrite=allow_overwrite)

		if make_default:
			self.set_default(profile.id)

		return self.get(profile.id)

	@property
	def profile_count(self):
		return len(self._load_all_identifiers())

	@property
	def last_modified(self):
		dates = [os.stat(self._folder).st_mtime]
		dates += [entry.stat().st_mtime for entry in scandir(self._folder) if entry.name.endswith(".profile")]
		return max(dates)

	def get_default(self):
		default = settings().get(["connectionProfiles", "default"])
		if default is not None and self.exists(default):
			profile = self.get(default)
			if profile is not None:
				return profile
			else:
				self._logger.warning("Default profile {} is invalid".format(default))

		return None

	def set_default(self, identifier):
		all_identifiers = self._load_all_identifiers()
		if identifier is not None and identifier not in all_identifiers:
			return

		settings().set(["connectionProfiles", "default"], identifier)
		settings().save()

	def get_current_or_default(self):
		if self._current is not None:
			return self._current
		else:
			return self.get_default()

	def get_current(self):
		return self._current

	def exists(self, identifier):
		if identifier is None:
			return False

		path = self._get_profile_path(identifier)
		return os.path.exists(path) and os.path.isfile(path)

	def _load_all(self):
		all_identifiers = self._load_all_identifiers()
		results = dict()
		for identifier, path in all_identifiers.items():
			try:
				profile = self._load_from_path(path)
			except InvalidProfileError:
				self._logger.warning("Profile {} is invalid, skipping".format(identifier))
				continue

			if profile is None:
				continue

			results[identifier] = profile
		return results

	def _load_all_identifiers(self):
		results = dict()
		for entry in scandir(self._folder):
			if is_hidden_path(entry.name) or not entry.name.endswith(".profile"):
				continue

			if not entry.is_file():
				continue

			identifier = entry.name[:-len(".profile")]
			results[identifier] = entry.path
		return results

	def _load_from_path(self, path):
		if not os.path.exists(path) or not os.path.isfile(path):
			return None

		import yaml
		with io.open(path, 'rt', encoding='utf-8') as f:
			data = yaml.safe_load(f)

		if data is None or not isinstance(data, dict):
			raise InvalidProfileError("Profile is None or not a dict")

		return ConnectionProfile.from_dict(data)

	def _save_to_path(self, path, profile, allow_overwrite=False):
		if os.path.exists(path) and not allow_overwrite:
			raise SaveError("Profile {} already exists and overwriting is not allowed".format(profile["id"]))

		from octoprint.util import atomic_write
		import yaml
		try:
			with atomic_write(path, mode="wt", max_permissions=0o666) as f:
				yaml.safe_dump(profile.as_dict(), f,
				               default_flow_style=False,
				               indent=2,
				               allow_unicode=True)
		except Exception as e:
			self._logger.exception("Error while trying to save profile {}".format(profile["id"]))
			raise SaveError("Cannot save profile {}: {}".format(profile["id"], e))

	def _remove_from_path(self, path):
		try:
			os.remove(path)
			return True
		except Exception:
			return False

	def _get_profile_path(self, identifier):
		return os.path.join(self._folder, "{}.profile".format(identifier))


class InvalidProfileError(Exception):
	pass

class SaveError(Exception):
	pass
