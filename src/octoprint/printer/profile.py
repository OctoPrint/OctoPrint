# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import os
import copy
import re
import logging

try:
	from os import scandir
except ImportError:
	from scandir import scandir

from octoprint.settings import settings
from octoprint.util import dict_merge, dict_sanitize, dict_contains_keys, is_hidden_path

class SaveError(Exception):
	pass

class CouldNotOverwriteError(SaveError):
	pass

class InvalidProfileError(Exception):
	pass

class BedTypes(object):
	RECTANGULAR = "rectangular"
	CIRCULAR = "circular"

	@classmethod
	def values(cls):
		return [getattr(cls, name) for name in cls.__dict__ if not (name.startswith("__") or name == "values")]

class BedOrigin(object):
	LOWERLEFT = "lowerleft"
	CENTER = "center"

	@classmethod
	def values(cls):
		return [getattr(cls, name) for name in cls.__dict__ if not (name.startswith("__") or name == "values")]

class PrinterProfileManager(object):
	"""
	Manager for printer profiles. Offers methods to select the globally used printer profile and to list, add, remove,
	load and save printer profiles.

	A printer profile is a ``dict`` of the following structure:

	.. list-table::
	   :widths: 15 5 10 30
	   :header-rows: 1

	   * - Name
	     - Type
	     - Description
	   * - ``id``
	     - ``string``
	     - Internal id of the printer profile
	   * - ``name``
	     - ``string``
	     - Human readable name of the printer profile
	   * - ``model``
	     - ``string``
	     - Printer model
	   * - ``color``
	     - ``string``
	     - Color to associate with the printer profile
	   * - ``volume``
	     - ``dict``
	     - Information about the print volume
	   * - ``volume.width``
	     - ``float``
	     - Width of the print volume (X axis)
	   * - ``volume.depth``
	     - ``float``
	     - Depth of the print volume (Y axis)
	   * - ``volume.height``
	     - ``float``
	     - Height of the print volume (Z axis)
	   * - ``volume.formFactor``
	     - ``string``
	     - Form factor of the print bed, either ``rectangular`` or ``circular``
	   * - ``volume.origin``
	     - ``string``
	     - Location of gcode origin in the print volume, either ``lowerleft`` or ``center``
	   * - ``volume.custom_box``
	     - ``dict`` or ``False``
	     - Custom boundary box overriding the default bounding box based on the provided width, depth, height and origin.
	       If ``False``, the default boundary box will be used.
	   * - ``volume.custom_box.x_min``
	     - ``float``
	     - Minimum valid X coordinate
	   * - ``volume.custom_box.y_min``
	     - ``float``
	     - Minimum valid Y coordinate
	   * - ``volume.custom_box.z_min``
	     - ``float``
	     - Minimum valid Z coordinate
	   * - ``volume.custom_box.x_max``
	     - ``float``
	     - Maximum valid X coordinate
	   * - ``volume.custom_box.y_max``
	     - ``float``
	     - Maximum valid Y coordinate
	   * - ``volume.custom_box.z_max``
	     - ``float``
	     - Maximum valid Z coordinate
	   * - ``heatedBed``
	     - ``bool``
	     - Whether the printer has a heated bed (``True``) or not (``False``)
	   * - ``extruder``
	     - ``dict``
	     - Information about the printer's extruders
	   * - ``extruder.count``
	     - ``int``
	     - How many extruders the printer has (default 1)
	   * - ``extruder.offsets``
	     - ``list`` of ``tuple``s
	     - Extruder offsets relative to first extruder, list of (x, y) tuples, first is always (0,0)
	   * - ``extruder.nozzleDiameter``
	     - ``float``
	     - Diameter of the printer nozzle
	   * - ``axes``
	     - ``dict``
	     - Information about the printer axes
	   * - ``axes.x``
	     - ``dict``
	     - Information about the printer's X axis
	   * - ``axes.x.speed``
	     - ``float``
	     - Speed of the X axis in mm/s
	   * - ``axes.x.inverted``
	     - ``bool``
	     - Whether a positive value change moves the nozzle away from the print bed's origin (False, default) or towards it (True)
	   * - ``axes.y``
	     - ``dict``
	     - Information about the printer's Y axis
	   * - ``axes.y.speed``
	     - ``float``
	     - Speed of the Y axis in mm/s
	   * - ``axes.y.inverted``
	     - ``bool``
	     - Whether a positive value change moves the nozzle away from the print bed's origin (False, default) or towards it (True)
	   * - ``axes.z``
	     - ``dict``
	     - Information about the printer's Z axis
	   * - ``axes.z.speed``
	     - ``float``
	     - Speed of the Z axis in mm/s
	   * - ``axes.z.inverted``
	     - ``bool``
	     - Whether a positive value change moves the nozzle away from the print bed (False, default) or towards it (True)
	   * - ``axes.e``
	     - ``dict``
	     - Information about the printer's E axis
	   * - ``axes.e.speed``
	     - ``float``
	     - Speed of the E axis in mm/s
	   * - ``axes.e.inverted``
	     - ``bool``
	     - Whether a positive value change extrudes (False, default) or retracts (True) filament
	"""

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
			origin = BedOrigin.LOWERLEFT,
			custom_box = False
		),
		heatedBed = True,
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
		self._logger = logging.getLogger(__name__)

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
		try:
			if identifier == "_default":
				return self._load_default()
			elif self.exists(identifier):
				return self._load_from_path(self._get_profile_path(identifier))
			else:
				return None
		except InvalidProfileError:
			return None

	def remove(self, identifier):
		if identifier == "_default":
			return False
		if self._current is not None and self._current["id"] == identifier:
			return False
		return self._remove_from_path(self._get_profile_path(identifier))

	def save(self, profile, allow_overwrite=False, make_default=False):
		if "id" in profile:
			identifier = profile["id"]
		elif "name" in profile:
			identifier = profile["name"]
		else:
			raise InvalidProfileError("profile must contain either id or name")

		identifier = self._sanitize(identifier)
		profile["id"] = identifier
		profile = dict_sanitize(profile, self.__class__.default)

		if identifier == self.__class__.default["id"]:
			default_profile = dict_merge(self._load_default(), profile)
			if not self._ensure_valid_profile(default_profile):
				raise InvalidProfileError()

			settings().set(["printerProfiles", "defaultProfile"], default_profile, defaults=dict(printerProfiles=dict(defaultProfile=self.__class__.default)))
			settings().save()
		else:
			self._save_to_path(self._get_profile_path(identifier), profile, allow_overwrite=allow_overwrite)

			if make_default:
				settings().set(["printerProfiles", "default"], identifier)
				settings().save()

		if self._current is not None and self._current["id"] == identifier:
			self.select(identifier)
		return self.get(identifier)

	def is_default_unmodified(self):
		default = settings().get(["printerProfiles", "default"])
		default_overrides = settings().get(["printerProfiles", "defaultProfile"])
		return (default is None or default == self.__class__.default["id"]) and not default_overrides

	@property
	def profile_count(self):
		return len(self._load_all_identifiers())

	@property
	def last_modified(self):
		dates = [os.stat(self._folder).st_mtime]
		dates += [entry.stat().st_mtime for entry in scandir(self._folder) if entry.name.endswith(".profile")]
		return max(dates)

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
			try:
				if identifier == "_default":
					profile = self._load_default()
				else:
					profile = self._load_from_path(path)
			except InvalidProfileError:
				continue

			if profile is None:
				continue

			results[identifier] = dict_merge(self._load_default(), profile)
		return results

	def _load_all_identifiers(self):
		results = dict(_default=None)
		for entry in scandir(self._folder):
			if is_hidden_path(entry.name) or not entry.name.endswith(".profile") or entry.name == "_default.profile":
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
		with open(path) as f:
			profile = yaml.safe_load(f)

		if self._migrate_profile(profile):
			try:
				self._save_to_path(path, profile, allow_overwrite=True)
			except:
				self._logger.exception("Tried to save profile to {path} after migrating it while loading, ran into exception".format(path=path))

		profile = self._ensure_valid_profile(profile)

		if not profile:
			self._logger.warn("Invalid profile: %s" % path)
			raise InvalidProfileError()
		return profile

	def _save_to_path(self, path, profile, allow_overwrite=False):
		validated_profile = self._ensure_valid_profile(profile)
		if not validated_profile:
			raise InvalidProfileError()

		if os.path.exists(path) and not allow_overwrite:
			raise SaveError("Profile %s already exists and not allowed to overwrite" % profile["id"])

		from octoprint.util import atomic_write
		import yaml
		try:
			with atomic_write(path, "wb", max_permissions=0o666) as f:
				yaml.safe_dump(profile, f, default_flow_style=False, indent="  ", allow_unicode=True)
		except Exception as e:
			self._logger.exception("Error while trying to save profile %s" % profile["id"])
			raise SaveError("Cannot save profile %s: %s" % (profile["id"], str(e)))

	def _remove_from_path(self, path):
		try:
			os.remove(path)
			return True
		except:
			return False

	def _load_default(self):
		default_overrides = settings().get(["printerProfiles", "defaultProfile"])
		profile = self._ensure_valid_profile(dict_merge(copy.deepcopy(self.__class__.default), default_overrides))
		if not profile:
			self._logger.warn("Invalid default profile after applying overrides")
			return copy.deepcopy(self.__class__.default)
		return profile

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

	def _migrate_profile(self, profile):
		# make sure profile format is up to date
		modified = False

		if "volume" in profile and "formFactor" in profile["volume"] and not "origin" in profile["volume"]:
			profile["volume"]["origin"] = BedOrigin.CENTER if profile["volume"]["formFactor"] == BedTypes.CIRCULAR else BedOrigin.LOWERLEFT
			modified = True

		if "volume" in profile and not "custom_box" in profile["volume"]:
			profile["volume"]["custom_box"] = False
			modified = True

		return modified

	def _ensure_valid_profile(self, profile):
		# ensure all keys are present
		if not dict_contains_keys(self.default, profile):
			self._logger.warn("Profile invalid, missing keys. Expected: {expected!r}. Actual: {actual!r}".format(expected=self.default.keys(), actual=profile.keys()))
			return False

		# conversion helper
		def convert_value(profile, path, converter):
			value = profile
			for part in path[:-1]:
				if not isinstance(value, dict) or not part in value:
					raise RuntimeError("%s is not contained in profile" % ".".join(path))
				value = value[part]

			if not isinstance(value, dict) or not path[-1] in value:
				raise RuntimeError("%s is not contained in profile" % ".".join(path))

			value[path[-1]] = converter(value[path[-1]])

		# convert ints
		for path in (("extruder", "count"), ("axes", "x", "speed"), ("axes", "y", "speed"), ("axes", "z", "speed")):
			try:
				convert_value(profile, path, int)
			except Exception as e:
				self._logger.warn("Profile has invalid value for path {path!r}: {msg}".format(path=".".join(path), msg=str(e)))
				return False

		# convert floats
		for path in (("volume", "width"), ("volume", "depth"), ("volume", "height"), ("extruder", "nozzleDiameter")):
			try:
				convert_value(profile, path, float)
			except Exception as e:
				self._logger.warn("Profile has invalid value for path {path!r}: {msg}".format(path=".".join(path), msg=str(e)))
				return False

		# convert booleans
		for path in (("axes", "x", "inverted"), ("axes", "y", "inverted"), ("axes", "z", "inverted")):
			try:
				convert_value(profile, path, bool)
			except Exception as e:
				self._logger.warn("Profile has invalid value for path {path!r}: {msg}".format(path=".".join(path), msg=str(e)))
				return False

		# validate form factor
		if not profile["volume"]["formFactor"] in BedTypes.values():
			self._logger.warn("Profile has invalid value volume.formFactor: {formFactor}".format(formFactor=profile["volume"]["formFactor"]))
			return False

		# validate origin type
		if not profile["volume"]["origin"] in BedOrigin.values():
			self._logger.warn("Profile has invalid value in volume.origin: {origin}".format(origin=profile["volume"]["origin"]))
			return False

		# ensure origin and form factor combination is legal
		if profile["volume"]["formFactor"] == BedTypes.CIRCULAR and not profile["volume"]["origin"] == BedOrigin.CENTER:
			profile["volume"]["origin"] = BedOrigin.CENTER

		# force width and depth of volume to be identical for circular beds, with width being the reference
		if profile["volume"]["formFactor"] == BedTypes.CIRCULAR:
			profile["volume"]["depth"] = profile["volume"]["width"]

		# if we have a custom bounding box, validate it
		if profile["volume"]["custom_box"] and isinstance(profile["volume"]["custom_box"], dict):
			if not len(profile["volume"]["custom_box"]):
				profile["volume"]["custom_box"] = False

			else:
				default_box = self._default_box_for_volume(profile["volume"])
				for prop, limiter in (("x_min", min), ("y_min", min), ("z_min", min),
				                      ("x_max", max), ("y_max", max), ("z_max", max)):
					if prop not in profile["volume"]["custom_box"] or profile["volume"]["custom_box"][prop] is None:
						profile["volume"]["custom_box"][prop] = default_box[prop]
					else:
						value = profile["volume"]["custom_box"][prop]
						try:
							value = limiter(float(value), default_box[prop])
							profile["volume"]["custom_box"][prop] = value
						except:
							self._logger.warn("Profile has invalid value in volume.custom_box.{}: {!r}".format(prop, value))
							return False

				# make sure we actually do have a custom box and not just the same values as the
				# default box
				for prop in profile["volume"]["custom_box"]:
					if profile["volume"]["custom_box"][prop] != default_box[prop]:
						break
				else:
					# exactly the same as the default box, remove custom box
					profile["volume"]["custom_box"] = False

		# validate offsets
		offsets = []
		for offset in profile["extruder"]["offsets"]:
			if not len(offset) == 2:
				self._logger.warn("Profile has an invalid extruder.offsets entry: {entry!r}".format(entry=offset))
				return False
			x_offset, y_offset = offset
			try:
				offsets.append((float(x_offset), float(y_offset)))
			except:
				self._logger.warn("Profile has an extruder.offsets entry with non-float values: {entry!r}".format(entry=offset))
				return False
		profile["extruder"]["offsets"] = offsets

		return profile

	@staticmethod
	def _default_box_for_volume(volume):
		if volume["origin"] == BedOrigin.CENTER:
			half_width = volume["width"] / 2.0
			half_depth = volume["depth"] / 2.0
			return dict(x_min=-half_width,
			            x_max=half_width,
			            y_min=-half_depth,
			            y_max=half_depth,
			            z_min=0.0,
			            z_max=volume["height"])
		else:
			return dict(x_min=0.0,
			            x_max=volume["width"],
			            y_min=0.0,
			            y_max=volume["depth"],
			            z_min=0.0,
			            z_max=volume["height"])
