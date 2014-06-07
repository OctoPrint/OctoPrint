# coding=utf-8

__author__ = "Andrew 'Nceromant' Andrianov <andrew@ncrmnt.org>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import logging
import os
import threading
import urllib
import time
import subprocess
import fnmatch
import datetime
import sys
import cwiid

import octoprint.util as util

from octoprint.settings import settings
from octoprint.events import eventManager

global current

def configureWii(config=None, persist=False, printer=None):
    global current
    if settings().getBoolean(["wii", "enabled"]):
        current = Wii(printer);


class Wii(object):
    	def __init__(self,printer):
		self._logger = logging.getLogger(__name__)
                self.printer = printer;
                eventManager().subscribe("PrintStarted", self.onPrintStarted)
                eventManager().subscribe("PrintFailed", self.onPrintDone)
                eventManager().subscribe("PrintDone", self.onPrintDone)
                eventManager().subscribe("PrintResumed", self.onPrintResumed)
                #TODO: Settings...
                self.ThreadRunning = True;
                self.handleInput = True;
		self._logger.info("WII now enabled, connect at will by holding 1+2")
                self._WiiThread = threading.Thread(target=self.WatchForWii)
                self._WiiThread.daemon = True
                self._WiiThread.start()

	def WatchForWii(self):
            while True:
                try:
                    self.wm = cwiid.Wiimote()
                    self.wm.rumble = 1;
                    time.sleep(0.5);
                    self.wm.rumble = 0;
                    
                    self.wm.rpt_mode = cwiid.RPT_BTN | cwiid.RPT_STATUS;
                    self.wm.enable(cwiid.FLAG_MESG_IFC);
                    self.wm.led = 0;
                    self.wm.mesg_callback = self.HandleWiiMessage;
                    led = 1;
                    while self.ThreadRunning:
                        self.wm.led = led;
                        led ^= 1;
                        time.sleep(1);
                except (RuntimeError, AttributeError):
                    pass


	def unload(self):
		if self._inTimelapse:
			self.stopTimelapse(doCreateMovie=False)

		# unsubscribe events
		eventManager().unsubscribe("PrintStarted", self.onPrintStarted)
		eventManager().unsubscribe("PrintFailed", self.onPrintDone)
		eventManager().unsubscribe("PrintDone", self.onPrintDone)
		eventManager().unsubscribe("PrintResumed", self.onPrintResumed)
		for (event, callback) in self.eventSubscriptions():
			eventManager().unsubscribe(event, callback)
                self.ThreadRunning = True;
                self._WiiThread.join();

        def HandleWiiMessage(self, mesg_list, time):
            if bool(self.wm.state['buttons'] & cwiid.BTN_HOME):
                self.printer.commands(settings().get(["wii", "BTN_HOME"]));

            if bool(self.wm.state['buttons'] & cwiid.BTN_A):
                self.printer.commands(settings().get(["wii", "BTN_A"]));

            if bool(self.wm.state['buttons'] & cwiid.BTN_PLUS):
                self.printer.commands(settings().get(["wii", "BTN_PLUS"]));

            if bool(self.wm.state['buttons'] & cwiid.BTN_MINUS):
                self.printer.commands(settings().get(["wii", "BTN_MINUS"]));

            if bool(self.wm.state['buttons'] & cwiid.BTN_UP):
                self.printer.commands(settings().get(["wii", "BTN_UP"]));

            if bool(self.wm.state['buttons'] & cwiid.BTN_DOWN):
                self.printer.commands(settings().get(["wii", "BTN_DOWN"]));

            if bool(self.wm.state['buttons'] & cwiid.BTN_LEFT):
                self.printer.commands(settings().get(["wii", "BTN_LEFT"]));

            if bool(self.wm.state['buttons'] & cwiid.BTN_RIGHT):
                self.printer.commands(settings().get(["wii", "BTN_RIGHT"]));

            if bool(self.wm.state['buttons'] & cwiid.BTN_B):
                self.printer.commands(settings().get(["wii", "BTN_B"]));
            
	def onPrintStarted(self, event, payload):
		"""
		Override this to perform additional actions upon start of a print job.
		"""
		self.HandleInput = True;

	def onPrintDone(self, event, payload):
		"""
		Override this to perform additional actions upon the stop of a print job.
		"""
		self.HandleInput = False;

	def onPrintResumed(self, event, payload):
		"""
		Override this to perform additional actions upon the pausing of a print job.
		"""
		self.HandleInput = False;

