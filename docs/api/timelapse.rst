.. _sec-api-timelapse:

*********
Timelapse
*********

.. contents::

.. _sec-api-timelapse-list:

Retrieve a list of timelapses and the current config
====================================================

.. http:get:: /api/timelapse

   Retrieves a list of timelapses and the current config.

   Returns a :ref:`timelapse list <sec-api-timelapse-datamodel-list>` in the
   response body.

   Requires the ``TIMELAPSE_LIST`` permission.

   :param unrendered: If provided and true, also include unrendered timelapses

.. _sec-api-timelapse-delete:

Delete a timelapse
==================

.. http:delete:: /api/timelapse/(string:name)

   Delete the timelapse ``name``.
   
   Returns a :ref:`timelapse list <sec-api-timelapse-datamodel-list>` in the
   response body with the updated information.

   Requires the ``TIMELAPSE_DELETE`` permission.

   :param unrendered: If provided and true, also include unrendered timelapses in the response

.. _sec-api-timelapse-render:

Issue a command for an unrendered timelapse
===========================================

.. http:post:: /api/timelapse/unrendered/(string:name)

   Current only supports to render the unrendered timelapse ``name`` via the
   ``render`` command.

   Requires the ``TIMELAPSE_ADMIN`` permission.

   :json command: The command to issue, currently only ``render`` is supported

.. _sec-api-timelapse-delete-unrendered:

Delete an unrendered timelapse
==============================

.. http:delete:: /api/timelapse/unrendered/(string:name)

   Delete the unrendered timelapse ``name``.

   Returns a :ref:`timelapse list <sec-api-timelapse-datamodel-list>` in the
   response body.

   Requires the ``TIMELAPSE_DELETE`` permission.

   :param unrendered: If provided and true, also include unrendered timelapses in the response

.. _sec-api-timelapse-saveconfig:

Change current timelapse config
===============================

.. http:post:: /api/timelapse

   Save a new :ref:`timelapse configuration <sec-api-timelapse-datamodel-config>` to use for the next print. Set the optional ``save`` flag in the
   configuration to ``true`` in order to make the new configuration persist accross restarts.

   The configuration is expected as the request body.

   Returns a :ref:`timelapse list <sec-api-timelapse-datamodel-list>` in the
   response body.

   Requires the ``TIMELAPSE_ADMIN`` permission.

   :param unrendered: If provided and true, also include unrendered timelapses in the response


.. _sec-api-timelapse-datamodel:

Data model
==========

.. _sec-api-timelapse-datamodel-list:

Timelapse list
--------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``config``
     - 1
     - :ref:`Timelapse config <sec-api-timelapse-datamodel-config>`
     - Current timelapse configuration
   * - ``files``
     - 0..*
     - List of :ref:`rendered timelapses <sec-api-timelapse-datamodel-rendered>`
     - List of rendered timelapse entries
   * - ``unrendered``
     - 0..*
     - List of :ref:`unrendered timelapses <sec-api-timelapse-datamodel-unrendered>`
     - List of unrendered timelapse entries, only present if requested

.. _sec-api-timelapse-datamodel-rendered:

Rendered timelapse
------------------

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
     - Name of the timelapse file
   * - ``size``
     - 1
     - string
     - Formatted size of the timelapse file
   * - ``bytes``
     - 1
     - int
     - Size of the timelapse file in bytes
   * - ``date``
     - 1
     - string
     - Formatted timestamp of the timelapse creation date
   * - ``url``
     - 1
     - string
     - URL for downloading the timelapse
   * - ``thumbnail``
     - 1
     - string
     - URL for downloading a thumbnail of the timelapse (optional)

.. _sec-api-timelapse-datamodel-unrendered:

Unrendered timelapse
--------------------

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
     - Name of the unrendered timelapse job
   * - ``size``
     - 1
     - string
     - Formatted size of all files in the unrendered timelapse job
   * - ``bytes``
     - 1
     - int
     - Size of all files in the unrendered timelapse job in bytes
   * - ``date``
     - 1
     - string
     - Formatted timestamp of the timelapse job creation date
   * - ``recording``
     - 1
     - bool
     - Whether the timelapse is still being recorded (true) or not (false)
   * - ``rendering``
     - 1
     - bool
     - Whether the timelapse is still being rendered (true) or not (false)
   * - ``processing``
     - 1
     - bool
     - Whether the timelapse is either still being recorded or rendered (true) or not (false)


.. _sec-api-timelapse-datamodel-config:

Timelapse configuration
-----------------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``type``
     - 1
     - string
     - Type of the timelapse, either ``off``, ``zchange`` or ``timed``.
   * - ``save``
     - 1
     - bool
     - Optional flag to be included when when saving a configuration to make the configuration persist accross restarts

Further fields are timelapse type specific, see below for details.

.. _sec-api-timelapse-datamodel-config-off:

Z-change-triggered timelapse
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For timelapse type ``zchange``.

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``postRoll``
     - 1
     - int
     - Configured post roll in seconds
   * - ``fps``
     - 1
     - int
     - Frames per second to use for rendered video
   * - ``retractionZHop``
     - 1
     - float
     - Size of retraction Z hop to detect and ignore for z-based snapshots
   * - ``minDelay``
     - 1
     - int
     - Snapshots will be rate limited against this interval, to prevent performance issues with vase mode/continuous z prints

.. _sec-api-timelapse-datamodel-config-timed:

Time triggered timelapse
~~~~~~~~~~~~~~~~~~~~~~~~

For timelapse type ``timed``.

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``postRoll``
     - 1
     - int
     - Configured post roll in seconds
   * - ``fps``
     - 1
     - int
     - Frames per second to use for rendered video
   * - ``interval``
     - 1
     - int
     - Seconds between individual shots

