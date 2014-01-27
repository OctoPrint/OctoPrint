# coding=utf-8
import time

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 Gina Häußge - Released under terms of the AGPLv3 License"


from octoprint.comm.transport import MessageReceiver, StateReceiver, LogReceiver, State as TransportState
from octoprint.filemanager.destinations import FileDestinations


class Protocol(MessageReceiver, StateReceiver, LogReceiver):

	def __init__(self, transportFactory, protocolListener=None):
		self._transport = transportFactory(self, self, self)
		self._transportProperties = self._transport.getProperties()

		self._protocolListener = protocolListener
		self._state = State.OFFLINE

		self._currentFile = None

		self._error = None

		# temperatures
		self._temp = {}
		self._targetTemp = {}
		self._bedTemp = 0
		self._bedTargetTemp = 0

		self._tempOffset = {}
		self._bedTempOffset = 0

	##~~ public

	def connect(self, opt):
		self._transport.connect(opt)

	def disconnect(self, onError=False):
		self._transport.disconnect(onError)

	def sendManually(self, command, highPriority=False):
		pass

	def selectFile(self, filename, origin):
		pass

	def deselectFile(self):
		pass

	def startPrint(self):
		if self._currentFile is None:
			raise ValueError("No file selected for printing")
		self._changeState(State.PRINTING)
		self._currentFile.start()

	def pausePrint(self):
		if self._state == State.PRINTING:
			self._changeState(State.PAUSED)
		elif self._state == State.PAUSED:
			self._changeState(State.PRINTING)

	def cancelPrint(self):
		pass

	##~~ private

	def _changeState(self, newState):
		oldState = self._state
		self._state = newState
		self._stateChanged(newState)
		if self._protocolListener is not None:
			self._protocolListener.onStateChange(self, oldState, newState)

	def _stateChanged(self, newState):
		pass

	def _updateTemperature(self, temperatureData):
		self._temperatureUpdated(temperatureData)
		if self._protocolListener is not None:
			self._protocolListener.onTemperatureUpdate(self, temperatureData)

	def _temperatureUpdated(self, temperatureData):
		pass

	def onError(self, error):
		self._changeState(State.ERROR)
		self._error = error

	##~~ StateReceiver

	def onStateChangeReceived(self, source, oldState, newState):
		if self._transport != source:
			return

		if newState == TransportState.DETECTING_CONNECTION or newState == TransportState.OPENING_CONNECTION:
			self._changeState(State.CONNECTING)
		elif newState == TransportState.CONNECTED:
			self._changeState(State.CONNECTED)
		elif newState == TransportState.DISCONNECTED:
			self._changeState(State.OFFLINE)
		elif newState == TransportState.DISCONNECTED_WITH_ERROR or newState == TransportState.ERROR:
			self._changeState(State.ERROR)

	##~~ LogReceiver

	def onLogRx(self, source, rx):
		if self._transport != source:
			return

		if self._protocolListener is not None:
			self._protocolListener.onLogRx(self, rx)

	def onLogTx(self, source, tx):
		if self._transport != source:
			return

		if self._protocolListener is not None:
			self._protocolListener.onLogTx(self, tx)

	def onLogError(self, source, error):
		if self._transport != source:
			return

		if self._protocolListener is not None:
			self._protocolListener.onLogError(self, error)


class ProtocolListener(object):
	def onStateChange(self, source, oldState, newState):
		pass

	def onTemperatureUpdate(self, source, temperatureData):
		pass

	def onLogTx(self, source, tx):
		pass

	def onLogRx(self, source, rx):
		pass

	def onLogError(self, source, error):
		pass


class State(object):

	OFFLINE = "Offline"
	CONNECTING = "Connecting"
	CONNECTED = "Connected"
	OPERATIONAL = "Operational"
	PRINTING = "Printing"
	STREAMING = "Streaming"
	PAUSED = "Paused"
	HEATING = "Heating"
	ERROR = "Error"


### Printing file information classes ##################################################################################

class PrintingFileInformation(object):
	"""
	Encapsulates information regarding the current file being printed: file name, current position, total size and
	time the print started.
	Allows to reset the current file position to 0 and to calculate the current progress as a floating point
	value between 0 and 1.
	"""

	def __init__(self, filename):
		self._filename = filename
		self._filepos = 0
		self._filesize = None
		self._startTime = None

	def getStartTime(self):
		return self._startTime

	def getFilename(self):
		return self._filename

	def getFilesize(self):
		return self._filesize

	def getFilepos(self):
		return self._filepos

	def getFileLocation(self):
		return FileDestinations.LOCAL

	def getProgress(self):
		"""
		The current progress of the file, calculated as relation between file position and absolute size. Returns -1
		if file size is None or < 1.
		"""
		if self._filesize is None or not self._filesize > 0:
			return -1
		return float(self._filepos) / float(self._filesize)

	def reset(self):
		"""
		Resets the current file position to 0.
		"""
		self._filepos = 0

	def start(self):
		"""
		Marks the print job as started and remembers the start time.
		"""
		self._startTime = time.time()


class PrintingSdFileInformation(PrintingFileInformation):
	"""
	Encapsulates information regarding an ongoing print from SD.
	"""

	def __init__(self, filename, filesize):
		PrintingFileInformation.__init__(self, filename)
		self._filesize = filesize

	def setFilepos(self, filepos):
		"""
		Sets the current file position.
		"""
		self._filepos = filepos

	def getFileLocation(self):
		return FileDestinations.SDCARD
