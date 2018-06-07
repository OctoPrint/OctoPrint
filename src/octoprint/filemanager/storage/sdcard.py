# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"


from . import Storage, StorageError


class PrinterSDStorage(Storage):
	def create_print_job(self, path, user=None):
		from octoprint.comm.job import SDFilePrintjob
		return SDFilePrintjob("/" + path, user=user)
