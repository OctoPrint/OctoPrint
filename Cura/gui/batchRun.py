from __future__ import absolute_import
import __init__

import wx, os, platform, types, webbrowser, math, subprocess, multiprocessing, threading, time, re, shutil

from util import profile
from util import sliceRun
from util import meshLoader
from gui import dropTarget

class batchRunWindow(wx.Frame):
	def __init__(self, parent):
		super(batchRunWindow, self).__init__(parent, title='Cura - Batch run')
		
		self.list = []
		
		self.SetDropTarget(dropTarget.FileDropTarget(self.OnDropFiles, meshLoader.supportedExtensions()))
		
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
	
	def OnDropFiles(self, filenames):
		for filename in filenames:
			profile.putPreference('lastFile', filename)
			self.list.append(filename)
			self.selection = filename
			self._updateListbox()

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
		self.sliceStartTime = time.time()

		try:
			self.threadCount = multiprocessing.cpu_count() - 1
		except:
			self.threadCount = 1
		if self.threadCount < 1:
			self.threadCount = 1
		self.cmdIndex = 0
		
		self.prevStep = []
		self.totalDoneFactor = []
		for i in xrange(0, self.threadCount):
			self.prevStep.append('start')
			self.totalDoneFactor.append(0.0)

		self.sizer = wx.GridBagSizer(2, 2) 
		self.progressGauge = []
		self.statusText = []
		for i in xrange(0, self.threadCount):
			self.statusText.append(wx.StaticText(self, -1, "Building: %d                           " % (len(self.sliceCmdList))))
			self.progressGauge.append(wx.Gauge(self, -1))
			self.progressGauge[i].SetRange(10000)
		self.progressGaugeTotal = wx.Gauge(self, -1)
		self.progressGaugeTotal.SetRange(len(self.sliceCmdList))
		self.abortButton = wx.Button(self, -1, "Abort")
		for i in xrange(0, self.threadCount):
			self.sizer.Add(self.statusText[i], (i*2,0), span=(1,4))
			self.sizer.Add(self.progressGauge[i], (1+i*2, 0), span=(1,4), flag=wx.EXPAND)
		self.sizer.Add(self.progressGaugeTotal, (1+self.threadCount*2, 0), span=(1,4), flag=wx.EXPAND)

		self.sizer.Add(self.abortButton, (2+self.threadCount*2,0), span=(1,4), flag=wx.ALIGN_CENTER)
		self.sizer.AddGrowableCol(0)
		self.sizer.AddGrowableRow(0)

		self.Bind(wx.EVT_BUTTON, self.OnAbort, self.abortButton)
		self.SetSizer(self.sizer)
		self.Layout()
		self.Fit()
		
		threading.Thread(target=self.OnRunManager).start()

	def OnAbort(self, e):
		if self.abort:
			self.Close()
		else:
			self.abort = True
			self.abortButton.SetLabel('Close')

	def SetProgress(self, index, stepName, layer, maxLayer):
		if self.prevStep[index] != stepName:
			self.totalDoneFactor[index] += sliceRun.sliceStepTimeFactor[self.prevStep[index]]
			newTime = time.time()
			self.prevStep[index] = stepName
		
		progresValue = ((self.totalDoneFactor[index] + sliceRun.sliceStepTimeFactor[stepName] * layer / maxLayer) / sliceRun.totalRunTimeFactor) * 10000
		self.progressGauge[index].SetValue(int(progresValue))
		self.statusText[index].SetLabel(stepName + " [" + str(layer) + "/" + str(maxLayer) + "]")
	
	def OnRunManager(self):
		threads = []
		for i in xrange(0, self.threadCount):
			threads.append(threading.Thread(target=self.OnRun, args=(i,)))

		for t in threads:
			t.start()
		for t in threads:
			t.join()

		self.abort = True
		sliceTime = time.time() - self.sliceStartTime
		status = "Build: %d" % (len(self.sliceCmdList))
		status += "\nSlicing took: %02d:%02d" % (sliceTime / 60, sliceTime % 60)

		wx.CallAfter(self.statusText[0].SetLabel, status)
		wx.CallAfter(self.OnSliceDone)
	
	def OnRun(self, index):
		while self.cmdIndex < len(self.sliceCmdList):
			action = self.sliceCmdList[self.cmdIndex]
			self.cmdIndex += 1
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
					wx.CallAfter(self.SetProgress, index, progress[0], int(progress[1]), maxValue)
				else:
					print line
					wx.CallAfter(self.statusText[index].SetLabel, line)
				if self.abort:
					p.terminate()
					wx.CallAfter(self.statusText[index].SetLabel, "Aborted by user.")
					return
				line = p.stdout.readline()
			self.returnCode = p.wait()
			
			wx.CallAfter(self.progressGauge[index].SetValue, 10000)
			self.totalDoneFactor[index] = 0.0
			wx.CallAfter(self.progressGaugeTotal.SetValue, self.cmdIndex)
	
	def OnSliceDone(self):
		self.abortButton.Destroy()
		self.closeButton = wx.Button(self, -1, "Close")
		self.sizer.Add(self.closeButton, (2+self.threadCount*2,0), span=(1,1))
		if profile.getPreference('sdpath') != '':
			self.copyToSDButton = wx.Button(self, -1, "To SDCard")
			self.Bind(wx.EVT_BUTTON, self.OnCopyToSD, self.copyToSDButton)
			self.sizer.Add(self.copyToSDButton, (2+self.threadCount*2,1), span=(1,1))
		self.Bind(wx.EVT_BUTTON, self.OnAbort, self.closeButton)
		self.Layout()
		self.Fit()

	def OnCopyToSD(self, e):
		for f in self.filenameList:
			exportFilename = sliceRun.getExportFilename(f)
			filename = os.path.basename(exportFilename)
			if profile.getPreference('sdshortnames') == 'True':
				filename = sliceRun.getShortFilename(filename)
			shutil.copy(exportFilename, os.path.join(profile.getPreference('sdpath'), filename))
