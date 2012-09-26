import os, glob, subprocess
import wx

try:
	#Try to find the OpenCV library for video capture.
	from opencv import cv
	from opencv import highgui
except:
	cv = None

try:
	#Use the vidcap library directly from the VideoCapture package. (Windows only)
	#	http://videocapture.sourceforge.net/
	# We're using the binary interface, not the python interface, so we don't depend on PIL
	import vidcap as win32vidcap
except:
	win32vidcap = None

class webcam(object):
	def __init__(self):
		if cv != None:
			self._cam = highgui.cvCreateCameraCapture(-1)
		elif win32vidcap != None:
			self._cam = win32vidcap.new_Dev(0, False)
			#self._cam.displaycapturefilterproperties()
			#self._cam.displaycapturepinproperties()
		else:
			raise exception("No camera implementation available")
		
		self._doTimelaps = False
		self._bitmap = None
	
	def takeNewImage(self):
		if cv != None:
			frame = cv.QueryFrame(self._cam)
			cv.CvtColor(frame, frame, cv.CV_BGR2RGB)
			self._bitmap = wx.BitmapFromBuffer(frame.width, frame.height, frame.imageData)
		elif win32vidcap != None:
			buffer, width, height = self._cam.getbuffer()
			wxImage = wx.EmptyImage(width, height)
			wxImage.SetData(buffer[::-1])
			if self._bitmap != None:
				del self._bitmap
			self._bitmap = wxImage.ConvertToBitmap()
			del wxImage
			del buffer

		if self._doTimelaps:
			filename = os.path.normpath(os.path.join(os.path.split(__file__)[0], "../__tmp_snap", "__tmp_snap_%04d.jpg" % (self._snapshotCount)))
			self._snapshotCount += 1
			self._bitmap.SaveFile(filename, wx.BITMAP_TYPE_JPEG)

		return self._bitmap
	
	def getLastImage(self):
		return self._bitmap
	
	def startTimelaps(self, filename):
		self._cleanTempDir()
		self._timelapsFilename = filename
		self._snapshotCount = 0
		self._doTimelaps = True
	
	def endTimelaps(self):
		if self._doTimelaps:
			if platform.system() == "Windows":
				ffmpeg = os.path.normpath(os.path.join(os.path.split(__file__)[0], "../ffmpeg.exe"))
			else:
				ffmpeg = os.path.normpath(os.path.join(os.path.split(__file__)[0], "../ffmpeg"))
			basePath = os.path.normpath(os.path.join(os.path.split(__file__)[0], "../__tmp_snap", "__tmp_snap_%04d.jpg"))
			subprocess.call([ffmpeg, '-r', '12.5', '-i', basePath, '-vcodec', 'mpeg2video', '-pix_fmt', 'yuv420p', '-r', '25', '-y', '-b:v', '1500k', '-f', 'vob', self._timelapsFilename])
		self._doTimelaps = False
	
	def _cleanTempDir(self):
		basePath = os.path.normpath(os.path.join(os.path.split(__file__)[0], "../__tmp_snap"))
		try:
			os.makedirs(basePath)
		except:
			pass
		for filename in glob.iglob(basePath + "/*.jpg"):
			os.remove(filename)
