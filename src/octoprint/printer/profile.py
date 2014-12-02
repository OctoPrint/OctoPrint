# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import os
import copy
import re

from octoprint.settings import settings
from octoprint.util import dict_merge, dict_clean

class SaveError(Exception):
	pass

class BedTypes(object):
	RECTANGULAR = "rectangular"
	CIRCULAR = "circular"

class PrinterProfileManager(object):

	default = dict(
		id = "_default",
		name = "Default",
		model = "Generic RepRap Printer",
		color = "default",
		volume=dict(
			width = 200,
			depth = 200,
			height = 200,
			formFactor = BedTypes.RECTANGULAR,
		),
		heatedBed = False,
		extruder=dict(
			count = 1,
			offsets = [
				(0, 0)
			],
			nozzleDiameter = 0.4
		),
		axes=dict(
			x = dict(speed=6000, inverted=False),
			y = dict(speed=6000, inverted=False),
			z = dict(speed=200, inverted=False),
			e = dict(speed=300, inverted=False)
		)
	)

	def __init__(self):
		self._current = None

		self._folder = settings().getBaseFolder("printerProfiles")

	def select(self, identifier):
		if identifier is None or not self.exists(identifier):
			self._current = self.get_default()
			return False
		else:
			self._current = self.get(identifier)
			return True

	def deselect(self):
		self._current = None

	def get_all(self):
		return self._load_all()

	def get(self, identifier):
		if identifier == "_default":
			return self._load_default()
		elif self.exists(identifier):
			return self._load_from_path(self._get_profile_path(identifier))
		else:
			return None

	def remove(self, identifier):
		if identifier == "_default":
			return False
		return self._remove_from_path(self._get_profile_path(identifier))

	def save(self, profile, allow_overwrite=False, make_default=False):
		if "id" in profile:
			identifier = profile["id"]
		elif "name" in profile:
			identifier = profile["name"]
		else:
			raise ValueError("profile must contain either id or name")

		identifier = self._sanitize(identifier)

		if identifier == "_default":
			default_profile = dict_merge(self._load_default(), profile)
			settings().set(["printerProfiles", "defaultProfile"], default_profile, defaults=dict(printerProfiles=dict(defaultProfile=self.__class__.default)))

		profile["id"] = identifier
		profile = dict_clean(profile, self.__class__.default)
		self._save_to_path(self._get_profile_path(identifier), profile, allow_overwrite=allow_overwrite)

		if make_default:
			settings().set(["printerProfiles", "default"], identifier)

		return self.get(identifier)

	def get_default(self):
		default = settings().get(["printerProfiles", "default"])
		if default is not None and self.exists(default):
			profile = self.get(default)
			if profile is not None:
				return profile

		return self._load_default()

	def set_default(self, identifier):
		all_identifiers = self._load_all_identifiers().keys()
		if identifier is not None and not identifier in all_identifiers:
			return

		settings().set(["printerProfile", "default"], identifier)
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
		elif identifier == "_default":
			return True
		else:
			path = self._get_profile_path(identifier)
			return os.path.exists(path) and os.path.isfile(path)

	def _load_all(self):
		all_identifiers = self._load_all_identifiers()
		results = dict()
		for identifier, path in all_identifiers.items():
			if identifier == "_default":
				profile = self._load_default()
			else:
				profile = self._load_from_path(path)

			if profile is None:
				continue

			results[identifier] = dict_merge(self._load_default(), profile)
		return results

	def _load_all_identifiers(self):
		results = dict(_default=None)
		for entry in os.listdir(self._folder):
			if entry.startswith(".") or not entry.endswith(".profile") or entry == "_default.profile":
				continue

			path = os.path.join(self._folder, entry)
			if not os.path.isfile(path):
				continue

			identifier = entry[:-len(".profile")]
			results[identifier] = path
		return results

	def _load_from_path(self, path):
		if not os.path.exists(path) or not os.path.isfile(path):
			return None

		import yaml
		with open(path) as f:
			profile = yaml.safe_load(f)
		return profile

	def _save_to_path(self, path, profile, allow_overwrite=False):
		if os.path.exists(path) and not allow_overwrite:
			raise SaveError("Profile %s already exists and not allowed to overwrite" % profile["id"])

		import yaml
		with open(path, "wb") as f:
			try:
				yaml.safe_dump(profile, f, default_flow_style=False, indent="  ", allow_unicode=True)
			except Exception as e:
				raise SaveError("Cannot save profile %s: %s" % (profile["id"], e.message))

	def _remove_from_path(self, path):
		try:
			os.remove(path)
			return True
		except:
			return False

	def _load_default(self):
		default_profile = settings().get(["printerProfiles", "defaultProfile"])
		return dict_merge(copy.deepcopy(self.__class__.default), default_profile)

	def _get_profile_path(self, identifier):
		return os.path.join(self._folder, "%s.profile" % identifier)

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

