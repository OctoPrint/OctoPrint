from __future__ import absolute_import
import __init__

import wx
import sys
import math
import threading
import subprocess
import time

from newui import sliceRun

class sliceProgessPanel(wx.Panel):
	def __init__(self, mainWindow, parent, filename):
		wx.Panel.__init__(self, parent, -1)
		self.mainWindow = mainWindow
		self.filename = filename
		self.abort = False
		
		#How long does each step take compared to the others. This is used to make a better scaled progress bar, and guess time left.
		self.sliceStepTimeFactor = {
			'start': 3.3713991642,
			'slice': 15.4984838963,
			'preface': 5.17178297043,
			'inset': 116.362634182,
			'fill': 215.702672005,
			'multiply': 21.9536788464,
			'speed': 12.759510994,
			'raft': 31.4580039978,
			'skirt': 19.3436040878,
			'joris': 1.0,
			'comb': 23.7805759907,
			'cool': 27.148763895,
			'dimension': 90.4914340973
		}
		self.totalRunTimeFactor = 0
		for v in self.sliceStepTimeFactor.itervalues():
			self.totalRunTimeFactor += v

		box = wx.StaticBox(self, -1, filename)
		self.sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)

		mainSizer = wx.BoxSizer(wx.VERTICAL) 
		mainSizer.Add(self.sizer, 0, flag=wx.EXPAND)

		self.statusText = wx.StaticText(self, -1, "Starting...")
		self.progressGauge = wx.Gauge(self, -1)
		self.progressGauge.SetRange(10000)
		self.abortButton = wx.Button(self, -1, "X", style=wx.BU_EXACTFIT)
		self.sizer.Add(self.statusText, 2, flag=wx.ALIGN_CENTER )
		self.sizer.Add(self.progressGauge, 2)
		self.sizer.Add(self.abortButton, 0)

		self.Bind(wx.EVT_BUTTON, self.OnAbort, self.abortButton)

		self.SetSizer(mainSizer)
		self.prevStep = 'start'
		self.totalDoneFactor = 0.0
		self.startTime = time.time()
		self.thread = WorkerThread(self, filename)
	
	def OnAbort(self, e):
		if self.abort:
			self.mainWindow.removeSliceProgress(self)
		else:
			self.abort = True
	
	def OnShowGCode(self, e):
		self.mainWindow.preview3d.loadModelFile(self.filename)
		self.mainWindow.preview3d.setViewMode("GCode")
	
	def OnShowLog(self, e):
		LogWindow('\n'.join(self.progressLog))
	
	def OnSliceDone(self, result):
		self.progressGauge.Destroy()
		self.abortButton.Destroy()
		self.progressLog = result.progressLog
		self.logButton = wx.Button(self, -1, "Show Log")
		self.abortButton = wx.Button(self, -1, "X", style=wx.BU_EXACTFIT)
		self.Bind(wx.EVT_BUTTON, self.OnShowLog, self.logButton)
		self.Bind(wx.EVT_BUTTON, self.OnAbort, self.abortButton)
		self.sizer.Add(self.logButton, 0)
		if result.returnCode == 0:
			self.statusText.SetLabel("Ready.")
			self.showButton = wx.Button(self, -1, "Show result")
			self.Bind(wx.EVT_BUTTON, self.OnShowGCode, self.showButton)
			self.sizer.Add(self.showButton, 0)
		else:
			self.statusText.SetLabel("Something went wrong during slicing!")
		self.sizer.Add(self.abortButton, 0)
		self.sizer.Layout()
		self.Layout()
		self.abort = True
		if self.mainWindow.preview3d.loadReModelFile(self.filename):
			self.mainWindow.preview3d.setViewMode("GCode")
	
	def SetProgress(self, stepName, layer, maxLayer):
		if self.prevStep != stepName:
			self.totalDoneFactor += self.sliceStepTimeFactor[self.prevStep]
			newTime = time.time()
			#print "#####" + str(newTime-self.startTime) + " " + self.prevStep + " -> " + stepName
			self.startTime = newTime
			self.prevStep = stepName
		
		progresValue = ((self.totalDoneFactor + self.sliceStepTimeFactor[stepName] * layer / maxLayer) / self.totalRunTimeFactor) * 10000
		self.progressGauge.SetValue(int(progresValue))
		self.statusText.SetLabel(stepName + " [" + str(layer) + "/" + str(maxLayer) + "]")

class WorkerThread(threading.Thread):
	def __init__(self, notifyWindow, filename):
		threading.Thread.__init__(self)
		self.filename = filename
		self.notifyWindow = notifyWindow
		self.start()

	def run(self):
		p = subprocess.Popen(sliceRun.getSliceCommand(self.filename), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		line = p.stdout.readline()
		maxValue = 1
		self.progressLog = []
		while(len(line) > 0):
			line = line.rstrip()
			if line[0:9] == "Progress[" and line[-1:] == "]":
				progress = line[9:-1].split(":")
				if len(progress) > 2:
					maxValue = int(progress[2])
				wx.CallAfter(self.notifyWindow.SetProgress, progress[0], int(progress[1]), maxValue)
			else:
				print line
				self.progressLog.append(line)
				wx.CallAfter(self.notifyWindow.statusText.SetLabel, line)
			if self.notifyWindow.abort:
				p.terminate()
				wx.CallAfter(self.notifyWindow.statusText.SetLabel, "Aborted by user.")
				return
			line = p.stdout.readline()
		self.returnCode = p.wait()
		logfile = open(self.filename[: self.filename.rfind('.')] + "_export.log", "w")
		for logLine in self.progressLog:
			logfile.write(logLine)
			logfile.write('\n')
		logfile.close()
		wx.CallAfter(self.notifyWindow.OnSliceDone, self)

class LogWindow(wx.Frame):
	def __init__(self, logText):
		super(LogWindow, self).__init__(None, title="Slice log")
		self.textBox = wx.TextCtrl(self, -1, logText, style=wx.TE_MULTILINE|wx.TE_DONTWRAP|wx.TE_READONLY)
		self.SetSize((400,300))
		self.Centre()
		self.Show(True)

