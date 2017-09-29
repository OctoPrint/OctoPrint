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
  * ``{__filename}`` : name of currently selected file, or ``NO FILE`` if no file is selected
  * ``{__filepath}`` : path in origin location of currently selected file, or ``NO FILE`` if no file is selected
  * ``{__fileorigin}`` : origin of currently selected file, or ``NO FILE`` if no file is selected
  * ``{__progress}``: the progress of the print in percent, 0 if not available
  * ``{__data}``: a string representation of the payload
  * ``{__now}``: the date and time of the event in ISO 8601

Additionally, all data from the payload can be accessed by its key. Example: If the payload happens to be defined
something like this:

  * ``name``: the file's name
  * ``path``: the file's path in its origin storage location
  * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``

then you'll be able to access the file's name via the placeholder ``{name}``, its path via the placeholder ``{path}``
and its origin via the placeholder ``{origin}``.


.. _sec-events-available_events:

Available Events
================

Server
------

Startup
   The server has started.

Shutdown
   The server is shutting down.

ClientOpened
   A client has connected to the web server.

   Payload:

     * ``remoteAddress``: the remote address (IP) of the client that connected

   **Note:** Name changed in version 1.1.0

ClientClosed
   A client has disconnected from the webserver

   Payload:

     * ``remoteAddress``: the remote address (IP) of the client that disconnected

ConnectivityChanged
   The server's internet connectivity changed

   Payload:

     * ``old``: Old connectivity value (true for online, false for offline)
     * ``new``: New connectivity value (true for online, false for offline)

Printer communication
---------------------

Connecting
   The server is attempting to connect to the printer.

Connected
   The server has connected to the printer.

   Payload:

     * ``port``: the connected serial port
     * ``baudrate``: the baud rate

Disconnecting
   The server is going to disconnect from the printer. Note that this
   event might not always be sent when the server and printer get disconnected
   from each other. Do not depend on this for critical life cycle management.

Disconnected
   The server has disconnected from the printer

Error
   An error has occurred in the printer communication.

   Payload:

     * ``error``: the error string

PrinterStateChanged
   The state of the printer changed.

   Payload:

     * ``state_id``: Id of the new state. See
       :func:`~octoprint.printer.PrinterInterface.get_state_id` for possible values.
     * ``state_string``: Text representation of the new state.

File handling
-------------

Upload
   A file has been uploaded through the web interface.

   Payload:
     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``target``: the target storage location to which the file was uploaded, either ``local`` or ``sdcard``

   .. deprecated:: 1.3.0

        * ``file``: the file's path within its storage location

      Still available for reasons of backwards compatibility. Will be removed with 1.4.0.

FileAdded
   A file has been added to a storage.

   Payload:
     * ``storage``: the storage's identifier
     * ``path``: the file's path within its storage location
     * ``name``: the file's name
     * ``type``: the file's type, a list of the path within the type hierarchy, e.g. ``["machinecode", "gcode"]`` or
       ``["model", "stl"]``

   .. note::

      A copied file triggers this for its new path. A moved file first triggers ``FileRemoved`` for its original
      path and then ``FileAdded`` for the new one.

FileRemoved
   A file has been removed from a storage.

   Payload:
     * ``storage``: the storage's identifier
     * ``path``: the file's path within its storage location
     * ``name``: the file's name
     * ``type``: the file's type, a list of the path within the type hierarchy, e.g. ``["machinecode", "gcode"]`` or
       ``["model", "stl"]``

   .. note::

      A moved file first triggers ``FileRemoved`` for its original path and then ``FileAdded`` for the new one.

FolderAdded
   A folder has been added to a storage.

   Payload:
     * ``storage``: the storage's identifier
     * ``path``: the folders's path within its storage location
     * ``name``: the folders's name

   .. note::

      A copied folder triggers this for its new path. A moved folder first triggers ``FolderRemoved`` for its original
      path and then ``FolderAdded`` for the new one.

FolderRemoved
   A folder has been removed from a storage.

   Payload:
     * ``storage``: the storage's identifier
     * ``path``: the folders's path within its storage location
     * ``name``: the folders's name

   .. note::

      A moved folder first triggers ``FolderRemoved`` for its original path and then ``FolderAdded`` for the new one.

UpdatedFiles
   A file list was modified.

   Payload:

     * ``type``: the type of file list that was modified. Only ``printables`` is supported here. See the deprecation
       note below.

       .. deprecated:: 1.2.0

          The ``gcode`` modification type has been superseded by ``printables``. It is currently still available for
          reasons of backwards compatibility and will also be sent on modification of ``printables``. It will however
          be removed with 1.4.0.


MetadataAnalysisStarted
   The metadata analysis of a file has started.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the file's origin storage location

   .. deprecated:: 1.3.0

        * ``file``: the file's path within its storage location

      Still available for reasons of backwards compatibility. Will be removed with 1.4.0.

MetadataAnalysisFinished
   The metadata analysis of a file has finished.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the file's origin storage location
     * ``result``: the analysis result -- this is a python object currently only available for internal use

   .. deprecated:: 1.3.0

        * ``file``: the file's path within its storage location

      Still available for reasons of backwards compatibility. Will be removed with 1.4.0.

FileSelected
   A file has been selected for printing.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``

   .. deprecated:: 1.3.0

        * ``file``: the file's full path on disk (``local``) or within its storage (``sdcard``)
        * ``filename``: the file's name

      Still available for reasons of backwards compatibility. Will be removed with 1.4.0.

FileDeselected
   No file is selected any more for printing.

TransferStarted
   A file transfer to the printer's SD has started.

   Payload:

     * ``local``: the file's name as stored locally
     * ``remote``: the file's name as stored on SD

   **Note:** Name changed in version 1.1.0

TransferDone
   A file transfer to the printer's SD has finished.

   Payload:

     * ``time``: the time it took for the transfer to complete in seconds
     * ``local``: the file's name as stored locally
     * ``remote``: the file's name as stored on SD

Printing
--------

PrintStarted
   A print has started.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``

   .. deprecated:: 1.3.0

        * ``file``: the file's full path on disk (``local``) or within its storage (``sdcard``)
        * ``filename``: the file's name

      Still available for reasons of backwards compatibility. Will be removed with 1.4.0.

PrintFailed
   A print failed.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``

   .. deprecated:: 1.3.0

        * ``file``: the file's full path on disk (``local``) or within its storage (``sdcard``)
        * ``filename``: the file's name

      Still available for reasons of backwards compatibility. Will be removed with 1.4.0.

PrintDone
   A print completed successfully.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``
     * ``time``: the time needed for the print, in seconds (float)

   .. deprecated:: 1.3.0

        * ``file``: the file's full path on disk (``local``) or within its storage (``sdcard``)
        * ``filename``: the file's name

      Still available for reasons of backwards compatibility. Will be removed with 1.4.0.

PrintCancelled
   The print has been cancelled via the cancel button.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``
     * ``position``: the print head position at the time of cancelling, if available
     * ``position.x``: x coordinate, as reported back from the firmware through `M114`
     * ``position.y``: y coordinate, as reported back from the firmware through `M114`
     * ``position.z``: z coordinate, as reported back from the firmware through `M114`
     * ``position.e``: e coordinate (of currently selected extruder), as reported back from the firmware through `M114`
     * ``position.t``: last tool selected *through OctoPrint* (note that if you did change the printer's selected
       tool outside of OctoPrint, e.g. through the printer controller, or if you are printing from SD, this will NOT
       be accurate)
     * ``position.f``: last feedrate for move commands **sent through OctoPrint** (note that if you modified the
       feedrate outside of OctoPrint, e.g. through the printer controller, or if you are printing from SD, this will
       NOT be accurate)

   .. deprecated:: 1.3.0

        * ``file``: the file's full path on disk (``local``) or within its storage (``sdcard``)
        * ``filename``: the file's name

      Still available for reasons of backwards compatibility. Will be removed with 1.4.0.

PrintPaused
   The print has been paused.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``
     * ``position``: the print head position at the time of pausing, if available
     * ``position.x``: x coordinate, as reported back from the firmware through `M114`
     * ``position.y``: y coordinate, as reported back from the firmware through `M114`
     * ``position.z``: z coordinate, as reported back from the firmware through `M114`
     * ``position.e``: e coordinate (of currently selected extruder), as reported back from the firmware through `M114`
     * ``position.t``: last tool selected *through OctoPrint* (note that if you did change the printer's selected
       tool outside of OctoPrint, e.g. through the printer controller, or if you are printing from SD, this will NOT
       be accurate)
     * ``position.f``: last feedrate for move commands **sent through OctoPrint** (note that if you modified the
       feedrate outside of OctoPrint, e.g. through the printer controller, or if you are printing from SD, this will
       NOT be accurate)

   .. deprecated:: 1.3.0

        * ``file``: the file's full path on disk (``local``) or within its storage (``sdcard``)
        * ``filename``: the file's name

      Still available for reasons of backwards compatibility. Will be removed with 1.4.0.

PrintResumed
   The print has been resumed.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``

   .. deprecated:: 1.3.0

        * ``file``: the file's full path on disk (``local``) or within its storage (``sdcard``)
        * ``filename``: the file's name

      Still available for reasons of backwards compatibility. Will be removed with 1.4.0.

GCODE processing
----------------

PowerOn
   An ``M80`` was sent to the printer through OctoPrint (not triggered when printing from SD!)

PowerOff
   An ``M81`` was sent to the printer through OctoPrint (not triggered when printing from SD!)

Home
   A ``G28`` was sent to the printer through OctoPrint (not triggered when printing from SD!)

ZChange
   The printer's Z-Height has changed (new layer) through a ``G0`` or ``G1`` that was sent to the printer through OctoPrint
   (not triggered when printing from SD!)

Dwell
   A ``G4`` was sent to the printer through OctoPrint (not triggered when printing from SD!)

Waiting
   One of the following commands was sent to the printer through OctoPrint (not triggered when printing from SD!):
   ``M0``, ``M1``, ``M226``

Cooling
   An ``M245`` was sent to the printer through OctoPrint (not triggered when printing from SD!)

Alert
   An ``M300`` was sent to the printer through OctoPrint (not triggered when printing from SD!)

Conveyor
   An ``M240`` was sent to the printer through OctoPrint (not triggered when printing from SD!)

Eject
   An ``M40`` was sent to the printer through OctoPrint (not triggered when printing from SD!)

EStop
   An ``M112`` was sent to the printer through OctoPrint (not triggered when printing from SD!)

PositionUpdate
   The response to an ``M114`` was received by OctoPrint. The payload contains the current position information
   parsed from the response and (in the case of the selected tool ``t`` and the current feedrate ``f``) tracked
   by OctoPrint.

   Payload:

     * ``x``: x coordinate, parsed from response
     * ``y``: y coordinate, parsed from response
     * ``z``: z coordinate, parsed from response
     * ``e``: e coordinate, parsed from response
     * ``t``: last tool selected *through OctoPrint*
     * ``f``: last feedrate for move commands ``G0``, ``G1`` or ``G28`` sent *through OctoPrint*

ToolChange
   A tool change command was sent to the printer. The payload contains the former current tool index and the
   new current tool index.

   Payload:

     * ``old``: old tool index
     * ``new``: new tool index

Timelapses
----------

CaptureStart
   A timelapse frame has started to be captured.

   Payload:

     * ``file``: the name of the image file to be saved

CaptureDone
   A timelapse frame has completed being captured.

   Payload:
     * ``file``: the name of the image file that was saved

CaptureFailed
   A timelapse frame could not be captured.

   Payload:
     * ``file``: the name of the image file that should have been saved
     * ``error``: the error that was caught

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
     * ``reason``: additional machine processable reason string - can be ``returncode`` if ffmpeg
       returned a non-0 return code, ``no_frames`` if no frames were captured that could be rendered
       to a timelapse, or ``unknown`` for any other reason of failure to render.

Slicing
-------

SlicingStarted
   The slicing of a file has started.

   Payload:

     * ``stl``: the STL's filename
     * ``stl_location``: the STL's location
     * ``gcode``: the sliced GCODE's filename
     * ``gcode_location``: the sliced GCODE's location
     * ``progressAvailable``: true if progress information via the ``slicingProgress`` push update will be available, false if not

SlicingDone
   The slicing of a file has completed.

   Payload:

     * ``stl``: the STL's filename
     * ``stl_location``: the STL's location
     * ``gcode``: the sliced GCODE's filename
     * ``gcode_location``: the sliced GCODE's location
     * ``time``: the time needed for slicing, in seconds (float)

SlicingCancelled
   The slicing of a file has been cancelled. This will happen if a second slicing job
   targeting the same GCODE file has been started by the user.

   Payload:

     * ``stl``: the STL's filename
     * ``stl_location``: the STL's location
     * ``gcode``: the sliced GCODE's filename
     * ``gcode_location``: the sliced GCODE's location

SlicingFailed
   The slicing of a file has failed.

   Payload:

     * ``stl``: the STL's filename
     * ``stl_location``: the STL's location
     * ``gcode``: the sliced GCODE's filename
     * ``gcode_location``: the sliced GCODE's location
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
