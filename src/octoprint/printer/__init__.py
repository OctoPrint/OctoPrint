# coding=utf-8
"""
This module defines the interface for communicating with a connected printer.

The communication is in fact divided in two components, the :class:`PrinterInterface` and a deeper lying
communication layer. However, plugins should only ever need to use the :class:`PrinterInterface` as the
abstracted version of the actual printer communication.

.. autofunction:: get_connection_options

.. autoclass:: PrinterInterface
   :members:

.. autoclass:: PrinterCallback
   :members:
"""

from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import re

import octoprint.util.comm as comm
from octoprint.settings import settings

def get_connection_options():
	"""
	Retrieves the available ports, baudrates, preferred port and baudrate for connecting to the printer.

	Returned ``dict`` has the following structure::

	    ports: <list of available serial ports>
	    baudrates: <list of available baudrates>
	    portPreference: <configured default serial port>
	    baudratePreference: <configured default baudrate>
	    autoconnect: <whether autoconnect upon server startup is enabled or not>

	Returns:
	    (dict): A dictionary holding the connection options in the structure specified above
	"""
	return {
		"ports": comm.serialList(),
		"baudrates": comm.baudrateList(),
		"portPreference": settings().get(["serial", "port"]),
		"baudratePreference": settings().getInt(["serial", "baudrate"]),
		"autoconnect": settings().getBoolean(["serial", "autoconnect"])
	}


class PrinterInterface(object):
	"""
	The :class:`PrinterInterface` represents the developer interface to the :class:`~octoprint.printer.standard.Printer`
	instance.
	"""

	valid_axes = ("x", "y", "z", "e")
	"""Valid axes identifiers."""

	valid_tool_regex = re.compile("^(tool\d+)$")
	"""Regex for valid tool identifiers."""

	valid_heater_regex = re.compile("^(tool\d+|bed)$")
	"""Regex for valid heater identifiers."""

	def connect(self, port=None, baudrate=None, profile=None):
		"""
		Connects to the printer, using the specified serial ``port``, ``baudrate`` and printer ``profile``. If a
		connection is already established, that connection will be closed prior to connecting anew with the provided
		parameters.

		Arguments:
		    port (str): Name of the serial port to connect to. If not provided, an auto detection will be attempted.
		    baudrate (int): Baudrate to connect with. If not provided, an auto detection will be attempted.
		    profile (str): Name of the printer profile to use for this connection. If not provided, the default
		        will be retrieved from the :class:`PrinterProfileManager`.
		"""
		pass

	def disconnect(self):
		"""
		Disconnects from the printer. Does nothing if no connection is currently established.
		"""
		raise NotImplementedError()

	def get_transport(self):
		"""
		Returns the communication layer's transport object, if a connection is currently established.

		Note that this doesn't have to necessarily be a :class:`serial.Serial` instance, it might also be something
		different, so take care to do instance checks before attempting to access any properties or methods.

		Returns:
		    object: The communication layer's transport object
		"""
		raise NotImplementedError()

	def fake_ack(self):
		"""
		Fakes an acknowledgment for the communication layer. If the communication between OctoPrint and the printer
		gets stuck due to lost "ok" responses from the server due to communication issues, this can be used to get
		things going again.
		"""
		raise NotImplementedError()

	def commands(self, commands):
		"""
		Sends the provided ``commands`` to the printer.

		Arguments:
		    commands (str, list): The commands to send. Might be a single command provided just as a string or a list
		        of multiple commands to send in order.
		"""
		raise NotImplementedError()

	def script(self, name, context=None):
		"""
		Sends the GCODE script ``name`` to the printer.

		The script will be run through the template engine, the rendering context can be extended by providing a
		``context`` with additional template variables to use.

		If the script is unknown, an :class:`UnknownScriptException` will be raised.

		Arguments:
		    name (str): The name of the GCODE script to render.
		    context (dict): An optional context of additional template variables to provide to the renderer.

		Raises:
		    UnknownScriptException: There is no GCODE script with name ``name``
		"""
		raise NotImplementedError()

	def jog(self, axis, amount):
		"""
		Jogs the specified printer ``axis`` by the specified ``amount`` in mm.

		Arguments:
		    axis (str): The axis to jog, will be converted to lower case, one of "x", "y", "z" or "e"
		    amount (int, float): The amount by which to jog in mm
		"""
		raise NotImplementedError()

	def home(self, axes):
		"""
		Homes the specified printer ``axes``.

		Arguments:
		    axes (str, list): The axis or axes to home, each of which must converted to lower case must match one of
		        "x", "y", "z" and "e"
		"""
		raise NotImplementedError()

	def extrude(self, amount):
		"""
		Extrude ``amount`` millimeters of material from the tool.

		Arguments:
		    amount (int, float): The amount of material to extrude in mm
		"""
		raise NotImplementedError()

	def change_tool(self, tool):
		"""
		Switch the currently active ``tool`` (for which extrude commands will apply).

		Arguments:
		    tool (str): The tool to switch to, matching the regex "tool[0-9]+" (e.g. "tool0", "tool1", ...)
		"""
		raise NotImplementedError()

	def set_temperature(self, heater, value):
		"""
		Sets the target temperature on the specified ``heater`` to the given ``value`` in celsius.

		Arguments:
		    heater (str): The heater for which to set the target temperature. Either "bed" for setting the bed
		        temperature or something matching the regular expression "tool[0-9]+" (e.g. "tool0", "tool1", ...) for
		        the hotends of the printer
		    value (int, float): The temperature in celsius to set the target temperature to.
		"""
		raise NotImplementedError()

	def set_temperature_offset(self, offsets=None):
		"""
		Sets the temperature ``offsets`` to apply to target temperatures red from a GCODE file while printing.

		Arguments:
		    offsets (dict): A dictionary specifying the offsets to apply. Keys must match the format for the ``heater``
		        parameter to :func:`set_temperature`, so "bed" for the offset for the bed target temperature and
		        "tool[0-9]+" for the offsets to the hotend target temperatures.
		"""
		raise NotImplementedError()

	def feed_rate(self, factor):
		"""
		Sets the ``factor`` for the printer's feed rate.

		Arguments:
		    factor (int, float): The factor for the feed rate to send to the firmware. Percentage expressed as either an
		    int between 0 and 100 or a float between 0 and 1.
		"""
		raise NotImplementedError()

	def flow_rate(self, factor):
		"""
		Sets the ``factor`` for the printer's flow rate.

		Arguments:
		    factor (int, float): The factor for the flow rate to send to the firmware. Percentage expressed as either an
		    int between 0 and 100 or a float between 0 and 1.
		"""
		raise NotImplementedError()

	def select_file(self, path, sd, printAfterSelect=False, pos=None):
		"""
		Selects the specified ``path`` for printing, specifying if the file is to be found on the ``sd`` or not.
		Optionally can also directly start the print after selecting the file.

		Arguments:
		    path (str): The path to select for printing. Either an absolute path (local file) or a
		        filename (SD card).
		    sd (boolean): Indicates whether the file is on the SD card or not.
		    printAfterSelect (boolean): Indicates whether a print should be started
		        after the file is selected.
		"""
		raise NotImplementedError()

	def unselect_file(self):
		"""
		Unselects and currently selected file.
		"""
		raise NotImplementedError()

	def start_print(self):
		"""
		Starts printing the currently selected file. If no file is currently selected, does nothing.
		"""
		raise NotImplementedError()

	def toggle_pause_print(self):
		"""
		Pauses the current print job if it is currently running or resumes it if it is currently paused.
		"""
		raise NotImplementedError()

	def cancel_print(self):
		"""
		Cancels the current print job.
		"""
		raise NotImplementedError()

	def get_state_string(self):
		"""
		Returns:
		     (str) A human readable string corresponding to the current communication state.
		"""
		raise NotImplementedError()

	def get_state_id(self):
		"""
		Identifier of the current communication state.

		Possible values are:

		  * OPEN_SERIAL
		  * DETECT_SERIAL
		  * DETECT_BAUDRATE
		  * CONNECTING
		  * OPERATIONAL
		  * PRINTING
		  * PAUSED
		  * CLOSED
		  * ERROR
		  * CLOSED_WITH_ERROR
		  * TRANFERING_FILE
		  * OFFLINE
		  * UNKNOWN
		  * NONE

		Returns:
		     (str) A unique identifier corresponding to the current communication state.
		"""

	def get_current_data(self):
		"""
		Returns:
		    (dict) The current state data.
		"""
		raise NotImplementedError()

	def get_current_job(self):
		"""
		Returns:
		    (dict) The data of the current job.
		"""
		raise NotImplementedError()

	def get_current_temperatures(self):
		"""
		Returns:
		    (dict) The current temperatures.
		"""
		raise NotImplementedError()

	def get_temperature_history(self):
		"""
		Returns:
		    (list) The temperature history.
		"""
		raise NotImplementedError()

	def get_current_connection(self):
		"""
		Returns:
		    (tuple) The current connection information as a 4-tuple ``(connection_string, port, baudrate, printer_profile)``.
		        If the printer is currently not connected, the tuple will be ``("Closed", None, None, None)``.
		"""
		raise NotImplementedError()

	def is_closed_or_error(self):
		"""
		Returns:
		    (boolean) Whether the printer is currently disconnected and/or in an error state.
		"""
		raise NotImplementedError()

	def is_operational(self):
		"""
		Returns:
		    (boolean) Whether the printer is currently connected and available.
		"""
		raise NotImplementedError()

	def is_printing(self):
		"""
		Returns:
		    (boolean) Whether the printer is currently printing.
		"""
		raise NotImplementedError()

	def is_paused(self):
		"""
		Returns:
		    (boolean) Whether the printer is currently paused.
		"""
		raise NotImplementedError()

	def is_error(self):
		"""
		Returns:
		    (boolean) Whether the printer is currently in an error state.
		"""
		raise NotImplementedError()

	def is_ready(self):
		"""
		Returns:
		    (boolean) Whether the printer is currently operational and ready for new print jobs (not printing).
		"""
		raise NotImplementedError()

	def register_callback(self, callback):
		"""
		Registers a :class:`PrinterCallback` with the instance.

		Arguments:
		    callback (PrinterCallback): The callback object to register.
		"""
		raise NotImplementedError()

	def unregister_callback(self, callback):
		"""
		Unregisters a :class:`PrinterCallback` from the instance.

		Arguments:
		    callback (PrinterCallback): The callback object to unregister.
		"""
		raise NotImplementedError()


class PrinterCallback(object):
	def on_printer_add_log(self, data):
		"""
		Called when the :class:`PrinterInterface` receives a new communication log entry from the communication layer.

		Arguments:
		    data (str): The received log line.
		"""
		pass

	def on_printer_add_message(self, data):
		"""
		Called when the :class:`PrinterInterface` receives a new message from the communication layer.

		Arguments:
		    data (str): The received message.
		"""
		pass

	def on_printer_add_temperature(self, data):
		"""
		Called when the :class:`PrinterInterface` receives a new temperature data set from the communication layer.

		``data`` is a ``dict`` of the following structure::

		    tool0:
		        actual: <temperature of the first hotend, in degC>
		        target: <target temperature of the first hotend, in degC>
		    ...
		    bed:
		        actual: <temperature of the bed, in degC>
		        target: <target temperature of the bed, in degC>

		Arguments:
		    data (dict): A dict of all current temperatures in the format as specified above
		"""
		pass

	def on_printer_received_registered_message(self, name, output):
		"""
		Called when the :class:`PrinterInterface` received a registered message, e.g. from a feedback command.

		Arguments:
		    name (str): Name of the registered message (e.g. the feedback command)
		    output (str): Output for the registered message
		"""
		pass

	def on_printer_send_initial_data(self, data):
		"""
		Called when registering as a callback with the :class:`PrinterInterface` to receive the initial data (state,
		log and temperature history etc) from the printer.

		``data`` is a ``dict`` of the following structure::

		    temps:
		      - time: <timestamp of the temperature data point>
		        tool0:
		            actual: <temperature of the first hotend, in degC>
		            target: <target temperature of the first hotend, in degC>
		        ...
		        bed:
		            actual: <temperature of the bed, in degC>
		            target: <target temperature of the bed, in degC>
		      - ...
		    logs: <list of current communication log lines>
		    messages: <list of current messages from the firmware>

		Arguments:
		    data (dict): The initial data in the format as specified above.
		"""
		pass

	def on_printer_send_current_data(self, data):
		"""
		Called when the internal state of the :class:`PrinterInterface` changes, due to changes in the printer state,
		temperatures, log lines, job progress etc. Updates via this method are guaranteed to be throttled to a maximum
		of 2 calls per second.

		``data`` is a ``dict`` of the following structure::

		    state:
		        text: <current state string>
		        flags:
		            operational: <whether the printer is currently connected and responding>
		            printing: <whether the printer is currently printing>
		            closedOrError: <whether the printer is currently disconnected and/or in an error state>
		            error: <whether the printer is currently in an error state>
		            paused: <whether the printer is currently paused>
		            ready: <whether the printer is operational and ready for jobs>
		            sdReady: <whether an SD card is present>
		    job:
		        file:
		            name: <name of the file>,
		            size: <size of the file in bytes>,
		            origin: <origin of the file, "local" or "sdcard">,
		            date: <last modification date of the file>
		        estimatedPrintTime: <estimated print time of the file in seconds>
		        lastPrintTime: <last print time of the file in seconds>
		        filament:
		            length: <estimated length of filament needed for this file, in mm>
		            volume: <estimated volume of filament needed for this file, in ccm>
		    progress:
		        completion: <progress of the print job in percent (0-100)>
		        filepos: <current position in the file in bytes>
		        printTime: <current time elapsed for printing, in seconds>
		        printTimeLeft: <estimated time left to finish printing, in seconds>
		    currentZ: <current position of the z axis, in mm>
		    offsets: <current configured temperature offsets, keys are "bed" or "tool[0-9]+", values the offset in degC>

		Arguments:
		    data (dict): The current data in the format as specified above.
		"""
		pass

class UnknownScript(Exception):
	def __init__(self, name, *args, **kwargs):
		self.name = name
