.. _sec-api-logs:

*******************
Log file management
*******************

.. note::

   All log file management operations require admin rights.

.. contents::

.. _sec-api-logs-list:

Retrieve a list of available log files
======================================

.. http:get:: /api/logs

   Retrieve information regarding all log files currently available and regarding the disk space still available
   in the system on the location the log files are being stored.

   Returns a :ref:`Logfile Retrieve response <sec-api-logs-datamodel-retrieveresponse>`.

   **Example**

   .. sourcecode:: http

      GET /api/logs HTTP/1.1
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
              "resource": "http://example.com/api/logs/octoprint.log",
              "download": "http://example.com/downloads/logs/octoprint.log"
            }
          },
          {
            "date" : 1392628936,
            "name" : "octoprint.log.2014-02-17",
            "size" : 13205,
            "refs": {
              "resource": "http://example.com/api/logs/octoprint.log.2014-02-17",
              "download": "http://example.com/downloads/logs/octoprint.log.2014-02-17"
            }
          },
          {
            "date" : 1393158814,
            "name" : "serial.log",
            "size" : 1798419,
            "refs": {
              "resource": "http://example.com/api/logs/serial.log",
              "download": "http://example.com/downloads/logs/serial.log"
            }
          }
        ],
        "free": 12237201408
      }

   :statuscode 200: No error
   :statuscode 403: If the given API token did not have admin rights associated with it

.. _sec-api-logs-delete:

Delete a specific logfile
=========================

.. http:delete:: /api/logs/(path:filename)

   Delete the selected log file with name `filename`.

   Returns a :http:statuscode:`204` after successful deletion.

   **Example Request**

   .. sourcecode:: http

      DELETE /api/logs/octoprint.log.2014-02-17 HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   :param filename: The filename of the log file to delete
   :statuscode 204: No error
   :statuscode 403: If the given API token did not have admin rights associated with it
   :statuscode 404: If the file was not found

.. _sec-api-logs-datamodel:

Data model
==========

.. _sec-api-logs-datamodel-retrieveresponse:

Logfile Retrieve Response
-------------------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``files``
     - 0..*
     - Array of :ref:`File information items <sec-api-logs-datamodel-fileinfo>`
     - The list of requested files. Might be an empty list if no files are available
   * - ``free``
     - 1
     - String
     - The amount of disk space in bytes available in the local disk space (refers to OctoPrint's ``logs`` folder).

.. _sec-api-logs-datamodel-fileinfo:

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
     - 1
     - Number
     - The size of the file in bytes.
   * - ``date``
     - 1
     - Unix timestamp
     - The timestamp when this file was last modified.
   * - ``refs``
     - 1
     - :ref:`sec-api-logs-datamodel-ref`
     - References relevant to this file

.. _sec-api-logs-datamodel-ref:

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
     - The resource that represents the file (e.g. for deleting)
   * - ``download``
     - 1
     - URL
     - The download URL for the file
