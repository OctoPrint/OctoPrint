# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 Gina Häußge - Released under terms of the AGPLv3 License"

from octoprint.comm.protocol import ProtocolListener, State
from octoprint.comm.protocol.reprap.protocol import RepRapProtocol
from octoprint.comm.transport.serialTransport import VirtualSerialTransport
from octoprint.filemanager.destinations import FileDestinations

if __name__ == "__main__":
	from octoprint.settings import settings
	settings(True)

	class DummyProtocolListener(ProtocolListener):
		def __init__(self):
			self.firstPrint = True

		def onStateChange(self, source, oldState, newState):
			print "New State: %s" % newState
			if newState == State.OPERATIONAL and self.firstPrint:
				self.firstPrint = False
				print "Selecting file and starting print job"
				protocol.selectFile("C:/Users/Gina/AppData/Roaming/OctoPrint/uploads/short.gcode", FileDestinations.LOCAL)
				protocol.startPrint()

		def onTemperatureUpdate(self, source, temperatureData):
			print "### Temperature update: %r" % temperatureData

		def onLogTx(self, source, tx):
			print ">> %s" % tx

		def onLogRx(self, source, rx):
			print "<< %s" % rx

		def onLogError(self, source, error):
			print "Error: %s" % error

	protocol = RepRapProtocol(VirtualSerialTransport, protocolListener=DummyProtocolListener())
	protocol.connect({})

	import time
	while True:
		time.sleep(0.1)