from __future__ import absolute_import
import __init__

import wx, os, platform, types, webbrowser, math, subprocess, threading, time, re

from util import profile
from util import sliceRun

class batchRunWindow(wx.Frame):
	def __init__(self, parent):
		super(batchRunWindow, self).__init__(parent, title='Cura - Batch run')
		
		self.list = []
		
		wx.EVT_CLOSE(self, self.OnClose)
		self.panel = wx.Panel(self, -1)
		self.SetSizer(wx.BoxSizer(wx.VERTICAL))
		self.GetSizer().Add(self.panel, 1, flag=wx.EXPAND)
		#self.SetIcon(icon.getMainIcon())

		self.sizer = wx.GridBagSizer(2,2)
		self.panel.SetSizer(self.sizer)

		self.listbox = wx.ListBox(self.panel, -1, choices=[])
		self.addButton = wx.Button(self.panel, -1, "Add")
		self.remButton = wx.Button(self.panel, -1, "Remove")
		self.sliceButton = wx.Button(self.panel, -1, "Slice")

		self.addButton.Bind(wx.EVT_BUTTON, self.OnAddModel)
		self.remButton.Bind(wx.EVT_BUTTON, self.OnRemModel)
		self.sliceButton.Bind(wx.EVT_BUTTON, self.OnSlice)
		self.listbox.Bind(wx.EVT_LISTBOX, self.OnListSelect)

		self.sizer.Add(self.listbox, (0,0), span=(1,3), flag=wx.EXPAND)
		self.sizer.Add(self.addButton, (1,0), span=(1,1))
		self.sizer.Add(self.remButton, (1,1), span=(1,1))
		self.sizer.Add(self.sliceButton, (1,2), span=(1,1))

		self.sizer.AddGrowableCol(2)
		self.sizer.AddGrowableRow(0)

	def OnAddModel(self, e):
		dlg=wx.FileDialog(self, "Open file to batch slice", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST|wx.FD_MULTIPLE)
		dlg.SetWildcard("STL files (*.stl)|*.stl;*.STL")
		if dlg.ShowModal() == wx.ID_OK:
			for filename in dlg.GetPaths():
				profile.putPreference('lastFile', filename)
				self.list.append(filename)
				self.selection = filename
				self._updateListbox()
		dlg.Destroy()
	
	def OnRemModel(self, e):
		if self.selection == None:
			return
		self.list.remove(self.selection)
		self._updateListbox()

	def OnListSelect(self, e):
		if self.listbox.GetSelection() == -1:
			return
		self.selection = self.list[self.listbox.GetSelection()]

	def _updateListbox(self):
		self.listbox.Clear()
		for item in self.list:
			self.listbox.AppendAndEnsureVisible(os.path.split(item)[1])
		if self.selection in self.list:
			self.listbox.SetSelection(self.list.index(self.selection))
		elif len(self.list) > 0:
			self.selection = self.list[0]
			self.listbox.SetSelection(0)
		else:
			self.selection = None
			self.listbox.SetSelection(-1)

	def OnClose(self, e):
		self.Destroy()

	def OnSlice(self, e):
		sliceCmdList = []
		for filename in self.list:
			sliceCmdList.append(sliceRun.getSliceCommand(filename))
		bspw = BatchSliceProgressWindow(self.list[:], sliceCmdList)
		bspw.Centre()
		bspw.Show(True)
	
class BatchSliceProgressWindow(wx.Frame):
	def __init__(self, filenameList, sliceCmdList):
		super(BatchSliceProgressWindow, self).__init__(None, title='Cura')
		self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
		
		self.filenameList = filenameList
		self.sliceCmdList = sliceCmdList
		self.abort = False
		self.prevStep = 'start'
		self.totalDoneFactor = 0.0
		self.startTime = time.time()
		self.sliceStartTime = time.time()
		
		self.sizer = wx.GridBagSizer(2, 2) 
		self.statusText = wx.StaticText(self, -1, "Building: %d XXXXXXXXXXXXXXXXXXXXX" % (len(self.sliceCmdList)))
		self.progressGauge = wx.Gauge(self, -1)
		self.progressGauge.SetRange(10000)
		self.progressGauge2 = wx.Gauge(self, -1)
		self.progressGauge2.SetRange(len(self.sliceCmdList))
		self.abortButton = wx.Button(self, -1, "Abort")
		self.sizer.Add(self.statusText, (0,0), span=(1,4))
		self.sizer.Add(self.progressGauge, (1, 0), span=(1,4), flag=wx.EXPAND)
		self.sizer.Add(self.progressGauge2, (2, 0), span=(1,4), flag=wx.EXPAND)

		self.sizer.Add(self.abortButton, (3,0), span=(1,4), flag=wx.ALIGN_CENTER)
		self.sizer.AddGrowableCol(0)
		self.sizer.AddGrowableRow(0)

		self.Bind(wx.EVT_BUTTON, self.OnAbort, self.abortButton)
		self.SetSizer(self.sizer)
		self.Layout()
		self.Fit()
		
		threading.Thread(target=self.OnRun).start()

	def OnAbort(self, e):
		if self.abort:
			self.Close()
		else:
			self.abort = True
			self.abortButton.SetLabel('Close')

	def SetProgress(self, stepName, layer, maxLayer):
		if self.prevStep != stepName:
			self.totalDoneFactor += sliceRun.sliceStepTimeFactor[self.prevStep]
			newTime = time.time()
			#print "#####" + str(newTime-self.startTime) + " " + self.prevStep + " -> " + stepName
			self.startTime = newTime
			self.prevStep = stepName
		
		progresValue = ((self.totalDoneFactor + sliceRun.sliceStepTimeFactor[stepName] * layer / maxLayer) / sliceRun.totalRunTimeFactor) * 10000
		self.progressGauge.SetValue(int(progresValue))
		self.statusText.SetLabel(stepName + " [" + str(layer) + "/" + str(maxLayer) + "]")
	
	def OnRun(self):
		for action in self.sliceCmdList:
			wx.CallAfter(self.SetTitle, "Building: [%d/%d]"  % (self.sliceCmdList.index(action) + 1, len(self.sliceCmdList)))

			p = subprocess.Popen(action, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			line = p.stdout.readline()
			maxValue = 1
			while(len(line) > 0):
				line = line.rstrip()
				if line[0:9] == "Progress[" and line[-1:] == "]":
					progress = line[9:-1].split(":")
					if len(progress) > 2:
						maxValue = int(progress[2])
					wx.CallAfter(self.SetProgress, progress[0], int(progress[1]), maxValue)
				else:
					print line
					wx.CallAfter(self.statusText.SetLabel, line)
				if self.abort:
					p.terminate()
					wx.CallAfter(self.statusText.SetLabel, "Aborted by user.")
					return
				line = p.stdout.readline()
			self.returnCode = p.wait()
			
			wx.CallAfter(self.progressGauge.SetValue, 10000)
			self.totalDoneFactor = 0.0
			wx.CallAfter(self.progressGauge2.SetValue, self.sliceCmdList.index(action) + 1)
		
		self.abort = True
		sliceTime = time.time() - self.sliceStartTime
		status = "Build: %d" % (len(self.sliceCmdList))
		status += "\nSlicing took: %02d:%02d" % (sliceTime / 60, sliceTime % 60)

		wx.CallAfter(self.statusText.SetLabel, status)
		wx.CallAfter(self.OnSliceDone)
	
	def OnSliceDone(self):
		self.abortButton.Destroy()
		self.closeButton = wx.Button(self, -1, "Close")
		self.sizer.Add(self.closeButton, (3,0), span=(1,1))
		self.Bind(wx.EVT_BUTTON, self.OnAbort, self.closeButton)
		self.Layout()
		self.Fit()

