.. _sec-api-printerprofiles:

**************************
Printer profile operations
**************************

.. contents::

OctoPrint allows the management of Printer profiles that define a printer's physical properties (such as print volume,
whether a heated bed is available, maximum speeds on its axes etc). The data stored within these profiles is used
for both slicing and gcode visualization.

.. _sec-api-printerprofiles-retrieve:

Retrieve all printer profiles
=============================

.. http:get:: /api/printerprofiles

.. _sec-api-printerprofiles-add:

Add a new printer profile
=========================

.. http:post:: /api/printerprofiles

.. _sec-api-printerporfiles-update:

Update an existing printer profile
==================================

.. http:patch:: /api/printerprofiles/(string:profile)

.. _sec-api-printerprofiles-delete:

Remove an existing printer profile
==================================

.. http:delete:: /api/printerprofiles/(string:profile)

.. _sec-api-printerprofiles-datamodel:

Datamodel
=========

.. _sec-api-printerprofiles-datamodel-profilelist:

Profile list
------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``profiles``
     - 1
     - Object
     - Collection of all printer profiles available in the system
   * - ``profiles.<profile id>``
     - 0..1
     - :ref:`Profile <sec-api-slicing-datamodel-profile>`
     - Information about a profile stored in the system.

.. _sec-api-printerprofiles-datamodel-update:

Add or update request
---------------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``profiles``
     - 1
     - :ref:`Profile <sec-api-slicing-datamodel-profile>`
     - Information about the profile being added/updated. For adding new profiles, all fields must be populated. For updating
       and existing profile, only the values to be overwritten need to be supplied.

.. _sec-api-printerprofiles-datamodel-profile:

Profile
-------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``id``
     - 0..1
     - ``string``
     - Identifier of the profile. Will always be
       returned in responses but can be left out of save/update requests.
   * - ``name``
     - 0..1
     - ``string``
     - Display name of the profile. Will always be
       returned in responses but can be left out of save/update requests.
   * - ``color``
     - 0..1
     - ``string``
     - The color to associate with this profile (used in the UI's title bar). Valid values are "default", "red", "orange",
       "yellow", "green", "blue", "black". Will always be
       returned in responses but can be left out of save/update requests.
   * - ``model``
     - 0..1
     - ``string``
     - Printer model of the profile. Will always be
       returned in responses but can be left out of save/update requests.
   * - ``default``
     - 0..1
     - ``boolean``
     - Whether this is the default profile to be used with new connections (``true``) or not (``false``). Will always be
       returned in responses but can be left out of save/update requests.
   * - ``current``
     - 0..1
     - ``boolean``
     - Whether this is the profile currently active. Will always be returned in responses but ignored in save/update
       requests.
   * - ``resource``
     - 0..1
     - ``URL``
     - Resource URL of the profile, will always be returned in responses but can be left out of save/update requests.
   * - ``volume``
     - 0..1
     - Object
     - The print volume, will always be returned in responses but can be left out of save/update requests.
   * - ``volume.formFactor``
     - 0..1
     - ``string``
     - The form factor of the printer's bed, valid values are "rectangular" and "circular"
   * - ``volume.width``
     - 0..1
     - ``float``
     - The width of the print volume
   * - ``volume.depth``
     - 0..1
     - ``float``
     - The depth of the print volume
   * - ``volume.height``
     - 0..1
     - ``float``
     - The height of the print volume
   * - ``heatedBed``
     - 0..1
     - ``boolean``
     - Whether the printer has a heated bed (``true``) or not (``false``)
   * - ``axes``
     - 0..1
     - Object
     - Description of the printer's axes properties, one entry each for ``x``, ``y``, ``z`` and ``e`` holding maxium speed
       and whether this axis is inverted or not.
   * - ``axes.{axis}.speed``
     - 0..1
     - ``int``
     - Maximum speed of the axis in mm/s.
   * - ``axes.{axis}.inverted``
     - 0..1
     - ``boolean``
     - Whether the axis is inverted or not.
   * - ``extruder``
     - 0..1
     - Object
     - Information about the printer's extruders
   * - ``extruder.nozzleDiameter``
     - 0..1
     - ``float``
     - The diameter of the printer's nozzle(s) in mm.
   * - ``extruder.count``
     - 0..1
     - ``int``
     - Count of extruders on the printer (defaults to 1)
   * - ``extruder.offsets``
     - 0..1
     - Array of ``float`` tuples
     - Tuple of (x, y) values describing the offsets of the other extruders relative to the first extruder. E.g. for a
       printer with two extruders, if the second extruder is offset by 20mm in the X and 25mm in the Y direction, this
       array will read ``[ [0.0, 0.0], [20.0, 25.0] ]``

