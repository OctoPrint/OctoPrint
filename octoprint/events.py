import sys
import datetime
import time
import math
import re
import logging, logging.config
import subprocess
import octoprint.printer as printer
import os

# right now we're logging a lot of extra information for testing
# we might want to comment out some of the logging eventually

class event_record(object):
	what = None
	who = None
	action = None
 
 
 # object that handles receiving events and dispatching them to listeners
 # 
class EventManager(object):
	def __init__(self):
		self.registered_events = []
		self.logger = logging.getLogger(__name__)
	 
	# Fire an event to anyone listening
	# any object can generate an event and any object can listen
	# pass in the event_name as a string (arbitrary, but case sensitive)
	# and any extra data that may pertain to the event
	def FireEvent (self,event_name,extra_data=None):
		self.logger.info (  "Firing event: " + event_name + " (" +str (extra_data)+")")
		for ev in self.registered_events:
			if event_name == ev.what:
				self.logger.info ( "Sending action to " + str(ev.who))
				if  ev.action != None :
					 ev.action (event_name,extra_data)
#            else:
#                self.logger.info ( "events don't match " + str(ev.what)+ " and " + event_name)
	
	
	# register a listener to an event -- pass in 
	# the event name (as a string), the target object
	# and the function to call
	def Register (self,event_name, target, action):
		new_ev =event_record()
		new_ev.what = event_name
		new_ev.who = target
		new_ev.action= action
		self.registered_events=self.registered_events+[new_ev]
		self.logger.info ("Registered event '"+new_ev.what+"' to invoke '"+str(new_ev.action)+"' on "+str(new_ev.who) )

		
	def unRegister (self,event_name, target, action):
		self.registered_events[:] = [e for e in  self.registered_events if event_name != e.what or e.action != action or e.who!=target]
	
	
	#sample event receiver
	#  def event_rec(self,event_name,extra_data):
	#     print str(self) + " Receieved event ", event_name ," (", str (extra_data),")"
	
	# and registering it:
	#   eventManager.Register("Startup",self,self.event_rec)

	
class event_dispatch(object):
	type = None
	event_string = None
	command_data = None
	
# object that hooks the event manager to system events, gcode, etc. 
# creates listeners to any events defined in the config.yaml settings
class EventResponse(object):
		
	def __init__(self, eventManager,printer):
		self.registered_responses= []
		self._eventManager = eventManager
		self._printer = printer
		self.logger = logging.getLogger(__name__)
		self._event_data = ""
	   
	def setupEvents(self,s):
		availableEvents = s.get(["system", "events"])
		for ev in availableEvents:
			event = event_dispatch()
			event.type = ev["type"].strip()
			event.event_string = ev["event"].strip()
			event.command_data = ev["command"]
			self._eventManager.Register ( event.event_string ,self,self.eventRec)
			self.registered_responses = self.registered_responses+[event]
			self.logger.info ("Registered "+event.type +" event '"+event.event_string+"' to execute '"+event.command_data+"'" )
		self.logger.info ( "Registered "+ str(len(self.registered_responses))+" events")
	 
	def eventRec (self,event_name, event_data):
		self.logger.info ( "Receieved event: " +  event_name +  " (" + str(event_data) + ")")
		self._event_data = event_data
		for ev in self.registered_responses:
			if ev.event_string == event_name:
				if ev.type == "system":
					self.executeSystemCommand (ev.command_data)
				if ev.type == "gcode":
					self.executeGCode(ev.command_data)
	
	# handle a few regex substs for job data passed to external apps
	def doStringProcessing (self, command_string):
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
		self.logger.info ("GCode command: " + command_string)
		self._printer.commands(command_string.split(','))
	   
	def executeSystemCommand(self,command_string):
		if command_string is None:
			return
		try:
			command_string = self.doStringProcessing(command_string)
			self.logger.info ("Executing system command: "+ command_string)
			#use Popen here since it won't wait for the shell to return...and we send some of these
			# commands during a print job, we don't want to block!
			subprocess.Popen(command_string,shell = True)
		except subprocess.CalledProcessError, e:
			self.logger.warn("Command failed with return code %i: %s" % (e.returncode, e.message))
		except Exception, ex:
			self.logger.exception("Command failed")
			
	
	