import sys, os
#We only need the core here, which speeds up the import. As we want to show the splashscreen ASAP.
import wx._core

def getBitmapImage(filename):
	#The frozen executable has the script files in a zip, so we need to exit another level to get to our images.
	if hasattr(sys, 'frozen'):
		return wx.Bitmap(os.path.normpath(os.path.join(os.path.split(__file__)[0], "../../images", filename)))
	else:
		return wx.Bitmap(os.path.normpath(os.path.join(os.path.split(__file__)[0], "../images", filename)))

class splashScreen(wx.SplashScreen):
	def __init__(self, callback):
		self.callback = callback
		bitmap = getBitmapImage("splash.png")
		super(splashScreen, self).__init__(bitmap, wx.SPLASH_CENTRE_ON_SCREEN, 0, None)
		wx.CallAfter(callback)
		wx.CallAfter(self.Destroy)

def showSplash(callback):
	app = wx.App(False)
	splashScreen(callback)
	app.MainLoop()

def testCallback():
	print "Callback!"
	import time
	time.sleep(2)
	print "!Callback"

def main():
	showSplash(testCallback)

if __name__ == u'__main__':
	main()

