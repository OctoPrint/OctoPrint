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
     - Integer
     - The estimated print time for the file, in seconds.
   * - ``lastPrintTime``
     - 0..1
     - Integer
     - The print time of the last print of the file, in seconds.
   * - ``filament``
     - 0..1
     - Object
     - Information regarding the estimated filament usage of the print job
   * - ``filament.length``
     - 0..1
     - Integer
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
     - The name of the file without path. E.g. "file.gco" for a file "file.gco" located anywhere in the file system.
   * - ``path``
     - 1
     - String
     - The path to the file within the location. E.g. "folder/subfolder/file.gco" for a file "file.gco" located within
       "folder" and "subfolder" relative to the root of the location.
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

Additional properties depend on ``type``. For a ``type`` value of ``folder``, see "Folders". For any other value
see "Files".

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
     - Contained children for entries of type ``folder``. Will only include children in subfolders in recursive
       listings. Not present in non recursive listings, this might be revisited in the future.
   * - ``size``
     - 0..1
     - Number
     - The size of all files contained in the folder and its subfolders. Not present in non recursive listings, this might
       be revisited in the future.

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
   * - ``path``
     - 1
     - String
     - The path to the file or folder within the location. E.g. "folder/subfolder/file.gco" for a file "file.gco" located within
       "folder" and "subfolder" relative to the root of the location.
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
     - Integer
     - The estimated print time of the file, in seconds
   * - ``filament``
     - 0..1
     - Object
     - The estimated usage of filament
   * - ``filament.length``
     - 0..1
     - Integer
     - The length of filament used, in mm
   * - ``filament.volume``
     - 0..1
     - Float
     - The volume of filament used, in cm³


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

