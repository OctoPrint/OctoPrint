.. _sec-events:

######
Events
######

.. contents::


.. note::

   With release of OctoPrint 1.1.0, the payload data has been harmonized, it is now a key-value-map for all events.
   Additionally, the format of the placeholders in both system command and gcode command triggers has been changed to
   accommodate for this new format. Last but not least, the way of specifying event hooks has changed, OctoPrint no longer
   separates hooks into two sections (gcodeCommandTrigger and systemCommandTrigger) but instead event hooks are now typed
   to indicate what to do with the command contained.

.. _sec-events-configuration:

Configuration
=============

Event hooks are configured via OctoPrint's configuration file ``config.yaml``. There they are contained in a
``subscriptions`` list located directly under the ``events`` node. The ``command`` node accepts either a single string
or a list of strings so that multiple commands can be executed in one go. Each hook carries an additional node type that
must be either ``gcode`` (for GCODE commands to be sent to the printer based on the event) or ``system`` (for commands to be
executed on the system OctoPrint is running on).

All event hooks can be disabled completely by setting ``event > enabled`` to ``false``. You can also disable individual
hooks by setting the (optional) node ``enabled`` to false, see the example below.

Example
-------

.. sourcecode:: yaml

   events:
     enabled: True
     subscriptions:
     - event: Disconnected
       command: python ~/growl.py -t mygrowlserver -d "Lost connection to printer" -a OctoPrint -i http://raspi/Octoprint_logo.png
       type: system
       enabled: false
     - event: PrintStarted
       command: python ~/growl.py -t mygrowlserver -d "Starting {file}" -a OctoPrint -i http://raspi/Octoprint_logo.png
       type: system
     - event: PrintDone
       command: python ~/growl.py -t mygrowlserver -d "Completed {file}" -a OctoPrint -i http://raspi/Octoprint_logo.png
       type: system
     - event: Connected
       command:
       - M115
       - M117 printer connected!
       - G28
       type: gcode

.. _sec-events-placeholders:

Placeholders
============

You can use the following generic placeholders in your event hooks:

  * ``{__currentZ}``: the current Z position of the head if known, -1 if not available
  * ``{__filename}``: filename of the currently selected file, "NO FILE" if not available
  * ``{__progress}``: the progress of the print in percent, 0 if not available
  * ``{__data}``: a string representation of the payload
  * ``{__now}``: the date and time of the event in ISO 8601

Additionally, all data from the payload can be accessed by its key. Example: If the payload happens to be defined
something like this:

  * ``file``: the file's name
  * ``origin``: the origin of the file, either ``local`` or ``sdcard``

then you'll be able to access the filename via the placeholder ``{file}`` and the origin via the placeholder ``{origin}``.


.. _sec-events-available_events:

Available Events
================

Server
------

Startup
   The server has started

ClientOpened
   A client has connected to the web server.

   Payload:

     * ``remoteAddress``: the remote address (IP) of the client that connected

   **Note:** Name changed in version 1.1.0

ClientClosed
   A client has disconnected from the webserver

   Payload:

     * ``remoteAddress``: the remote address (IP) of the client that disconnected

Printer communication
---------------------

Connected
   The server has connected to the printer.

   Payload:

     * ``port``: the connected serial port
     * ``baudrate``: the baud rate

Disconnected
   The server has disconnected from the printer

Error
   An error has occurred in the printer communication.

   Payload:

     * ``error``: the error string

File handling
-------------

Upload
   A file has been uploaded.

   Payload:
     * ``file``: the file's name
     * ``target``: the target to which the file was uploaded, either ``local`` or ``sdcard``

UpdatedFiles
   A file list was modified.

   Payload:

     * ``type``: the type of file list that was modified. Currently only ``printables`` and ``gcode`` (DEPRECATED) are supported here.

       .. note::

          The type ``gcode`` has been renamed to ``printables`` with the introduction of a new file management layer that
          supports STL files as first class citizens as well. For reasons of backwards compatibility the ``UpdatedFiles``
          event for printable files will be fired twice, once with ``type`` set to ``gcode``, once set to ``printables``.
          Support for the ``gcode`` type will be removed in the next release after version 1.2.0.

MetadataAnalysisStarted
   The metadata analysis of a GCODE file has started.

   Payload:

     * ``file``: the file's name

MetadataAnalaysisFinished
   The metadata analysis of a GCODE file has finished.

   Payload:

     * ``file``: the file's name
     * ``result``: the analysis result -- this is a python object currently only available for internal use

FileSelected
   A GCODE file has been selected for printing.

   Payload:

     * ``file``: the full path to the file
     * ``filename``: the file's name
     * ``origin``: the origin of the file, either ``local`` or ``sdcard``

FileDeselected
   No file is selected any more for printing.

TransferStarted
   A GCODE file transfer to SD has started.

   Payload:

     * ``local``: the file's name as stored locally
     * ``remote``: the file's name as stored on SD

   **Note:** Name changed in version 1.1.0

TransferDone
   A GCODE file transfer to SD has finished.

   Payload:

     * ``time``: the time it took for the transfer to complete in seconds
     * ``local``: the file's name as stored locally
     * ``remote``: the file's name as stored on SD

Printing
--------

PrintStarted
   A print has started.

   Payload:

     * ``file``: the file's name
     * ``origin``: the origin of the file, either ``local`` or ``sdcard``

PrintFailed
   A print failed.

   Payload:

     * ``file``: the file's name
     * ``origin``: the origin of the file, either ``local`` or ``sdcard``

PrintDone
   A print completed successfully.

   Payload:

     * ``file``: the file's name
     * ``origin``: the origin of the file, either ``local`` or ``sdcard``
     * ``time``: the time needed for the print, in seconds (float)

PrintCancelled
   The print has been cancelled via the cancel button.

   Payload:

     * ``file``: the file's name
     * ``origin``: the origin of the file, either ``local`` or ``sdcard``

PrintPaused
   The print has been paused.

   Payload:

     * ``file``: the file's name
     * ``origin``: the origin of the file, either ``local`` or ``sdcard``

PrintResumed
   The print has been resumed.

   Payload:

     * ``file``: the file's name
     * ``origin``: the origin of the file, either ``local`` or ``sdcard``

GCODE processing
----------------

PowerOn
   The GCode has turned on the printer power via M80

PowerOff
   The GCODE has turned on the printer power via M81

Home
   The head has gone home via G28

ZChange
   The printer's Z-Height has changed (new layer)

Paused
   The print has been paused

Waiting
   The print is paused due to a gcode wait command

Cooling
   The GCODE has enabled the platform cooler via M245

Alert
   The GCODE has issued a user alert (beep) via M300

Conveyor
   The GCODE has enabled the conveyor belt via M240

Eject
   The GCODE has enabled the part ejector via M40

EStop
   The GCODE has issued a panic stop via M112

Timelapses
----------

CaptureStart
   A timelapse image has started to be captured.

   Payload:

     * ``file``: the name of the image file to be saved

CaptureDone
   A timelapse image has completed being captured.

   Payload:
     * ``file``: the name of the image file that was saved

MovieRendering
   The timelapse movie has started rendering.

   Payload:

     * ``gcode``: the GCODE file for which the timelapse would have been created (only the filename without the path)
     * ``movie``: the movie file that is being created (full path)
     * ``movie_basename``: the movie file that is being created (only the file name without the path)

MovieDone
   The timelapse movie is completed.

   Payload:

     * ``gcode``: the GCODE file for which the timelapse would have been created (only the filename without the path)
     * ``movie``: the movie file that has been created (full path)
     * ``movie_basename``: the movie file that has been created (only the file name without the path)

MovieFailed
   There was an error while rendering the timelapse movie.

   Payload:

     * ``gcode``: the GCODE file for which the timelapse would have been created (only the filename without the path)
     * ``movie``: the movie file that would have been created (full path)
     * ``movie_basename``: the movie file that would have been created (only the file name without the path)
     * ``returncode``: the return code of ``ffmpeg`` that indicates the error that occurred

Slicing
-------

SlicingStarted
   The slicing of a file has started.

   Payload:

     * ``stl``: the STL's filename
     * ``gcode``: the sliced GCODE's filename
     * ``progressAvailable``: true if progress information via the ``slicingProgress`` push update will be available, false if not

SlicingDone
   The slicing of a file has completed.

   Payload:

     * ``stl``: the STL's filename
     * ``gcode``: the sliced GCODE's filename
     * ``time``: the time needed for slicing, in seconds (float)

SlicingCancelled
   The slicing of a file has been cancelled. This will happen if a second slicing job
   targeting the same GCODE file has been started by the user.

   Payload:

     * ``stl``: the STL's filename
     * ``gcode``: the sliced GCODE's filename

SlicingFailed
   The slicing of a file has failed.

   Payload:

     * ``stl``: the STL's filename
     * ``gcode``: the sliced GCODE's filename
     * ``reason``: the reason for the slicing having failed

SlicingProfileAdded
   A new slicing profile was added.

   Payload:

     * ``slicer``: the slicer for which the profile was added
     * ``profile``: the profile that was added

SlicingProfileModified
   A new slicing profile was modified.

   Payload:

     * ``slicer``: the slicer for which the profile was modified
     * ``profile``: the profile that was modified

SlicingProfileDeleted
   A slicing profile was deleted.

   Payload:

     * ``slicer``: the slicer for which the profile was deleted
     * ``profile``: the profile that was deleted

Settings
--------

SettingsUpdated
   The internal settings were updated.
