import datetime
import re
import logging
import subprocess
import os

# right now we're logging a lot of extra information for testing
# we might want to comment out some of the logging eventually

class event_record(object):
	def __init__(self, what, who, action):
		self.what = what
		self.who = who
		self.action = action

class EventManager(object):
	"""
	Handles receiving events and dispatching them to listeners
	"""

	def __init__(self):
		self.registered_events = []
		self.logger = logging.getLogger(__name__)
	 
	def fire(self, name, payload=None):
		"""
		Fire an event to anyone listening.

		Any object can generate an event and any object can listen pass in the event_name as a string (arbitrary, but
		case sensitive) and any extra payload data that may pertain to the event.
		"""

		self.logger.debug("Firing event: %s (%r)" % (name, payload))
		for event in self.registered_events:
			(who, what, action) = event
			if name == what:
				self.logger.debug("Sending action to %r" % who)
				if action is not None:
					action(name, payload)

	
	def subscribe(self, name, target, action):
		"""
		Subscribe a listener to an event -- pass in the event name (as a string), the target object
		and the callback object
		"""

		newEvent = (name, target, action)
		self.registered_events = self.registered_events.append(newEvent)
		self.logger.debug("Registered event \"%s\" to invoke \"%r\" on %r" % (name, action, target))

	def unsubscribe (self, event_name, target, action):
		self.registered_events[:] = [e for e in self.registered_events if event_name != e.what or e.action != action or e.who != target]
	
	#sample event receiver
	#  def event_rec(self,event_name,extra_data):
	#     print str(self) + " Receieved event ", event_name ," (", str (extra_data),")"
	
	# and registering it:
	#   eventManager.Register("Startup",self,self.event_rec)

	
class event_dispatch(object):
	type = None
	event_string = None
	command_data = None
	
class EventResponse(object):
	"""
	Hooks the event manager to system events, gcode, etc. Creates listeners to any events defined in the settings.
	"""

	def __init__(self, eventManager,printer):
		self.registered_responses = []
		self._eventManager = eventManager
		self._printer = printer
		self.logger = logging.getLogger(__name__)
		self._event_data = ""
	   
	def setupEvents(self,s):
		availableEvents = s.get(["system", "events"])
		for event in availableEvents:
			name = event["event"].strip()
			action = event["type"].strip()
			data = event["command"]

			self._eventManager.subscribe(event.event_string, self, self.eventRec)

			self.registered_responses = self.registered_responses.append(event)
			self.logger.debug("Registered %s event \"%s\" to execute \"%s\"" % (event.type, event.event_string, event.command_data))
		self.logger.debug("Registered %d events" % len(self.registered_responses))
	 
	def eventRec (self,event_name, event_data):
		self.logger.debug("Received event: %s (%r)" % (event_name, event_data))
		self._event_data = event_data
		for ev in self.registered_responses:
			if ev.event_string == event_name:
				if ev.type == "system":
					self.executeSystemCommand (ev.command_data)
				if ev.type == "gcode":
					self.executeGCode(ev.command_data)
	
	def doStringProcessing (self, command_string):
		"""
		Handles a few regex substs for job data passed to external apps
		"""
		cmd_string_with_params = command_string
		cmd_string_with_params = re.sub("_ZHEIGHT_",str(self._printer._currentZ), cmd_string_with_params)
		if self._printer._filename:
			cmd_string_with_params = re.sub("_FILE_",os.path.basename(self._printer._filename), cmd_string_with_params)
		else:
			cmd_string_with_params = re.sub("_FILE_","NO FILE", cmd_string_with_params)
		# cut down to 2 decimal places, forcing through an int to avoid the 10.320000000001 floating point thing...
		if self._printer._gcodeList and self._printer._progress: 
			prog =  int(10000.0 * self._printer._progress / len(self._printer._gcodeList))/100.0 
		else: 
			prog = 0.0
		cmd_string_with_params = re.sub("_PROGRESS_",str(prog), cmd_string_with_params)
		if self._printer._comm:
			cmd_string_with_params = re.sub("_LINE_",str(self._printer._comm._gcodePos), cmd_string_with_params)
		else:
			cmd_string_with_params = re.sub("_LINE_","0", cmd_string_with_params)
		if self._event_data:
			cmd_string_with_params = re.sub("_DATA_",str(self._event_data), cmd_string_with_params)            
		else: 
			cmd_string_with_params = re.sub("_DATA_","", cmd_string_with_params)                        
		cmd_string_with_params = re.sub("_NOW_",str(datetime.datetime.now()), cmd_string_with_params)                        
		return cmd_string_with_params

		
	def executeGCode(self,command_string):
		command_string = self.doStringProcessing(command_string)
		self.logger.debug("GCode command: " + command_string)
		self._printer.commands(command_string.split(','))
	   
	def executeSystemCommand(self, command_string):
		if command_string is None:
			return

		try:
			command_string = self.doStringProcessing(command_string)
			self.logger.info("Executing system command: %s" % command_string)
			#use Popen here since it won't wait for the shell to return...and we send some of these
			# commands during a print job, we don't want to block!
			subprocess.Popen(command_string, shell=True)
		except subprocess.CalledProcessError, e:
			self.logger.warn("Command failed with return code %i: %s" % (e.returncode, e.message))
		except Exception, ex:
			self.logger.exception("Command failed")
