.. _sec-api-push:

************
Push updates
************

.. warning::

   The interface documented here is the status quo that might be changed while the interfaces are streamlined for
   a more general consumption. If you happen to want to develop against it, you should drop me an email to make sure I can give you a heads-up when
   something changes.

.. contents::

To enable real time information exchange between client and server, OctoPrint uses
`SockJS <https://github.com/sockjs/sockjs-protocol>`_ to push
status updates, temperature changes etc to connected web interface instances.

Each pushed message consists of a simple JSON object that follows this basic structure:

.. sourcecode:: javascript

   {
     "<type>": <payload>
   }

``type`` indicates the type of message being pushed to the client, the attached ``payload`` is message specific. The
following message types are currently available for usage by 3rd party clients:

  * ``current``: Rate limited general state update, payload contains information about the printer's state, job progress,
    accumulated temperature points and log lines since last update. OctoPrint will send these updates when new information
    is available, but not more often than twice per second in order to not flood the client with messages (e.g.
    during printing). See :ref:`the payload data model <sec-api-push-datamodel-currentandhistory>`.
  * ``history``: Current state, temperature and log history, sent upon initial connect to get the client up to date. Same
    payload data model as ``current``, see :ref:`below <sec-api-push-datamodel-currentandhistory>`.
  * ``event``: Events triggered within OctoPrint, such as e.g. ``PrintFailed`` or ``MovieRenderDone``. Payload is the event
    type and payload, see :ref:`below <sec-api-push-datamodel-event>`. Sent when an event is triggered internally.
  * ``slicingProgress``: Progress updates from an active slicing background job, payload contains information about the
    model being sliced, the target file, the slicer being used and the progress as a percentage.
    See :ref:`the payload data model <sec-api-push-datamodel-slicingprogress>`.

Clients must ignore any unknown messages.

The data model of the attached payloads is described further below.

OctoPrint's SockJS socket also accepts one command from the client to the server,
the ``throttle`` command. Usually, OctoPrint will push the general state update
in the ``current`` message twice per second. For some clients that might still
be too fast, so they can signal a different factor to OctoPrint utilizing the
``throttle`` message. OctoPrint expects a single integer here which represents
the multiplier for the base rate limit of one message every 500ms. A value of
1 hence will produce the default behaviour of getting every update. A value of
2 will set the rate limit to maximally one message every 1s, 3 to maximally one
message every 1.5s and so on.

Example for a ``throttle`` client-server-message:

.. sourcecode:: javascript

   {
     "throttle": 2
   }

.. _sec-api-push-datamodel:

Datamodel
=========

.. _sec-api-push-datamodel-currentandhistory:

``current`` and ``history`` payload
-----------------------------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``state``
     - 1
     - :ref:`State information <sec-api-datamodel-printer-state>`
     - Information about the current machine state
   * - ``job``
     - 1
     - :ref:`Job information <sec-api-datamodel-jobs-job>`
     - Information about the currently active print job
   * - ``progress``
     - 1
     - :ref:`Progress information <sec-api-datamodel-jobs-progress>`
     - Information about the current print/streaming progress
   * - ``currentZ``
     - 1
     - Float
     - Current height of the Z-Axis (= current height of model) during printing from a local file
   * - ``offsets``
     - 0..1
     - :ref:`Temperature offsets <sec-api-datamodel-printer-tempoffset>`
     - Currently configured temperature offsets
   * - ``temps``
     - 0..*
     - List of :ref:`Temperature Data Points <sec-api-datamodel-printer-temphistory>`
     - Temperature data points for plotting
   * - ``logs``
     - 0..*
     - List of String
     - Lines for the serial communication log (send/receive)
   * - ``messages``
     - 0..*
     - List of String
     - Lines for the serial communication log (special messages)

.. _sec-api-push-datamodel-event:

``event`` payload
-----------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``type``
     - 1
     - String
     - Name of the event
   * - ``payload``
     - 1
     - Object
     - Payload associated with the event

.. _sec-api-push-datamodel-slicingprogress:

``slicingProgress`` payload
---------------------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``slicer``
     - 1
     - String
     - Name of the slicer used
   * - ``source_location``
     - 1
     - String
     - Location of the source file being sliced, at the moment either ``local`` or ``sdcard``
   * - ``source_path``
     - 1
     - String
     - Path of the source file being sliced (e.g. an STL file)
   * - ``dest_location``
     - 1
     - String
     - Location of the destination file being created, at the moment either ``local`` or ``sdcard``
   * - ``dest_path``
     - 1
     - String
     - Path of the destination file being sliced (e.g. a GCODE file)
   * - ``progress``
     - 1
     - Number (Float)
     - Percentage of slicing job already completed
