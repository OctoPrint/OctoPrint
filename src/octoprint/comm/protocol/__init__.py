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
from octoprint.settings import settings


class Protocol(MessageReceiver, StateReceiver, LogReceiver):

	def __init__(self, transport_factory, protocol_listener=None):
		self._logger = logging.getLogger(__name__)

		self._transport = transport_factory(self, self, self)
		self._transport_properties = self._transport.get_properties()

		self._protocol_listener = protocol_listener
		self._state = State.OFFLINE

		self._heatup_start_time = None
		self._heatup_time_lost = 0.0

		self._current_file = None

		self._current_z = 0.0

		self._sd_available = False
		self._sd_files = []

		self._current_temperature = {}
		self._temperature_offsets = {}

		self._error = None

	def _reset(self):
		self._heatup_start_time = None
		self._heatup_time_lost = 0.0

		self._current_file = None

		self._current_z = 0.0

		self._sd_available = False
		self._sd_files = []

		self._current_temperature = {}
		self._temperature_offsets = {}

		self._error = None

	##~~ public

	def connect(self, opt):
		self._transport.connect(opt)

	def disconnect(self, on_error=False):
		self._transport.disconnect(on_error)

	def send_manually(self, command, high_priority=False):
		pass

	def select_file(self, filename, origin):
		pass

	def deselect_file(self):
		pass

	def start_print(self):
		if self._current_file is None:
			raise ValueError("No file selected for printing")

		self._heatup_start_time = None
		self._heatup_time_lost = 0.0

		self._changeState(State.PRINTING)
		self._current_file.start()

	def pause_print(self):
		if self._state == State.PRINTING:
			self._changeState(State.PAUSED)
		elif self._state == State.PAUSED:
			self._changeState(State.PRINTING)

	def cancel_print(self):
		eventManager().fire(Events.PRINT_CANCELLED, {
			"file": self._current_file.getFilename(),
			"origin": self._current_file.getFileLocation()
		})
		self._changeState(State.OPERATIONAL)

	def init_sd(self):
		pass

	def release_sd(self):
		pass

	def refresh_sd_files(self):
		pass

	def add_sd_file(self, path, local, remote):
		pass

	def remove_sd_file(self, filename):
		pass

	def get_state(self):
		return self._state

	def get_current_temperatures(self):
		return self._current_temperature

	def get_temperature_offsets(self):
		result = {}
		result.update(self._temperature_offsets)
		return result

	def set_temperature_offsets(self, new_temperature_offsets):
		offsets = {}
		offsets.update(new_temperature_offsets)
		self._temperature_offsets = offsets

	def get_sd_files(self):
		return self._sd_files

	def get_print_time(self):
		if self._current_file is None or self._current_file.getStartTime() is None:
			return None
		else:
			return max(int(time.time() - self._current_file.getStartTime() - self._heatup_time_lost), 0)

	def get_print_time_remaining_estimate(self):
		print_time = self.get_print_time()
		if print_time is None:
			return None

		progress = self._current_file.getProgress()
		if progress:
			print_time_total = print_time / progress
			return int(print_time_total - print_time)
		else:
			return None

	def get_connection_options(self):
		return self._transport.get_connection_options()

	def get_current_connection(self):
		return self._transport.get_current_connection()

	##~~ granular state detection for implementations

	def is_heating_up(self):
		return self._heatup_start_time is not None

	def is_printing(self):
		return self._state == State.PRINTING or self._state == State.PAUSED

	def is_sd_printing(self):
		return isinstance(self._current_file, PrintingSdFileInformation) and self.is_busy()

	def is_streaming(self):
		return self._state == State.STREAMING

	def is_busy(self):
		return self.is_printing() or self.is_streaming()

	def is_operational(self):
		return self._state == State.OPERATIONAL

	def is_sd_ready(self):
		return self._sd_available

	##~~ state tracking and reporting to protocol listener

	def _changeState(self, newState):
		oldState = self._state
		self._state = newState
		self._stateChanged(newState)
		if self._protocol_listener is not None:
			self._protocol_listener.onStateChange(self, oldState, newState)

	def _stateChanged(self, newState):
		pass

	def _updateTemperature(self, temperatureData):
		self._current_temperature = temperatureData
		self._temperatureUpdated(temperatureData)
		if self._protocol_listener is not None:
			self._protocol_listener.onTemperatureUpdate(self, temperatureData)

	def _temperatureUpdated(self, temperatureData):
		pass

	def _reportProgress(self):
		progress = {
			"completion": self.__getPrintCompletion(),
			"filepos": self.__getPrintFilepos(),
			"printTime": self.get_print_time(),
			"printTimeLeft": self.get_print_time_remaining_estimate()
		}

		self._progressReported(progress)
		if self._protocol_listener is not None:
			self._protocol_listener.onProgress(self, progress)

	def _progressReported(self, progress):
		pass

	def _reportZChange(self, z):
		old_z = self._current_z
		self._current_z = z

		self._zChangeReported(z)
		if self._protocol_listener is not None:
			self._protocol_listener.onZChange(self, old_z, z)

	def _zChangeReported(self, newZ):
		pass

	def _changeSdState(self, sdAvailable):
		self._sd_available = sdAvailable
		self._sdStateChanged(sdAvailable)
		if self._sd_available:
			self.refresh_sd_files()
		else:
			self._sd_files = []
		if self._protocol_listener is not None:
			self._protocol_listener.onSdStateChange(self, sdAvailable)

	def _sdStateChanged(self, sdAvailable):
		pass

	def _selectFile(self, currentFile):
		self._current_file = currentFile
		self._fileSelected(currentFile)
		if self._protocol_listener is not None:
			self._protocol_listener.onFileSelected(self, currentFile.getFilename(), currentFile.getFilesize(), currentFile.getFileLocation())
		eventManager().fire(Events.FILE_SELECTED, {
			"file": self._current_file.getFilename(),
			"origin": self._current_file.getFileLocation()
		})

	def _fileSelected(self, currentFile):
		pass

	def _sendSdFiles(self):
		self._sdFilesSent()
		if self._protocol_listener is not None:
			self._protocol_listener.onSdFiles(self, self._sd_files)

	def _sdFilesSent(self):
		pass

	def _finishPrintjob(self):
		self._changeState(State.OPERATIONAL)
		if self._protocol_listener is not None:
			self._protocol_listener.onPrintjobDone(self)
		eventManager().fire(Events.PRINT_DONE, {
			"file": self._current_file.getFilename(),
			"filename": os.path.basename(self._current_file.getFilename()),
			"origin": self._current_file.getFileLocation(),
			"time": time.time() - self._current_file.getStartTime() if self._current_file.getStartTime() is not None else None
		})
		self._printJobFinished()

	def _printJobFinished(self):
		pass

	def _startFileTransfer(self, filename, filesize):
		self._fileTransferStarted(filename, filesize)
		if self._protocol_listener is not None:
			self._protocol_listener.onFileTransferStarted(self, filename, filesize)

	def _fileTransferStarted(self, filename, filesize):
		pass

	def _finishFileTransfer(self):
		self._changeState(State.OPERATIONAL)

		current_file = self._current_file
		self._current_file = None

		self._fileTransferFinished(current_file)

		if self._protocol_listener is not None:
			self._protocol_listener.onFileTransferDone(self)

	def _fileTransferFinished(self, current_file):
		pass

	def _addSdFile(self, filename, filesize):
		"""
		Adds a file to the SD file list

		:param filename: the filename to add to the list
		:param filesize: the filesize to add to the list, may be None
		"""
		self._sd_files.append((filename, filesize))
		self._sdFileAdded(filename, filesize)

	def _sdFileAdded(self, filename, filesize):
		"""
		Called when a file has been added to the SD file list, can be used by the underyling protocol implementation
		to react to that.

		:param filename: the filename to add to the list
		:param filesize: the filesize to add to the list, may be None
		"""
		pass

	def _addSdFiles(self, files):
		"""
		Adds a list of files to the SD file list

		:param files: the list of file tuples (name, size) to add to the list, size may be None
		"""
		for f in files:
			self._sd_files.append(f)
		self._sdFilesAdded(files)

	def _sdFilesAdded(self, files):
		"""
		Called when a list of files has been added to the SD file list, can be used by the underlying protocol
		implementation to react to that.

		:param files: the file tuples (name, size) added to the list, size may be None
		"""
		pass

	def _resetSdFiles(self):
		"""
		Resets the SD file list
		"""
		self._sd_files = []
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
		self._heatup_start_time = time.time()

	def _heatupDone(self):
		"""
		Called when the underlying protocol detects the end of a heat-up interval.
		"""
		if self._heatup_start_time is not None:
			self._heatup_time_lost += time.time() - self._heatup_start_time
			self._heatup_start_time = None

	def _log_error(self, error):
		if self._protocol_listener is not None:
			self._protocol_listener.onLogError(self, error)

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
			self.onError(self._transport.getError())
			try:
				self._transport.disconnect()
			except:
				# TODO do we need to handle that?
				pass

	##~~ MessageReceiver

	def onError(self, error):
		self._changeState(State.ERROR)
		self._error = error
		eventManager().fire(Events.ERROR, {"error": error})

	##~~ LogReceiver

	def onLogRx(self, source, rx):
		if self._transport != source:
			return

		if self._protocol_listener is not None:
			self._protocol_listener.onLogRx(self, rx)

	def onLogTx(self, source, tx):
		if self._transport != source:
			return

		if self._protocol_listener is not None:
			self._protocol_listener.onLogTx(self, tx)

	def onLogError(self, source, error):
		if self._transport != source:
			return
		self._log_error(error)

	##~~ helpers

	def __getPrintCompletion(self):
		if self._current_file is None:
			return None
		return self._current_file.getProgress() * 100

	def __getPrintFilepos(self):
		if self._current_file is None:
			return None
		return self._current_file.getFilepos()


class ProtocolListener(object):
	def onStateChange(self, source, oldState, newState):
		pass

	def onTemperatureUpdate(self, source, temperatureData):
		pass

	def onProgress(self, source, progress):
		pass

	def onZChange(self, source, oldZ, newZ):
		pass

	def onFileSelected(self, source, filename, filesize, origin):
		pass

	def onPrintjobDone(self, source):
		pass

	def onFileTransferStarted(self, source, filename, filesize):
		pass

	def onFileTransferDone(self, source):
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
