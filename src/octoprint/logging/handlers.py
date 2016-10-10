# coding=utf-8
from __future__ import absolute_import

import logging.handlers
import os

class CleaningTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):

	def __init__(self, *args, **kwargs):
		logging.handlers.TimedRotatingFileHandler.__init__(self, *args, **kwargs)

		# clean up old files on handler start
		if self.backupCount > 0:
			for s in self.getFilesToDelete():
				os.remove(s)

