# coding=utf-8
from __future__ import absolute_import

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

