# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import logging.handlers
import os
import flask
import math

import octoprint.plugin
import octoprint.util
import octoprint.slicing
import octoprint.settings

from octoprint.util.paths import normalize as normalize_path
from octoprint.util import to_unicode

from .profile import Profile
from .profile import GcodeFlavors
from .profile import parse_gcode_flavor

class CuraPlugin(octoprint.plugin.SlicerPlugin,
                 octoprint.plugin.SettingsPlugin,
                 octoprint.plugin.TemplatePlugin,
                 octoprint.plugin.AssetPlugin,
                 octoprint.plugin.BlueprintPlugin,
                 octoprint.plugin.StartupPlugin,
                 octoprint.plugin.WizardPlugin):

	# noinspection PyMissingConstructor
	def __init__(self):
		self._logger = logging.getLogger("octoprint.plugins.cura")
		self._cura_logger = logging.getLogger("octoprint.plugins.cura.engine")

		# setup job tracking across threads
		import threading
		self._slicing_commands = dict()
		self._cancelled_jobs = []
		self._job_mutex = threading.Lock()

	def _is_engine_configured(self, cura_engine=None):
		if cura_engine is None:
			cura_engine = normalize_path(self._settings.get(["cura_engine"]))
		return cura_engine is not None and os.path.isfile(cura_engine) and os.access(cura_engine, os.X_OK)

	def _is_profile_available(self):
		return bool(self._slicing_manager.all_profiles("cura", require_configured=False))

	##~~ TemplatePlugin API

	def get_template_vars(self):
		return dict(
			homepage=__plugin_url__
		)

	##~~ WizardPlugin API

	def is_wizard_required(self):
		return not self._is_engine_configured() or not self._is_profile_available()

	def get_wizard_details(self):
		return dict(
			engine=self._is_engine_configured(),
			profile=self._is_profile_available()
		)

	##~~ StartupPlugin API

	def on_startup(self, host, port):
		# setup our custom logger
		from octoprint.logging.handlers import CleaningTimedRotatingFileHandler
		cura_logging_handler = CleaningTimedRotatingFileHandler(self._settings.get_plugin_logfile_path(postfix="engine"), when="D", backupCount=3)
		cura_logging_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
		cura_logging_handler.setLevel(logging.DEBUG)

		self._cura_logger.addHandler(cura_logging_handler)
		self._cura_logger.setLevel(logging.DEBUG if self._settings.get_boolean(["debug_logging"]) else logging.CRITICAL)
		self._cura_logger.propagate = False

		engine = self._settings.get(["cura_engine"])
		if not self._is_engine_configured(cura_engine=engine):
			self._logger.info("Path to CuraEngine has not been configured or does not exist (currently set to %r), "
			                  "Cura will not be selectable for slicing" % engine)

	##~~ BlueprintPlugin API

	@octoprint.plugin.BlueprintPlugin.route("/import", methods=["POST"])
	def import_cura_profile(self):
		import datetime

		input_name = "file"
		input_upload_name = input_name + "." + self._settings.global_get(["server", "uploads", "nameSuffix"])
		input_upload_path = input_name + "." + self._settings.global_get(["server", "uploads", "pathSuffix"])

		if input_upload_name in flask.request.values and input_upload_path in flask.request.values:
			filename = flask.request.values[input_upload_name]
			try:
				profile_dict = Profile.from_cura_ini(flask.request.values[input_upload_path])
			except Exception as e:
				self._logger.exception("Error while converting the imported profile")
				return flask.make_response("Something went wrong while converting imported profile: {message}".format(message=str(e)), 500)

		else:
			self._logger.warn("No profile file included for importing, aborting")
			return flask.make_response("No file included", 400)

		if profile_dict is None:
			self._logger.warn("Could not convert profile, aborting")
			return flask.make_response("Could not convert Cura profile", 400)

		name, _ = os.path.splitext(filename)

		# default values for name, display name and description
		profile_name = _sanitize_name(name)
		profile_display_name = name
		profile_description = "Imported from {filename} on {date}".format(filename=filename, date=octoprint.util.get_formatted_datetime(datetime.datetime.now()))
		profile_allow_overwrite = False
		profile_make_default = False

		# overrides
		from octoprint.server.api import valid_boolean_trues
		if "name" in flask.request.values:
			profile_name = flask.request.values["name"]
		if "displayName" in flask.request.values:
			profile_display_name = flask.request.values["displayName"]
		if "description" in flask.request.values:
			profile_description = flask.request.values["description"]
		if "allowOverwrite" in flask.request.values:
			profile_allow_overwrite = flask.request.values["allowOverwrite"] in valid_boolean_trues
		if "default" in flask.request.values:
			profile_make_default = flask.request.values["default"] in valid_boolean_trues

		try:
			self._slicing_manager.save_profile("cura",
			                                   profile_name,
			                                   profile_dict,
			                                   allow_overwrite=profile_allow_overwrite,
			                                   display_name=profile_display_name,
			                                   description=profile_description)
		except octoprint.slicing.ProfileAlreadyExists:
			self._logger.warn("Profile {profile_name} already exists, aborting".format(**locals()))
			return flask.make_response("A profile named {profile_name} already exists for slicer cura".format(**locals()), 409)

		if profile_make_default:
			try:
				self._slicing_manager.set_default_profile("cura", profile_name)
			except octoprint.slicing.UnknownProfile:
				self._logger.warn("Profile {profile_name} could not be set as default, aborting".format(**locals()))
				return flask.make_response("The profile {profile_name} for slicer cura could not be set as default".format(**locals()), 500)

		result = dict(
			resource=flask.url_for("api.slicingGetSlicerProfile", slicer="cura", name=profile_name, _external=True),
			name=profile_name,
			displayName=profile_display_name,
			description=profile_description
		)
		r = flask.make_response(flask.jsonify(result), 201)
		r.headers["Location"] = result["resource"]
		return r

	##~~ AssetPlugin API

	def get_assets(self):
		return {
			"js": ["js/cura.js"],
			"less": ["less/cura.less"],
			"css": ["css/cura.css"]
		}

	##~~ SettingsPlugin API

	def on_settings_save(self, data):
		old_engine = self._settings.get(["cura_engine"])
		old_debug_logging = self._settings.get_boolean(["debug_logging"])

		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

		new_engine = self._settings.get(["cura_engine"])
		new_debug_logging = self._settings.get_boolean(["debug_logging"])

		if old_engine != new_engine and not self._is_engine_configured(new_engine):
			self._logger.info("Path to CuraEngine has not been configured or does not exist (currently set to %r), "
			                  "Cura will not be selectable for slicing" % new_engine)

		if old_debug_logging != new_debug_logging:
			if new_debug_logging:
				self._cura_logger.setLevel(logging.DEBUG)
			else:
				self._cura_logger.setLevel(logging.CRITICAL)

	def get_settings_defaults(self):
		return dict(
			cura_engine=None,
			default_profile=None,
			debug_logging=False
		)

	##~~ SlicerPlugin API

	def is_slicer_configured(self):
		cura_engine = normalize_path(self._settings.get(["cura_engine"]))
		return self._is_engine_configured(cura_engine=cura_engine)

	def get_slicer_properties(self):
		return dict(
			type="cura",
			name="CuraEngine",
			same_device=True,
			progress_report=True,
			source_file_types=["stl"],
			destination_extensions=["gco", "gcode", "g"]
		)

	def get_slicer_default_profile(self):
		path = self._settings.get(["default_profile"])
		if not path:
			path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "profiles", "default.profile.yaml")
		return self.get_slicer_profile(path)

	def get_slicer_profile(self, path):
		profile_dict = self._load_profile(path)

		display_name = None
		description = None
		if "_display_name" in profile_dict:
			display_name = profile_dict["_display_name"]
			del profile_dict["_display_name"]
		if "_description" in profile_dict:
			description = profile_dict["_description"]
			del profile_dict["_description"]

		properties = self.get_slicer_properties()
		return octoprint.slicing.SlicingProfile(properties["type"], "unknown", profile_dict, display_name=display_name, description=description)

	def save_slicer_profile(self, path, profile, allow_overwrite=True, overrides=None):
		new_profile = Profile.merge_profile(profile.data, overrides=overrides)

		if profile.display_name is not None:
			new_profile["_display_name"] = profile.display_name
		if profile.description is not None:
			new_profile["_description"] = profile.description

		self._save_profile(path, new_profile, allow_overwrite=allow_overwrite)

	def do_slice(self, model_path, printer_profile, machinecode_path=None, profile_path=None, position=None,
	             on_progress=None, on_progress_args=None, on_progress_kwargs=None):
		try:
			with self._job_mutex:
				if not profile_path:
					profile_path = self._settings.get(["default_profile"])
				if not machinecode_path:
					path, _ = os.path.splitext(model_path)
					machinecode_path = path + ".gco"

				if position and isinstance(position, dict) and "x" in position and "y" in position:
					pos_x = position["x"]
					pos_y = position["y"]
				else:
					pos_x = None
					pos_y = None

				if on_progress:
					if not on_progress_args:
						on_progress_args = ()
					if not on_progress_kwargs:
						on_progress_kwargs = dict()

				self._cura_logger.info(u"### Slicing {} to {} using profile stored at {}"
				                       .format(to_unicode(model_path, errors="replace"),
				                               to_unicode(machinecode_path, errors="replace"),
				                               to_unicode(profile_path, errors="replace")))

				executable = normalize_path(self._settings.get(["cura_engine"]))
				if not executable:
					return False, "Path to CuraEngine is not configured "

				working_dir = os.path.dirname(executable)

				slicing_profile = Profile(self._load_profile(profile_path), printer_profile, pos_x, pos_y)

				# NOTE: We can assume an extruder count of 1 here since the only way we currently
				# support dual extrusion in this implementation is by using the second extruder for support (which
				# the engine conversion will automatically detect and adapt accordingly).
				#
				# We currently do only support STL files as sliceables, which by default can only contain one mesh,
				# so no risk of having to slice multi-objects at the moment, which would necessitate a full analysis
				# of the objects to slice to determine amount of needed extruders to use here. If we ever decide to
				# also support dual extrusion slicing (including composition from multiple STLs or support for OBJ or
				# AMF files and the like), this code needs to be adapted!
				#
				# The extruder count is needed to decide which start/end gcode will be used from the Cura profile.
				# Stock Cura implementation counts the number of objects in the scene for this (and also takes a look
				# at the support usage, like the engine conversion here does). We only ever have one object.
				engine_settings = self._convert_to_engine(profile_path, printer_profile,
				                                          pos_x=pos_x, pos_y=pos_y,
				                                          used_extruders=1)

				# Start building the argument list for the CuraEngine command execution
				args = [executable, '-v', '-p']

				# Add the settings (sorted alphabetically) to the command
				for k, v in sorted(engine_settings.items(), key=lambda s: s[0]):
					args += ["-s", "%s=%s" % (k, str(v))]
				args += ["-o", machinecode_path, model_path]

				self._logger.info(u"Running {!r} in {}".format(u" ".join(map(lambda x: to_unicode(x, errors="replace"),
				                                                             args)),
				                                               working_dir))

				import sarge
				p = sarge.run(args, cwd=working_dir, async=True, stdout=sarge.Capture(), stderr=sarge.Capture())
				p.wait_events()
				self._slicing_commands[machinecode_path] = p.commands[0]

			try:
				layer_count = None
				step_factor = dict(
					inset=0,
					skin=1,
					export=2
				)
				analysis = None
				while p.returncode is None:
					line = p.stderr.readline(timeout=0.5)
					if not line:
						p.commands[0].poll()
						continue

					line = to_unicode(line, errors="replace")
					self._cura_logger.debug(line.strip())

					if on_progress is not None:
						# The Cura slicing process has three individual steps, each consisting of <layer_count> substeps:
						#
						#   - inset
						#   - skin
						#   - export
						#
						# So each layer will be processed three times, once for each step, resulting in a total amount of
						# substeps of 3 * <layer_count>.
						#
						# The CuraEngine reports the calculated layer count and the continuous progress on stderr.
						# The layer count gets reported right at the beginning in a line of the format:
						#
						#   Layer count: <layer_count>
						#
						# The individual progress per each of the three steps gets reported on stderr in a line of
						# the format:
						#
						#   Progress:<step>:<current_layer>:<layer_count>
						#
						# Thus, for determining the overall progress the following formula applies:
						#
						#   progress = <step_factor> * <layer_count> + <current_layer> / <layer_count> * 3
						#
						# with <step_factor> being 0 for "inset", 1 for "skin" and 2 for "export".

						if line.startswith(u"Layer count:") and layer_count is None:
							try:
								layer_count = float(line[len(u"Layer count:"):].strip())
							except:
								pass

						elif line.startswith(u"Progress:"):
							split_line = line[len(u"Progress:"):].strip().split(":")
							if len(split_line) == 3:
								step, current_layer, _ = split_line
								try:
									current_layer = float(current_layer)
								except:
									pass
								else:
									if not step in step_factor:
										continue
									on_progress_kwargs["_progress"] = (step_factor[step] * layer_count + current_layer) / (layer_count * 3)
									on_progress(*on_progress_args, **on_progress_kwargs)

						elif line.startswith(u"Print time:"):
							try:
								print_time = int(line[len(u"Print time:"):].strip())
								if analysis is None:
									analysis = dict()
								analysis["estimatedPrintTime"] = print_time
							except:
								pass

						# Get the filament usage

						elif line.startswith(u"Filament:") or line.startswith(u"Filament2:"):
							if line.startswith(u"Filament:"):
								filament_str = line[len(u"Filament:"):].strip()
								tool_key = "tool0"
							else:
								filament_str = line[len(u"Filament2:"):].strip()
								tool_key = "tool1"

							try:
								filament = int(filament_str)

								if analysis is None:
									analysis = dict()
								if not "filament" in analysis:
									analysis["filament"] = dict()
								if not tool_key in analysis["filament"]:
									analysis["filament"][tool_key] = dict()

								if slicing_profile.get_float("filament_diameter") is not None:
									if slicing_profile.get("gcode_flavor") == GcodeFlavors.ULTIGCODE or slicing_profile.get("gcode_flavor") == GcodeFlavors.REPRAP_VOLUME:
										analysis["filament"][tool_key] = _get_usage_from_volume(filament, slicing_profile.get_float("filament_diameter"))
									else:
										analysis["filament"][tool_key] = _get_usage_from_length(filament, slicing_profile.get_float("filament_diameter"))

							except:
								pass
			finally:
				p.close()

			with self._job_mutex:
				if machinecode_path in self._cancelled_jobs:
					self._cura_logger.info(u"### Cancelled")
					raise octoprint.slicing.SlicingCancelled()

			self._cura_logger.info(u"### Finished, returncode %d" % p.returncode)
			if p.returncode == 0:
				return True, dict(analysis=analysis)
			else:
				self._logger.warn(u"Could not slice via Cura, got return code %r" % p.returncode)
				return False, "Got returncode %r" % p.returncode

		except octoprint.slicing.SlicingCancelled as e:
			raise e
		except:
			self._logger.exception(u"Could not slice via Cura, got an unknown error")
			return False, "Unknown error, please consult the log file"

		finally:
			with self._job_mutex:
				if machinecode_path in self._cancelled_jobs:
					self._cancelled_jobs.remove(machinecode_path)
				if machinecode_path in self._slicing_commands:
					del self._slicing_commands[machinecode_path]

			self._cura_logger.info("-" * 40)

	def cancel_slicing(self, machinecode_path):
		with self._job_mutex:
			if machinecode_path in self._slicing_commands:
				self._cancelled_jobs.append(machinecode_path)
				command = self._slicing_commands[machinecode_path]
				if command is not None:
					command.terminate()
				self._logger.info(u"Cancelled slicing of {}"
				                  .format(to_unicode(machinecode_path, errors="replace")))

	def _load_profile(self, path):
		import yaml
		profile_dict = dict()
		with open(path, "r") as f:
			try:
				profile_dict = yaml.safe_load(f)
			except:
				raise IOError("Couldn't read profile from {path}".format(path=path))

		if "gcode_flavor" in profile_dict and not isinstance(profile_dict["gcode_flavor"], (list, tuple)):
			profile_dict["gcode_flavor"] = parse_gcode_flavor(profile_dict["gcode_flavor"])
			self._save_profile(path, profile_dict)

		return profile_dict

	def _save_profile(self, path, profile, allow_overwrite=True):
		import yaml
		with octoprint.util.atomic_write(path, "wb", max_permissions=0o666) as f:
			yaml.safe_dump(profile, f, default_flow_style=False, indent="  ", allow_unicode=True)

	def _convert_to_engine(self, profile_path, printer_profile, pos_x=None, pos_y=None, used_extruders=1):
		profile = Profile(self._load_profile(profile_path), printer_profile, pos_x, pos_y)
		return profile.convert_to_engine(used_extruders=used_extruders)

def _sanitize_name(name):
	if name is None:
		return None

	if "/" in name or "\\" in name:
		raise ValueError("name must not contain / or \\")

	import string
	valid_chars = "-_.() {ascii}{digits}".format(ascii=string.ascii_letters, digits=string.digits)
	sanitized_name = ''.join(c for c in name if c in valid_chars)
	sanitized_name = sanitized_name.replace(" ", "_")
	return sanitized_name.lower()

def _get_usage_from_volume(filament_volume, filament_diameter):

	# filament_volume is expressed in mm^3
	# usage["volume"] is in cm^3 and usage["length"] is in mm

	usage = dict()
	usage["volume"] = filament_volume / 1000.0

	radius_in_mm = filament_diameter / 2.0
	usage["length"] = filament_volume / (math.pi * radius_in_mm * radius_in_mm)

	return usage

def _get_usage_from_length(filament_length, filament_diameter):

	# filament_length is expressed in mm
	# usage["volume"] is in cm^3 and usage["length"] is in mm

	usage = dict()
	usage["length"] = filament_length

	radius_in_cm = (filament_diameter / 10.0) / 2.0
	length_in_cm = filament_length / 10.0
	usage["volume"] = length_in_cm * math.pi * radius_in_cm * radius_in_cm

	return usage


__plugin_name__ = "CuraEngine (<= 15.04)"
__plugin_author__ = "Gina Häußge"
__plugin_url__ = "http://docs.octoprint.org/en/master/bundledplugins/cura.html"
__plugin_description__ = "Adds support for slicing via CuraEngine versions up to and including version 15.04 from within OctoPrint"
__plugin_license__ = "AGPLv3"
__plugin_implementation__ = CuraPlugin()



