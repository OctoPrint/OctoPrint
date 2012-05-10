from __future__ import absolute_import
import __init__

import wx, threading, re, subprocess, sys, os
from wx.lib import buttons

from gui import machineCom
from gui import icon
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
	printWindowHandle.LoadGCodeFile(filename)
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
		self.bitmap = wx.Bitmap(os.path.join(os.path.split(__file__)[0], "../images", bitmapFilename))
		super(PrintCommandButton, self).__init__(parent.directControlPanel, -1, self.bitmap, size=size)

		self.command = command
		self.parent = parent

		self.SetBezelWidth(1)
		self.SetUseFocusIndicator(False)

		self.Bind(wx.EVT_BUTTON, self.OnClick)

	def OnClick(self, e):
		self.parent.sendCommand("G91")
		self.parent.sendCommand(self.command)
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
		self.bufferLineCount = 4
		self.sendCnt = 0

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
		
		self.sizer.Add(boxsizer, pos=(0,0), span=(4,1), flag=wx.EXPAND)
		
		self.connectButton = wx.Button(self.panel, -1, 'Connect')
		#self.loadButton = wx.Button(self.panel, -1, 'Load GCode')
		self.printButton = wx.Button(self.panel, -1, 'Print GCode')
		self.cancelButton = wx.Button(self.panel, -1, 'Cancel print')
		self.progress = wx.Gauge(self.panel, -1)
		
		h = self.connectButton.GetSize().GetHeight()
		self.temperatureSelect = wx.SpinCtrl(self.panel, -1, '0', size=(21*3,21), style=wx.SP_ARROW_KEYS)
		self.temperatureSelect.SetRange(0, 400)
		
		self.sizer.Add(self.connectButton, pos=(0,1))
		#self.sizer.Add(self.loadButton, pos=(1,1))
		self.sizer.Add(self.printButton, pos=(2,1))
		self.sizer.Add(self.cancelButton, pos=(3,1))
		self.sizer.Add(self.progress, pos=(4,0), span=(1,2), flag=wx.EXPAND)
		
		self.sizer.Add(wx.StaticText(self.panel, -1, "Temp:"), pos=(0,3))
		self.sizer.Add(self.temperatureSelect, pos=(0,4))
		
		self.directControlPanel = wx.Panel(self.panel)
		self.sizer.Add(self.directControlPanel, pos=(1,3), span=(5,4))
		
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

		sizer.Add(PrintCommandButton(self, 'G28 X0 Y0', 'exit.png'), pos=(3,3))

		sizer.Add(PrintCommandButton(self, 'G1 X1 F6000', 'print-move-x1.png'), pos=(3,4))
		sizer.Add(PrintCommandButton(self, 'G1 X10 F6000', 'print-move-x10.png'), pos=(3,5))
		sizer.Add(PrintCommandButton(self, 'G1 X100 F6000', 'print-move-x100.png'), pos=(3,6))

		sizer.Add(PrintCommandButton(self, 'G1 Z10 F200', 'print-move-z10.png'), pos=(0,6))
		sizer.Add(PrintCommandButton(self, 'G1 Z1 F200', 'print-move-z1.png'), pos=(1,6))
		sizer.Add(PrintCommandButton(self, 'G1 Z0.1 F200', 'print-move-z0.1.png'), pos=(2,6))

		sizer.Add(PrintCommandButton(self, 'G1 Z-0.1 F200', 'print-move-z-0.1.png'), pos=(4,6))
		sizer.Add(PrintCommandButton(self, 'G1 Z-1 F200', 'print-move-z-1.png'), pos=(5,6))
		sizer.Add(PrintCommandButton(self, 'G1 Z-10 F200', 'print-move-z-10.png'), pos=(6,6))

		self.sizer.AddGrowableRow(3)
		self.sizer.AddGrowableCol(0)
		
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		self.connectButton.Bind(wx.EVT_BUTTON, self.OnConnect)
		#self.loadButton.Bind(wx.EVT_BUTTON, self.OnLoad)
		self.printButton.Bind(wx.EVT_BUTTON, self.OnPrint)
		self.cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)
		
		self.Bind(wx.EVT_SPINCTRL, self.OnTempChange, self.temperatureSelect)
		
		self.Layout()
		self.Fit()
		self.Centre()
		
		self.UpdateButtonStates()
		self.UpdateProgress()
	
	def UpdateButtonStates(self):
		self.connectButton.Enable(not self.machineConnected)
		#self.loadButton.Enable(self.printIdx == None)
		self.printButton.Enable(self.machineConnected and self.gcodeList != None and self.printIdx == None)
		self.cancelButton.Enable(self.printIdx != None)
		self.temperatureSelect.Enable(self.machineConnected)
		self.directControlPanel.Enable(self.machineConnected)
	
	def UpdateProgress(self):
		status = ""
		if self.gcode != None:
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
		self.statsText.SetLabel(status.strip())
		self.Layout()
	
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
		self.UpdateButtonStates()
	
	def OnClose(self, e):
		global printWindowHandle
		printWindowHandle = None
		if self.machineCom != None:
			self.machineCom.close()
			self.thread.join()
		self.Destroy()

	def OnTempChange(self, e):
		self.sendCommand("M104 S%d" % (self.temperatureSelect.GetValue()))

	def LoadGCodeFile(self, filename):
		if self.printIdx != None:
			return
		#Send an initial M110 to reset the line counter to zero.
		gcodeList = ["M110"]
		for line in open(filename, 'r'):
			if ';' in line:
				line = line[0:line.find(';')]
			line = line.strip()
			if len(line) > 0:
				gcodeList.append(line)
		gcode = gcodeInterpreter.gcode()
		gcode.loadList(gcodeList)
		print "Loaded: %s (%d)" % (filename, len(gcodeList))
		self.progress.SetRange(len(gcodeList))
		self.gcode = gcode
		self.gcodeList = gcodeList
		self.UpdateButtonStates()
		self.UpdateProgress()
		
	def sendCommand(self, cmd):
		if self.machineConnected:
			if self.printIdx == None:
				self.machineCom.sendCommand(cmd)
			else:
				self.sendList.append(cmd)

	def sendLine(self, lineNr):
		if lineNr >= len(self.gcodeList):
			return False
		checksum = reduce(lambda x,y:x^y, map(ord, "N%d%s" % (lineNr, self.gcodeList[lineNr])))
		self.machineCom.sendCommand("N%d%s*%d" % (lineNr, self.gcodeList[lineNr], checksum))
		return True

	def PrinterMonitor(self):
		while True:
			line = self.machineCom.readline()
			if line == None:
				self.machineConnected = False
				wx.CallAfter(self.UpdateButtonStates)
				return
			if self.machineConnected:
				while self.sendCnt > 0:
					self.sendLine(self.printIdx)
					self.printIdx += 1
					self.sendCnt -= 1
			elif line.startswith("start"):
				self.machineConnected = True
				wx.CallAfter(self.UpdateButtonStates)
			if 'T:' in line:
				self.temp = float(re.search("[0-9\.]*", line.split('T:')[1]).group(0))
				wx.CallAfter(self.UpdateProgress)
			if self.printIdx == None:
				if line == '':	#When we have a communication "timeout" and we're not sending gcode, then read the temperature.
					self.machineCom.sendCommand("M105")
			else:
				if line.startswith("ok"):
					if len(self.sendList) > 0:
						self.machineCom.sendCommand(self.sendList.pop(0))
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

