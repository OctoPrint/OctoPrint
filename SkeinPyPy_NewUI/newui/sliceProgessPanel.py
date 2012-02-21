from __future__ import absolute_import
import __init__

import wx,sys,math,threading,subprocess
from newui import skeinRun

class sliceProgessPanel(wx.Panel):
	def __init__(self, mainWindow, parent, filename):
		wx.Panel.__init__(self, parent, -1)
		self.mainWindow = mainWindow
		self.filename = filename
		self.abort = False

		box = wx.StaticBox(self, -1, filename)
		self.sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)

		mainSizer = wx.BoxSizer(wx.VERTICAL) 
		mainSizer.Add(self.sizer, 0, flag=wx.EXPAND)

		self.statusText = wx.StaticText(self, -1, "Starting...")
		self.progressGauge = wx.Gauge(self, -1)
		self.abortButton = wx.Button(self, -1, "X", style=wx.BU_EXACTFIT)
		self.sizer.Add(self.statusText, 2, flag=wx.ALIGN_CENTER )
		self.sizer.Add(self.progressGauge, 2)
		self.sizer.Add(self.abortButton, 0)

		self.Bind(wx.EVT_BUTTON, self.OnAbort, self.abortButton)

		self.SetSizer(mainSizer)
		self.thread = WorkerThread(self, filename)
	
	def OnAbort(self, e):
		if self.abort:
			self.mainWindow.removeSliceProgress(self)
		else:
			self.abort = True
	
	def OnShowGCode(self, e):
		self.mainWindow.preview3d.loadGCodeFile(self.filename[: self.filename.rfind('.')] + "_export.gcode")
	
	def OnSliceDone(self):
		self.statusText.SetLabel("Ready.")
		self.progressGauge.Destroy()
		self.showButton = wx.Button(self, -1, "Show GCode")
		self.Bind(wx.EVT_BUTTON, self.OnShowGCode, self.showButton)
		self.sizer.Remove(self.abortButton)
		self.sizer.Add(self.showButton, 0)
		self.sizer.Add(self.abortButton, 0)
		self.sizer.Layout()
		self.abort = True

class WorkerThread(threading.Thread):
	def __init__(self, notifyWindow, filename):
		threading.Thread.__init__(self)
		self.filename = filename
		self.notifyWindow = notifyWindow
		self.start()

	def run(self):
		p = subprocess.Popen(skeinRun.getSkeinCommand(self.filename), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		line = p.stdout.readline()
		maxValue = 1
		while(len(line) > 0):
			line = line.rstrip()
			print line
			if line[0:9] == "Progress[" and line[-1:] == "]":
				progress = line[9:-1].split(":")
				if len(progress) > 2:
					maxValue = int(progress[2])
					wx.CallAfter(self.notifyWindow.progressGauge.SetRange, maxValue)
				wx.CallAfter(self.notifyWindow.statusText.SetLabel, progress[0] + " [" + progress[1] + "/" + str(maxValue) + "]")
				wx.CallAfter(self.notifyWindow.progressGauge.SetValue, int(progress[1]))
			else:
				wx.CallAfter(self.notifyWindow.statusText.SetLabel, line)
			if self.notifyWindow.abort:
				p.terminate()
				wx.CallAfter(self.notifyWindow.statusText.SetLabel, "Aborted by user.")
				return
			line = p.stdout.readline()
		wx.CallAfter(self.notifyWindow.OnSliceDone)
