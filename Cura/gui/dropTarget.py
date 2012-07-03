from __future__ import absolute_import
import __init__

import wx

# Define File Drop Target class
class FileDropTarget(wx.FileDropTarget):
	def __init__(self, callback, filenameFilter = None):
		super(FileDropTarget, self).__init__()
		self.callback = callback
		self.filenameFilter = filenameFilter

	def OnDropFiles(self, x, y, filenames):
		if self.filenameFilter != None:
			filenames = filter(lambda f: f.endswith(self.filenameFilter) or f.endswith(self.filenameFilter.upper()), filenames)
		if len(filenames) > 0:
			self.callback(filenames)

