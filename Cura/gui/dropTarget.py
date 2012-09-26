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
		filteredList = []
		if self.filenameFilter != None:
			for f in filenames:
				for ext in self.filenameFilter:
					if f.endswith(ext) or f.endswith(ext.upper()):
						filteredList.append(f)
		else:
			filteredList = filenames
		if len(filteredList) > 0:
			self.callback(filteredList)

