from __future__ import absolute_import
import __init__

import wx, threading, re, subprocess, sys, os, time, platform
from wx.lib import buttons

from gui import icon
from gui import toolbarUtil
from gui import webcam
from gui import taskbar
from util import machineCom
from util import profile
from util import gcodeInterpreter

printWindowMonitorHandle = None

def printFile(filename):
	global printWindowMonitorHandle
	if printWindowMonitorHandle == None:
		printWindowMonitorHandle = printProcessMonitor()
	printWindowMonitorHandle.loadFile(filename)

def startPrintInterface(filename):
	#startPrintInterface is called from the main script when we want the printer interface to run in a seperate process.
	# It needs to run in a seperate process, as any running python code blocks the GCode sender pyton code (http://wiki.python.org/moin/GlobalInterpreterLock).
	app = wx.App(False)
	printWindowHandle = printWindow()
	printWindowHandle.Show(True)
	printWindowHandle.Raise()
	printWindowHandle.OnConnect(None)
	t = threading.Thread(target=printWindowHandle.LoadGCodeFile,args=(filename,))
	t.daemon = True
	t.start()
	app.MainLoop()

class printProcessMonitor():
	def __init__(self):
		self.handle = None
	
	def loadFile(self, filename):
		if self.handle == None:
			cmdList = [sys.executable, sys.argv[0], '-r', filename]
			if platform.system() == "Darwin":
				if platform.machine() == 'i386':
					cmdList.insert(0, 'arch')
					cmdList.insert(1, '-i386')
			self.handle = subprocess.Popen(cmdList, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			self.thread = threading.Thread(target=self.Monitor)
			self.thread.start()
		else:
			self.handle.stdin.write(filename + '\n')
	
	def Monitor(self):
		p = self.handle
		line = p.stdout.readline()
		while(len(line) > 0):
			#print line.rstrip()
			line = p.stdout.readline()
		p.communicate()
		self.handle = None
		self.thread = None

class PrintCommandButton(buttons.GenBitmapButton):
	def __init__(self, parent, commandList, bitmapFilename, size=(20,20)):
		self.bitmap = toolbarUtil.getBitmapImage(bitmapFilename)
		super(PrintCommandButton, self).__init__(parent.directControlPanel, -1, self.bitmap, size=size)

		self.commandList = commandList
		self.parent = parent

		self.SetBezelWidth(1)
		self.SetUseFocusIndicator(False)

		self.Bind(wx.EVT_BUTTON, self.OnClick)

	def OnClick(self, e):
		if self.parent.machineCom == None or self.parent.machineCom.isPrinting():
			return;
		for cmd in self.commandList:
			self.parent.machineCom.sendCommand(cmd)
		e.Skip()

class printWindow(wx.Frame):
	"Main user interface window"
	def __init__(self):
		super(printWindow, self).__init__(None, -1, title='Printing')
		self.machineCom = None
		self.gcode = None
		self.gcodeList = None
		self.sendList = []
		self.temp = None
		self.bedTemp = None
		self.bufferLineCount = 4
		self.sendCnt = 0
		self.feedrateRatioOuterWall = 1.0
		self.feedrateRatioInnerWall = 1.0
		self.feedrateRatioFill = 1.0
		self.feedrateRatioSupport = 1.0
		self.pause = False
		self.termHistory = []
		self.termHistoryIdx = 0
		
		self.cam = None
		if webcam.hasWebcamSupport():
			self.cam = webcam.webcam()

		#self.SetIcon(icon.getMainIcon())
		
		self.SetSizer(wx.BoxSizer())
		self.panel = wx.Panel(self)
		self.GetSizer().Add(self.panel, 1, flag=wx.EXPAND)
		self.sizer = wx.GridBagSizer(2, 2)
		self.panel.SetSizer(self.sizer)
		
		sb = wx.StaticBox(self.panel, label="Statistics")
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		self.statsText = wx.StaticText(self.panel, -1, "Filament: ####.##m #.##g\nEstimated print time: #####:##\nMachine state:\nDetecting baudrateXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
		boxsizer.Add(self.statsText, flag=wx.LEFT, border=5)
		
		self.sizer.Add(boxsizer, pos=(0,0), span=(6,1), flag=wx.EXPAND)
		
		self.connectButton = wx.Button(self.panel, -1, 'Connect')
		#self.loadButton = wx.Button(self.panel, -1, 'Load')
		self.printButton = wx.Button(self.panel, -1, 'Print')
		self.pauseButton = wx.Button(self.panel, -1, 'Pause')
		self.cancelButton = wx.Button(self.panel, -1, 'Cancel print')
		self.machineLogButton = wx.Button(self.panel, -1, 'Error log')
		self.progress = wx.Gauge(self.panel, -1)
		
		self.sizer.Add(self.connectButton, pos=(0,1))
		#self.sizer.Add(self.loadButton, pos=(1,1))
		self.sizer.Add(self.printButton, pos=(2,1))
		self.sizer.Add(self.pauseButton, pos=(3,1))
		self.sizer.Add(self.cancelButton, pos=(4,1))
		self.sizer.Add(self.machineLogButton, pos=(5,1))
		self.sizer.Add(self.progress, pos=(6,0), span=(1,7), flag=wx.EXPAND)

		nb = wx.Notebook(self.panel)
		self.sizer.Add(nb, pos=(0,3), span=(6,4), flag=wx.EXPAND)
		
		self.temperaturePanel = wx.Panel(nb)
		sizer = wx.GridBagSizer(2, 2)
		self.temperaturePanel.SetSizer(sizer)

		self.temperatureSelect = wx.SpinCtrl(self.temperaturePanel, -1, '0', size=(21*3,21), style=wx.SP_ARROW_KEYS)
		self.temperatureSelect.SetRange(0, 400)
		self.bedTemperatureLabel = wx.StaticText(self.temperaturePanel, -1, "BedTemp:")
		self.bedTemperatureSelect = wx.SpinCtrl(self.temperaturePanel, -1, '0', size=(21*3,21), style=wx.SP_ARROW_KEYS)
		self.bedTemperatureSelect.SetRange(0, 400)
		self.bedTemperatureLabel.Show(False)
		self.bedTemperatureSelect.Show(False)
		
		self.temperatureGraph = temperatureGraph(self.temperaturePanel)
		
		sizer.Add(wx.StaticText(self.temperaturePanel, -1, "Temp:"), pos=(0,0))
		sizer.Add(self.temperatureSelect, pos=(0,1))
		sizer.Add(self.bedTemperatureLabel, pos=(1,0))
		sizer.Add(self.bedTemperatureSelect, pos=(1,1))
		sizer.Add(self.temperatureGraph, pos=(2,0), span=(1,2), flag=wx.EXPAND)
		sizer.AddGrowableRow(2)
		sizer.AddGrowableCol(1)

		nb.AddPage(self.temperaturePanel, 'Temp')

		self.directControlPanel = wx.Panel(nb)
		
		sizer = wx.GridBagSizer(2, 2)
		self.directControlPanel.SetSizer(sizer)
		sizer.Add(PrintCommandButton(self, ['G91', 'G1 Y100 F6000', 'G90'], 'print-move-y100.png'), pos=(0,3))
		sizer.Add(PrintCommandButton(self, ['G91', 'G1 Y10 F6000', 'G90'], 'print-move-y10.png'), pos=(1,3))
		sizer.Add(PrintCommandButton(self, ['G91', 'G1 Y1 F6000', 'G90'], 'print-move-y1.png'), pos=(2,3))

		sizer.Add(PrintCommandButton(self, ['G91', 'G1 Y-1 F6000', 'G90'], 'print-move-y-1.png'), pos=(4,3))
		sizer.Add(PrintCommandButton(self, ['G91', 'G1 Y-10 F6000', 'G90'], 'print-move-y-10.png'), pos=(5,3))
		sizer.Add(PrintCommandButton(self, ['G91', 'G1 Y-100 F6000', 'G90'], 'print-move-y-100.png'), pos=(6,3))

		sizer.Add(PrintCommandButton(self, ['G91', 'G1 X-100 F6000', 'G90'], 'print-move-x-100.png'), pos=(3,0))
		sizer.Add(PrintCommandButton(self, ['G91', 'G1 X-10 F6000', 'G90'], 'print-move-x-10.png'), pos=(3,1))
		sizer.Add(PrintCommandButton(self, ['G91', 'G1 X-1 F6000', 'G90'], 'print-move-x-1.png'), pos=(3,2))

		sizer.Add(PrintCommandButton(self, ['G28 X0 Y0'], 'print-move-home.png'), pos=(3,3))

		sizer.Add(PrintCommandButton(self, ['G91', 'G1 X1 F6000', 'G90'], 'print-move-x1.png'), pos=(3,4))
		sizer.Add(PrintCommandButton(self, ['G91', 'G1 X10 F6000', 'G90'], 'print-move-x10.png'), pos=(3,5))
		sizer.Add(PrintCommandButton(self, ['G91', 'G1 X100 F6000', 'G90'], 'print-move-x100.png'), pos=(3,6))

		sizer.Add(PrintCommandButton(self, ['G91', 'G1 Z10 F200', 'G90'], 'print-move-z10.png'), pos=(0,8))
		sizer.Add(PrintCommandButton(self, ['G91', 'G1 Z1 F200', 'G90'], 'print-move-z1.png'), pos=(1,8))
		sizer.Add(PrintCommandButton(self, ['G91', 'G1 Z0.1 F200', 'G90'], 'print-move-z0.1.png'), pos=(2,8))

		sizer.Add(PrintCommandButton(self, ['G28 Z0'], 'print-move-home.png'), pos=(3,8))

		sizer.Add(PrintCommandButton(self, ['G91', 'G1 Z-0.1 F200', 'G90'], 'print-move-z-0.1.png'), pos=(4,8))
		sizer.Add(PrintCommandButton(self, ['G91', 'G1 Z-1 F200', 'G90'], 'print-move-z-1.png'), pos=(5,8))
		sizer.Add(PrintCommandButton(self, ['G91', 'G1 Z-10 F200', 'G90'], 'print-move-z-10.png'), pos=(6,8))

		sizer.Add(PrintCommandButton(self, ['G92 E0', 'G1 E2 F120'], 'extrude.png', size=(60,20)), pos=(1,10), span=(1,3), flag=wx.EXPAND)
		sizer.Add(PrintCommandButton(self, ['G92 E0', 'G1 E-2 F120'], 'retract.png', size=(60,20)), pos=(2,10), span=(1,3), flag=wx.EXPAND)

		nb.AddPage(self.directControlPanel, 'Jog')

		self.speedPanel = wx.Panel(nb)
		sizer = wx.GridBagSizer(2, 2)
		self.speedPanel.SetSizer(sizer)

		self.outerWallSpeedSelect = wx.SpinCtrl(self.speedPanel, -1, '100', size=(21*3,21), style=wx.SP_ARROW_KEYS)
		self.outerWallSpeedSelect.SetRange(5, 1000)
		self.innerWallSpeedSelect = wx.SpinCtrl(self.speedPanel, -1, '100', size=(21*3,21), style=wx.SP_ARROW_KEYS)
		self.innerWallSpeedSelect.SetRange(5, 1000)
		self.fillSpeedSelect = wx.SpinCtrl(self.speedPanel, -1, '100', size=(21*3,21), style=wx.SP_ARROW_KEYS)
		self.fillSpeedSelect.SetRange(5, 1000)
		self.supportSpeedSelect = wx.SpinCtrl(self.speedPanel, -1, '100', size=(21*3,21), style=wx.SP_ARROW_KEYS)
		self.supportSpeedSelect.SetRange(5, 1000)
		
		sizer.Add(wx.StaticText(self.speedPanel, -1, "Outer wall:"), pos=(0,0))
		sizer.Add(self.outerWallSpeedSelect, pos=(0,1))
		sizer.Add(wx.StaticText(self.speedPanel, -1, "%"), pos=(0,2))
		sizer.Add(wx.StaticText(self.speedPanel, -1, "Inner wall:"), pos=(1,0))
		sizer.Add(self.innerWallSpeedSelect, pos=(1,1))
		sizer.Add(wx.StaticText(self.speedPanel, -1, "%"), pos=(1,2))
		sizer.Add(wx.StaticText(self.speedPanel, -1, "Fill:"), pos=(2,0))
		sizer.Add(self.fillSpeedSelect, pos=(2,1))
		sizer.Add(wx.StaticText(self.speedPanel, -1, "%"), pos=(2,2))
		sizer.Add(wx.StaticText(self.speedPanel, -1, "Support:"), pos=(3,0))
		sizer.Add(self.supportSpeedSelect, pos=(3,1))
		sizer.Add(wx.StaticText(self.speedPanel, -1, "%"), pos=(3,2))

		nb.AddPage(self.speedPanel, 'Speed')
		
		self.termPanel = wx.Panel(nb)
		sizer = wx.GridBagSizer(2, 2)
		self.termPanel.SetSizer(sizer)
		
		f = wx.Font(8, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False)
		self.termLog = wx.TextCtrl(self.termPanel, style=wx.TE_MULTILINE|wx.TE_DONTWRAP)
		self.termLog.SetFont(f)
		self.termLog.SetEditable(0)
		self.termInput = wx.TextCtrl(self.termPanel, style=wx.TE_PROCESS_ENTER)
		self.termInput.SetFont(f)

		sizer.Add(self.termLog, pos=(0,0),flag=wx.EXPAND)
		sizer.Add(self.termInput, pos=(1,0),flag=wx.EXPAND)
		sizer.AddGrowableCol(0)
		sizer.AddGrowableRow(0)

		nb.AddPage(self.termPanel, 'Term')
		
		if self.cam != None and self.cam.hasCamera():
			self.camPage = wx.Panel(nb)
			sizer = wx.GridBagSizer(2, 2)
			self.camPage.SetSizer(sizer)
			
			self.timelapsEnable = wx.CheckBox(self.camPage, -1, 'Enable timelaps movie recording')
			sizer.Add(self.timelapsEnable, pos=(0,0), span=(1,2), flag=wx.EXPAND)
			
			pages = self.cam.propertyPages()
			self.cam.buttons = [self.timelapsEnable]
			for page in pages:
				button = wx.Button(self.camPage, -1, page)
				button.index = pages.index(page)
				sizer.Add(button, pos=(1, pages.index(page)))
				button.Bind(wx.EVT_BUTTON, self.OnPropertyPageButton)
				self.cam.buttons.append(button)

			self.campreviewEnable = wx.CheckBox(self.camPage, -1, 'Show preview')
			sizer.Add(self.campreviewEnable, pos=(2,0), span=(1,2), flag=wx.EXPAND)
			
			self.camPreview = wx.Panel(self.camPage)
			sizer.Add(self.camPreview, pos=(3,0), span=(1,2), flag=wx.EXPAND)
			
			nb.AddPage(self.camPage, 'Camera')
			self.camPreview.timer = wx.Timer(self)
			self.Bind(wx.EVT_TIMER, self.OnCameraTimer, self.camPreview.timer)
			self.camPreview.timer.Start(500)
			self.camPreview.Bind(wx.EVT_ERASE_BACKGROUND, self.OnCameraEraseBackground)

		self.sizer.AddGrowableRow(5)
		self.sizer.AddGrowableCol(3)
		
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		self.connectButton.Bind(wx.EVT_BUTTON, self.OnConnect)
		#self.loadButton.Bind(wx.EVT_BUTTON, self.OnLoad)
		self.printButton.Bind(wx.EVT_BUTTON, self.OnPrint)
		self.pauseButton.Bind(wx.EVT_BUTTON, self.OnPause)
		self.cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)
		self.machineLogButton.Bind(wx.EVT_BUTTON, self.OnMachineLog)
		
		self.Bind(wx.EVT_SPINCTRL, self.OnTempChange, self.temperatureSelect)
		self.Bind(wx.EVT_SPINCTRL, self.OnBedTempChange, self.bedTemperatureSelect)

		self.Bind(wx.EVT_SPINCTRL, self.OnSpeedChange, self.outerWallSpeedSelect)
		self.Bind(wx.EVT_SPINCTRL, self.OnSpeedChange, self.innerWallSpeedSelect)
		self.Bind(wx.EVT_SPINCTRL, self.OnSpeedChange, self.fillSpeedSelect)
		self.Bind(wx.EVT_SPINCTRL, self.OnSpeedChange, self.supportSpeedSelect)
		self.Bind(wx.EVT_TEXT_ENTER, self.OnTermEnterLine, self.termInput)
		self.termInput.Bind(wx.EVT_CHAR, self.OnTermKey)
		
		self.Layout()
		self.Fit()
		self.Centre()
		
		self.statsText.SetMinSize(self.statsText.GetSize())

		self.UpdateButtonStates()
		#self.UpdateProgress()
	
	def OnCameraTimer(self, e):
		if not self.campreviewEnable.GetValue():
			return
		if self.machineCom != None and self.machineCom.isPrinting():
			return
		self.cam.takeNewImage()
		self.camPreview.Refresh()
	
	def OnCameraEraseBackground(self, e):
		dc = e.GetDC()
		if not dc:
			dc = wx.ClientDC(self)
			rect = self.GetUpdateRegion().GetBox()
			dc.SetClippingRect(rect)
		dc.SetBackground(wx.Brush(self.camPreview.GetBackgroundColour(), wx.SOLID))
		if self.cam.getLastImage() != None:
			self.camPreview.SetMinSize((self.cam.getLastImage().GetWidth(), self.cam.getLastImage().GetHeight()))
			self.camPage.Fit()
			dc.DrawBitmap(self.cam.getLastImage(), 0, 0)
		else:
			dc.Clear()
		
	def OnPropertyPageButton(self, e):
		self.cam.openPropertyPage(e.GetEventObject().index)

	def UpdateButtonStates(self):
		self.connectButton.Enable(self.machineCom == None or self.machineCom.isClosedOrError())
		#self.loadButton.Enable(self.machineCom == None or not (self.machineCom.isPrinting() or self.machineCom.isPaused()))
		self.printButton.Enable(self.machineCom != None and self.machineCom.isOperational() and not (self.machineCom.isPrinting() or self.machineCom.isPaused()))
		self.pauseButton.Enable(self.machineCom != None and (self.machineCom.isPrinting() or self.machineCom.isPaused()))
		if self.machineCom != None and self.machineCom.isPaused():
			self.pauseButton.SetLabel('Resume')
		else:
			self.pauseButton.SetLabel('Pause')
		self.cancelButton.Enable(self.machineCom != None and (self.machineCom.isPrinting() or self.machineCom.isPaused()))
		self.temperatureSelect.Enable(self.machineCom != None and self.machineCom.isOperational())
		self.bedTemperatureSelect.Enable(self.machineCom != None and self.machineCom.isOperational())
		self.directControlPanel.Enable(self.machineCom != None and self.machineCom.isOperational() and not self.machineCom.isPrinting())
		self.machineLogButton.Show(self.machineCom != None and self.machineCom.isError())
		if self.cam:
			for button in self.cam.buttons:
				button.Enable(self.machineCom == None or not self.machineCom.isPrinting())
	
	def UpdateProgress(self):
		status = ""
		if self.gcode == None:
			status += "Loading gcode...\n"
		else:
			status += "Filament: %.2fm %.2fg\n" % (self.gcode.extrusionAmount / 1000, self.gcode.calculateWeight() * 1000)
			cost = self.gcode.calculateCost()
			if cost != False:
				status += "Filament cost: %s\n" % (cost)
			status += "Estimated print time: %02d:%02d\n" % (int(self.gcode.totalMoveTimeMinute / 60), int(self.gcode.totalMoveTimeMinute % 60))
		if self.machineCom == None or not self.machineCom.isPrinting():
			self.progress.SetValue(0)
			if self.gcodeList != None:
				status += 'Line: -/%d\n' % (len(self.gcodeList))
		else:
			printTime = self.machineCom.getPrintTime() / 60
			printTimeLeft = self.machineCom.getPrintTimeRemainingEstimate()
			status += 'Line: %d/%d %d%%\n' % (self.machineCom.getPrintPos(), len(self.gcodeList), self.machineCom.getPrintPos() * 100 / len(self.gcodeList))
			if self.currentZ > 0:
				status += 'Height: %0.1f\n' % (self.currentZ)
			status += 'Print time: %02d:%02d\n' % (int(printTime / 60), int(printTime % 60))
			if printTimeLeft == None:
				status += 'Print time left: Unknown\n'
			else:
				status += 'Print time left: %02d:%02d\n' % (int(printTimeLeft / 60), int(printTimeLeft % 60))
			self.progress.SetValue(self.machineCom.getPrintPos())
			taskbar.setProgress(self, self.machineCom.getPrintPos(), len(self.gcodeList))
		if self.machineCom != None:
			if self.machineCom.getTemp() > 0:
				status += 'Temp: %d\n' % (self.machineCom.getTemp())
			if self.machineCom.getBedTemp() > 0:
				status += 'Bed Temp: %d\n' % (self.machineCom.getBedTemp())
				self.bedTemperatureLabel.Show(True)
				self.bedTemperatureSelect.Show(True)
				self.temperaturePanel.Layout()
			status += 'Machine state:%s\n' % (self.machineCom.getStateString())
		
		self.statsText.SetLabel(status.strip())
	
	def OnConnect(self, e):
		if self.machineCom != None:
			self.machineCom.close()
		self.machineCom = machineCom.MachineCom(callbackObject=self)
		self.UpdateButtonStates()
		taskbar.setBusy(self, True)
	
	def OnLoad(self, e):
		pass
	
	def OnPrint(self, e):
		if self.machineCom == None or not self.machineCom.isOperational():
			return
		if self.gcodeList == None:
			return
		if self.machineCom.isPrinting():
			return
		self.currentZ = -1
		if self.cam != None and self.timelapsEnable.GetValue():
			self.cam.startTimelaps(self.filename[: self.filename.rfind('.')] + ".mpg")
		self.machineCom.printGCode(self.gcodeList)
		self.UpdateButtonStates()
	
	def OnCancel(self, e):
		self.pauseButton.SetLabel('Pause')
		self.machineCom.cancelPrint()
		self.machineCom.sendCommand("M84")
		self.UpdateButtonStates()
	
	def OnPause(self, e):
		if self.machineCom.isPaused():
			self.machineCom.setPause(False)
		else:
			self.machineCom.setPause(True)
	
	def OnMachineLog(self, e):
		LogWindow('\n'.join(self.machineCom.getLog()))
	
	def OnClose(self, e):
		global printWindowHandle
		printWindowHandle = None
		if self.machineCom != None:
			self.machineCom.close()
		self.Destroy()

	def OnTempChange(self, e):
		self.machineCom.sendCommand("M104 S%d" % (self.temperatureSelect.GetValue()))

	def OnBedTempChange(self, e):
		self.machineCom.sendCommand("M140 S%d" % (self.bedTemperatureSelect.GetValue()))
	
	def OnSpeedChange(self, e):
		if self.machineCom == None:
			return
		self.machineCom.setFeedrateModifier('WALL-OUTER', self.outerWallSpeedSelect.GetValue() / 100.0)
		self.machineCom.setFeedrateModifier('WALL-INNER', self.innerWallSpeedSelect.GetValue() / 100.0)
		self.machineCom.setFeedrateModifier('FILL', self.fillSpeedSelect.GetValue() / 100.0)
		self.machineCom.setFeedrateModifier('SUPPORT', self.supportSpeedSelect.GetValue() / 100.0)
	
	def AddTermLog(self, line):
		self.termLog.AppendText(unicode(line, 'utf-8', 'replace'))
		l = len(self.termLog.GetValue())
		self.termLog.SetCaret(wx.Caret(self.termLog, (l, l)))
	
	def OnTermEnterLine(self, e):
		line = self.termInput.GetValue()
		if line == '':
			return
		self.termLog.AppendText('>%s\n' % (line))
		self.machineCom.sendCommand(line)
		self.termHistory.append(line)
		self.termHistoryIdx = len(self.termHistory)
		self.termInput.SetValue('')

	def OnTermKey(self, e):
		if len(self.termHistory) > 0:
			if e.GetKeyCode() == wx.WXK_UP:
				self.termHistoryIdx = self.termHistoryIdx - 1
				if self.termHistoryIdx < 0:
					self.termHistoryIdx = len(self.termHistory) - 1
				self.termInput.SetValue(self.termHistory[self.termHistoryIdx])
			if e.GetKeyCode() == wx.WXK_DOWN:
				self.termHistoryIdx = self.termHistoryIdx - 1
				if self.termHistoryIdx >= len(self.termHistory):
					self.termHistoryIdx = 0
				self.termInput.SetValue(self.termHistory[self.termHistoryIdx])
		e.Skip()

	def LoadGCodeFile(self, filename):
		if self.machineCom != None and self.machineCom.isPrinting():
			return
		#Send an initial M110 to reset the line counter to zero.
		prevLineType = lineType = 'CUSTOM'
		gcodeList = ["M110"]
		for line in open(filename, 'r'):
			if line.startswith(';TYPE:'):
				lineType = line[6:].strip()
			if ';' in line:
				line = line[0:line.find(';')]
			line = line.strip()
			if len(line) > 0:
				if prevLineType != lineType:
					gcodeList.append((line, lineType, ))
				else:
					gcodeList.append(line)
				prevLineType = lineType
		gcode = gcodeInterpreter.gcode()
		gcode.loadList(gcodeList)
		#print "Loaded: %s (%d)" % (filename, len(gcodeList))
		self.filename = filename
		self.gcode = gcode
		self.gcodeList = gcodeList
		
		wx.CallAfter(self.progress.SetRange, len(gcodeList))
		wx.CallAfter(self.UpdateButtonStates)
		wx.CallAfter(self.UpdateProgress)
		wx.CallAfter(self.SetTitle, 'Printing: %s' % (filename))
		
	def sendLine(self, lineNr):
		if lineNr >= len(self.gcodeList):
			return False
		line = self.gcodeList[lineNr]
		try:
			if ('M104' in line or 'M109' in line) and 'S' in line:
				n = int(re.search('S([0-9]*)', line).group(1))
				wx.CallAfter(self.temperatureSelect.SetValue, n)
			if ('M140' in line or 'M190' in line) and 'S' in line:
				n = int(re.search('S([0-9]*)', line).group(1))
				wx.CallAfter(self.bedTemperatureSelect.SetValue, n)
		except:
			print "Unexpected error:", sys.exc_info()
		checksum = reduce(lambda x,y:x^y, map(ord, "N%d%s" % (lineNr, line)))
		self.machineCom.sendCommand("N%d%s*%d" % (lineNr, line, checksum))
		return True

	def mcLog(self, message):
		#print message
		pass
	
	def mcTempUpdate(self, temp, bedTemp, targetTemp, bedTargetTemp):
		self.temperatureGraph.addPoint(temp, targetTemp, bedTemp, bedTargetTemp)
		if self.temperatureSelect.GetValue() != targetTemp:
			wx.CallAfter(self.temperatureSelect.SetValue, targetTemp)
		if self.bedTemperatureSelect.GetValue() != bedTargetTemp:
			wx.CallAfter(self.bedTemperatureSelect.SetValue, bedTargetTemp)
	
	def mcStateChange(self, state):
		if self.machineCom != None:
			if state == self.machineCom.STATE_OPERATIONAL and self.cam != None:
				self.cam.endTimelaps()
			if state == self.machineCom.STATE_OPERATIONAL:
				taskbar.setBusy(self, False)
			if self.machineCom.isClosedOrError():
				taskbar.setBusy(self, False)
			if self.machineCom.isPaused():
				taskbar.setPause(self, True)
		wx.CallAfter(self.UpdateButtonStates)
		wx.CallAfter(self.UpdateProgress)
	
	def mcMessage(self, message):
		wx.CallAfter(self.AddTermLog, message)
	
	def mcProgress(self, lineNr):
		wx.CallAfter(self.UpdateProgress)
	
	def mcZChange(self, newZ):
		self.currentZ = newZ
		if self.cam != None:
			wx.CallAfter(self.cam.takeNewImage)
			wx.CallAfter(self.camPreview.Refresh)

class temperatureGraph(wx.Panel):
	def __init__(self, parent):
		super(temperatureGraph, self).__init__(parent)
		
		self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
		self.Bind(wx.EVT_SIZE, self.OnSize)
		self.Bind(wx.EVT_PAINT, self.OnDraw)
		
		self.lastDraw = time.time() - 1.0
		self.points = []
		self.backBuffer = None
		self.addPoint(0,0,0,0)
		self.SetMinSize((320,200))
	
	def OnEraseBackground(self, e):
		pass
	
	def OnSize(self, e):
		if self.backBuffer == None or self.GetSize() != self.backBuffer.GetSize():
			self.backBuffer = wx.EmptyBitmap(*self.GetSizeTuple())
			self.UpdateDrawing(True)
	
	def OnDraw(self, e):
		dc = wx.BufferedPaintDC(self, self.backBuffer)
	
	def UpdateDrawing(self, force = False):
		now = time.time()
		if not force and now - self.lastDraw < 1.0:
			return
		self.lastDraw = now
		dc = wx.MemoryDC()
		dc.SelectObject(self.backBuffer)
		dc.Clear()
		w, h = self.GetSizeTuple()
		bgLinePen = wx.Pen('#A0A0A0')
		tempPen = wx.Pen('#FF4040')
		tempSPPen = wx.Pen('#FFA0A0')
		tempPenBG = wx.Pen('#FFD0D0')
		bedTempPen = wx.Pen('#4040FF')
		bedTempSPPen = wx.Pen('#A0A0FF')
		bedTempPenBG = wx.Pen('#D0D0FF')

		#Draw the background up to the current temperatures.
		x0 = 0
		t0 = 0
		bt0 = 0
		tSP0 = 0
		btSP0 = 0
		for temp, tempSP, bedTemp, bedTempSP, t in self.points:
			x1 = int(w - (now - t))
			for x in xrange(x0, x1 + 1):
				t = float(x - x0) / float(x1 - x0 + 1) * (temp - t0) + t0
				bt = float(x - x0) / float(x1 - x0 + 1) * (bedTemp - bt0) + bt0
				dc.SetPen(tempPenBG)
				dc.DrawLine(x, h, x, h - (t * h / 300))
				dc.SetPen(bedTempPenBG)
				dc.DrawLine(x, h, x, h - (bt * h / 300))
			t0 = temp
			bt0 = bedTemp
			tSP0 = tempSP
			btSP0 = bedTempSP
			x0 = x1 + 1

		#Draw the grid
		for x in xrange(w, 0, -30):
			dc.SetPen(bgLinePen)
			dc.DrawLine(x, 0, x, h)
		for y in xrange(h-1, 0, -h * 50 / 300):
			dc.SetPen(bgLinePen)
			dc.DrawLine(0, y, w, y)
		dc.DrawLine(0, 0, w, 0)
		dc.DrawLine(0, 0, 0, h)
		
		#Draw the main lines
		x0 = 0
		t0 = 0
		bt0 = 0
		tSP0 = 0
		btSP0 = 0
		for temp, tempSP, bedTemp, bedTempSP, t in self.points:
			x1 = int(w - (now - t))
			for x in xrange(x0, x1 + 1):
				t = float(x - x0) / float(x1 - x0 + 1) * (temp - t0) + t0
				bt = float(x - x0) / float(x1 - x0 + 1) * (bedTemp - bt0) + bt0
				tSP = float(x - x0) / float(x1 - x0 + 1) * (tempSP - tSP0) + tSP0
				btSP = float(x - x0) / float(x1 - x0 + 1) * (bedTempSP - btSP0) + btSP0
				dc.SetPen(tempSPPen)
				dc.DrawPoint(x, h - (tSP * h / 300))
				dc.SetPen(bedTempSPPen)
				dc.DrawPoint(x, h - (btSP * h / 300))
				dc.SetPen(tempPen)
				dc.DrawPoint(x, h - (t * h / 300))
				dc.SetPen(bedTempPen)
				dc.DrawPoint(x, h - (bt * h / 300))
			t0 = temp
			bt0 = bedTemp
			tSP0 = tempSP
			btSP0 = bedTempSP
			x0 = x1 + 1
		
		del dc
		self.Refresh(eraseBackground=False)
		self.Update()
		
		if len(self.points) > 0 and (time.time() - self.points[0][4]) > w + 20:
			self.points.pop(0)

	def addPoint(self, temp, tempSP, bedTemp, bedTempSP):
		if bedTemp == None:
			bedTemp = 0
		if bedTempSP == None:
			bedTempSP = 0
		self.points.append((temp, tempSP, bedTemp, bedTempSP, time.time()))
		wx.CallAfter(self.UpdateDrawing)

class LogWindow(wx.Frame):
	def __init__(self, logText):
		super(LogWindow, self).__init__(None, title="Machine log")
		self.textBox = wx.TextCtrl(self, -1, logText, style=wx.TE_MULTILINE|wx.TE_DONTWRAP|wx.TE_READONLY)
		self.SetSize((500,400))
		self.Centre()
		self.Show(True)
