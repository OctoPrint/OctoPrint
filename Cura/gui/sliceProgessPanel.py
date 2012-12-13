from __future__ import absolute_import

import wx
import os
import shutil
import threading
import time
import re
import platform

from Cura.gui import preferencesDialog
from Cura.gui.util import taskbar
from Cura.util import profile
from Cura.util import sliceRun
from Cura.util import exporer
from Cura.util import gcodeInterpreter

class sliceProgessPanel(wx.Panel):
	def __init__(self, mainWindow, parent, filelist):
		wx.Panel.__init__(self, parent, -1)
		self.mainWindow = mainWindow
		self.filelist = filelist
		self.abort = False
		
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
		for filename in self.filelist:
			idx = self.filelist.index(filename)
			#print filename, idx
			if idx > 0:
				profile.setTempOverride('fan_enabled', 'False')
				profile.setTempOverride('skirt_line_count', '0')
				profile.setTempOverride('object_center_x', profile.getPreferenceFloat('machine_width') / 2 - profile.getPreferenceFloat('extruder_offset_x%d' % (idx)))
				profile.setTempOverride('object_center_y', profile.getPreferenceFloat('machine_depth') / 2 - profile.getPreferenceFloat('extruder_offset_y%d' % (idx)))
				profile.setTempOverride('alternative_center', self.filelist[0])
			if len(self.filelist) > 1:
				profile.setTempOverride('add_start_end_gcode', 'False')
				profile.setTempOverride('gcode_extension', 'multi_extrude_tmp')
			cmdList.append(sliceRun.getSliceCommand(filename))
		profile.resetTempOverride()
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
		exporer.openExporer(sliceRun.getExportFilename(self.filelist[0]))
	
	def OnCopyToSD(self, e):
		if profile.getPreference('sdpath') == '':
			wx.MessageBox("You need to configure your SD card drive first before you can copy files to it.\nOpening the preferences now.", 'No SD card drive.', wx.OK | wx.ICON_INFORMATION)
			prefDialog = preferencesDialog.preferencesDialog(self.GetParent())
			prefDialog.Centre()
			prefDialog.Show(True)
			if profile.getPreference('sdpath') == '':
				print "No path set"
				return
		exportFilename = sliceRun.getExportFilename(self.filelist[0])
		filename = os.path.basename(exportFilename)
		if profile.getPreference('sdshortnames') == 'True':
			filename = sliceRun.getShortFilename(filename)
		try:
			shutil.copy(exportFilename, os.path.join(profile.getPreference('sdpath'), filename))
		except:
			self.GetParent().preview3d.ShowWarningPopup("Failed to copy file to SD card.")
			return
		self.GetParent().preview3d.ShowWarningPopup("Copy finished, safely remove SD card?", self.OnSafeRemove)
	
	def OnSafeRemove(self):
		if platform.system() == "Windows":
			cmd = "%s %s>NUL" % (os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'EjectMedia.exe')), profile.getPreference('sdpath'))
		elif platform.system() == "Darwin":
			cmd = "diskutil eject '%s' > /dev/null 2>&1" % (profile.getPreference('sdpath'))
		else:
			cmd = "umount '%s' > /dev/null 2>&1" % (profile.getPreference('sdpath'))
		if os.system(cmd):
			self.GetParent().preview3d.ShowWarningPopup("Safe remove failed.")
		else:
			self.GetParent().preview3d.ShowWarningPopup("You can now eject the card.")

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
			if len(profile.getSDcardDrives()) > 0:
				self.copyToSDButton = wx.Button(self, -1, "Copy to SDCard")
				self.Bind(wx.EVT_BUTTON, self.OnCopyToSD, self.copyToSDButton)
				self.sizer.Add(self.copyToSDButton, 0)
			self.showButton = wx.Button(self, -1, "Show result")
			self.Bind(wx.EVT_BUTTON, self.OnShowGCode, self.showButton)
			self.sizer.Add(self.showButton, 0)
		else:
			self.statusText.SetLabel("Something went wrong during slicing!")
		self.sizer.Add(self.abortButton, 0)
		self.sizer.Layout()
		self.Layout()
		self.abort = True
		if self.mainWindow.preview3d.reloadModelFiles(self.filelist):
			self.mainWindow.preview3d.setViewMode("GCode")
		taskbar.setBusy(self.GetParent(), False)
	
	def SetProgress(self, stepName, layer, maxLayer):
		if self.prevStep != stepName:
			self.totalDoneFactor += sliceRun.sliceStepTimeFactor[self.prevStep]
			newTime = time.time()
			#print "#####" + str(newTime-self.startTime) + " " + self.prevStep + " -> " + stepName
			self.startTime = newTime
			self.prevStep = stepName
		
		progresValue = ((self.totalDoneFactor + sliceRun.sliceStepTimeFactor[stepName] * layer / maxLayer) / sliceRun.totalRunTimeFactor) * 10000
		self.progressGauge.SetValue(int(progresValue))
		taskbar.setProgress(self.GetParent(), int(progresValue), self.progressGauge.GetRange())
		self.statusText.SetLabel("Preparing: processing %s [%d/%d]" % (stepName, layer, maxLayer))

class WorkerThread(threading.Thread):
	def __init__(self, notifyWindow, filelist, cmdList):
		threading.Thread.__init__(self)
		self.filelist = filelist
		self.notifyWindow = notifyWindow
		self.cmdList = cmdList
		self.fileIdx = 0
		self.start()

	def run(self):
		p = sliceRun.startSliceCommandProcess(self.cmdList[self.fileIdx])
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
				self.progressLog.append(line)
				wx.CallAfter(self.notifyWindow.statusText.SetLabel, line)
			if self.notifyWindow.abort:
				p.terminate()
				wx.CallAfter(self.notifyWindow.statusText.SetLabel, "Aborted by user.")
				return
			line = p.stdout.readline()
		line = p.stderr.readline()
		while(len(line) > 0):
			line = line.rstrip()
			self.progressLog.append(line)
			line = p.stderr.readline()
		self.returnCode = p.wait()
		self.fileIdx += 1
		if self.fileIdx == len(self.cmdList):
			if len(self.filelist) > 1:
				self._stitchMultiExtruder()
			gcodeFilename = sliceRun.getExportFilename(self.filelist[0])
			gcodefile = open(gcodeFilename, "a")
			for logLine in self.progressLog:
				if logLine.startswith('Model error('):
					gcodefile.write(';%s\n' % (logLine))
			gcodefile.close()
			wx.CallAfter(self.notifyWindow.statusText.SetLabel, "Running plugins")
			ret = profile.runPostProcessingPlugins(gcodeFilename)
			if ret != None:
				self.progressLog.append(ret)
			self.gcode = gcodeInterpreter.gcode()
			self.gcode.load(gcodeFilename)
			profile.replaceGCodeTags(gcodeFilename, self.gcode)
			wx.CallAfter(self.notifyWindow.OnSliceDone, self)
		else:
			self.run()
	
	def _stitchMultiExtruder(self):
		files = []
		resultFile = open(sliceRun.getExportFilename(self.filelist[0]), "w")
		resultFile.write(';TYPE:CUSTOM\n')
		resultFile.write(profile.getAlterationFileContents('start.gcode'))
		for filename in self.filelist:
			if os.path.isfile(sliceRun.getExportFilename(filename, 'multi_extrude_tmp')):
				files.append(open(sliceRun.getExportFilename(filename, 'multi_extrude_tmp'), "r"))
			else:
				return
		
		currentExtruder = 0
		resultFile.write('T%d\n' % (currentExtruder))
		layerNr = -1
		hasLine = True
		filesOrder = files[:]
		while hasLine:
			hasLine = False
			filesOrder.reverse()
			for f in filesOrder:
				layerHasLine = False
				for line in f:
					hasLine = True
					if line.startswith(';LAYER:'):
						break
					if 'Z' in line:
						lastZ = float(re.search('Z([^\s]+)', line).group(1))
					if not layerHasLine:
						nextExtruder = files.index(f)
						resultFile.write(';LAYER:%d\n' % (layerNr))
						resultFile.write(';EXTRUDER:%d\n' % (nextExtruder))
						if nextExtruder != currentExtruder:
							resultFile.write(';TYPE:CUSTOM\n')
							profile.setTempOverride('extruder', nextExtruder)
							resultFile.write(profile.getAlterationFileContents('switchExtruder.gcode') + '\n')
							profile.resetTempOverride()
							currentExtruder = nextExtruder
						layerHasLine = True
					resultFile.write(line)
			layerNr += 1
		for f in files:
			f.close()
		for filename in self.filelist:
			os.remove(sliceRun.getExportFilename(filename, 'multi_extrude_tmp'))
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

