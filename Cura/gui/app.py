from __future__ import absolute_import

import sys
import os
import platform
import shutil
import glob
import warnings

#Only import the _core to save import time
import wx._core

from Cura.gui import splashScreen
from Cura.util import profile

class CuraApp(wx.App):
	def __init__(self):
		if platform.system() == "Windows":
			super(CuraApp, self).__init__(redirect = True, filename = 'output.txt')
		else:
			super(CuraApp, self).__init__(redirect = False)

		self.mainWindow = None
		self.splash = None

		if sys.platform.startswith('darwin'):
			#Do not show a splashscreen on OSX, as by Apple guidelines
			self.afterSplashCallback()
		else:
			self.splash = splashScreen.splashScreen(self.afterSplashCallback)

	def MacOpenFile(self, path):
		try:
			self.mainWindow._loadModels([path])
		except Exception as e:
			warnings.warn("File at {p} cannot be read: {e}".format(p=path, e=str(e)))

	def afterSplashCallback(self):
		#These imports take most of the time and thus should be done after showing the splashscreen
		from Cura.gui import mainWindow
		from Cura.gui import configWizard

		#If we haven't run it before, run the configuration wizard.
		if profile.getPreference('machine_type') == 'unknown':
			if platform.system() == "Darwin":
				#Check if we need to copy our examples
				exampleFile = os.path.expanduser('~/CuraExamples/UltimakerRobot_support.stl')
				if not os.path.isfile(exampleFile):
					try:
						os.makedirs(os.path.dirname(exampleFile))
					except:
						pass
					for filename in glob.glob(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'example', '*.*'))):
						shutil.copy(filename, os.path.join(os.path.dirname(exampleFile), os.path.basename(filename)))
					profile.putPreference('lastFile', exampleFile)
			configWizard.configWizard()

		#Hide the splashscreen before showing the main window.
		if self.splash is not None:
			self.splash.Show(False)
		self.mainWindow = mainWindow.mainWindow()
