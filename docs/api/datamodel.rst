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
     - A couple of boolean printer state flags
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
     - The name of the file
   * - ``size``
     - 0..1
     - Number
     - The size of the file in bytes. Only available for ``local`` files.
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
     - :ref:`Print history <sec-api-datamodel-files-prints>`
     - Information regarding prints of this file, if available. Left out in abridged version.

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


.. _sec-api-datamodel-files-prints:

Print history
-------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``failure``
     - 1
     - Number
     - The number of failed prints on record for the file
   * - ``success``
     - 1
     - Number
     - The number of successful prints on record for the file
   * - ``last``
     - 0..1
     - Object
     - Information regarding the last print on record for the file
   * - ``last.date``
     - 1
     - Unix timestamp
     - Timestamp when this file was printed last
   * - ``last.success``
     - 1
     - Boolean
     - Whether the last print on record was a success (``true``) or not (``false``)

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
     - The resource that represents the file (e.g. for issuing commands to or for deleting)
   * - ``download``
     - 0..1
     - URL
     - The download URL for the file
   * - ``model``
     - 0..1
     - URL
     - The model from which this file was generated (e.g. an STL, currently not used)

