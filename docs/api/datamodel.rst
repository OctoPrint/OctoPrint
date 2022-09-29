.. _sec-api-datamodel:

*****************
Common data model
*****************

.. contents::

.. _sec-api-datamodel-printer:

Printer related
===============

.. _sec-api-datamodel-printer-state:

Printer State
-------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``text``
     - 1
     - String
     - A textual representation of the current state of the printer, e.g. "Operational" or "Printing"
   * - ``flags``
     - 1
     - Printer state flags
     - A few boolean printer state flags
   * - ``flags.operational``
     - 1
     - Boolean
     - ``true`` if the printer is operational, ``false`` otherwise
   * - ``flags.paused``
     - 1
     - Boolean
     - ``true`` if the printer is currently paused, ``false`` otherwise
   * - ``flags.printing``
     - 1
     - Boolean
     - ``true`` if the printer is currently printing, ``false`` otherwise
   * - ``flags.pausing``
     - 1
     - Boolean
     - ``true`` if the printer is currently printing and in the process of pausing, ``false`` otherwise
   * - ``flags.cancelling``
     - 1
     - Boolean
     - ``true`` if the printer is currently printing and in the process of pausing, ``false`` otherwise
   * - ``flags.sdReady``
     - 1
     - Boolean
     - ``true`` if the printer's SD card is available and initialized, ``false`` otherwise. This is redundant information
       to :ref:`the SD State <sec-api-printer-datamodel-sdstate>`.
   * - ``flags.error``
     - 1
     - Boolean
     - ``true`` if an unrecoverable error occurred, ``false`` otherwise
   * - ``flags.ready``
     - 1
     - Boolean
     - ``true`` if the printer is operational and no data is currently being streamed to SD, so ready to receive instructions
   * - ``flags.closedOrError``
     - 1
     - Boolean
     - ``true`` if the printer is disconnected (possibly due to an error), ``false`` otherwise

.. _sec-api-datamodel-printer-tempdata:

Temperature Data
----------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``actual``
     - 1
     - Number
     - Current temperature
   * - ``target``
     - 1
     - Number
     - Target temperature, may be ``null`` if no target temperature is set.
   * - ``offset``
     - 0..1
     - Number
     - Currently configured temperature offset to apply, will be left out for historic temperature information.

.. _sec-api-datamodel-printer-temphistory:

Historic Temperature Data Point
-------------------------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``time``
     - 1
     - Unix Timestamp
     - Timestamp of this data point
   * - ``tool{n}``
     - 0..*
     - :ref:`Temperature Data <sec-api-datamodel-printer-tempdata>`
     - Temperature stats for tool *n*. Enumeration starts at 0 for the first tool. Not included if querying only
       bed state.
   * - ``bed``
     - 0..*
     - :ref:`Temperature Data <sec-api-datamodel-printer-tempdata>`
     - Temperature stats for the printer's heated bed. Not included if querying only tool state.

.. _sec-api-datamodel-printer-tempoffset:

Temperature offset
------------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``tool{n}``
     - 0..1
     - Number
     - Temperature offset for tool *n*. Enumeration starts at 0 for the first tool.
   * - ``bed``
     - 0..1
     - Number
     - Temperature offset for the printer's heated bed.

.. _sec-api-datamodel-printer-resends:

Resend stats
------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``count``
     - 1
     - int
     - Number of resend requests received since connecting.
   * - ``transmitted``
     - 1
     - int
     - Number of transmitted lines since connecting.
   * - ``ratio``
     - 1
     - int
     - Percentage of resend requests vs transmitted lines. Value between 0 and 100.

.. _sec-api-datamodel-jobs:

Job related
===========

.. _sec-api-datamodel-jobs-job:

Job information
---------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``file``
     - 1
     - :ref:`File information (abridged) <sec-api-datamodel-files-file>`
     - The file that is the target of the current print job
   * - ``estimatedPrintTime``
     - 0..1
     - Float
     - The estimated print time for the file, in seconds.
   * - ``lastPrintTime``
     - 0..1
     - Float
     - The print time of the last print of the file, in seconds.
   * - ``filament``
     - 0..1
     - Object
     - Information regarding the estimated filament usage of the print job
   * - ``filament.length``
     - 0..1
     - Float
     - Length of filament used, in mm
   * - ``filament.volume``
     - 0..1
     - Float
     - Volume of filament used, in cm³

.. _sec-api-datamodel-jobs-progress:

Progress information
--------------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``completion``
     - 1
     - Float
     - Percentage of completion of the current print job
   * - ``filepos``
     - 1
     - Integer
     - Current position in the file being printed, in bytes from the beginning
   * - ``printTime``
     - 1
     - Integer
     - Time already spent printing, in seconds
   * - ``printTimeLeft``
     - 1
     - Integer
     - Estimate of time left to print, in seconds
   * - ``printTimeLeftOrigin``
     - 1
     - String
     - Origin of the current time left estimate. Can currently be either of:

         * ``linear``: based on an linear approximation of the progress in file in bytes vs time
         * ``analysis``: based on an analysis of the file
         * ``estimate``: calculated estimate after stabilization of linear estimation
         * ``average``: based on the average total from past prints of the same model against the same printer profile
         * ``mixed-analysis``: mixture of ``estimate`` and ``analysis``
         * ``mixed-average``: mixture of ``estimate`` and ``average``

.. _sec-api-datamodel-files:

File related
============

.. _sec-api-datamodel-files-file:

File information
----------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``name``
     - 1
     - String
     - The name of the file without path. E.g. "file.gco" for a file "file.gco" located anywhere in the file system. Currently
       this will always fit into ASCII.
   * - ``display``
     - 1
     - String
     - The name of the file without the path, this time potentially with non-ASCII unicode characters.
       E.g. "a turtle 🐢.gco" for a file "a_turtle_turtle.gco" located anywhere in the file system.
   * - ``path``
     - 1
     - String
     - The path to the file within the location. E.g. "folder/subfolder/file.gco" for a file "file.gco" located within
       "folder" and "subfolder" relative to the root of the location. Currently this will always fit into ASCII.
   * - ``type``
     - 1
     - String
     - Type of file. ``model`` or ``machinecode``. Or ``folder`` if it's a folder, in which case the ``children``
       node will be populated
   * - ``typePath``
     - 1
     - list
     - Path to type of file in extension tree. E.g. ``["model", "stl"]`` for ``.stl`` files, or ``["machinecode", "gcode"]``
       for ``.gcode`` files. ``["folder"]`` for folders.

Additional properties depend on ``type``.
For a ``type`` value of ``folder``, see :ref:`Folders <sec-api-datamodel-files-folders>`.
For any other value see :ref:`Files <sec-api-datamodel-files-files>`.

.. _sec-api-datamodel-files-folders:

Folders
'''''''

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``children``
     - 0..*
     - Array of :ref:`File information items <sec-api-datamodel-files-file>`
     - Contained children for entries of type ``folder``. On non recursive listings only present on first level
       sub folders!
   * - ``size``
     - 0..1
     - Number
     - The size of all files contained in the folder and its subfolders. Not present in non recursive listings!

.. _sec-api-datamodel-files-files:

Files
'''''

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``hash``
     - 0..1
     - String
     - MD5 hash of the file. Only available for ``local`` files.
   * - ``size``
     - 0..1
     - Number
     - The size of the file in bytes. Only available for ``local`` files or ``sdcard`` files if the printer
       supports file sizes for sd card files.
   * - ``date``
     - 0..1
     - Unix timestamp
     - The timestamp when this file was uploaded. Only available for ``local`` files.
   * - ``origin``
     - 1
     - String, either ``local`` or ``sdcard``
     - The origin of the file, ``local`` when stored in OctoPrint's ``uploads`` folder, ``sdcard`` when stored on the
       printer's SD card (if available)
   * - ``refs``
     - 0..1
     - :ref:`sec-api-datamodel-files-ref`
     - References relevant to this file, left out in abridged version
   * - ``gcodeAnalysis``
     - 0..1
     - :ref:`GCODE analysis information <sec-api-datamodel-files-gcodeanalysis>`
     - Information from the analysis of the GCODE file, if available. Left out in abridged version.
   * - ``prints``
     - 0..1
     - :ref:`Print history information <sec-api-datamodel-files-prints>`
     - Information about previous prints of the file. Left out if the file has never been printed.
   * - ``statistics``
     - 0..1
     - :ref:`Print statistics information <sec-api-datamodel-files-stats>`
     - Statistics about the file, based on the previous print times. Left out if the file has never been printed.

.. _sec-api-datamodel-files-fileabridged:

Abridged file or folder information
-----------------------------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``name``
     - 1
     - String
     - The name of the file or folder without path. E.g. "file.gco" for a file "file.gco" located anywhere in the file system.
       Currently this will always fit into ASCII.
   * - ``display``
     - 1
     - String
     - The name of the file without the path, this potentially with non-ASCII unicode characters.
       E.g. "a turtle 🐢.gco" for a file "a_turtle_turtle.gco" located anywhere in the file system.
   * - ``path``
     - 1
     - String
     - The path to the file or folder within the location. E.g. "folder/subfolder/file.gco" for a file "file.gco" located within
       "folder" and "subfolder" relative to the root of the location. Currently this will always fit into ASCII.
   * - ``origin``
     - 1
     - String, either ``local`` or ``sdcard``
     - The origin of the file, ``local`` when stored in OctoPrint's ``uploads`` folder, ``sdcard`` when stored on the
       printer's SD card (if available)
   * - ``refs``
     - 0..1
     - :ref:`sec-api-datamodel-files-ref`
     - References relevant to this file or folder, left out in abridged version

.. _sec-api-datamodel-files-gcodeanalysis:

GCODE analysis information
--------------------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``estimatedPrintTime``
     - 0..1
     - Float
     - The estimated print time of the file, in seconds
   * - ``filament``
     - 0..1
     - Object
     - The estimated usage of filament
   * - ``filament.tool{n}.length``
     - 0..1
     - Float
     - The length of filament used, in mm
   * - ``filament.tool{n}.volume``
     - 0..1
     - Float
     - The volume of filament used, in cm³
   * - ``dimensions``
     - 0..1
     - Object
     - Information regarding the size of the printed model
   * - ``dimensions.depth``
     - 0..1
     - Float
     - The depth of the printed model, in mm
   * - ``dimensions.height``
     - 0..1
     - Float
     - The height of the printed model, in mm
   * - ``dimensions.width``
     - 0..1
     - Float
     - The width of the printed model, in mm
   * - ``printingArea``
     - 0..1
     - Object
     - Information regarding the size of the printing area
   * - ``printingArea.maxX``
     - 0..1
     - Float
     - The maximum X coordinate of the printed model, in mm
   * - ``printingArea.maxY``
     - 0..1
     - Float
     - The maximum Y coordinate of the printed model, in mm
   * - ``printingArea.maxZ``
     - 0..1
     - Float
     - The maximum Z coordinate of the printed model, in mm
   * - ``printingArea.minX``
     - 0..1
     - Float
     - The minimum X coordinate of the printed model, in mm
   * - ``printingArea.minY``
     - 0..1
     - Float
     - The minimum Y coordinate of the printed model, in mm
   * - ``printingArea.minZ``
     - 0..1
     - Float
     - The minimum Z coordinate of the printed model, in mm
   * - ``travelArea``
     - 0..1
     - Object
     - Information regarding the bounding box of all moves
   * - ``travelArea.maxX``
     - 0..1
     - Float
     - The maximum X coordinate of all moves, in mm
   * - ``travelArea.maxY``
     - 0..1
     - Float
     - The maximum Y coordinate of all moves, in mm
   * - ``travelArea.maxZ``
     - 0..1
     - Float
     - The maximum Z coordinate of all moves, in mm
   * - ``travelArea.minX``
     - 0..1
     - Float
     - The minimum X coordinate of all moves, in mm
   * - ``travelArea.minY``
     - 0..1
     - Float
     - The minimum Y coordinate of all moves, in mm
   * - ``travelArea.minZ``
     - 0..1
     - Float
     - The minimum Z coordinate of all moves, in mm
   * - ``travelDimensions``
     - 0..1
     - Object
     - Information regarding the size of the travel area
   * - ``travelDimensions.depth``
     - 0..1
     - Float
     - The depth of the travel area, in mm
   * - ``travelDimensions.height``
     - 0..1
     - Float
     - The height of the travel area, in mm
   * - ``travelDimensions.width``
     - 0..1
     - Float
     - The width of the travel area, in mm


.. _sec-api-datamodel-files-ref:

References
----------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``resource``
     - 1
     - URL
     - The resource that represents the file or folder (e.g. for issuing commands to or for deleting)
   * - ``download``
     - 0..1
     - URL
     - The download URL for the file. Never present for folders.
   * - ``model``
     - 0..1
     - URL
     - The model from which this file was generated (e.g. an STL, currently not used). Never present for
       folders.

.. _sec-api-datamodel-files-prints:

Print History
-------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``success``
     - 1
     - Number
     - Number of successful prints
   * - ``failure``
     - 1
     - Number
     - Number of failed prints
   * - ``last.date``
     - 1
     - Unix Timestamp
     - Last date this file was printed
   * - ``last.printTime``
     - 1
     - Float
     - Last print time in seconds
   * - ``last.success``
     - 1
     - Boolean
     - Whether the last print was a success or not

.. _sec-api-datamodel-files-stats:

Print Statistics
----------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``averagePrintTime``
     - 1
     - Object
     - Object that maps printer profile names to the last print time of the file, in seconds
   * - ``lastPrintTime``
     - 1
     - Object
     - Object that maps printer profile names to the average print time of the file, in seconds

.. _sec-api-datamodel-access:

Access control
==============

.. _sec-api-datamodel-access-users:

User record
-----------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``name``
     - 1
     - string
     - The user's name
   * - ``active``
     - 1
     - bool
     - Whether the user's account is active (true) or not (false)
   * - ``user``
     - 1
     - bool
     - Whether the user has user rights. Should always be true. Deprecated as of 1.4.0, use the ``users`` group instead.
   * - ``admin``
     - 1
     - bool
     - Whether the user has admin rights (true) or not (false). Deprecated as of 1.4.0, use the ``admins`` group instead.
   * - ``apikey``
     - 0..1
     - string
     - The user's personal API key
   * - ``settings``
     - 1
     - object
     - The user's personal settings, might be an empty object.
   * - ``groups``
     - 1..n
     - List of string
     - Groups assigned to the user
   * - ``needs``
     - 1
     - :ref:`Needs object <sec-api-datamodel-access-needs>`
     - Effective needs of the user
   * - ``permissions``
     - 0..n
     - List of :ref:`Permissions <sec-api-datamodel-access-permissions>`
     - The list of permissions assigned to the user (note: this does not include implicit permissions inherit from groups).

.. _sec-api-datamodel-access-permissions:

Permission record
-----------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``key``
     - 1
     - string
     - The permission's identifier
   * - ``name``
     - 1
     - string
     - The permission's name
   * - ``dangerous``
     - 1
     - boolean
     - Whether the permission should be considered dangerous due to a high responsibility (true) or not (false).
   * - ``default_groups``
     - 1
     - List of string
     - List of group identifiers for which this permission is enabled by default
   * - ``description``
     - 1
     - string
     - Human readable description of the permission
   * - ``needs``
     - 1
     - :ref:`Needs object <sec-api-datamodel-access-needs>`
     - Needs assigned to the permission

.. _sec-api-datamodel-access-groups:

Group record
------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``key``
     - 1
     - string
     - The group's identifier
   * - ``name``
     - 1
     - string
     - The group's name
   * - ``description``
     - 1
     - string
     - A human readable description of the group
   * - ``permissions``
     - 0..n
     - List of :ref:`Permissions <sec-api-datamodel-access-permissions>`
     - The list of permissions assigned to the group (note: this does not include implicit permissions inherited from
       subgroups).
   * - ``subgroups``
     - 0..n
     - List of :ref:`Groups <sec-api-datamodel-access-groups>`
     - Subgroups assigned to the group
   * - ``needs``
     - 1
     - :ref:`Needs object <sec-api-datamodel-access-needs>`
     - Effective needs of the group
   * - ``default``
     - 1
     - boolean
     - Whether this is a default group (true) or not (false)
   * - ``removable``
     - 1
     - boolean
     - Whether this group can be removed (true) or not (false)
   * - ``changeable``
     - 1
     - boolean
     - Whether this group can be modified (true) or not (false)
   * - ``toggleable``
     - 1
     - boolean
     - Whether this group can be assigned to users or other groups (true) or not (false)

.. _sec-api-datamodel-access-needs:

Needs
-----

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``role``
     - 0..1
     - List of string
     - List of ``role`` needs
   * - ``group``
     - 0..1
     - List of string
     - List of ``group`` needs
