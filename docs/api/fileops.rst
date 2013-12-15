.. _sec-api-fileops:

***************
File operations
***************

.. _sec-api-fileops-retrieveall:

Retrieve all files
==================

.. http:get:: /api/gcodefiles

   Retrieve information regarding all GCODE files currently available and regarding the disk space still available
   locally in the system.

   Returns a :ref:`Retrieve response <sec-api-fileops-datamodel-retrieveresponse>`.

   **Example request**:

   .. sourcecode:: http

      GET /api/gcodefiles?apikey=abcdef HTTP/1.1
      Host: example.com

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "files": [
          {
            "name": "whistle_v2.gcode",
            "bytes": 1468987,
            "size": "1.4MB"
            "date": "2013-05-21 23:15",
            "origin": "local"
            "gcodeAnalysis": {
              "estimatedPrintTime": "00:31:40",
              "filament": "0.79m"
            },
            "print": {
              "failure": 4,
              "success": 23,
              "last": {
                "date": "2013-11-18 18:00",
                "success": true
              }
            }
          },
          {
            "name": "whistle_.gco",
            "bytes": 0,
            "size": "n/a",
            "date": "n/a",
            "origin": "sdcard"
          }
        ],
        "free": "3.2GB"
      }

   :query apikey: The API key to use for the request, either the global one or a user specific one (see
                  :ref:`Authorization <sec-api-general-authorization>` for more details)
   :statuscode 200: No error
   :statuscode 401: If the API key is missing
   :statuscode 403: If the API key is invalid

.. _sec-api-fileops-retrievetarget:

Retrieve files from specific origin
===================================

.. http:get:: /api/gcodefiles/(string:origin)

   Retrieve information regarding the GCODE files currently available on the selected `origin` and regarding the
   disk space still available locally in the system.

   Returns a :ref:`Retrieve response <sec-api-fileops-datamodel-retrieveresponse>`.

   **Example request**:

   .. sourcecode:: http

      GET /api/gcodefiles/local?apikey=abcdef HTTP/1.1
      Host: example.com

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "files": [
          {
            "name": "whistle_v2.gcode",
            "bytes": 1468987,
            "size": "1.4MB"
            "date": "2013-05-21 23:15",
            "origin": "local"
            "gcodeAnalysis": {
              "estimatedPrintTime": "00:31:40",
              "filament": "0.79m"
            },
            "print": {
              "failure": 4,
              "success": 23,
              "last": {
                "date": "2013-11-18 18:00",
                "success": true
              }
            }
          }
        ],
        "free": "3.2GB"
      }

   :param target: The target location from which to retrieve the files. Currently only ``local`` and ``sdcard`` are
                  supported, with ``local`` referring to files stored in OctoPrint's ``uploads`` folder and ``sdcard``
                  referring to files stored on the printer's SD card (if available).
   :query apikey: The API key to use for the request, either the global one or a user specific one (see
                  :ref:`Authorization <sec-api-general-authorization>` for more details)
   :statuscode 200: No error
   :statuscode 400: If `origin` is neither ``local`` nor ``sdcard``
   :statuscode 401: If the API key is missing
   :statuscode 403: If the API key is invalid

.. _sec-api-fileops-datamodel:

Datamodel
=========

.. _sec-api-fileops-datamodel-retrieveresponse:

Retrieve response
-----------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``files``
     - 0..*
     - Array of :ref:`File information items <sec-api-fileops-datamodel-fileinfo>`
     - The list of requested files. Might be an empty list if no files are available
   * - ``free``
     - 1
     - String
     - The amount of disk space available in the local disk space (refers to OctoPrint's ``uploads`` folder)

.. _sec-api-fileops-datamodel-fileinfo:

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
   * - ``bytes``
     - 1
     - Number
     - The size of the file in bytes. Only available for ``local`` files, always ``0`` for files stored on ``sdcard``.
   * - ``size``
     - 1
     - String
     - The size of the file in a human readable format. Only available for ``local`` files, set to ``n/a`` for files
       stored on ``sdcard``.
   * - ``date``
     - 1
     - String representing a date and time in the format ``YYYY-MM-DD HH:mm``
     - The date and time this files was uploaded. Only available for ``local`` files,
       set to ``n/a`` for files stored on ``sdcard``.
   * - ``origin``
     - 0..1
     - String, either ``local`` or ``sdcard``
     - The origin of the file, ``local`` when stored in OctoPrint's ``uploads`` folder, ``sdcard`` when stored on the
       printer's SD card (if available)
   * - ``gcodeAnalysis``
     - 0..1
     - :ref:`GCODE analysis information <sec-api-fileops-datamodel-gcodeanalysis>`
     - Information from the analysis of the GCODE file, if available.
   * - ``prints``
     - 0..1
     - :ref:`Print information <sec-api-fileops-datamodel-prints>`
     - Information regarding prints of this file, if available.

.. todo::
   Make fields which are not available for ``sdcard`` (``bytes``, ``size``, ``date``) optional and don't include them
   in the output if not available. Clients should be able to decide on their own what to display in such a case.

.. _sec-api-fileops-datamodel-gcodeanalysis:

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
     - 1
     - String representing a duration in the format ``HH:mm:ss``
     - The estimated print time of the file
   * - ``filament``
     - 1
     - String
     - The estimated usage of filament (length in meters and volume in cubic centimeters) in a human readable format.
       Example: ``1.89m / 11.90cm³``


.. _sec-api-fileops-datamodel-prints:

Print information
-----------------

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
     - String representing a date and time in the format ``YYYY-MM-DD HH:mm``
     - Date and time when the file was printed last
   * - ``last.success``
     - 1
     - Boolean
     - Whether the last print on record was a success (``true``) or not (``false``)
