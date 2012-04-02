from __future__ import absolute_import
import __init__

import wx, threading

from gui import machineCom
from gui import icon

printWindowHandle = None

def printFile(filename):
	global printWindowHandle
	if printWindowHandle == None:
		printWindowHandle = printWindow()
	printWindowHandle.Show(True)
	printWindowHandle.Raise()
	printWindowHandle.LoadGCodeFile(filename)

class printWindow(wx.Frame):
	"Main user interface window"
	def __init__(self):
		super(printWindow, self).__init__(None, -1, title='Printing')
		self.machineCom = None
		self.thread = None
		self.gcodeList = None
		self.printIdx = None
		self.bufferLineCount = 4
		self.sendCnt = 0

		self.SetIcon(icon.getMainIcon())
		
		self.SetSizer(wx.BoxSizer())
		self.panel = wx.Panel(self)
		self.GetSizer().Add(self.panel, 1, flag=wx.EXPAND)
		self.sizer = wx.GridBagSizer(2, 2)
		self.panel.SetSizer(self.sizer)
		
		sb = wx.StaticBox(self.panel, label="Statistics")
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(wx.StaticText(self.panel, -1, "Filament: #.##m #.##g"), flag=wx.LEFT, border=5)
		boxsizer.Add(wx.StaticText(self.panel, -1, "Print time: ##:##"), flag=wx.LEFT, border=5)
		
		self.sizer.Add(boxsizer, pos=(0,0), span=(4,1), flag=wx.EXPAND)
		
		self.connectButton = wx.Button(self.panel, -1, 'Connect')
		self.loadButton = wx.Button(self.panel, -1, 'Load GCode')
		self.printButton = wx.Button(self.panel, -1, 'Print GCode')
		self.cancelButton = wx.Button(self.panel, -1, 'Cancel print')
		self.sizer.Add(self.connectButton, pos=(0,1))
		self.sizer.Add(self.loadButton, pos=(1,1))
		self.sizer.Add(self.printButton, pos=(2,1))
		self.sizer.Add(self.cancelButton, pos=(3,1))
		self.sizer.Add(wx.Gauge(self.panel, -1), pos=(4,0), span=(1,2), flag=wx.EXPAND)
		self.sizer.AddGrowableRow(3)
		self.sizer.AddGrowableCol(0)
		
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		self.connectButton.Bind(wx.EVT_BUTTON, self.OnConnect)
		self.loadButton.Bind(wx.EVT_BUTTON, self.OnLoad)
		self.printButton.Bind(wx.EVT_BUTTON, self.OnPrint)
		self.cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)
		
		self.Layout()
		self.Fit()
		self.Centre()
	
	def OnConnect(self, e):
		if self.machineCom != None:
			self.machineCom.close()
			self.thread.join()
		self.machineCom = machineCom.MachineCom()
		self.thread = threading.Thread(target=self.PrinterMonitor)
		self.thread.start()
	
	def OnLoad(self, e):
		pass
	
	def OnPrint(self, e):
		if self.machineCom == None:
			return
		if self.gcodeList == None:
			return
		if self.printIdx != None:
			return
		self.printIdx = 1
		self.sendLine(0)
		self.sendCnt = self.bufferLineCount
	
	def OnCancel(self, e):
		pass
	
	def OnClose(self, e):
		global printWindowHandle
		printWindowHandle = None
		if self.machineCom != None:
			self.machineCom.close()
			self.thread.join()
		self.Destroy()

	def LoadGCodeFile(self, filename):
		gcodeList = ["M110"]
		for line in open(filename, 'r'):
			if ';' in line:
				line = line[0:line.find(';')]
			line = line.strip()
			if len(line) > 0:
				gcodeList.append(line)
		print "Loaded: %s (%d)" % (filename, len(gcodeList))
		self.gcodeList = gcodeList

	def sendLine(self, lineNr):
		if lineNr >= len(self.gcodeList):
			return
		checksum = reduce(lambda x,y:x^y, map(ord, "N%d%s" % (lineNr, self.gcodeList[lineNr])))
		self.machineCom.sendCommand("N%d%s*%d" % (lineNr, self.gcodeList[lineNr], checksum))

	def PrinterMonitor(self):
		skipCount = 0
		while True:
			line = self.machineCom.readline()
			if line == None:
				return
			while self.sendCnt > 0:
				self.sendLine(self.printIdx)
				self.printIdx += 1
				self.sendCnt -= 1
			if self.printIdx != None:
				if line.startswith("ok"):
					if skipCount > 0:
						skipCount -= 1
					else:
						self.sendLine(self.printIdx)
						self.printIdx += 1
				elif "resend" in line.lower() or "rs" in line:
					try:
						lineNr=int(line.replace("N:"," ").replace("N"," ").replace(":"," ").split()[-1])
					except:
						if "rs" in line:
							lineNr=int(line.split()[1])
					self.printIdx = lineNr
