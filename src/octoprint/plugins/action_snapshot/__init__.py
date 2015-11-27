# coding=utf-8
from __future__ import absolute_import

__plugin_name__ = "Snapshot Trigger action command"
__plugin_version__ = "0.0.1"
__plugin_description__ = "A plugin that triggers the event \"SNAPSHOT\" when receiving action:snapshot from the printer and used in timelapse."


# coding=utf-8

import octoprint.plugin
from octoprint.events import eventManager, Events

class SnapshotTriggerPlugin(octoprint.plugin.OctoPrintPlugin):

	def custom_action_handler(self, comm, line, action, *args, **kwargs):
		if not action == "snapshot":
			return
			
		eventManager().fire(Events.SNAPSHOT)
		
		self._logger.info("Received \"snapshot\" action from printer")



def __plugin_load__():
	plugin = SnapshotTriggerPlugin()

	global __plugin_implementation__
	__plugin_implementation__ = plugin

	global __plugin_hooks__
	__plugin_hooks__ = {"octoprint.comm.protocol.action": plugin.custom_action_handler}