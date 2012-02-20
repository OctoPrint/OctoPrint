from __future__ import absolute_import
import __init__

import wx, os

from newui import preview3d
from fabmetheus_utilities import archive
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_profile

def main():
	app = wx.App(False)
	mainWindow()
	app.MainLoop()

class mainWindow(wx.Frame):
	"Main user interface window"
	def __init__(self):
		super(mainWindow, self).__init__(None, title='SkeinPyPy')
		menubar = wx.MenuBar()
		fileMenu = wx.Menu()
		fitem = fileMenu.Append(-1, 'Open Profile...', 'Open Profile...')
		fitem = fileMenu.Append(-1, 'Save Profile...', 'Save Profile...')
		fitem = fileMenu.Append(wx.ID_EXIT, 'Quit', 'Quit application')
		self.Bind(wx.EVT_MENU, self.OnQuit, fitem)
		menubar.Append(fileMenu, '&File')
		menubar.Append(wx.Menu(), 'Expert')
		self.SetMenuBar(menubar)
		
		plugins = {}
		for m in skeinforge_profile.getCraftTypePluginModule().getCraftSequence():
			plugins[m] = archive.getModuleWithDirectoryPath(archive.getCraftPluginsDirectoryPath(), m).getNewRepository()
			settings.getReadRepository(plugins[m])
		
		p = wx.Panel(self)
		nb = wx.Notebook(p, size=(500,10))
		
		printConfig = wx.Panel(nb);

		sizer = wx.GridBagSizer(2, 2)
		printConfig.SetSizer(sizer)
		
		skeinPyPySettingInfo = settings.getSkeinPyPyConfigInformation()

		for pluginName in plugins.keys():
			box, configPanel = self.CreateGroup(printConfig, pluginName)
			
			for pref in plugins[pluginName].preferences:
				if skeinPyPySettingInfo[pluginName][settings.safeConfigName(pref.name)] == 'save':
					self.AddSetting(configPanel, pref.name, wx.TextCtrl(configPanel, -1, str(pref.value)))

			if configPanel.GetSizer().GetRows() > 0:
				sizer.Add(box, (sizer.GetRows(),0))
				sizer.SetRows(sizer.GetRows()+1)
		
		#self.AddSetting(generalConfig, "Speed (mm/s)", wx.TextCtrl(generalConfig, -1, "50.0"))

		machineConfig = wx.Panel(nb);
		sizer = wx.GridBagSizer(2, 2)
		machineConfig.SetSizer(sizer)
		box, dimensionsConfig = self.CreateGroup(machineConfig, "Dimensions")
		self.AddSetting(dimensionsConfig, "Printer size (mm)", wx.TextCtrl(dimensionsConfig, -1, "205,205,200"))
		sizer.Add(box, (0,0))
		
		nb.AddPage(printConfig, "Print")
		nb.AddPage(machineConfig, "Machine")
		nb.AddPage(wx.Panel(nb), "Start/End-GCode")

		#Preview window, load and slice buttons.
		self.preview3d = preview3d.myGLCanvas(p)
		
		loadButton = wx.Button(p, 1, 'Load STL')
		self.Bind(wx.EVT_BUTTON, self.OnLoadSTL, loadButton)
		
		sizer = wx.GridBagSizer()
		sizer.Add(nb, (0,0), span=(2,1), flag=wx.EXPAND)
		sizer.Add(self.preview3d, (0,1), span=(1,1), flag=wx.EXPAND)
		sizer.Add(loadButton, (1,1))
		sizer.AddGrowableCol(1)
		sizer.AddGrowableRow(0)
		p.SetSizer(sizer)
		
		self.SetSize((800, 400))
		self.Centre()
		self.Show(True)
	
	def CreateGroup(self, panel, name):
		retPanel = wx.Panel(panel)
		sizer = wx.GridBagSizer(2, 2)
		retPanel.SetSizer(sizer)

		box = wx.StaticBox(panel, -1, name)
		sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
		sizer.Add(retPanel)
		
		return (sizer, retPanel)
	
	def AddSetting(self, panel, name, ctrl):
		sizer = panel.GetSizer()
		sizer.Add(wx.StaticText(panel, -1, name), (sizer.GetRows(),0), flag=wx.ALIGN_BOTTOM)
		sizer.Add(ctrl, (sizer.GetRows(),1), flag=wx.ALIGN_BOTTOM|wx.EXPAND)
		sizer.SetRows(sizer.GetRows()+1)
	
	def OnLoadSTL(self, e):
		dlg=wx.FileDialog(self, "Open file to print", style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("OBJ, STL files (;*.stl;*.STL;*.obj;*.OBJ;)")
		if dlg.ShowModal() == wx.ID_OK:
			self.filename=dlg.GetPath()
			if not(os.path.exists(self.filename)):
				return
			self.preview3d.loadFile(self.filename)
	
	def OnQuit(self, e):
		self.Close()

