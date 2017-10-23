# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


class NoUpdateAvailable(Exception):
	pass

class UpdateAlreadyInProgress(Exception):
	pass

class UnknownUpdateType(Exception):
	pass

class UnknownCheckType(Exception):
	pass

class NetworkError(Exception):
	def __init__(self, message=None, cause=None):
		Exception.__init__(self)
		self.message = message
		self.cause = cause

	def __str__(self):
		if self.message is not None:
			return self.message
		elif self.cause is not None:
			return "NetworkError caused by {}".format(self.cause)
		else:
			return "NetworkError"

class UpdateError(Exception):
	def __init__(self, message, data):
		self.message = message
		self.data = data

class ScriptError(Exception):
	def __init__(self, returncode, stdout, stderr):
		self.returncode = returncode
		self.stdout = stdout
		self.stderr = stderr

class RestartFailed(Exception):
	pass

class ConfigurationInvalid(Exception):
	pass

class CannotCheckOffline(Exception):
	pass

class CannotUpdateOffline(Exception):
	pass
