# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 Gina Häußge - Released under terms of the AGPLv3 License"


import logging
import os
import time
from octoprint.events import eventManager, Events
from octoprint.comm.transport import MessageReceiver, StateReceiver, LogReceiver, State as TransportState
from octoprint.filemanager.destinations import FileDestinations


class Protocol(MessageReceiver, StateReceiver, LogReceiver):

	def __init__(self, transportFactory, protocolListener=None):
		self._logger = logging.getLogger(__name__)

		self._transport = transportFactory(self, self, self)
		self._transportProperties = self._transport.getProperties()

		self._protocolListener = protocolListener
		self._state = State.OFFLINE

		self._heatupStartTime = None
		self._heatupTimeLost = 0.0

		self._currentFile = None

		self._sdAvailable = False
		self._sdFiles = []

		self._error = None

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

		self._heatupStartTime = None
		self._heatupTimeLost = 0.0

		self._changeState(State.PRINTING)
		self._currentFile.start()

	def pausePrint(self):
		if self._state == State.PRINTING:
			self._changeState(State.PAUSED)
		elif self._state == State.PAUSED:
			self._changeState(State.PRINTING)

	def cancelPrint(self):
		pass

	def refreshSdFiles(self):
		pass

	##~~ granular state detection for implementations

	def _isHeatingUp(self):
		return self._heatupStartTime is not None

	def _isPrinting(self):
		return self._state == State.PRINTING or self._state == State.PAUSED

	def _isSdPrinting(self):
		return isinstance(self._currentFile, PrintingSdFileInformation) and self._isBusy()

	def _isStreaming(self):
		return self._state == State.STREAMING

	def _isBusy(self):
		return self._isPrinting() or self._isStreaming()

	##~~ state tracking and reporting to protocol listener

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

	def _reportProgress(self):
		progress = {
			"completion": self.__getPrintCompletion(),
			"filepos": self.__getPrintFilepos(),
			"printTime": self.__getPrintTime(),
			"printTimeLeft": self.__getPrintTimeRemainingEstimate()
		}

		self._progressReported(progress)
		if self._protocolListener is not None:
			self._protocolListener.onProgress(self, progress)

	def _progressReported(self, progress):
		pass

	def _changeSdState(self, sdAvailable):
		self._sdAvailable = sdAvailable
		self._sdStateChanged(sdAvailable)
		if self._sdAvailable:
			self.refreshSdFiles()
		else:
			self._sdFiles = []
		if self._protocolListener is not None:
			self._protocolListener.onSdStateChange(self, sdAvailable)

	def _sdStateChanged(self, sdAvailable):
		pass

	def _selectFile(self, currentFile):
		self._currentFile = currentFile
		self._fileSelected(currentFile)
		if self._protocolListener is not None:
			self._protocolListener.onFileSelected(self, currentFile.getFilename(), currentFile.getFilesize(), currentFile.getFileLocation())
		eventManager().fire(Events.FILE_SELECTED, {
			"file": self._currentFile.getFilename(),
			"origin": self._currentFIle.getFileLocation()
		})

	def _fileSelected(self, currentFile):
		pass

	def _sendSdFiles(self):
		self._sdFilesSent()
		if self._protocolListener is not None:
			self._protocolListener.onSdFiles(self, self._sdFiles)

	def _sdFilesSent(self):
		pass

	def _finishPrintjob(self):
		self._changeState(State.OPERATIONAL)
		if self._protocolListener is not None:
			self._protocolListener.onPrintjobDone(self)
		eventManager().fire(Events.PRINT_DONE, {
			"file": self._currentFile.getFilename(),
			"filename": os.path.basename(self._currentFile.getFilename()),
			"origin": self._currentFile.getFileLocation(),
			"time": time.time() - self._currentFile.getStartTime()
		})

	def _printJobFinished(self):
		pass

	def _addSdFile(self, filename):
		"""
		Adds a file to the SD file list

		:param filename: the filename to add to the list
		"""
		self._sdFiles.append(filename)
		self._sdFileAdded(filename)

	def _sdFileAdded(self, filename):
		"""
		Called when a file has been added to the SD file list, can be used by the underyling protocol implementation
		to react to that.

		:param filename: the filename to add to the list
		"""
		pass

	def _addSdFiles(self, filenames):
		"""
		Adds a list of files to the SD file list

		:param filenames: the list of filenames to add to the list
		"""
		for filename in filenames:
			self._sdFiles.append(filename)
		self._sdFilesAdded(filenames)

	def _sdFilesAdded(self, filenames):
		"""
		Called when a list of files has been added to the SD file list, can be used by the underlying protocol
		implementation to react to that.

		:param filenames: the filenames added to the list
		"""
		pass

	def _resetSdFiles(self):
		"""
		Resets the SD file list
		"""
		self._sdFiles = []
		self._sdFilesReset()

	def _sdFilesReset(self):
		"""
		Called when the list of SD files has been reset, can be used in the underlying protocol implementation to
		react to that
		"""
		pass

	def _heatupDetected(self):
		"""
		Called when the underlying protocol detects the beginning of a heat-up interval.
		"""
		self._heatupStartTime = time.time()

	def _heatupDone(self):
		"""
		Called when the underlying protocol detects the end of a heat-up interval.
		"""
		if self._heatupStartTime is not None:
			self._heatupTimeLost += time.time() - self._heatupStartTime
			self._heatupStartTime = None

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

	##~~ MessageReceiver

	def onError(self, error):
		self._changeState(State.ERROR)
		self._error = error
		eventManager().fire(Events.ERROR, {"error": error})

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

	##~~ helpers

	def __getPrintCompletion(self):
		if self._currentFile is None:
			return None
		return self._currentFile.getProgress() * 100

	def __getPrintFilepos(self):
		if self._currentFile is None:
			return None
		return self._currentFile.getFilepos()

	def __getPrintTime(self):
		if self._currentFile is None or self._currentFile.getStartTime() is None:
			return None
		else:
			return max(int(time.time() - self._currentFile.getStartTime() - self._heatupTimeLost), 0)

	def __getPrintTimeRemainingEstimate(self):
		printTime = self.__getPrintTime()
		if printTime is None:
			return None

		printTime /= 60
		progress = self._currentFile.getProgress()
		if progress:
			printTimeTotal = printTime / progress
			return int(printTimeTotal - printTime)
		else:
			return None


class ProtocolListener(object):
	def onStateChange(self, source, oldState, newState):
		pass

	def onTemperatureUpdate(self, source, temperatureData):
		pass

	def onProgress(self, source, progress):
		pass

	def onFileSelected(self, source, filename, filesize, origin):
		pass

	def onPrintjobDone(self, source):
		pass

	def onSdStateChange(self, source, sdAvailable):
		pass

	def onSdFiles(self, source, files):
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
