# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import copy

from flask import jsonify, make_response, request, url_for

from octoprint.server.api import api
from octoprint.server import printer, fileManager, slicingManager, eventManager, NO_CONTENT, current_user
from octoprint.server.util.flask import restricted_access, get_json_command_from_request, with_revalidation_checking
from octoprint.settings import settings, valid_boolean_trues

import psutil
import logging

def _create_lastmodified(path, recursive):
	if path.endswith("/files"):
		# all storages involved
		lms = [0]
		for storage in fileManager.registered_storages:
			try:
				lms.append(fileManager.last_modified(storage, recursive=recursive))
			except:
				logging.getLogger(__name__).exception("There was an error retrieving the last modified data from storage {}".format(storage))
				lms.append(None)

		if filter(lambda x: x is None, lms):
			# we return None if ANY of the involved storages returned None
			return None

		# if we reach this point, we return the maximum of all dates
		return max(lms)

	elif path.endswith("/files/local"):
		# only local storage involved
		try:
			return fileManager.last_modified(FileDestinations.LOCAL, recursive=recursive)
		except:
			logging.getLogger(__name__).exception("There was an error retrieving the last modified data from storage {}".format(FileDestinations.LOCAL))
			return None

	else:
		return None


def _create_etag(path, filter, recursive, lm=None):
	if lm is None:
		lm = _create_lastmodified(path, recursive)

	if lm is None:
		return None

	hash = hashlib.sha1()
	hash.update(str(lm))
	hash.update(str(filter))
	hash.update(str(recursive))

	if path.endswith("/files") or path.endswith("/files/sdcard"):
		# include sd data in etag
		hash.update(repr(sorted(printer.get_sd_files(), key=lambda x: x[0])))

	hash.update(_DATA_FORMAT_VERSION) # increment version if we change the API format

	return hash.hexdigest()

@api.route("/folders/local/<string:folder>/usage", methods=["GET"])
@with_revalidation_checking(etag_factory=lambda lm=None: _create_etag(request.path,
                                                                      request.values.get("filter", False),
                                                                      request.values.get("recursive", False),
                                                                      lm=lm),
                            lastmodified_factory=lambda: _create_lastmodified(request.path,
                                                                              request.values.get("recursive", False)),
                            unless=lambda: request.values.get("force", False) or request.values.get("_refresh", False))
def readUsageForFolder(folder):
	# import pry; pry()
	folder_path = settings().getBaseFolder(folder, check_writable=False)

	if folder_path is None:
		return make_response("Folder name %s not found" % folder, 404)

	usage = psutil.disk_usage(folder_path)

	return jsonify(folder=folder, free=usage.free, total=usage.total)
