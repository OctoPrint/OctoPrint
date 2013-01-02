# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

try:
	#Try to find the OpenCV library for video capture.
	import cv
except:
	cv = None

try:
	import VideoCapture as win32vidcap
except:
	win32vidcap = None

def hasWebcamSupport():
	if cv == None and win32vidcap == None:
		return False
	return True

class Webcam(object):
	def __init__(self):
		self._cam = None
		if cv != None:
			self._cam = cv.CreateCameraCapture(-1)
		elif win32vidcap != None:
			try:
				self._cam = win32vidcap.Device()
				self._cam.setResolution(640, 480)
			except:
				pass

	def save(self, filename):
		if self._cam is None:
			return

		if cv is not None:
			frame = cv.QueryFrame(self._cam)
			cv.SaveImage(filename, frame)
		elif win32vidcap is not None:
			self._cam.saveSnapshot(filename)

if __name__ == "__main__":
	from printer_webui.settings import settings
	import os

	webcam = Webcam()
	webcam.save(os.path.join(settings().settings_dir, "image.png"))
