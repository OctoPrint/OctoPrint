.. _sec-api-datamodel:

*****************
Common data model
*****************

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
     - ``true`` if the printer is currently printing and in the process of cancelling, ``false`` otherwise
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
     - The list of permissions assigned to the user (note: this does not include implicit permissions inherited from groups).

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
