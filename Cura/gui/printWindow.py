from __future__ import absolute_import
import __init__

import wx, threading, re, subprocess, sys, os, time
from wx.lib import buttons

from gui import icon
from gui import toolbarUtil
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
			self.handle = subprocess.Popen([sys.executable, sys.argv[0], '-r', filename], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			self.thread = threading.Thread(target=self.Monitor)
			self.thread.start()
		else:
			self.handle.stdin.write(filename + '\n')
	
	def Monitor(self):
		p = self.handle
		line = p.stdout.readline()
		while(len(line) > 0):
			print line.rstrip()
			line = p.stdout.readline()
		p.wait()
		self.handle = None
		self.thread = None

class PrintCommandButton(buttons.GenBitmapButton):
	def __init__(self, parent, command, bitmapFilename, size=(20,20)):
		self.bitmap = toolbarUtil.getBitmapImage(bitmapFilename)
		super(PrintCommandButton, self).__init__(parent.directControlPanel, -1, self.bitmap, size=size)

		self.command = command
		self.parent = parent

		self.SetBezelWidth(1)
		self.SetUseFocusIndicator(False)

		self.Bind(wx.EVT_BUTTON, self.OnClick)

	def OnClick(self, e):
		self.parent.sendCommand("G91")
		self.parent.sendCommand(self.command)
		self.parent.sendCommand("G90")
		e.Skip()

class printWindow(wx.Frame):
	"Main user interface window"
	def __init__(self):
		super(printWindow, self).__init__(None, -1, title='Printing')
		self.machineCom = None
		self.machineConnected = False
		self.thread = None
		self.gcode = None
		self.gcodeList = None
		self.sendList = []
		self.printIdx = None
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

		#self.SetIcon(icon.getMainIcon())
		
		self.SetSizer(wx.BoxSizer())
		self.panel = wx.Panel(self)
		self.GetSizer().Add(self.panel, 1, flag=wx.EXPAND)
		self.sizer = wx.GridBagSizer(2, 2)
		self.panel.SetSizer(self.sizer)
		
		sb = wx.StaticBox(self.panel, label="Statistics")
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		self.statsText = wx.StaticText(self.panel, -1, "Filament: ####.##m #.##g\nPrint time: #####:##")
		boxsizer.Add(self.statsText, flag=wx.LEFT, border=5)
		
		self.sizer.Add(boxsizer, pos=(0,0), span=(5,1), flag=wx.EXPAND)
		
		self.connectButton = wx.Button(self.panel, -1, 'Connect')
		#self.loadButton = wx.Button(self.panel, -1, 'Load GCode')
		self.printButton = wx.Button(self.panel, -1, 'Print GCode')
		self.pauseButton = wx.Button(self.panel, -1, 'Pause')
		self.cancelButton = wx.Button(self.panel, -1, 'Cancel print')
		self.progress = wx.Gauge(self.panel, -1)
		
		self.sizer.Add(self.connectButton, pos=(0,1))
		#self.sizer.Add(self.loadButton, pos=(1,1))
		self.sizer.Add(self.printButton, pos=(2,1))
		self.sizer.Add(self.pauseButton, pos=(3,1))
		self.sizer.Add(self.cancelButton, pos=(4,1))
		self.sizer.Add(self.progress, pos=(5,0), span=(1,2), flag=wx.EXPAND)

		nb = wx.Notebook(self.panel)
		self.sizer.Add(nb, pos=(0,3), span=(7,4))
		
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
		sizer.AddGrowableCol(0)

		nb.AddPage(self.temperaturePanel, 'Temp')

		self.directControlPanel = wx.Panel(nb)
		
		sizer = wx.GridBagSizer(2, 2)
		self.directControlPanel.SetSizer(sizer)
		sizer.Add(PrintCommandButton(self, 'G1 Y100 F6000', 'print-move-y100.png'), pos=(0,3))
		sizer.Add(PrintCommandButton(self, 'G1 Y10 F6000', 'print-move-y10.png'), pos=(1,3))
		sizer.Add(PrintCommandButton(self, 'G1 Y1 F6000', 'print-move-y1.png'), pos=(2,3))

		sizer.Add(PrintCommandButton(self, 'G1 Y-1 F6000', 'print-move-y-1.png'), pos=(4,3))
		sizer.Add(PrintCommandButton(self, 'G1 Y-10 F6000', 'print-move-y-10.png'), pos=(5,3))
		sizer.Add(PrintCommandButton(self, 'G1 Y-100 F6000', 'print-move-y-100.png'), pos=(6,3))

		sizer.Add(PrintCommandButton(self, 'G1 X-100 F6000', 'print-move-x-100.png'), pos=(3,0))
		sizer.Add(PrintCommandButton(self, 'G1 X-10 F6000', 'print-move-x-10.png'), pos=(3,1))
		sizer.Add(PrintCommandButton(self, 'G1 X-1 F6000', 'print-move-x-1.png'), pos=(3,2))

		sizer.Add(PrintCommandButton(self, 'G28 X0 Y0', 'print-move-home.png'), pos=(3,3))

		sizer.Add(PrintCommandButton(self, 'G1 X1 F6000', 'print-move-x1.png'), pos=(3,4))
		sizer.Add(PrintCommandButton(self, 'G1 X10 F6000', 'print-move-x10.png'), pos=(3,5))
		sizer.Add(PrintCommandButton(self, 'G1 X100 F6000', 'print-move-x100.png'), pos=(3,6))

		sizer.Add(PrintCommandButton(self, 'G1 Z10 F200', 'print-move-z10.png'), pos=(0,7))
		sizer.Add(PrintCommandButton(self, 'G1 Z1 F200', 'print-move-z1.png'), pos=(1,7))
		sizer.Add(PrintCommandButton(self, 'G1 Z0.1 F200', 'print-move-z0.1.png'), pos=(2,7))

		sizer.Add(PrintCommandButton(self, 'G28 Z0', 'print-move-home.png'), pos=(3,7))

		sizer.Add(PrintCommandButton(self, 'G1 Z-0.1 F200', 'print-move-z-0.1.png'), pos=(4,7))
		sizer.Add(PrintCommandButton(self, 'G1 Z-1 F200', 'print-move-z-1.png'), pos=(5,7))
		sizer.Add(PrintCommandButton(self, 'G1 Z-10 F200', 'print-move-z-10.png'), pos=(6,7))

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

		self.sizer.AddGrowableRow(3)
		self.sizer.AddGrowableCol(0)
		
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		self.connectButton.Bind(wx.EVT_BUTTON, self.OnConnect)
		#self.loadButton.Bind(wx.EVT_BUTTON, self.OnLoad)
		self.printButton.Bind(wx.EVT_BUTTON, self.OnPrint)
		self.pauseButton.Bind(wx.EVT_BUTTON, self.OnPause)
		self.cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)
		
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

		self.UpdateButtonStates()
		self.UpdateProgress()
	
	def UpdateButtonStates(self):
		self.connectButton.Enable(not self.machineConnected)
		#self.loadButton.Enable(self.printIdx == None)
		self.printButton.Enable(self.machineConnected and self.gcodeList != None and self.printIdx == None)
		self.pauseButton.Enable(self.printIdx != None)
		self.cancelButton.Enable(self.printIdx != None)
		self.temperatureSelect.Enable(self.machineConnected)
		self.bedTemperatureSelect.Enable(self.machineConnected)
		self.directControlPanel.Enable(self.machineConnected)
	
	def UpdateProgress(self):
		status = ""
		if self.gcode == None:
			status += "Loading gcode...\n"
		else:
			status += "Filament: %.2fm %.2fg\n" % (self.gcode.extrusionAmount / 1000, self.gcode.calculateWeight() * 1000)
			cost = self.gcode.calculateCost()
			if cost != False:
				status += "Filament cost: %s\n" % (cost)
			status += "Print time: %02d:%02d\n" % (int(self.gcode.totalMoveTimeMinute / 60), int(self.gcode.totalMoveTimeMinute % 60))
		if self.printIdx == None:
			self.progress.SetValue(0)
			if self.gcodeList != None:
				status += 'Line: -/%d\n' % (len(self.gcodeList))
		else:
			status += 'Line: %d/%d\n' % (self.printIdx, len(self.gcodeList))
			self.progress.SetValue(self.printIdx)
		if self.temp != None:
			status += 'Temp: %d\n' % (self.temp)
		if self.bedTemp != None and self.bedTemp > 0:
			status += 'Bed Temp: %d\n' % (self.bedTemp)
			self.bedTemperatureLabel.Show(True)
			self.bedTemperatureSelect.Show(True)
			self.temperaturePanel.Layout()
		self.statsText.SetLabel(status.strip())
		#self.Layout()
	
	def OnConnect(self, e):
		if self.machineCom != None:
			self.machineCom.close()
			self.thread.join()
		self.machineCom = machineCom.MachineCom()
		self.thread = threading.Thread(target=self.PrinterMonitor)
		self.thread.start()
		self.UpdateButtonStates()
	
	def OnLoad(self, e):
		pass
	
	def OnPrint(self, e):
		if not self.machineConnected:
			return
		if self.gcodeList == None:
			return
		if self.printIdx != None:
			return
		self.printIdx = 1
		self.sendLine(0)
		self.sendCnt = self.bufferLineCount
		self.UpdateButtonStates()
	
	def OnCancel(self, e):
		self.printIdx = None
		self.pause = False
		self.pauseButton.SetLabel('Pause')
		self.sendCommand("M84")
		self.UpdateButtonStates()
	
	def OnPause(self, e):
		if self.pause:
			self.pause = False
			self.sendLine(self.printIdx)
			self.printIdx += 1
			self.pauseButton.SetLabel('Pause')
		else:
			self.pause = True
			self.pauseButton.SetLabel('Resume')
	
	def OnClose(self, e):
		global printWindowHandle
		printWindowHandle = None
		if self.machineCom != None:
			self.machineCom.close()
			self.thread.join()
		self.Destroy()

	def OnTempChange(self, e):
		self.sendCommand("M104 S%d" % (self.temperatureSelect.GetValue()))

	def OnBedTempChange(self, e):
		self.sendCommand("M140 S%d" % (self.bedTemperatureSelect.GetValue()))
	
	def OnSpeedChange(self, e):
		self.feedrateRatioOuterWall = self.outerWallSpeedSelect.GetValue() / 100.0
		self.feedrateRatioInnerWall = self.innerWallSpeedSelect.GetValue() / 100.0
		self.feedrateRatioFill = self.fillSpeedSelect.GetValue() / 100.0
		self.feedrateRatioSupport = self.supportSpeedSelect.GetValue() / 100.0
	
	def AddTermLog(self, line):
		self.termLog.AppendText(line)
	
	def OnTermEnterLine(self, e):
		line = self.termInput.GetValue()
		if line == '':
			return
		self.termLog.AppendText('>%s\n' % (line))
		self.sendCommand(line)
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
		if self.printIdx != None:
			return
		#Send an initial M110 to reset the line counter to zero.
		lineType = 'CUSTOM'
		gcodeList = ["M110"]
		typeList = [lineType]
		for line in open(filename, 'r'):
			if line.startswith(';TYPE:'):
				lineType = line[6:].strip()
			if ';' in line:
				line = line[0:line.find(';')]
			line = line.strip()
			if len(line) > 0:
				gcodeList.append(line)
				typeList.append(lineType)
		gcode = gcodeInterpreter.gcode()
		gcode.loadList(gcodeList)
		print "Loaded: %s (%d)" % (filename, len(gcodeList))
		self.gcode = gcode
		self.gcodeList = gcodeList
		self.typeList = typeList
		
		wx.CallAfter(self.progress.SetRange, len(gcodeList))
		wx.CallAfter(self.UpdateButtonStates)
		wx.CallAfter(self.UpdateProgress)
		
	def sendCommand(self, cmd):
		if self.machineConnected:
			if self.printIdx == None or self.pause:
				self.machineCom.sendCommand(cmd)
			else:
				self.sendList.append(cmd)

	def sendLine(self, lineNr):
		if lineNr >= len(self.gcodeList):
			return False
		line = self.gcodeList[lineNr]
		try:
			if line == 'M0' or line == 'M1':
				self.OnPause(None)
				line = 'M105'
			if ('M104' in line or 'M109' in line) and 'S' in line:
				n = int(re.search('S([0-9]*)', line).group(1))
				wx.CallAfter(self.temperatureSelect.SetValue, n)
			if ('M140' in line or 'M190' in line) and 'S' in line:
				n = int(re.search('S([0-9]*)', line).group(1))
				wx.CallAfter(self.bedTemperatureSelect.SetValue, n)
			if self.typeList[lineNr] == 'WALL-OUTER':
				line = re.sub('F([0-9]*)', lambda m: 'F' + str(int(int(m.group(1)) * self.feedrateRatioOuterWall)), line)
			if self.typeList[lineNr] == 'WALL-INNER':
				line = re.sub('F([0-9]*)', lambda m: 'F' + str(int(int(m.group(1)) * self.feedrateRatioInnerWall)), line)
			if self.typeList[lineNr] == 'FILL':
				line = re.sub('F([0-9]*)', lambda m: 'F' + str(int(int(m.group(1)) * self.feedrateRatioFill)), line)
			if self.typeList[lineNr] == 'SUPPORT':
				line = re.sub('F([0-9]*)', lambda m: 'F' + str(int(int(m.group(1)) * self.feedrateRatioSupport)), line)
		except:
			print "Unexpected error:", sys.exc_info()
		checksum = reduce(lambda x,y:x^y, map(ord, "N%d%s" % (lineNr, line)))
		self.machineCom.sendCommand("N%d%s*%d" % (lineNr, line, checksum))
		return True

	def PrinterMonitor(self):
		while True:
			line = self.machineCom.readline()
			if line == None:
				self.machineConnected = False
				wx.CallAfter(self.UpdateButtonStates)
				return
			if line == '':	#When we have a communication "timeout" and we're not sending gcode, then read the temperature.
				if self.printIdx == None or self.pause:
					self.machineCom.sendCommand("M105")
				else:
					wx.CallAfter(self.AddTermLog, '!!Comm timeout, forcing next line!!\n')
					line = 'ok'
			if self.machineConnected:
				while self.sendCnt > 0 and not self.pause:
					self.sendLine(self.printIdx)
					self.printIdx += 1
					self.sendCnt -= 1
			if line.startswith("start"):
				self.machineConnected = True
				wx.CallAfter(self.UpdateButtonStates)
			elif 'T:' in line:
				self.temp = float(re.search("[0-9\.]*", line.split('T:')[1]).group(0))
				if 'B:' in line:
					self.bedTemp = float(re.search("[0-9\.]*", line.split('B:')[1]).group(0))
				self.temperatureGraph.addPoint(self.temp, self.temperatureSelect.GetValue(), self.bedTemp, self.bedTemperatureSelect.GetValue())
				wx.CallAfter(self.UpdateProgress)
			elif line.strip() != 'ok':
				wx.CallAfter(self.AddTermLog, line)
			if self.printIdx != None:
				if line.startswith("ok"):
					if len(self.sendList) > 0:
						self.machineCom.sendCommand(self.sendList.pop(0))
					elif self.pause:
						self.sendCnt += 1
					else:
						if self.sendLine(self.printIdx):
							self.printIdx += 1
						else:
							self.printIdx = None
							wx.CallAfter(self.UpdateButtonStates)
						wx.CallAfter(self.UpdateProgress)
				elif "resend" in line.lower() or "rs" in line:
					try:
						lineNr=int(line.replace("N:"," ").replace("N"," ").replace(":"," ").split()[-1])
					except:
						if "rs" in line:
							lineNr=int(line.split()[1])
					self.printIdx = lineNr
					#we should actually resend the line here, but we also get an "ok" for each error from Marlin. And thus we'll resend on the OK.

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
		x0 = 0
		t0 = 0
		bt0 = 0
		tSP0 = 0
		btSP0 = 0
		tempPen = wx.Pen('#FF4040')
		tempSPPen = wx.Pen('#FFA0A0')
		tempPenBG = wx.Pen('#FFD0D0')
		bedTempPen = wx.Pen('#4040FF')
		bedTempSPPen = wx.Pen('#A0A0FF')
		bedTempPenBG = wx.Pen('#D0D0FF')
		for temp, tempSP, bedTemp, bedTempSP, t in self.points:
			x1 = int(w - (now - t))
			for x in xrange(x0, x1 + 1):
				t = float(x - x0) / float(x1 - x0 + 1) * (temp - t0) + t0
				bt = float(x - x0) / float(x1 - x0 + 1) * (bedTemp - bt0) + bt0
				tSP = float(x - x0) / float(x1 - x0 + 1) * (tempSP - tSP0) + tSP0
				btSP = float(x - x0) / float(x1 - x0 + 1) * (bedTempSP - btSP0) + btSP0
				dc.SetPen(tempPenBG)
				dc.DrawLine(x, h, x, h - (t * h / 300))
				dc.SetPen(bedTempPenBG)
				dc.DrawLine(x, h, x, h - (bt * h / 300))
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
		self.points.append((temp, tempSP, bedTemp, bedTempSP, time.time()))
		wx.CallAfter(self.UpdateDrawing)

