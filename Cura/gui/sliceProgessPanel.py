from __future__ import absolute_import
import __init__

import wx, sys, os, math, threading, subprocess, time

from util import profile
from util import sliceRun
from util import exporer
from util import gcodeInterpreter

class sliceProgessPanel(wx.Panel):
	def __init__(self, mainWindow, parent, filelist):
		wx.Panel.__init__(self, parent, -1)
		self.mainWindow = mainWindow
		self.filelist = filelist
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
			'skin': 1.0,
			'joris': 1.0,
			'comb': 23.7805759907,
			'cool': 27.148763895,
			'dimension': 90.4914340973
		}
		self.totalRunTimeFactor = 0
		for v in self.sliceStepTimeFactor.itervalues():
			self.totalRunTimeFactor += v

		box = wx.StaticBox(self, -1, filelist[0])
		self.sizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)

		mainSizer = wx.BoxSizer(wx.VERTICAL) 
		mainSizer.Add(self.sizer, 0, flag=wx.EXPAND)

		self.statusText = wx.StaticText(self, -1, "Starting...")
		self.progressGauge = wx.Gauge(self, -1)
		self.progressGauge.SetRange(10000 * len(filelist))
		self.abortButton = wx.Button(self, -1, "X", style=wx.BU_EXACTFIT)
		self.sizer.Add(self.statusText, 2, flag=wx.ALIGN_CENTER )
		self.sizer.Add(self.progressGauge, 2)
		self.sizer.Add(self.abortButton, 0)

		self.Bind(wx.EVT_BUTTON, self.OnAbort, self.abortButton)

		self.SetSizer(mainSizer)
		self.prevStep = 'start'
		self.totalDoneFactor = 0.0
		self.startTime = time.time()
		if profile.getPreference('save_profile') == 'True':
			profile.saveGlobalProfile(self.filelist[0][: self.filelist[0].rfind('.')] + "_profile.ini")
		cmdList = []
		oldProfile = profile.getGlobalProfileString()
		for filename in self.filelist:
			idx = self.filelist.index(filename)
			print filename, idx
			if idx > 0:
				profile.putProfileSetting('fan_enabled', 'False')
				profile.putProfileSetting('skirt_line_count', '0')
				profile.putProfileSetting('machine_center_x', profile.getProfileSettingFloat('machine_center_x') - float(profile.getPreference('extruder_offset_x%d' % (idx))))
				profile.putProfileSetting('machine_center_y', profile.getProfileSettingFloat('machine_center_y') - float(profile.getPreference('extruder_offset_y%d' % (idx))))
				profile.putProfileSetting('alternative_center', self.filelist[0])
			if len(self.filelist) > 1:
				profile.putProfileSetting('add_start_end_gcode', 'False')
				profile.putProfileSetting('gcode_extension', 'multi_extrude_tmp')
			cmdList.append(sliceRun.getSliceCommand(filename))
		profile.loadGlobalProfileFromString(oldProfile)
		self.thread = WorkerThread(self, filelist, cmdList)
	
	def OnAbort(self, e):
		if self.abort:
			self.mainWindow.removeSliceProgress(self)
		else:
			self.abort = True
	
	def OnShowGCode(self, e):
		self.mainWindow.preview3d.loadModelFiles(self.filelist)
		self.mainWindow.preview3d.setViewMode("GCode")
	
	def OnShowLog(self, e):
		LogWindow('\n'.join(self.progressLog))
	
	def OnOpenFileLocation(self, e):
		exporer.openExporer(self.filelist[0][: self.filelist[0].rfind('.')] + "_export.gcode")
	
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
			status = "Ready: Filament: %.2fm %.2fg" % (result.gcode.extrusionAmount / 1000, result.gcode.calculateWeight() * 1000)
			status += " Print time: %02d:%02d" % (int(result.gcode.totalMoveTimeMinute / 60), int(result.gcode.totalMoveTimeMinute % 60))
			cost = result.gcode.calculateCost()
			if cost != False:
				status += " Cost: %s" % (cost)
			self.statusText.SetLabel(status)
			if exporer.hasExporer():
				self.openFileLocationButton = wx.Button(self, -1, "Open file location")
				self.Bind(wx.EVT_BUTTON, self.OnOpenFileLocation, self.openFileLocationButton)
				self.sizer.Add(self.openFileLocationButton, 0)
			self.showButton = wx.Button(self, -1, "Show result")
			self.Bind(wx.EVT_BUTTON, self.OnShowGCode, self.showButton)
			self.sizer.Add(self.showButton, 0)
		else:
			self.statusText.SetLabel("Something went wrong during slicing!")
		self.sizer.Add(self.abortButton, 0)
		self.sizer.Layout()
		self.Layout()
		self.abort = True
		if self.mainWindow.preview3d.loadReModelFiles(self.filelist):
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
	def __init__(self, notifyWindow, filelist, cmdList):
		threading.Thread.__init__(self)
		self.filelist = filelist
		self.notifyWindow = notifyWindow
		self.cmdList = cmdList
		self.fileIdx = 0
		self.start()

	def run(self):
		p = subprocess.Popen(self.cmdList[self.fileIdx], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		line = p.stdout.readline()
		self.progressLog = []
		maxValue = 1
		while(len(line) > 0):
			line = line.rstrip()
			if line[0:9] == "Progress[" and line[-1:] == "]":
				progress = line[9:-1].split(":")
				if len(progress) > 2:
					maxValue = int(progress[2])
				wx.CallAfter(self.notifyWindow.SetProgress, progress[0], int(progress[1]), maxValue)
			else:
				#print line
				self.progressLog.append(line)
				wx.CallAfter(self.notifyWindow.statusText.SetLabel, line)
			if self.notifyWindow.abort:
				p.terminate()
				wx.CallAfter(self.notifyWindow.statusText.SetLabel, "Aborted by user.")
				return
			line = p.stdout.readline()
		self.returnCode = p.wait()
		logfile = open(self.filelist[self.fileIdx][: self.filelist[self.fileIdx].rfind('.')] + "_export.log", "w")
		for logLine in self.progressLog:
			logfile.write(logLine)
			logfile.write('\n')
		logfile.close()
		self.fileIdx += 1
		if self.fileIdx == len(self.cmdList):
			if len(self.filelist) > 1:
				self._stitchMultiExtruder()
			self.gcode = gcodeInterpreter.gcode()
			self.gcode.load(self.filelist[0][:self.filelist[0].rfind('.')]+'_export.gcode')
			wx.CallAfter(self.notifyWindow.OnSliceDone, self)
		else:
			self.run()
	
	def _stitchMultiExtruder(self):
		files = []
		resultFile = open(self.filelist[0][:self.filelist[0].rfind('.')]+'_export.gcode', "w")
		resultFile.write(';TYPE:CUSTOM\n')
		resultFile.write(profile.getAlterationFileContents('start.gcode'))
		for filename in self.filelist:
			files.append(open(filename[:filename.rfind('.')]+'_export.multi_extrude_tmp', "r"))
		
		currentExtruder = 0
		resultFile.write('T%d\n' % (currentExtruder))
		layerNr = -1
		hasLine = True
		while hasLine:
			hasLine = False
			for f in files:
				layerHasLine = False
				for line in f:
					hasLine = True
					if line.startswith(';LAYER:'):
						break
					if not layerHasLine:
						nextExtruder = files.index(f)
						resultFile.write(';LAYER:%d\n' % (layerNr))
						resultFile.write(';EXTRUDER:%d\n' % (nextExtruder))
						if nextExtruder != currentExtruder:
							resultFile.write("G1 E-5 F5000\n")
							resultFile.write("G92 E0\n")
							resultFile.write("T%d\n" % (nextExtruder))
							resultFile.write("G1 E5 F5000\n")
							resultFile.write("G92 E0\n")
							currentExtruder = nextExtruder
						layerHasLine = True
					resultFile.write(line)
			layerNr += 1
		for f in files:
			f.close()
		for filename in self.filelist:
			os.remove(filename[:filename.rfind('.')]+'_export.multi_extrude_tmp')
		resultFile.write(';TYPE:CUSTOM\n')
		resultFile.write(profile.getAlterationFileContents('end.gcode'))
		resultFile.close()

class LogWindow(wx.Frame):
	def __init__(self, logText):
		super(LogWindow, self).__init__(None, title="Slice log")
		self.textBox = wx.TextCtrl(self, -1, logText, style=wx.TE_MULTILINE|wx.TE_DONTWRAP|wx.TE_READONLY)
		self.SetSize((400,300))
		self.Centre()
		self.Show(True)

