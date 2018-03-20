.. _sec-bundledplugins-logging:

Logging
=======

The OctoPrint Logging plugin comes bundled with OctoPrint starting with version 1.3.7.

It implements the log management functionality that was formerly part of the core application and adds features to
configure logging levels for sub modules through the included settings dialog.

.. _fig-bundledplugins-logging-settings:
.. figure:: ../images/bundledplugins-logging-settings.png
   :align: center
   :alt: Logging plugin

   The settings dialog of the Logging plugin

.. _sec-bundledplugins-logging-api:

API
---

.. note::

   All log file management operations require admin rights.

.. _sec-bundledplugins-logging-api-list_logs:

Retrieve a list of available log files
++++++++++++++++++++++++++++++++++++++

.. http:get:: /plugin/logging/logs

   Retrieve information regarding all log files currently available and regarding the disk space still available
   in the system on the location the log files are being stored.

   Returns a :ref:`Logfile Retrieve response <sec-bundledplugins-logging-api-datamodel-retrieveresponse>`.

   **Example**

   .. sourcecode:: http

      GET /plugin/logging/logs HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "files" : [
          {
            "date" : 1393158814,
            "name" : "octoprint.log",
            "size" : 43712,
            "refs": {
              "resource": "http://example.com/plugin/logging/logs/octoprint.log",
              "download": "http://example.com/downloads/logs/octoprint.log"
            }
          },
          {
            "date" : 1392628936,
            "name" : "octoprint.log.2014-02-17",
            "size" : 13205,
            "refs": {
              "resource": "http://example.com/plugin/logging/logs/octoprint.log.2014-02-17",
              "download": "http://example.com/downloads/logs/octoprint.log.2014-02-17"
            }
          },
          {
            "date" : 1393158814,
            "name" : "serial.log",
            "size" : 1798419,
            "refs": {
              "resource": "http://example.com/plugin/logging/logs/serial.log",
              "download": "http://example.com/downloads/logs/serial.log"
            }
          }
        ],
        "free": 12237201408
      }

   :statuscode 200: No error
   :statuscode 403: If the given API token did not have admin rights associated with it

.. _sec-bundledplugins-logging-api-delete_logs:

Delete a specific logfile
+++++++++++++++++++++++++

.. http:delete:: /plugin/logging/logs/(path:filename)

   Delete the selected log file with name `filename`.

   Returns a :http:statuscode:`204` after successful deletion.

   **Example Request**

   .. sourcecode:: http

      DELETE /plugin/logging/logs/octoprint.log.2014-02-17 HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   :param filename: The filename of the log file to delete
   :statuscode 204: No error
   :statuscode 403: If the given API token did not have admin rights associated with it
   :statuscode 404: If the file was not found

.. _sec-bundledplugins-logging-api-datamodel:

Data model
++++++++++

.. _sec-bundledplugins-logging-api-datamodel-retrieveresponse:

Logfile Retrieve Response
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``files``
     - 0..*
     - Array of :ref:`File information items <sec-bundledplugins-logging-api-datamodel-fileinfo>`
     - The list of requested files. Might be an empty list if no files are available
   * - ``free``
     - 1
     - String
     - The amount of disk space in bytes available in the local disk space (refers to OctoPrint's ``logs`` folder).

.. _sec-bundledplugins-logging-api-datamodel-fileinfo:

File information
~~~~~~~~~~~~~~~~

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
     - 1
     - Number
     - The size of the file in bytes.
   * - ``date``
     - 1
     - Unix timestamp
     - The timestamp when this file was last modified.
   * - ``refs``
     - 1
     - :ref:`References <sec-bundledplugins-logging-api-datamodel-ref>`
     - References relevant to this file

.. _sec-bundledplugins-logging-api-datamodel-ref:

References
~~~~~~~~~~

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
     - The resource that represents the file (e.g. for deleting)
   * - ``download``
     - 1
     - URL
     - The download URL for the file

.. _sec-bundledplugins-logging-jsclientlib:

JS Client Library
-----------------

:mod:`OctoPrintClient.plugins.logging`
--------------------------------------

.. note::

   All methods here require that the used API token or the existing browser session
   has admin rights.

.. js:function:: OctoPrintClient.plugins.logging.listLogs(opts)

   Retrieves a list of log files.

   See :ref:`Retrieve a list of available log files <sec-bundledplugins-logging-api-list_logs>` for details.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.plugins.logging.deleteLog(path, opts)

   Deletes the specified log ``path``.

   See :ref:`Delete a specific log file <sec-bundledplugins-logging-api-delete_logs>` for details.

   :param string path: The path to the log file to delete
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.plugins.logging.downloadLog(path, opts)

   Downloads the specified log ``file``.

   See :js:func:`OctoPrint.download` for more details on the underlying library download mechanism.

   :param string path: The path to the log file to download
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. _sec-bundledplugins-logging-sourcecode:

Source Code
-----------

The source of the Logging plugin is bundled with OctoPrint and can be found in its source repository under ``src/octoprint/plugins/logging``.
