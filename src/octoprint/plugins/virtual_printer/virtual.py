# coding=utf-8
from __future__ import absolute_import
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


import time
import os
import re
import threading
import math
import Queue

from serial import SerialTimeoutException

from octoprint.settings import settings

class VirtualPrinter():
	command_regex = re.compile("[GM]\d+")
	sleep_regex = re.compile("sleep (\d+)")
	sleep_after_regex = re.compile("sleep_after ([GM]\d+) (\d+)")
	sleep_after_next_regex = re.compile("sleep_after_next ([GM]\d+) (\d+)")

	def __init__(self, read_timeout=5.0, write_timeout=10.0):
		self._read_timeout = read_timeout
		self._write_timeout = write_timeout

		self.incoming = CharCountingQueue(settings().getInt(["devel", "virtualPrinter", "rxBuffer"]), name="RxBuffer")
		self.outgoing = Queue.Queue()
		self.buffered = Queue.Queue(maxsize=settings().getInt(["devel", "virtualPrinter", "commandBuffer"]))

		for item in ['start\n', 'Marlin: Virtual Marlin!\n', '\x80\n', 'SD card ok\n']: # no sd card as default startup scenario
			self.outgoing.put(item)

		self.currentExtruder = 0
		self.temp = [0.0] * settings().getInt(["devel", "virtualPrinter", "numExtruders"])
		self.targetTemp = [0.0] * settings().getInt(["devel", "virtualPrinter", "numExtruders"])
		self.lastTempAt = time.time()
		self.bedTemp = 1.0
		self.bedTargetTemp = 1.0
		self.speeds = settings().get(["devel", "virtualPrinter", "movementSpeed"])

		self._relative = True
		self._lastX = None
		self._lastY = None
		self._lastZ = None
		self._lastE = None

		self._unitModifier = 1

		self._virtualSd = settings().getBaseFolder("virtualSd")
		self._sdCardReady = True
		self._sdPrinter = None
		self._sdPrintingSemaphore = threading.Event()
		self._selectedSdFile = None
		self._selectedSdFileSize = None
		self._selectedSdFilePos = None
		self._writingToSd = False
		self._newSdFilePos = None
		self._heatupThread = None

		self._okBeforeCommandOutput = settings().getBoolean(["devel", "virtualPrinter", "okBeforeCommandOutput"])

		self.currentLine = 0
		self.lastN = 0

		self._incoming_lock = threading.RLock()

		self._sleepAfterNext = dict()
		self._sleepAfter = dict()

		waitThread = threading.Thread(target=self._sendWaitAfterTimeout)
		waitThread.start()

		readThread = threading.Thread(target=self._processIncoming)
		readThread.start()

		bufferThread = threading.Thread(target=self._processBuffer)
		bufferThread.start()

	def __str__(self):
		return "VIRTUAL(read_timeout={read_timeout},write_timeout={write_timeout},options={options})"\
			.format(read_timeout=self._read_timeout, write_timeout=self._write_timeout, options=settings().get(["devel", "virtualPrinter"]))

	def _clearQueue(self, queue):
		try:
			while queue.get(block=False):
				continue
		except Queue.Empty:
			pass

	def _processIncoming(self):
		while self.incoming is not None:
			self._simulateTemps()

			try:
				data = self.incoming.get(timeout=0.01)
			except Queue.Empty:
				continue

			if data is None:
				continue

			data = data.strip()

			# strip checksum
			if "*" in data:
				data = data[:data.rfind("*")]
				self.currentLine += 1
			elif settings().getBoolean(["devel", "virtualPrinter", "forceChecksum"]):
				self.outgoing.put("Error: Missing checksum")
				continue

			# track N = N + 1
			if data.startswith("N") and "M110" in data:
				linenumber = int(re.search("N([0-9]+)", data).group(1))
				self.lastN = linenumber
				self.currentLine = linenumber
				self._sendOk()
				continue
			elif data.startswith("N"):
				linenumber = int(re.search("N([0-9]+)", data).group(1))
				expected = self.lastN + 1
				if linenumber != expected:
					with self._incoming_lock:
						self._clearQueue(self.incoming)
						self.outgoing.put("Error: expected line %d got %d" % (expected, linenumber))
						self.outgoing.put("Resend:%d" % expected)
						self.outgoing.put("ok")
					continue
				elif self.currentLine == 100:
					# simulate a resend at line 100
					with self._incoming_lock:
						self._clearQueue(self.incoming)
						self.outgoing.put("Error: Line Number is not Last Line Number\n")
						self.outgoing.put("rs 100\n")
						self.outgoing.put("ok")
					continue
				else:
					self.lastN = linenumber
				data = data.split(None, 1)[1].strip()

			data += "\n"

			# shortcut for writing to SD
			if self._writingToSd and not self._selectedSdFile is None and not "M29" in data:
				with open(self._selectedSdFile, "a") as f:
					f.write(data)
				self._sendOk()
				continue

			if data.strip() == "version":
				from octoprint._version import get_versions
				self.outgoing.put("OctoPrint VirtualPrinter v" + get_versions()["version"])
				continue

			if len(data.strip()) > 0 and self._okBeforeCommandOutput:
				self._sendOk()

			#print "Send: %s" % (data.rstrip())
			if 'M104' in data or 'M109' in data:
				self._parseHotendCommand(data)

			if 'M140' in data or 'M190' in data:
				self._parseBedCommand(data)

			if 'M105' in data:
				self._processTemperatureQuery()
				continue
			elif 'M20' in data:
				if self._sdCardReady:
					self._listSd()
			elif 'M21' in data:
				self._sdCardReady = True
				self.outgoing.put("SD card ok")
			elif 'M22' in data:
				self._sdCardReady = False
			elif 'M23' in data:
				if self._sdCardReady:
					filename = data.split(None, 1)[1].strip()
					self._selectSdFile(filename)
			elif 'M24' in data:
				if self._sdCardReady:
					self._startSdPrint()
			elif 'M25' in data:
				if self._sdCardReady:
					self._pauseSdPrint()
			elif 'M26' in data:
				if self._sdCardReady:
					pos = int(re.search("S([0-9]+)", data).group(1))
					self._setSdPos(pos)
			elif 'M27' in data:
				if self._sdCardReady:
					self._reportSdStatus()
			elif 'M28' in data:
				if self._sdCardReady:
					filename = data.split(None, 1)[1].strip()
					self._writeSdFile(filename)
			elif 'M29' in data:
				if self._sdCardReady:
					self._finishSdFile()
			elif 'M30' in data:
				if self._sdCardReady:
					filename = data.split(None, 1)[1].strip()
					self._deleteSdFile(filename)
			elif "M114" in data:
				# send dummy position report
				output = "C: X:10.00 Y:3.20 Z:5.20 E:1.24"
				if not self._okBeforeCommandOutput:
					output = "ok " + output
				self.outgoing.put(output)
				continue
			elif "M117" in data:
				# we'll just use this to echo a message, to allow playing around with pause triggers
				self.outgoing.put("echo:%s" % re.search("M117\s+(.*)", data).group(1))
			elif "M999" in data:
				# mirror Marlin behaviour
				self.outgoing.put("Resend: 1")
			elif data.startswith("T"):
				self.currentExtruder = int(re.search("T(\d+)", data).group(1))
				self.outgoing.put("Active Extruder: %d" % self.currentExtruder)
			elif "G20" in data:
				self._unitModifier = 1.0 / 2.54
				if self._lastX is not None:
					self._lastX *= 2.54
				if self._lastY is not None:
					self._lastY *= 2.54
				if self._lastZ is not None:
					self._lastZ *= 2.54
				if self._lastE is not None:
					self._lastE *= 2.54
			elif "G21" in data:
				self._unitModifier = 1.0
				if self._lastX is not None:
					self._lastX /= 2.54
				if self._lastY is not None:
					self._lastY /= 2.54
				if self._lastZ is not None:
					self._lastZ /= 2.54
				if self._lastE is not None:
					self._lastE /= 2.54
			elif "G90" in data:
				self._relative = False
			elif "G91" in data:
				self._relative = True
			elif "G92" in data:
				self._setPosition(data)
			elif data.startswith("!!DEBUG:"):
				self._debugTrigger(data[len("!!DEBUG:"):].strip())

			elif data.startswith("G0") or data.startswith("G1") or data.startswith("G2") or data.startswith("G3") \
					or data.startswith("G28") or data.startswith("G29") or data.startswith("G30") \
					or data.startswith("G31") or data.startswith("G32"):
				# simulate reprap buffered commands via a Queue with maxsize which internally simulates the moves
				self.buffered.put(data)

			if len(self._sleepAfter) or len(self._sleepAfterNext):
				command_match = VirtualPrinter.command_regex.match(data)
				if command_match is not None:
					command = command_match.group(0)

					interval = None
					if command in self._sleepAfter:
						interval = self._sleepAfter[command]
					elif command in self._sleepAfterNext:
						interval = self._sleepAfterNext[command]
						del self._sleepAfterNext[command]

					if interval is not None:
						self.outgoing.put("// sleeping for {interval} seconds".format(interval=interval))
						time.sleep(interval)

			if len(data.strip()) > 0 and not self._okBeforeCommandOutput:
				self._sendOk()

	def _debugTrigger(self, data):
		if data == "action_pause":
			self.outgoing.put("// action:pause")
		elif data == "action_resume":
			self.outgoing.put("// action:resume")
		elif data == "action_disconnect":
			self.outgoing.put("// action:disconnect")
		elif data == "action_custom":
			self.outgoing.put("// action:custom")
		else:
			try:
				sleep_match = VirtualPrinter.sleep_regex.match(data)
				sleep_after_match = VirtualPrinter.sleep_after_regex.match(data)
				sleep_after_next_match = VirtualPrinter.sleep_after_next_regex.match(data)

				if sleep_match is not None:
					interval = int(sleep_match.group(1))
					self.outgoing.put("// sleeping for {interval} seconds".format(interval=interval))
					time.sleep(interval)
				elif sleep_after_match is not None:
					command = sleep_after_match.group(1)
					interval = int(sleep_after_match.group(2))
					self._sleepAfter[command] = interval
					self.outgoing.put("// going to sleep {interval} seconds after each {command}".format(**locals()))
				elif sleep_after_next_match is not None:
					command = sleep_after_next_match.group(1)
					interval = int(sleep_after_next_match.group(2))
					self._sleepAfterNext[command] = interval
					self.outgoing.put("// going to sleep {interval} seconds after next {command}".format(**locals()))
			except:
				pass

	def _listSd(self):
		self.outgoing.put("Begin file list")
		if settings().getBoolean(["devel", "virtualPrinter", "extendedSdFileList"]):
			items = map(
				lambda x: "%s %d" % (x.upper(), os.stat(os.path.join(self._virtualSd, x)).st_size),
				os.listdir(self._virtualSd)
			)
		else:
			items = map(
				lambda x: x.upper(),
				os.listdir(self._virtualSd)
			)
		for item in items:
			self.outgoing.put(item)
		self.outgoing.put("End file list")

	def _selectSdFile(self, filename):
		if filename.startswith("/"):
			filename = filename[1:]
		file = os.path.join(self._virtualSd, filename.lower())
		if not os.path.exists(file) or not os.path.isfile(file):
			self.outgoing.put("open failed, File: %s." % filename)
		else:
			self._selectedSdFile = file
			self._selectedSdFileSize = os.stat(file).st_size
			self.outgoing.put("File opened: %s  Size: %d" % (filename, self._selectedSdFileSize))
			self.outgoing.put("File selected")

	def _startSdPrint(self):
		if self._selectedSdFile is not None:
			if self._sdPrinter is None:
				self._sdPrinter = threading.Thread(target=self._sdPrintingWorker)
				self._sdPrinter.start()
		self._sdPrintingSemaphore.set()

	def _pauseSdPrint(self):
		self._sdPrintingSemaphore.clear()

	def _setSdPos(self, pos):
		self._newSdFilePos = pos

	def _reportSdStatus(self):
		if self._sdPrinter is not None and self._sdPrintingSemaphore.is_set:
			self.outgoing.put("SD printing byte %d/%d" % (self._selectedSdFilePos, self._selectedSdFileSize))
		else:
			self.outgoing.put("Not SD printing")

	def _processTemperatureQuery(self):
		includeTarget = not settings().getBoolean(["devel", "virtualPrinter", "repetierStyleTargetTemperature"])
		includeOk = not self._okBeforeCommandOutput

		# send simulated temperature data
		if settings().getInt(["devel", "virtualPrinter", "numExtruders"]) > 1:
			allTemps = []
			for i in range(len(self.temp)):
				allTemps.append((i, self.temp[i], self.targetTemp[i]))
			allTempsString = " ".join(map(lambda x: "T%d:%.2f /%.2f" % x if includeTarget else "T%d:%.2f" % (x[0], x[1]), allTemps))

			if settings().getBoolean(["devel", "virtualPrinter", "smoothieTemperatureReporting"]):
				allTempsString = allTempsString.replace("T0:", "T:")

			if settings().getBoolean(["devel", "virtualPrinter", "hasBed"]):
				if includeTarget:
					allTempsString = "B:%.2f /%.2f %s" % (self.bedTemp, self.bedTargetTemp, allTempsString)
				else:
					allTempsString = "B:%.2f %s" % (self.bedTemp, allTempsString)

			if settings().getBoolean(["devel", "virtualPrinter", "includeCurrentToolInTemps"]):
				if includeTarget:
					output = "T:%.2f /%.2f %s @:64\n" % (self.temp[self.currentExtruder], self.targetTemp[self.currentExtruder] + 1, allTempsString)
				else:
					output = "T:%.2f %s @:64\n" % (self.temp[self.currentExtruder], allTempsString)
			else:
				output = "%s @:64\n" % allTempsString
		else:
			if includeTarget:
				output = "T:%.2f /%.2f B:%.2f /%.2f @:64\n" % (self.temp[0], self.targetTemp[0], self.bedTemp, self.bedTargetTemp)
			else:
				output = "T:%.2f B:%.2f @:64\n" % (self.temp[0], self.bedTemp)

		if includeOk:
			output = "ok " + output
		self.outgoing.put(output)

	def _parseHotendCommand(self, line):
		tool = 0
		toolMatch = re.search('T([0-9]+)', line)
		if toolMatch:
			try:
				tool = int(toolMatch.group(1))
			except:
				pass

		if tool >= settings().getInt(["devel", "virtualPrinter", "numExtruders"]):
			return

		try:
			self.targetTemp[tool] = float(re.search('S([0-9]+)', line).group(1))
		except:
			pass

		if "M109" in line:
			self._waitForHeatup("tool%d" % tool)
		if settings().getBoolean(["devel", "virtualPrinter", "repetierStyleTargetTemperature"]):
			self.outgoing.put("TargetExtr%d:%d" % (tool, self.targetTemp[tool]))

	def _parseBedCommand(self, line):
		try:
			self.bedTargetTemp = float(re.search('S([0-9]+)', line).group(1))
		except:
			pass

		if "M190" in line:
			self._waitForHeatup("bed")
		if settings().getBoolean(["devel", "virtualPrinter", "repetierStyleTargetTemperature"]):
			self.outgoing.put("TargetBed:%d" % self.bedTargetTemp)

	def _performMove(self, line):
		matchX = re.search("X([0-9.]+)", line)
		matchY = re.search("Y([0-9.]+)", line)
		matchZ = re.search("Z([0-9.]+)", line)
		matchE = re.search("E([0-9.]+)", line)

		duration = 0
		if matchX is not None:
			try:
				x = float(matchX.group(1))
				if self._relative or self._lastX is None:
					duration = max(duration, x * self._unitModifier / float(self.speeds["x"]) * 60.0)
				else:
					duration = max(duration, (x - self._lastX) * self._unitModifier / float(self.speeds["x"]) * 60.0)
				self._lastX = x
			except:
				pass
		if matchY is not None:
			try:
				y = float(matchY.group(1))
				if self._relative or self._lastY is None:
					duration = max(duration, y * self._unitModifier / float(self.speeds["y"]) * 60.0)
				else:
					duration = max(duration, (y - self._lastY) * self._unitModifier / float(self.speeds["y"]) * 60.0)
				self._lastY = y
			except:
				pass
		if matchZ is not None:
			try:
				z = float(matchZ.group(1))
				if self._relative or self._lastZ is None:
					duration = max(duration, z * self._unitModifier / float(self.speeds["z"]) * 60.0)
				else:
					duration = max(duration, (z - self._lastZ) * self._unitModifier / float(self.speeds["z"]) * 60.0)
				self._lastZ = z
			except:
				pass
		if matchE is not None:
			try:
				e = float(matchE.group(1))
				if self._relative or self._lastE is None:
					duration = max(duration, e * self._unitModifier / float(self.speeds["e"]) * 60.0)
				else:
					duration = max(duration, (e - self._lastE) * self._unitModifier / float(self.speeds["e"]) * 60.0)
				self._lastE = e
			except:
				pass

		if duration:
			if settings().getBoolean(["devel", "virtualPrinter", "waitOnLongMoves"]):
				slept = 0
				while duration - slept > self._read_timeout:
					time.sleep(self._read_timeout)
					self.outgoing.put("wait")
					slept += self._read_timeout
			else:
				time.sleep(duration)

	def _setPosition(self, line):
		matchX = re.search("X([0-9.]+)", line)
		matchY = re.search("Y([0-9.]+)", line)
		matchZ = re.search("Z([0-9.]+)", line)
		matchE = re.search("E([0-9.]+)", line)

		if matchX is None and matchY is None and matchZ is None and matchE is None:
			self._lastX = self._lastY = self._lastZ = self._lastE = 0
		else:
			if matchX is not None:
				try:
					self._lastX = float(matchX.group(1))
				except:
					pass
			if matchY is not None:
				try:
					self._lastY = float(matchY.group(1))
				except:
					pass
			if matchZ is not None:
				try:
					self._lastZ = float(matchZ.group(1))
				except:
					pass
			if matchE is not None:
				try:
					self._lastE = float(matchE.group(1))
				except:
					pass

	def _writeSdFile(self, filename):
		if filename.startswith("/"):
			filename = filename[1:]
		file = os.path.join(self._virtualSd, filename).lower()
		if os.path.exists(file):
			if os.path.isfile(file):
				os.remove(file)
			else:
				self.outgoing.put("error writing to file")

		self._writingToSd = True
		self._selectedSdFile = file
		self.outgoing.put("Writing to file: %s" % filename)

	def _finishSdFile(self):
		self._writingToSd = False
		self._selectedSdFile = None

	def _sdPrintingWorker(self):
		self._selectedSdFilePos = 0
		with open(self._selectedSdFile, "r") as f:
			for line in iter(f.readline, ""):
				# reset position if requested by client
				if self._newSdFilePos is not None:
					f.seek(self._newSdFilePos)
					self._newSdFilePos = None

				# read current file position
				self._selectedSdFilePos = f.tell()

				# if we are paused, wait for unpausing
				self._sdPrintingSemaphore.wait()

				# set target temps
				if 'M104' in line or 'M109' in line:
					self._parseHotendCommand(line)
				if 'M140' in line or 'M190' in line:
					self._parseBedCommand(line)

				time.sleep(settings().getFloat(["devel", "virtualPrinter", "throttle"]))

		self._sdPrintingSemaphore.clear()
		self._selectedSdFilePos = 0
		self._sdPrinter = None
		self.outgoing.put("Done printing file")

	def _waitForHeatup(self, heater):
		delta = 1
		delay = 1
		if heater.startswith("tool"):
			toolNum = int(heater[len("tool"):])
			while self.temp[toolNum] < self.targetTemp[toolNum] - delta or self.temp[toolNum] > self.targetTemp[toolNum] + delta:
				self._simulateTemps(delta=delta)
				self.outgoing.put("T:%0.2f" % self.temp[toolNum])
				time.sleep(delay)
		elif heater == "bed":
			while self.bedTemp < self.bedTargetTemp - delta or self.bedTemp > self.bedTargetTemp + delta:
				self._simulateTemps(delta=delta)
				self.outgoing.put("B:%0.2f" % self.bedTemp)
				time.sleep(delay)

	def _deleteSdFile(self, filename):
		if filename.startswith("/"):
			filename = filename[1:]
		f = os.path.join(self._virtualSd, filename)
		if os.path.exists(f) and os.path.isfile(f):
			os.remove(f)

	def _simulateTemps(self, delta=1):
		timeDiff = self.lastTempAt - time.time()
		self.lastTempAt = time.time()
		for i in range(len(self.temp)):
			if abs(self.temp[i] - self.targetTemp[i]) > delta:
				oldVal = self.temp[i]
				self.temp[i] += math.copysign(timeDiff * 10, self.targetTemp[i] - self.temp[i])
				if math.copysign(1, self.targetTemp[i] - oldVal) != math.copysign(1, self.targetTemp[i] - self.temp[i]):
					self.temp[i] = self.targetTemp[i]
				if self.temp[i] < 0:
					self.temp[i] = 0
		if abs(self.bedTemp - self.bedTargetTemp) > delta:
			oldVal = self.bedTemp
			self.bedTemp += math.copysign(timeDiff * 10, self.bedTargetTemp - self.bedTemp)
			if math.copysign(1, self.bedTargetTemp - oldVal) != math.copysign(1, self.bedTargetTemp - self.bedTemp):
				self.bedTemp = self.bedTargetTemp
			if self.bedTemp < 0:
				self.bedTemp = 0

	def _processBuffer(self):
		while self.buffered is not None:
			try:
				line = self.buffered.get(timeout=0.5)
			except Queue.Empty:
				continue

			if line is None:
				continue

			self._performMove(line)

	def write(self, data):
		with self._incoming_lock:
			if self.incoming is None or self.outgoing is None:
				return
			try:
				self.incoming.put(data, timeout=self._write_timeout)
			except Queue.Full:
				raise SerialTimeoutException()

	def readline(self):
		try:
			line = self.outgoing.get(timeout=self._read_timeout)
			time.sleep(settings().getFloat(["devel", "virtualPrinter", "throttle"]))
			return line
		except Queue.Empty:
			return ""

	def close(self):
		self.incoming = None
		self.outgoing = None
		self.buffered = None

	def _sendOk(self):
		if settings().getBoolean(["devel", "virtualPrinter", "okWithLinenumber"]):
			self.outgoing.put("ok %d" % self.lastN)
		else:
			self.outgoing.put("ok")

	def _sendWaitAfterTimeout(self, timeout=5):
		time.sleep(timeout)
		if self.outgoing is not None:
			self.outgoing.put("wait")

class CharCountingQueue(Queue.Queue):

	def __init__(self, maxsize, name=None):
		Queue.Queue.__init__(self, maxsize=maxsize)
		self._size = 0
		self._name = name

	def put(self, item, block=True, timeout=None):
		self.not_full.acquire()
		try:
			item_size = self._len(item)

			if not block:
				if self._qsize() + item_size >= self.maxsize:
					raise Queue.Full
			elif timeout is None:
				while self._qsize() + item_size >= self.maxsize:
					self.not_full.wait()
			elif timeout < 0:
				raise ValueError("'timeout' must be a positive number")
			else:
				endtime = time.time() + timeout
				while self._qsize() + item_size >= self.maxsize:
					remaining = endtime - time.time()
					if remaining <= 0.0:
						raise Queue.Full
					self.not_full.wait(remaining)

			self._put(item)
			self.unfinished_tasks += 1
			self.not_empty.notify()
		finally:
			self.not_full.release()

	def _len(self, item):
		return len(item)

	def _qsize(self, len=len):
		return self._size

	# Put a new item in the queue
	def _put(self, item):
		self.queue.append(item)
		self._size += self._len(item)

	# Get an item from the queue
	def _get(self):
		item = self.queue.popleft()
		self._size -= self._len(item)
		return item
