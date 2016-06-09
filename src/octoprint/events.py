# coding=utf-8
from __future__ import (print_function, absolute_import)

__author__ = "Gina Häußge <osd@foosel.net>, Lars Norpchen"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import datetime
import logging
import subprocess
import Queue
import threading
import collections

from octoprint.settings import settings
import octoprint.plugin

# singleton
_instance = None


def all_events():
	return [getattr(Events, name) for name in Events.__dict__ if not name.startswith("__")]


class Events(object):
	# application startup
	STARTUP = "Startup"

	# connect/disconnect to printer
	CONNECTED = "Connected"
	DISCONNECTED = "Disconnected"

	# connect/disconnect by client
	CLIENT_OPENED = "ClientOpened"
	CLIENT_CLOSED = "ClientClosed"

	# File management
	UPLOAD = "Upload"
	FILE_SELECTED = "FileSelected"
	FILE_DESELECTED = "FileDeselected"
	UPDATED_FILES = "UpdatedFiles"
	METADATA_ANALYSIS_STARTED = "MetadataAnalysisStarted"
	METADATA_ANALYSIS_FINISHED = "MetadataAnalysisFinished"
	METADATA_STATISTICS_UPDATED = "MetadataStatisticsUpdated"

	# SD Upload
	TRANSFER_STARTED = "TransferStarted"
	TRANSFER_DONE = "TransferDone"

	# print job
	PRINT_STARTED = "PrintStarted"
	PRINT_DONE = "PrintDone"
	PRINT_FAILED = "PrintFailed"
	PRINT_CANCELLED = "PrintCancelled"
	PRINT_PAUSED = "PrintPaused"
	PRINT_RESUMED = "PrintResumed"
	ERROR = "Error"

	# print/gcode events
	POWER_ON = "PowerOn"
	POWER_OFF = "PowerOff"
	HOME = "Home"
	Z_CHANGE = "ZChange"
	WAITING = "Waiting"
	DWELL = "Dwelling"
	COOLING = "Cooling"
	ALERT = "Alert"
	CONVEYOR = "Conveyor"
	EJECT = "Eject"
	E_STOP = "EStop"
	REGISTERED_MESSAGE_RECEIVED = "RegisteredMessageReceived"

	# Timelapse
	CAPTURE_START = "CaptureStart"
	CAPTURE_DONE = "CaptureDone"
	CAPTURE_FAILED = "CaptureFailed"
	POSTROLL_START = "PostRollStart"
	POSTROLL_END = "PostRollEnd"
	MOVIE_RENDERING = "MovieRendering"
	MOVIE_DONE = "MovieDone"
	MOVIE_FAILED = "MovieFailed"

	# Slicing
	SLICING_STARTED = "SlicingStarted"
	SLICING_DONE = "SlicingDone"
	SLICING_FAILED = "SlicingFailed"
	SLICING_CANCELLED = "SlicingCancelled"
	SLICING_PROFILE_ADDED = "SlicingProfileAdded"
	SLICING_PROFILE_MODIFIED = "SlicingProfileModified"
	SLICING_PROFILE_DELETED = "SlicingProfileDeleted"

	# Printer Profiles
	PRINTER_PROFILE_ADDED = "PrinterProfileAdded"
	PRINTER_PROFILE_MODIFIED = "PrinterProfileModified"
	PRINTER_PROFILE_DELETED = "PrinterProfileDeleted"

	# Settings
	SETTINGS_UPDATED = "SettingsUpdated"


def eventManager():
	global _instance
	if _instance is None:
		_instance = EventManager()
	return _instance


class EventManager(object):
	"""
	Handles receiving events and dispatching them to subscribers
	"""

	def __init__(self):
		self._registeredListeners = collections.defaultdict(list)
		self._logger = logging.getLogger(__name__)

		self._queue = Queue.Queue()
		self._worker = threading.Thread(target=self._work)
		self._worker.daemon = True
		self._worker.start()

	def _work(self):
		try:
			while True:
				event, payload = self._queue.get(True)

				eventListeners = self._registeredListeners[event]
				self._logger.debug("Firing event: %s (Payload: %r)" % (event, payload))

				for listener in eventListeners:
					self._logger.debug("Sending action to %r" % listener)
					try:
						listener(event, payload)
					except:
						self._logger.exception("Got an exception while sending event %s (Payload: %r) to %s" % (event, payload, listener))

				octoprint.plugin.call_plugin(octoprint.plugin.types.EventHandlerPlugin,
				                             "on_event",
				                             args=[event, payload])
		except:
			self._logger.exception("Ooops, the event bus worker loop crashed")

	def fire(self, event, payload=None):
		"""
		Fire an event to anyone subscribed to it

		Any object can generate an event and any object can subscribe to the event's name as a string (arbitrary, but
		case sensitive) and any extra payload data that may pertain to the event.

		Callbacks must implement the signature "callback(event, payload)", with "event" being the event's name and
		payload being a payload object specific to the event.
		"""

		self._queue.put((event, payload))

		if event == Events.UPDATED_FILES and "type" in payload and payload["type"] == "printables":
			# when sending UpdatedFiles with type "printables", also send another event with deprecated type "gcode"
			# TODO v1.3.0 Remove again
			import copy
			legacy_payload = copy.deepcopy(payload)
			legacy_payload["type"] = "gcode"
			self._queue.put((event, legacy_payload))

	def subscribe(self, event, callback):
		"""
		Subscribe a listener to an event -- pass in the event name (as a string) and the callback object
		"""

		if callback in self._registeredListeners[event]:
			# callback is already subscribed to the event
			return

		self._registeredListeners[event].append(callback)
		self._logger.debug("Subscribed listener %r for event %s" % (callback, event))

	def unsubscribe (self, event, callback):
		"""
		Unsubscribe a listener from an event -- pass in the event name (as string) and the callback object
		"""

		if not callback in self._registeredListeners[event]:
			# callback not subscribed to event, just return
			return

		self._registeredListeners[event].remove(callback)
		self._logger.debug("Unsubscribed listener %r for event %s" % (callback, event))


class GenericEventListener(object):
	"""
	The GenericEventListener can be subclassed to easily create custom event listeners.
	"""

	def __init__(self):
		self._logger = logging.getLogger(__name__)

	def subscribe(self, events):
		"""
		Subscribes the eventCallback method for all events in the given list.
		"""

		for event in events:
			eventManager().subscribe(event, self.eventCallback)

	def unsubscribe(self, events):
		"""
		Unsubscribes the eventCallback method for all events in the given list
		"""

		for event in events:
			eventManager().unsubscribe(event, self.eventCallback)

	def eventCallback(self, event, payload):
		"""
		Actual event callback called with name of event and optional payload. Not implemented here, override in
		child classes.
		"""
		pass


class DebugEventListener(GenericEventListener):
	def __init__(self):
		GenericEventListener.__init__(self)

		events = filter(lambda x: not x.startswith("__"), dir(Events))
		self.subscribe(events)

	def eventCallback(self, event, payload):
		GenericEventListener.eventCallback(self, event, payload)
		self._logger.debug("Received event: %s (Payload: %r)" % (event, payload))


class CommandTrigger(GenericEventListener):
	def __init__(self, printer):
		GenericEventListener.__init__(self)
		self._printer = printer
		self._subscriptions = {}

		self._initSubscriptions()

	def _initSubscriptions(self):
		"""
		Subscribes all events as defined in "events > $triggerType > subscriptions" in the settings with their
		respective commands.
		"""
		if not settings().get(["events"]):
			return

		if not settings().getBoolean(["events", "enabled"]):
			return

		eventsToSubscribe = []
		for subscription in settings().get(["events", "subscriptions"]):
			if not "event" in subscription.keys() or not "command" in subscription.keys() \
					or not "type" in subscription.keys() or not subscription["type"] in ["system", "gcode"]:
				self._logger.info("Invalid command trigger, missing either event, type or command or type is invalid: %r" % subscription)
				continue

			if "enabled" in subscription.keys() and not subscription["enabled"]:
				self._logger.info("Disabled command trigger: %r" % subscription)
				continue

			event = subscription["event"]
			command = subscription["command"]
			commandType = subscription["type"]
			debug = subscription["debug"] if "debug" in subscription else False

			if not event in self._subscriptions.keys():
				self._subscriptions[event] = []
			self._subscriptions[event].append((command, commandType, debug))

			if not event in eventsToSubscribe:
				eventsToSubscribe.append(event)

		self.subscribe(eventsToSubscribe)

	def eventCallback(self, event, payload):
		"""
		Event callback, iterates over all subscribed commands for the given event, processes the command
		string and then executes the command via the abstract executeCommand method.
		"""

		GenericEventListener.eventCallback(self, event, payload)

		if not event in self._subscriptions:
			return

		for command, commandType, debug in self._subscriptions[event]:
			try:
				if isinstance(command, (tuple, list, set)):
					processedCommand = []
					for c in command:
						processedCommand.append(self._processCommand(c, payload))
				else:
					processedCommand = self._processCommand(command, payload)
				self.executeCommand(processedCommand, commandType, debug=debug)
			except KeyError, e:
				self._logger.warn("There was an error processing one or more placeholders in the following command: %s" % command)

	def executeCommand(self, command, commandType, debug=False):
		if commandType == "system":
			self._executeSystemCommand(command, debug=debug)
		elif commandType == "gcode":
			self._executeGcodeCommand(command, debug=debug)

	def _executeSystemCommand(self, command, debug=False):
		def commandExecutioner(command):
			if debug:
				self._logger.info("Executing system command: %s" % command)
			# we run this with shell=True since we have to trust whatever
			# our admin configured as command and since we want to allow
			# shell-alike handling here...
			subprocess.Popen(command, shell=True)

		try:
			if isinstance(command, (list, tuple, set)):
				for c in command:
					commandExecutioner(c)
			else:
				commandExecutioner(command)
		except subprocess.CalledProcessError, e:
			self._logger.warn("Command failed with return code %i: %s" % (e.returncode, str(e)))
		except:
			self._logger.exception("Command failed")

	def _executeGcodeCommand(self, command, debug=False):
		commands = [command]
		if isinstance(command, (list, tuple, set)):
			commands = list(command)
		if debug:
			self._logger.info("Executing GCode commands: %r" % command)
		self._printer.commands(commands)

	def _processCommand(self, command, payload):
		"""
		Performs string substitutions in the command string based on a couple of current parameters.

		The following substitutions are currently supported:

		  - {__currentZ} : current Z position of the print head, or -1 if not available
		  - {__filename} : current selected filename, or "NO FILE" if no file is selected
		  - {__progress} : current print progress in percent, 0 if no print is in progress
		  - {__data} : the string representation of the event's payload
		  - {__now} : ISO 8601 representation of the current date and time

		Additionally, the keys of the event's payload can also be used as placeholder.
		"""

		params = {
			"__currentZ": "-1",
			"__filename": "NO FILE",
			"__progress": "0",
			"__data": str(payload),
			"__now": datetime.datetime.now().isoformat()
		}

		currentData = self._printer.get_current_data()

		if "currentZ" in currentData.keys() and currentData["currentZ"] is not None:
			params["__currentZ"] = str(currentData["currentZ"])

		if "job" in currentData.keys() and currentData["job"] is not None:
			params["__filename"] = currentData["job"]["file"]["name"]
			if "progress" in currentData.keys() and currentData["progress"] is not None \
				and "completion" in currentData["progress"].keys() and currentData["progress"]["completion"] is not None:
				params["__progress"] = str(round(currentData["progress"]["completion"] * 100))

		# now add the payload keys as well
		if isinstance(payload, dict):
			params.update(payload)

		return command.format(**params)
