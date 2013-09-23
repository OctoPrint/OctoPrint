from __future__ import absolute_import
# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


import time
import os
import re
import threading
import math

from octoprint.settings import settings

class VirtualPrinter():
	def __init__(self):
		self.readList = ['start\n', 'Marlin: Virtual Marlin!\n', '\x80\n', 'SD init fail\n'] # no sd card as default startup scenario
		self.temp = 0.0
		self.targetTemp = 0.0
		self.lastTempAt = time.time()
		self.bedTemp = 1.0
		self.bedTargetTemp = 1.0

		self._virtualSd = settings().getBaseFolder("virtualSd")
		self._sdCardReady = False
		self._sdPrinter = None
		self._sdPrintingSemaphore = threading.Event()
		self._selectedSdFile = None
		self._selectedSdFileSize = None
		self._selectedSdFilePos = None
		self._writingToSd = False
		self._newSdFilePos = None

		self.currentLine = 0
		self.lastN = 0

		waitThread = threading.Thread(target=self._sendWaitAfterTimeout)
		waitThread.start()

	def write(self, data):
		if self.readList is None:
			return

		data = data.strip()

		# strip checksum
		if "*" in data:
			data = data[:data.rfind("*")]
			self.currentLine += 1
		elif settings().getBoolean(["devel", "virtualPrinter", "forceChecksum"]):
			self.readList.append("Error: Missing checksum")
			return

		# track N = N + 1
		if data.startswith("N") and "M110" in data:
			linenumber = int(re.search("N([0-9]+)", data).group(1))
			self.lastN = linenumber
			self.currentLine = linenumber
			return
		elif data.startswith("N"):
			linenumber = int(re.search("N([0-9]+)", data).group(1))
			expected = self.lastN + 1
			if linenumber != expected:
				self.readList.append("Error: expected line %d got %d" % (expected, linenumber))
				self.readList.append("Resend:%d" % expected)
				if settings().getBoolean(["devel", "virtualPrinter", "okAfterResend"]):
					self.readList.append("ok")
				return
			elif self.currentLine == 100:
				# simulate a resend at line 100 of the last 5 lines
				self.lastN = 94
				self.readList.append("Error: Line Number is not Last Line Number\n")
				self.readList.append("rs %d\n" % (self.currentLine - 5))
				if settings().getBoolean(["devel", "virtualPrinter", "okAfterResend"]):
					self.readList.append("ok")
				return
			else:
				self.lastN = linenumber
			data = data.split(None, 1)[1].strip()

		data += "\n"

		# shortcut for writing to SD
		if self._writingToSd and not self._selectedSdFile is None and not "M29" in data:
			with open(self._selectedSdFile, "a") as f:
				f.write(data)
			self._sendOk()
			return

		#print "Send: %s" % (data.rstrip())
		if 'M104' in data or 'M109' in data:
			try:
				self.targetTemp = float(re.search('S([0-9]+)', data).group(1))
			except:
				pass
		if 'M140' in data or 'M190' in data:
			try:
				self.bedTargetTemp = float(re.search('S([0-9]+)', data).group(1))
			except:
				pass

		if 'M105' in data:
			# send simulated temperature data
			self.readList.append("ok T:%.2f /%.2f B:%.2f /%.2f @:64\n" % (self.temp, self.targetTemp, self.bedTemp, self.bedTargetTemp))
		elif 'M20' in data:
			if self._sdCardReady:
				self._listSd()
		elif 'M21' in data:
			self._sdCardReady = True
			self.readList.append("SD card ok")
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
			self.readList.append("ok C: X:10.00 Y:3.20 Z:5.20 E:1.24")
		elif "M117" in data:
			# we'll just use this to echo a message, to allow playing around with pause triggers
			self.readList.append("ok %s" % re.search("M117\s+(.*)", data).group(1))
		elif "M999" in data:
			# mirror Marlin behaviour
			self.readList.append("Resend: 1")
		elif len(data.strip()) > 0:
			self._sendOk()

	def _listSd(self):
		self.readList.append("Begin file list")
		for osFile in os.listdir(self._virtualSd):
			self.readList.append(osFile.upper())
		self.readList.append("End file list")
		self._sendOk()

	def _selectSdFile(self, filename):
		file = os.path.join(self._virtualSd, filename).lower()
		if not os.path.exists(file) or not os.path.isfile(file):
			self.readList.append("open failed, File: %s." % filename)
		else:
			self._selectedSdFile = file
			self._selectedSdFileSize = os.stat(file).st_size
			self.readList.append("File opened: %s  Size: %d" % (filename, self._selectedSdFileSize))
			self.readList.append("File selected")

	def _startSdPrint(self):
		if self._selectedSdFile is not None:
			if self._sdPrinter is None:
				self._sdPrinter = threading.Thread(target=self._sdPrintingWorker)
				self._sdPrinter.start()
		self._sdPrintingSemaphore.set()
		self._sendOk()

	def _pauseSdPrint(self):
		self._sdPrintingSemaphore.clear()
		self._sendOk()

	def _setSdPos(self, pos):
		self._newSdFilePos = pos

	def _reportSdStatus(self):
		if self._sdPrinter is not None and self._sdPrintingSemaphore.is_set:
			self.readList.append("SD printing byte %d/%d" % (self._selectedSdFilePos, self._selectedSdFileSize))
		else:
			self.readList.append("Not SD printing")

	def _writeSdFile(self, filename):
		file = os.path.join(self._virtualSd, filename).lower()
		if os.path.exists(file):
			if os.path.isfile(file):
				os.remove(file)
			else:
				self.readList.append("error writing to file")

		self._writingToSd = True
		self._selectedSdFile = file
		self.readList.append("Writing to file: %s" % filename)
		self._sendOk()

	def _finishSdFile(self):
		self._writingToSd = False
		self._selectedSdFile = None
		self._sendOk()

	def _sdPrintingWorker(self):
		self._selectedSdFilePos = 0
		with open(self._selectedSdFile, "r") as f:
			for line in f:
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
					try:
						self.targetTemp = float(re.search('S([0-9]+)', line).group(1))
					except:
						pass
				if 'M140' in line or 'M190' in line:
					try:
						self.bedTargetTemp = float(re.search('S([0-9]+)', line).group(1))
					except:
						pass

				time.sleep(0.01)

		self._sdPrintingSemaphore.clear()
		self._selectedSdFilePos = 0
		self._sdPrinter = None
		self.readList.append("Done printing file")

	def _deleteSdFile(self, filename):
		file = os.path.join(self._virtualSd, filename)
		if os.path.exists(file) and os.path.isfile(file):
			os.remove(file)
		self._sendOk()

	def readline(self):
		if self.readList is None:
			return ''
		n = 0
		timeDiff = self.lastTempAt - time.time()
		self.lastTempAt = time.time()
		if abs(self.temp - self.targetTemp) > 1:
			self.temp += math.copysign(timeDiff * 10, self.targetTemp - self.temp)
			if self.temp < 0:
				self.temp = 0
		if abs(self.bedTemp - self.bedTargetTemp) > 1:
			self.bedTemp += math.copysign(timeDiff * 10, self.bedTargetTemp - self.bedTemp)
			if self.bedTemp < 0:
				self.bedTemp = 0
		while len(self.readList) < 1:
			time.sleep(0.1)
			n += 1
			if n == 20:
				return ''
			if self.readList is None:
				return ''
		time.sleep(0.001)
		return self.readList.pop(0)

	def close(self):
		self.readList = None

	def _sendOk(self):
		if settings().getBoolean(["devel", "virtualPrinter", "okWithLinenumber"]):
			self.readList.append("ok %d" % self.lastN)
		else:
			self.readList.append("ok")

	def _sendWaitAfterTimeout(self, timeout=5):
		time.sleep(timeout)
		if self.readList is not None:
			self.readList.append("wait")

