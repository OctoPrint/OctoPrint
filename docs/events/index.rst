.. _sec-events:

######
Events
######

.. contents::

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
     - event:
       - PrintStarted
       - PrintFailed
       - PrintDone
       - PrintCancelled
       command: python ~/growl.py -t mygrowlserver -d "Event {__eventname} ({name})" -a OctoPrint -i http://raspi/Octoprint_logo.png
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
  * ``{__eventname}`` : the name of the event hook being triggered
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

.. note::

   Plugins may add additional events via the :ref:`octoprint.events.register_custom_events hook <sec-plugins-hook-events-register_custom_events>`.

.. _sec-events-available_events-server:

Server
------

Startup
   The server has started.

Shutdown
   The server is shutting down.

ClientOpened
   A client has connected to the push socket.

   Payload:

     * ``remoteAddress``: the remote address (IP) of the client that connected. On the push socket only available with
       a valid login session.

   **Note:** Name changed in version 1.1.0

   .. versionchanged:: 1.1.0
   .. versionchanged:: 1.4.0

ClientAuthed
   A client has authenticated a user session on the push socket.

   Payload:

     * ``remoteAddress``: the remote address (IP) of the client that authed. On the push socket only available with a
       valid login session.
     * ``username``: the name of the user who authed. On the push socket only available with a valid login session.

  .. versionadded:: 1.4.0

ClientClosed
   A client has disconnected from the push socket.

   Payload:

     * ``remoteAddress``: the remote address (IP) of the client that disconnected. On the push socket only available
       with a valid login session.

UserLoggedIn
   A user logged in. On the push socket only available with a valid login session with admin rights.

   Payload:

     * ``username``: the name of the user who logged in

  .. versionadded:: 1.4.0

UserLoggedOut
   A user logged out. On the push socket only available with a valid login session with admin rights.

   Payload:
     * ``username``: the name of the user who logged out

  .. versionadded:: 1.4.0

ConnectivityChanged
   The server's internet connectivity changed

   Payload:

     * ``old``: Old connectivity value (true for online, false for offline)
     * ``new``: New connectivity value (true for online, false for offline)

  .. versionadded:: 1.3.5

.. _sec-events-available_events-printer_commmunication:

Printer communication
---------------------

Connecting
   The server is attempting to connect to the printer.

  .. versionadded:: 1.3.0

Connected
   The server has connected to the printer.

   Payload:

     * ``port``: the connected serial port
     * ``baudrate``: the baud rate

Disconnecting
   The server is going to disconnect from the printer. Note that this
   event might not always be sent when the server and printer get disconnected
   from each other. Do not depend on this for critical life cycle management.

  .. versionadded:: 1.3.0

Disconnected
   The server has disconnected from the printer

Error
   An unrecoverable error has been encountered, either as reported by the firmware (e.g. a thermal runaway) or
   on the connection.

   Note that this event will not fire for error messages from the firmware that are handled (and as such recovered from)
   either by OctoPrint or a plugin.

   Payload:

     * ``error``: the error string

PrinterStateChanged
   The state of the printer changed.

   Payload:

     * ``state_id``: Id of the new state. See
       :func:`~octoprint.printer.PrinterInterface.get_state_id` for possible values.
     * ``state_string``: Text representation of the new state.

  .. versionadded:: 1.3.0

.. _sec-events-available_events-file_handling:

File handling
-------------

Upload
   A file has been uploaded through the :ref:`REST API <sec-api-fileops-uploadfile>`.

   Payload:
     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``target``: the target storage location to which the file was uploaded, either ``local`` or ``sdcard``
     * ``select``: whether an immediate selection of the file was requested on the API by the corresponding parameter
     * ``print``: whether an immediate print start of the file was requested on the API by the corresponding parameter
     * ``effective_select``: whether the file will actually be selected (``select`` request got granted)
     * ``effective_print``: whether the file will actually start printing (``print`` request got granted)
     * ``userdata``: optional ``userdata`` if provided on the API, will only be present if supplied in the upload request

   .. deprecated:: 1.3.0

        * ``file``: the file's path within its storage location. To be removed in 1.4.0.

  .. versionchanged:: 1.4.0

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

  .. versionadded:: 1.3.3

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

  .. versionadded:: 1.3.3

FileMoved
   A file has been moved from one location to an other location.

   Payload:
     * ``storage``: the storage's identifier
     * ``source_path``: the source file's path within its storage location
     * ``source_name``: the source file's name
     * ``source_type``: the source file's type, a list of the path within the type hierarchy, e.g. ``["machinecode", "gcode"]`` or
       ``["model", "stl"]``
     * ``destination_path``: the source file's path within its storage location
     * ``destination_name``: the source file's name
     * ``destination_type``: the source file's type, a list of the path within the type hierarchy, e.g. ``["machinecode", "gcode"]`` or
       ``["model", "stl"]``

   .. note::

      A moved file still triggers first a ``FileRemoved`` for its original path and then ``FileAdded`` event for the new one. After that a ```UpdatedFiles``` event is also fired.

  .. versionadded:: 1.8.0

FolderAdded
   A folder has been added to a storage.

   Payload:
     * ``storage``: the storage's identifier
     * ``path``: the folder's path within its storage location
     * ``name``: the folder's name

   .. note::

      A copied folder triggers this for its new path. A moved folder first triggers ``FolderRemoved`` for its original
      path and then ``FolderAdded`` for the new one.

  .. versionadded:: 1.3.3

FolderRemoved
   A folder has been removed from a storage.

   Payload:
     * ``storage``: the storage's identifier
     * ``path``: the folder's path within its storage location
     * ``name``: the folder's name

   .. note::

      A moved folder first triggers ``FolderRemoved`` for its original path and then ``FolderAdded`` for the new one.

  .. versionadded:: 1.3.3

FolderMoved
   A folder has been moved from one location to an other location.

   Payload:
     * ``storage``: the storage's identifier
     * ``source_path``: the source folder's path within its storage location
     * ``source_name``: the source folder's name
     * ``destination_path``: the source folder's path within its storage location
     * ``destination_name``: the source folder's name

   .. note::

      A moved folder still triggers first a ``FolderRemoved`` for its original path and then ``FolderAdded`` event for the new one. After that a ```UpdatedFiles``` event is also fired.

  .. versionadded:: 1.8.0

UpdatedFiles
   A file list was modified.

   Payload:

     * ``type``: the type of file list that was modified. Only ``printables`` is supported here. See the deprecation
       note below.

       .. deprecated:: 1.2.0

          The ``gcode`` modification type has been superseded by ``printables``. It is currently still available for
          reasons of backwards compatibility and will also be sent on modification of ``printables``. It will however
          be removed with 1.4.0.

   .. versionchanged:: 1.4.0

MetadataAnalysisStarted
   The metadata analysis of a file has started.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the file's origin storage location

   .. deprecated:: 1.3.0

        * ``file``: the file's path within its storage location. To be removed in 1.4.0.

  .. versionchanged:: 1.4.0

MetadataAnalysisFinished
   The metadata analysis of a file has finished.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the file's origin storage location
     * ``result``: the analysis result -- this is a Python object currently only available for internal use

   .. deprecated:: 1.3.0

        * ``file``: the file's path within its storage location. To be removed in 1.4.0.

   .. versionchanged:: 1.4.0

FileSelected
   A file has been selected for printing.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``

   .. deprecated:: 1.3.0

        * ``file``: the file's full path on disk (``local``) or within its storage (``sdcard``). To be removed in 1.4.0.
        * ``filename``: the file's name.  To be removed in 1.4.0.

   .. versionchanged:: 1.4.0

FileDeselected
   No file is selected any more for printing.

TransferStarted
   A file transfer to the printer's SD has started.

   Payload:

     * ``local``: the file's name as stored locally
     * ``remote``: the file's name as stored on SD

   **Note:** Name changed in version 1.1.0

   .. versionchanged:: 1.1.0

TransferDone
   A file transfer to the printer's SD has finished.

   Payload:

     * ``time``: the time it took for the transfer to complete in seconds
     * ``local``: the file's name as stored locally
     * ``remote``: the file's name as stored on SD

.. _sec-events-available_events-printing:

Printing
--------

PrintStarted
   A print has started.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``
     * ``size``: the file's size in bytes (if available)
     * ``owner``: the user who started the print job (if available)
     * ``user``: the user who started the print job (if available)

   .. deprecated:: 1.3.0

        * ``file``: the file's full path on disk (``local``) or within its storage (``sdcard``). To be removed in 1.4.0.
        * ``filename``: the file's name.  To be removed in 1.4.0.

   .. versionchanged:: 1.4.0

PrintFailed
   A print failed.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``
     * ``size``: the file's size in bytes (if available)
     * ``owner``: the user who started the print job (if available)
     * ``time``: the elapsed time of the print when it failed, in seconds (float)
     * ``reason``: the reason the print failed, either ``cancelled`` or ``error``

   .. deprecated:: 1.3.0

        * ``file``: the file's full path on disk (``local``) or within its storage (``sdcard``). To be removed in 1.4.0.
        * ``filename``: the file's name.  To be removed in 1.4.0.

   .. versionchanged:: 1.4.0

PrintDone
   A print completed successfully.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``
     * ``size``: the file's size in bytes (if available)
     * ``owner``: the user who started the print job (if available)
     * ``time``: the time needed for the print, in seconds (float)

   .. deprecated:: 1.3.0

        * ``file``: the file's full path on disk (``local``) or within its storage (``sdcard``). To be removed in 1.4.0.
        * ``filename``: the file's name.  To be removed in 1.4.0.

   .. versionchanged:: 1.4.0

PrintCancelling
   The print is about to be cancelled.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``
     * ``size``: the file's size in bytes (if available)
     * ``owner``: the user who started the print job (if available)
     * ``user``: the user who cancelled the print job (if available)
     * ``firmwareError``: the firmware error that caused cancelling the print job, if any

  .. versionadded:: 1.3.7

PrintCancelled
   The print has been cancelled.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``
     * ``size``: the file's size in bytes (if available)
     * ``owner``: the user who started the print job (if available)
     * ``time``: the elapsed time of the print when it was cancelled, in seconds (float)
     * ``user``: the user who cancelled the print job (if available)
     * ``position``: the print head position at the time of cancelling (if available, not available if recording of the
       position on cancel is disabled)
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

        * ``file``: the file's full path on disk (``local``) or within its storage (``sdcard``). To be removed in 1.4.0.
        * ``filename``: the file's name. To be removed in 1.4.0.

   .. versionchanged:: 1.4.0

PrintPaused
   The print has been paused.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``
     * ``size``: the file's size in bytes (if available)
     * ``owner``: the user who started the print job (if available)
     * ``user``: the user who paused the print job (if available)
     * ``position``: the print head position at the time of pausing (if available, not available if the recording of
       the position on pause is disabled or the pause is completely handled by the printer's firmware)
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

        * ``file``: the file's full path on disk (``local``) or within its storage (``sdcard``). To be removed in 1.4.0.
        * ``filename``: the file's name. To be removed in 1.4.0.

   .. versionchanged:: 1.4.0

PrintResumed
   The print has been resumed.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``
     * ``size``: the file's size in bytes (if available)
     * ``owner``: the user who started the print job (if available)
     * ``user``: the user who resumed the print job (if available)

   .. deprecated:: 1.3.0

        * ``file``: the file's full path on disk (``local``) or within its storage (``sdcard``). To be removed in 1.4.0.
        * ``filename``: the file's name. To be removed in 1.4.0.

   .. versionchanged:: 1.4.0

GcodeScript${ScriptName}Running
   A custom :ref:`GCODE script <sec-features-gcode_scripts>` has started running.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``
     * ``size``: the file's size in bytes (if available)
     * ``owner``: the user who started the print job (if available)
     * ``time``: the time needed for the print, in seconds (float)

   .. versionadded:: 1.6.0

GcodeScript${ScriptName}Finished
   A custom :ref:`GCODE script <sec-features-gcode_scripts>` has finished running.

   Payload:

     * ``name``: the file's name
     * ``path``: the file's path within its storage location
     * ``origin``: the origin storage location of the file, either ``local`` or ``sdcard``
     * ``size``: the file's size in bytes (if available)
     * ``owner``: the user who started the print job (if available)
     * ``time``: the time needed for the print, in seconds (float)

   .. versionadded:: 1.6.0

ChartMarked
   A time-based marking has been made on the UI's temperature chart.

   Payload:

     * ``type``: the marking's ID. Built-in types are ``print``, ``done``, ``cancel``, ``pause``, and ``resume``. Plugins may set arbitrary types
     * ``label``: the human-readable short label of the marking
     * ``time``: the epoch time of marking

   .. versionadded:: 1.9.0

.. _sec-events-available_events-gcode_processing:

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

FilamentChange
  An ``M600``, ``M701`` or ``M702`` was sent to the printer through OctoPrint (not triggered when printing from SD!)

  .. versionadded:: 1.7.0

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

   .. versionadded:: 1.3.0

ToolChange
   A tool change command was sent to the printer. The payload contains the former current tool index and the
   new current tool index.

   Payload:

     * ``old``: old tool index
     * ``new``: new tool index

   .. versionadded:: 1.3.5

CommandSuppressed
   A command was suppressed by OctoPrint due to according configuration and will not be
   sent to the printer.

   Payload:

     * ``command``: the command that was suppressed
     * ``message``: a message containing an explanation of the command suppression
     * ``severity``: a severity level, either ``warn`` or ``info`` - ``warn`` indicates
       that the command was suppressed probably due to a misconfiguration either inside
       OctoPrint or the firmware and that it should be investigated by the user

   .. versionadded:: 1.5.0

InvalidToolReported
   The firmware reported a tool as invalid upon trying to select it. It has thus been marked
   as invalid and further attempts to select said tool will result in the tool command
   to get suppressed (and ``SuppressedCommand`` to be generated).

   Payload:

     * ``tool``: the tool number that was reported as invalid by the firmware
     * ``fallback``: the tool number that OctoPrint will revert to

   .. versionadded:: 1.5.0

.. _sec-events-available_events-timelapses:

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

   .. versionadded:: 1.3.0

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

.. _sec-events-available_events-slicing:

Slicing
-------

SlicingStarted
   The slicing of a file has started.

   Payload:

     * ``slicer``: the used slicer
     * ``stl``: the STL's filename
     * ``stl_location``: the STL's location
     * ``gcode``: the sliced GCODE's filename
     * ``gcode_location``: the sliced GCODE's location
     * ``progressAvailable``: true if progress information via the ``slicingProgress`` push update will be available, false if not

SlicingDone
   The slicing of a file has completed.

   Payload:

     * ``slicer``: the used slicer
     * ``stl``: the STL's filename
     * ``stl_location``: the STL's location
     * ``gcode``: the sliced GCODE's filename
     * ``gcode_location``: the sliced GCODE's location
     * ``time``: the time needed for slicing, in seconds (float)

SlicingCancelled
   The slicing of a file has been cancelled. This will happen if a second slicing job
   targeting the same GCODE file has been started by the user.

   Payload:

     * ``slicer``: the used slicer
     * ``stl``: the STL's filename
     * ``stl_location``: the STL's location
     * ``gcode``: the sliced GCODE's filename
     * ``gcode_location``: the sliced GCODE's location

SlicingFailed
   The slicing of a file has failed.

   Payload:

     * ``slicer``: the used slicer
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

  .. versionadded:: 1.2.12

SlicingProfileModified
   A slicing profile was modified.

   Payload:

     * ``slicer``: the slicer for which the profile was modified
     * ``profile``: the profile that was modified

  .. versionadded:: 1.2.12

SlicingProfileDeleted
   A slicing profile was deleted.

   Payload:

     * ``slicer``: the slicer for which the profile was deleted
     * ``profile``: the profile that was deleted

  .. versionadded:: 1.2.12

.. _sec-events-available_events-settings:

Settings
--------

SettingsUpdated
   The settings were updated via the REST API.

   This event may also be triggered if calling code of :py:class:`octoprint.settings.Settings.save` or
   :py:class:`octoprint.plugin.PluginSettings.save` sets the ``trigger_event`` parameter to ``True``.

   .. versionadded:: 1.2.0

.. _sec-events-available_events-printer_profile:

Printer Profile
---------------

PrinterProfileModified
   A printer profile was modified.

   Payload:

     * ``identifier``: the identifier of the modified printer profile

   .. versionadded:: 1.3.12
