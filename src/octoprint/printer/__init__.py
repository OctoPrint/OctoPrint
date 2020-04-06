# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

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

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import re

from octoprint.settings import settings
from octoprint.util import deprecated, natural_key
from octoprint.filemanager import FileDestinations


@deprecated(message="get_connection_options has been replaced by PrinterInterface.get_connection_options",
            includedoc="Replaced by :func:`PrinterInterface.get_connection_options`",
            since="1.3.0")
def get_connection_options():
	return PrinterInterface.get_connection_options()


class PrinterInterface(object):
	"""
	The :class:`PrinterInterface` represents the developer interface to the :class:`~octoprint.printer.standard.Printer`
	instance.
	"""

	valid_axes = ("x", "y", "z", "e")
	"""Valid axes identifiers."""

	valid_tool_regex = re.compile(r"^(tool\d+)$")
	"""Regex for valid tool identifiers."""

	valid_heater_regex = re.compile(r"^(tool\d+|bed|chamber)$")
	"""Regex for valid heater identifiers."""

	@classmethod
	def get_connection_options(cls, *args, **kwargs):
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
		import octoprint.util.comm as comm
		return {
			"ports": sorted(comm.serialList(), key=natural_key),
			"baudrates": sorted(comm.baudrateList(), reverse=True),
			"portPreference": settings().get(["serial", "port"]),
			"baudratePreference": settings().getInt(["serial", "baudrate"]),
			"autoconnect": settings().getBoolean(["serial", "autoconnect"])
		}

	def connect(self, port=None, baudrate=None, profile=None, *args, **kwargs):
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

	def disconnect(self, *args, **kwargs):
		"""
		Disconnects from the printer. Does nothing if no connection is currently established.
		"""
		raise NotImplementedError()

	def get_transport(self, *args, **kwargs):
		"""
		Returns the communication layer's transport object, if a connection is currently established.

		Note that this doesn't have to necessarily be a :class:`serial.Serial` instance, it might also be something
		different, so take care to do instance checks before attempting to access any properties or methods.

		Returns:
		    object: The communication layer's transport object
		"""
		raise NotImplementedError()

	def job_on_hold(self, blocking=True, *args, **kwargs):
		"""
		Contextmanager that allows executing code while printing while making sure that no commands from the file
		being printed are continued to be sent to the printer. Note that this will only work for local files,
		NOT SD files.

		Example:

		.. code-block:: python

		   with printer.job_on_hold():
		       park_printhead()
		       take_snapshot()
		       send_printhead_back()

		It should be used sparingly and only for very specific situations (such as parking the print head somewhere,
		taking a snapshot from the webcam, then continuing). If you abuse this, you WILL cause print quality issues!

		A lock is in place that ensures that the context can only actually be held by one thread at a time. If you
		don't want to block on acquire, be sure to set ``blocking`` to ``False`` and catch the ``RuntimeException`` thrown
		if the lock can't be acquired.

		Args:
			blocking (bool): Whether to block while attempting to acquire the lock (default) or not
		"""
		raise NotImplementedError()

	def set_job_on_hold(self, value, blocking=True, *args, **kwargs):
		"""
		Setter for finer control over putting jobs on hold. Set to ``True`` to ensure that no commands from the file
		being printed are continued to be sent to the printer. Set to ``False`` to resume. Note that this will only
		work for local files, NOT SD files.

		Make absolutely sure that if you set this flag, you will always also unset it again. If you don't, the job will
		be stuck forever.

		Example:

		.. code-block:: python

		   if printer.set_job_on_hold(True):
		       try:
		           park_printhead()
		           take_snapshot()
		           send_printhead_back()
		       finally:
		           printer.set_job_on_hold(False)

		Just like :func:`~octoprint.printer.PrinterInterface.job_on_hold` this should be used sparingly and only for
		very specific situations. If you abuse this, you WILL cause print quality issues!

		Args:
			value (bool): The value to set
			blocking (bool): Whether to block while attempting to set the value (default) or not

		Returns:
			(bool) Whether the value could be set successfully (True) or a timeout was encountered (False)
		"""
		raise NotImplementedError()

	def fake_ack(self, *args, **kwargs):
		"""
		Fakes an acknowledgment for the communication layer. If the communication between OctoPrint and the printer
		gets stuck due to lost "ok" responses from the server due to communication issues, this can be used to get
		things going again.
		"""
		raise NotImplementedError()

	def commands(self, commands, tags=None, *args, **kwargs):
		"""
		Sends the provided ``commands`` to the printer.

		Arguments:
		    commands (str, list): The commands to send. Might be a single command provided just as a string or a list
		        of multiple commands to send in order.
		    tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
		"""
		raise NotImplementedError()

	def script(self, name, context=None, tags=None, *args, **kwargs):
		"""
		Sends the GCODE script ``name`` to the printer.

		The script will be run through the template engine, the rendering context can be extended by providing a
		``context`` with additional template variables to use.

		If the script is unknown, an :class:`UnknownScriptException` will be raised.

		Arguments:
		    name (str): The name of the GCODE script to render.
		    context (dict): An optional context of additional template variables to provide to the renderer.
		    tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle

		Raises:
		    UnknownScriptException: There is no GCODE script with name ``name``
		"""
		raise NotImplementedError()

	def jog(self, axes, relative=True, speed=None, tags=None, *args, **kwargs):
		"""
		Jogs the specified printer ``axis`` by the specified ``amount`` in mm.

		Arguments:
		    axes (dict): Axes and distances to jog, keys are axes ("x", "y", "z"), values are distances in mm
		    relative (bool): Whether to interpret the distance values as relative (true, default) or absolute (false)
		        coordinates
		    speed (int, bool or None): Speed at which to jog (F parameter). If set to ``False`` no speed will be set
		        specifically. If set to ``None`` (or left out) the minimum of all involved axes speeds from the printer
		        profile will be used.
		    tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
		"""
		raise NotImplementedError()

	def home(self, axes, tags=None, *args, **kwargs):
		"""
		Homes the specified printer ``axes``.

		Arguments:
		    axes (str, list): The axis or axes to home, each of which must converted to lower case must match one of
		        "x", "y", "z" and "e"
		    tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
		"""
		raise NotImplementedError()

	def extrude(self, amount, speed=None, tags=None, *args, **kwargs):
		"""
		Extrude ``amount`` millimeters of material from the tool.

		Arguments:
		    amount (int, float): The amount of material to extrude in mm
		    speed (int, None): Speed at which to extrude (F parameter). If set to ``None`` (or left out)
		    the maximum speed of E axis from the printer profile will be used.
		    tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
		"""
		raise NotImplementedError()

	def change_tool(self, tool, tags=None, *args, **kwargs):
		"""
		Switch the currently active ``tool`` (for which extrude commands will apply).

		Arguments:
		    tool (str): The tool to switch to, matching the regex "tool[0-9]+" (e.g. "tool0", "tool1", ...)
		    tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
		"""
		raise NotImplementedError()

	def set_temperature(self, heater, value, tags=None, *args, **kwargs):
		"""
		Sets the target temperature on the specified ``heater`` to the given ``value`` in celsius.

		Arguments:
		    heater (str): The heater for which to set the target temperature. Either "bed" for setting the bed
		        temperature or something matching the regular expression "tool[0-9]+" (e.g. "tool0", "tool1", ...) for
		        the hotends of the printer
		    value (int, float): The temperature in celsius to set the target temperature to.
		    tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
		"""
		raise NotImplementedError()

	def set_temperature_offset(self, offsets=None, tags=None, *args, **kwargs):
		"""
		Sets the temperature ``offsets`` to apply to target temperatures read from a GCODE file while printing.

		Arguments:
		    offsets (dict): A dictionary specifying the offsets to apply. Keys must match the format for the ``heater``
		        parameter to :func:`set_temperature`, so "bed" for the offset for the bed target temperature and
		        "tool[0-9]+" for the offsets to the hotend target temperatures.
		    tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
		"""
		raise NotImplementedError()

	def feed_rate(self, factor, tags=None, *args, **kwargs):
		"""
		Sets the ``factor`` for the printer's feed rate.

		Arguments:
		    factor (int, float): The factor for the feed rate to send to the firmware. Percentage expressed as either an
		        int between 0 and 100 or a float between 0 and 1.
		    tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
		"""
		raise NotImplementedError()

	def flow_rate(self, factor, tags=None, *args, **kwargs):
		"""
		Sets the ``factor`` for the printer's flow rate.

		Arguments:
		    factor (int, float): The factor for the flow rate to send to the firmware. Percentage expressed as either an
		        int between 0 and 100 or a float between 0 and 1.
		    tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
		"""
		raise NotImplementedError()

	def can_modify_file(self, path, sd, *args, **kwargs):
		"""
		Determines whether the ``path`` (on the printer's SD if ``sd`` is True) may be modified (updated or deleted)
		or not.

		A file that is currently being printed is not allowed to be modified. Any other file or the current file
		when it is not being printed is fine though.

		:since: 1.3.2

		.. warning::

		   This was introduced in 1.3.2 to work around an issue when updating a file that is already selected.
		   I'm not 100% sure at this point if this is the best approach to solve this issue, so if you decide
		   to depend on this particular method in this interface, be advised that it might vanish in future
		   versions!

		Arguments:
		    path (str): path in storage of the file to check
		    sd (bool): True if to check against SD storage, False otherwise

		Returns:
		    (bool) True if the file may be modified, False otherwise
		"""
		return not (self.is_current_file(path, sd) and (self.is_printing() or self.is_paused()))

	def is_current_file(self, path, sd, *args, **kwargs):
		"""
		Returns whether the provided ``path`` (on the printer's SD if ``sd`` is True) is the currently selected
		file for printing.

		:since: 1.3.2

		.. warning::

		   This was introduced in 1.3.2 to work around an issue when updating a file that is already selected.
		   I'm not 100% sure at this point if this is the best approach to solve this issue, so if you decide
		   to depend on this particular method in this interface, be advised that it might vanish in future
		   versions!

		Arguments:
		    path (str): path in storage of the file to check
		    sd (bool): True if to check against SD storage, False otherwise

		Returns:
		    (bool) True if the file is currently selected, False otherwise
		"""
		current_job = self.get_current_job()
		if current_job is not None and "file" in current_job:
			current_job_file = current_job["file"]
			if "path" in current_job_file and "origin" in current_job_file:
				current_file_path = current_job_file["path"]
				current_file_origin = current_job_file["origin"]

				return path == current_file_path and sd == (current_file_origin == FileDestinations.SDCARD)

		return False

	def select_file(self, path, sd, printAfterSelect=False, pos=None, tags=None, *args, **kwargs):
		"""
		Selects the specified ``path`` for printing, specifying if the file is to be found on the ``sd`` or not.
		Optionally can also directly start the print after selecting the file.

		Arguments:
		    path (str): The path to select for printing. Either an absolute path or relative path to a  local file in
		        the uploads folder or a filename on the printer's SD card.
		    sd (boolean): Indicates whether the file is on the printer's SD card or not.
		    printAfterSelect (boolean): Indicates whether a print should be started
		        after the file is selected.
		    tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle

		Raises:
		    InvalidFileType: if the file is not a machinecode file and hence cannot be printed
		    InvalidFileLocation: if an absolute path was provided and not contained within local storage or
		        doesn't exist
		"""
		raise NotImplementedError()

	def unselect_file(self, *args, **kwargs):
		"""
		Unselects and currently selected file.
		"""
		raise NotImplementedError()

	def start_print(self, tags=None, *args, **kwargs):
		"""
		Starts printing the currently selected file. If no file is currently selected, does nothing.

		Arguments:
		    tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
		"""
		raise NotImplementedError()

	def pause_print(self, tags=None, *args, **kwargs):
		"""
		Pauses the current print job if it is currently running, does nothing otherwise.

		Arguments:
		    tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
		"""
		raise NotImplementedError()

	def resume_print(self, tags=None, *args, **kwargs):
		"""
		Resumes the current print job if it is currently paused, does nothing otherwise.

		Arguments:
		    tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
		"""
		raise NotImplementedError()

	def toggle_pause_print(self, tags=None, *args, **kwargs):
		"""
		Pauses the current print job if it is currently running or resumes it if it is currently paused.

		Arguments:
		    tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
		"""
		if self.is_printing():
			self.pause_print(tags=tags, *args, **kwargs)
		elif self.is_paused():
			self.resume_print(tags=tags, *args, **kwargs)

	def cancel_print(self, tags=None, *args, **kwargs):
		"""
		Cancels the current print job.

		Arguments:
		    tags (set of str): An optional set of tags to attach to the command(s) throughout their lifecycle
		"""
		raise NotImplementedError()

	def log_lines(self, *lines):
		"""
		Logs the provided lines to the printer log and serial.log
		Args:
			*lines: the lines to log
		"""
		pass

	def get_state_string(self, *args, **kwargs):
		"""
		Returns:
		     (str) A human readable string corresponding to the current communication state.
		"""
		raise NotImplementedError()

	def get_state_id(self, *args, **kwargs):
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
		  * TRANSFERING_FILE
		  * OFFLINE
		  * UNKNOWN
		  * NONE

		Returns:
		     (str) A unique identifier corresponding to the current communication state.
		"""

	def get_current_data(self, *args, **kwargs):
		"""
		Returns:
		    (dict) The current state data.
		"""
		raise NotImplementedError()

	def get_current_job(self, *args, **kwargs):
		"""
		Returns:
		    (dict) The data of the current job.
		"""
		raise NotImplementedError()

	def get_current_temperatures(self, *args, **kwargs):
		"""
		Returns:
		    (dict) The current temperatures.
		"""
		raise NotImplementedError()

	def get_temperature_history(self, *args, **kwargs):
		"""
		Returns:
		    (list) The temperature history.
		"""
		raise NotImplementedError()

	def get_current_connection(self, *args, **kwargs):
		"""
		Returns:
		    (tuple) The current connection information as a 4-tuple ``(connection_string, port, baudrate, printer_profile)``.
		        If the printer is currently not connected, the tuple will be ``("Closed", None, None, None)``.
		"""
		raise NotImplementedError()

	def is_closed_or_error(self, *args, **kwargs):
		"""
		Returns:
		    (boolean) Whether the printer is currently disconnected and/or in an error state.
		"""
		raise NotImplementedError()

	def is_operational(self, *args, **kwargs):
		"""
		Returns:
		    (boolean) Whether the printer is currently connected and available.
		"""
		raise NotImplementedError()

	def is_printing(self, *args, **kwargs):
		"""
		Returns:
		    (boolean) Whether the printer is currently printing.
		"""
		raise NotImplementedError()

	def is_cancelling(self, *args, **kwargs):
		"""
		Returns:
		    (boolean) Whether the printer is currently cancelling a print.
		"""
		raise NotImplementedError()

	def is_pausing(self, *args, **kwargs):
		"""
		Returns:
			(boolean) Whether the printer is currently pausing a print.
		"""
		raise NotImplementedError()

	def is_paused(self, *args, **kwargs):
		"""
		Returns:
		    (boolean) Whether the printer is currently paused.
		"""
		raise NotImplementedError()

	def is_error(self, *args, **kwargs):
		"""
		Returns:
		    (boolean) Whether the printer is currently in an error state.
		"""
		raise NotImplementedError()

	def is_ready(self, *args, **kwargs):
		"""
		Returns:
		    (boolean) Whether the printer is currently operational and ready for new print jobs (not printing).
		"""
		raise NotImplementedError()

	def register_callback(self, callback, *args, **kwargs):
		"""
		Registers a :class:`PrinterCallback` with the instance.

		Arguments:
		    callback (PrinterCallback): The callback object to register.
		"""
		raise NotImplementedError()

	def unregister_callback(self, callback, *args, **kwargs):
		"""
		Unregisters a :class:`PrinterCallback` from the instance.

		Arguments:
		    callback (PrinterCallback): The callback object to unregister.
		"""
		raise NotImplementedError()

	def send_initial_callback(self, callback):
		"""
		Sends the initial printer update to :class:`PrinterCallback`.

		Arguments:
			callback (PrinterCallback): The callback object to send initial data to.
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
		    chamber:
		        actual: <temperature of the chamber, in degC>
		        target: <target temperature of the chamber, in degC>

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

class InvalidFileLocation(Exception):
	pass

class InvalidFileType(Exception):
	pass
