# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os
import tarfile
import zipfile

try:
	from os import scandir
except ImportError:
	from scandir import scandir

from collections import defaultdict

from flask import request, jsonify, make_response

from octoprint.settings import settings

from octoprint.server import admin_permission
from octoprint.server.api import api
from octoprint.server.util.flask import restricted_access

from octoprint.plugin import plugin_manager

from flask.ext.babel import Locale

@api.route("/languages", methods=["GET"])
@restricted_access
@admin_permission.require(403)
def getInstalledLanguagePacks():
	translation_folder = settings().getBaseFolder("translations")
	if not os.path.exists(translation_folder):
		return jsonify(language_packs=dict(_core=[]))

	core_packs = []
	plugin_packs = defaultdict(lambda: dict(identifier=None, display=None, languages=[]))
	for entry in scandir(translation_folder):
		if not entry.is_dir():
			continue

		def load_meta(path, locale):
			meta = dict()

			meta_path = os.path.join(path, "meta.yaml")
			if os.path.isfile(meta_path):
				import yaml
				try:
					with open(meta_path) as f:
						meta = yaml.safe_load(f)
				except:
					pass
				else:
					import datetime
					if "last_update" in meta and isinstance(meta["last_update"], datetime.datetime):
						meta["last_update"] = (meta["last_update"] - datetime.datetime(1970,1,1)).total_seconds()

			l = Locale.parse(locale)
			meta["locale"] = locale
			meta["locale_display"] = l.display_name
			meta["locale_english"] = l.english_name
			return meta

		if entry.name == "_plugins":
			for plugin_entry in scandir(entry.path):
				if not plugin_entry.is_dir():
					continue

				if not plugin_entry.name in plugin_manager().plugins:
					continue

				plugin_info = plugin_manager().plugins[plugin_entry.name]

				plugin_packs[plugin_entry.name]["identifier"] = plugin_entry.name
				plugin_packs[plugin_entry.name]["display"] = plugin_info.name

				for language_entry in scandir(plugin_entry.path):
					plugin_packs[plugin_entry.name]["languages"].append(load_meta(language_entry.path, language_entry.name))
		else:
			core_packs.append(load_meta(entry.path, entry.name))

	result = dict(_core=dict(identifier="_core", display="Core", languages=core_packs))
	result.update(plugin_packs)
	return jsonify(language_packs=result)

@api.route("/languages", methods=["POST"])
@restricted_access
@admin_permission.require(403)
def uploadLanguagePack():
	input_name = "file"
	input_upload_path = input_name + "." + settings().get(["server", "uploads", "pathSuffix"])
	input_upload_name = input_name + "." + settings().get(["server", "uploads", "nameSuffix"])
	if not input_upload_path in request.values or not input_upload_name in request.values:
		return make_response("No file included", 400)

	upload_name = request.values[input_upload_name]
	upload_path = request.values[input_upload_path]

	exts = filter(lambda x: upload_name.lower().endswith(x), (".zip", ".tar.gz", ".tgz", ".tar"))
	if not len(exts):
		return make_response("File doesn't have a valid extension for a language pack archive", 400)

	target_path = settings().getBaseFolder("translations")

	if tarfile.is_tarfile(upload_path):
		_unpack_uploaded_tarball(upload_path, target_path)
	elif zipfile.is_zipfile(upload_path):
		_unpack_uploaded_zipfile(upload_path, target_path)
	else:
		return make_response("Neither zip file nor tarball included", 400)

	return getInstalledLanguagePacks()

@api.route("/languages/<string:locale>/<string:pack>", methods=["DELETE"])
@restricted_access
@admin_permission.require(403)
def deleteInstalledLanguagePack(locale, pack):

	if pack == "_core":
		target_path = os.path.join(settings().getBaseFolder("translations"), locale)
	else:
		target_path = os.path.join(settings().getBaseFolder("translations"), "_plugins", pack, locale)

	if os.path.isdir(target_path):
		import shutil
		shutil.rmtree(target_path)

	return getInstalledLanguagePacks()

def _unpack_uploaded_zipfile(path, target):
	with zipfile.ZipFile(path, "r") as zip:
		# sanity check
		map(_validate_archive_name, zip.namelist())

		# unpack everything
		zip.extractall(target)

def _unpack_uploaded_tarball(path, target):
	with tarfile.open(path, "r") as tar:
		# sanity check
		map(_validate_archive_name, tar.getmembers())

		# unpack everything
		tar.extractall(target)

def _validate_archive_name(name):
	if name.startswith("/") or ".." in name:
		raise InvalidLanguagePack("Provided language pack contains invalid name {name}".format(**locals()))


class InvalidLanguagePack(Exception):
	pass
