# coding=utf-8

__author__ = "Lars Norpchen"
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import datetime
import logging
import subprocess

from octoprint.settings import settings

# singleton
_instance = None

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
		self._registeredListeners = {}
		self._logger = logging.getLogger(__name__)

	def fire(self, event, payload=None):
		"""
		Fire an event to anyone subscribed to it

		Any object can generate an event and any object can subscribe to the event's name as a string (arbitrary, but
		case sensitive) and any extra payload data that may pertain to the event.

		Callbacks must implement the signature "callback(event, payload)", with "event" being the event's name and
		payload being a payload object specific to the event.
		"""

		if not event in self._registeredListeners.keys():
			return
		self._logger.debug("Firing event: %s (Payload: %r)" % (event, payload))

		eventListeners = self._registeredListeners[event]
		for listener in eventListeners:
			self._logger.debug("Sending action to %r" % listener)
			listener(event, payload)

	
	def subscribe(self, event, callback):
		"""
		Subscribe a listener to an event -- pass in the event name (as a string) and the callback object
		"""

		if not event in self._registeredListeners.keys():
			self._registeredListeners[event] = []

		if callback in self._registeredListeners[event]:
			# callback is already subscribed to the event
			return

		self._registeredListeners[event].append(callback)
		self._logger.debug("Subscribed listener %r for event %s" % (callback, event))

	def unsubscribe (self, event, callback):
		if not event in self._registeredListeners:
			# no callback registered for callback, just return
			return

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

		events = ["Startup", "Connected", "Disconnected", "ClientOpen", "ClientClosed", "PowerOn", "PowerOff", "Upload",
				  "FileSelected", "TransferStarted", "TransferDone", "PrintStarted", "PrintDone", "PrintFailed",
				  "Cancelled", "Home", "ZChange", "Paused", "Waiting", "Cooling", "Alert", "Conveyor", "Eject",
				  "CaptureStart", "CaptureDone", "MovieDone", "EStop", "Error"]
		self.subscribe(events)

	def eventCallback(self, event, payload):
		GenericEventListener.eventCallback(self, event, payload)
		self._logger.debug("Received event: %s (Payload: %r)" % (event, payload))

class CommandTrigger(GenericEventListener):
	def __init__(self, triggerType, printer):
		GenericEventListener.__init__(self)
		self._printer = printer
		self._subscriptions = {}

		self._initSubscriptions(triggerType)

	def _initSubscriptions(self, triggerType):
		"""
		Subscribes all events as defined in "events > $triggerType > subscriptions" in the settings with their
		respective commands.
		"""
		if not settings().get(["events", triggerType]):
			return

		if not settings().getBoolean(["events", triggerType, "enabled"]):
			return

		eventsToSubscribe = []
		for subscription in settings().get(["events", triggerType, "subscriptions"]):
			if not "event" in subscription.keys() or not "command" in subscription.keys():
				self._logger.info("Invalid %s, missing either event or command: %r" % (triggerType, subscription))
				continue

			event = subscription["event"]
			command = subscription["command"]

			if not event in self._subscriptions.keys():
				self._subscriptions[event] = []
			self._subscriptions[event].append(command)

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

		for command in self._subscriptions[event]:
			processedCommand = self._processCommand(command, payload)
			self.executeCommand(processedCommand)

	def executeCommand(self, command):
		"""
		Not implemented, override in child classes
		"""
		pass

	def _processCommand(self, command, payload):
		"""
		Performs string substitutions in the command string based on a couple of current parameters.

		The following substitutions are currently supported:

		  - %(currentZ)s : current Z position of the print head, or -1 if not available
		  - %(filename)s : current selected filename, or "NO FILE" if no file is selected
		  - %(progress)s : current print progress in percent, 0 if no print is in progress
		  - %(data)s : the string representation of the event's payload
		  - %(now)s : ISO 8601 representation of the current date and time
		"""

		params = {
			"currentZ": "-1",
			"filename": "NO FILE",
			"progress": "0",
			"data": str(payload),
			"now": datetime.datetime.now().isoformat()
		}

		currentData = self._printer.getCurrentData()

		if "currentZ" in currentData.keys() and currentData["currentZ"] is not None:
			params["currentZ"] = str(currentData["currentZ"])

		if "job" in currentData.keys() and currentData["job"] is not None:
			params["filename"] = currentData["job"]["filename"]
			if "progress" in currentData.keys() and currentData["progress"] is not None \
				and "progress" in currentData["progress"].keys() and currentData["progress"]["progress"] is not None:
				params["progress"] = str(round(currentData["progress"]["progress"] * 100))

		return command % params

class SystemCommandTrigger(CommandTrigger):
	"""
	Performs configured system commands for configured events.
	"""

	def __init__(self, printer):
		CommandTrigger.__init__(self, "systemCommandTrigger", printer)

	def executeCommand(self, command):
		try:
			self._logger.info("Executing system command: %s" % command)
			subprocess.Popen(command, shell=True)
		except subprocess.CalledProcessError, e:
			self._logger.warn("Command failed with return code %i: %s" % (e.returncode, e.message))
		except Exception, ex:
			self._logger.exception("Command failed")

class GcodeCommandTrigger(CommandTrigger):
	"""
	Sends configured GCODE commands to the printer for configured events.
	"""

	def __init__(self, printer):
		CommandTrigger.__init__(self, "gcodeCommandTrigger", printer)

	def executeCommand(self, command):
		self._logger.debug("Executing GCode command: %s" % command)
		self._printer.commands(command.split(","))
