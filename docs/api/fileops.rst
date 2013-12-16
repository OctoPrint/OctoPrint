.. _sec-api-fileops:

***************
File operations
***************

.. toctree::
   :maxdepth: 5

.. _sec-api-fileops-retrieveall:

Retrieve all files
==================

.. http:get:: /api/files

   Retrieve information regarding all files currently available and regarding the disk space still available
   locally in the system.

   Returns a :ref:`Retrieve response <sec-api-fileops-datamodel-retrieveresponse>`.

   **Example request**:

   .. sourcecode:: http

      GET /api/files HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

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
            "origin": "local",
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

   :statuscode 200: No error

.. _sec-api-fileops-retrievetarget:

Retrieve files from specific origin
===================================

.. http:get:: /api/files/(string:origin)

   Retrieve information regarding the files currently available on the selected `origin` and regarding the
   disk space still available locally in the system.

   Returns a :ref:`Retrieve response <sec-api-fileops-datamodel-retrieveresponse>`.

   **Example request**:

   .. sourcecode:: http

      GET /api/files/local HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

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
            "origin": "local",
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

   :param origin: The origin location from which to retrieve the files. Currently only ``local`` and ``sdcard`` are
                  supported, with ``local`` referring to files stored in OctoPrint's ``uploads`` folder and ``sdcard``
                  referring to files stored on the printer's SD card (if available).
   :statuscode 200: No error
   :statuscode 400: If `origin` is neither ``local`` nor ``sdcard`` or the request is otherwise invalid.

.. _sec-api-fileops-uploadfile:

Upload file
===========

.. http:post:: /api/files/(string:target)

   Upload a file to the selected `target`.

   Other than most of the other requests on OctoPrint's API which are expected as JSON, this request is expected as
   ``Content-Type: multipart/form-data`` due to the included file upload.

   Returns an :ref:`Upload Response <sec-api-fileops-datamodel-uploadresponse>` upon successful completion.

   **Example request**

   .. sourcecode:: http

      POST /api/files/local HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...
      Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryDeC2E3iWbTv1PwMC

      ------WebKitFormBoundaryDeC2E3iWbTv1PwMC
      Content-Disposition: form-data; name="file"; filename="whistle_v2.gcode"
      Content-Type: application/octet-stream

      ;Generated with Cura_SteamEngine 13.11.2
      M109 T0 S220.000000
      T0
      ;Sliced at: Wed 11-12-2013 16:53:12
      ;Basic settings: Layer height: 0.2 Walls: 0.8 Fill: 20
      ;Print time: #P_TIME#
      ;Filament used: #F_AMNT#m #F_WGHT#g
      ;Filament cost: #F_COST#
      ;M190 S70 ;Uncomment to add your own bed temperature line
      ;M109 S220 ;Uncomment to add your own temperature line
      G21        ;metric values
      G90        ;absolute positioning
      ...
      ------WebKitFormBoundaryDeC2E3iWbTv1PwMC
      Content-Disposition: form-data; name="select"

      true
      ------WebKitFormBoundaryDeC2E3iWbTv1PwMC
      Content-Disposition: form-data; name="print"

      true
      ------WebKitFormBoundaryDeC2E3iWbTv1PwMC--

   **Example response**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "files": [
          ...
          {
            "name": "whistle_v2.gcode",
            "bytes": 1468987,
            "size": "1.4MB"
            "date": "2013-05-21 23:15",
            "origin": "local"
          },
          ...
        ],
        "done": true,
        "filename": "whistle_v2.gcode"
      }

   :param target: The target location to which to upload the file. Currently only ``local`` and ``sdcard`` are supported
                  here, with ``local`` referring to OctoPrint's ``uploads`` folder and ``sdcard`` referring to
                  the printer's SD card. If an upload targets the SD card, it will also be stored locally first.
   :form file:    The file to upload, including a valid ``filename``.
   :form select:  Whether to select the file directly after upload (``true``) or not (``false``). Optional, defaults
                  to ``false``.
   :form print:   Whether to start printing the file directly after upload (``true``) or not (``false``). If set, `select`
                  is implicitely ``true`` as well. Optional, defaults to ``false``.
   :statuscode 200: No error
   :statuscode 400: If `target` is neither ``local`` nor ``sdcard``, no `file` is included in the request, the file is
                    neither a ``gcode`` nor an ``stl`` file (or it is an ``stl`` file but slicing support is
                    disabled) or the request is otherwise invalid.
   :statuscode 403: If the upload of the file would override the file that is currently being printed
   :statuscode 500: If the upload failed internally

.. _sec-api-fileops-retrievefile:

Retrieve a file's contents
==========================

.. http:get:: /api/files/local/(path:filename)

   Downloads the selected file's contents. Only available for locally stored files, hence no `target` parameter.

   Will actually redirect to serve the download via a static context directly from the filesystem.

   **Example Request**

   .. sourcecode:: http

      GET /api/files/local/whistle_v2.gcode HTTP/1.1
      Host: example.com

   **Example Response**

   .. sourcecode:: http

      HTTP/1.1 302 Found
      Location: /downloads/files/whistle_v2.gcode

   **Redirect Request**

   .. sourcecode:: http

      GET /downloads/files/whistle_v2.gcode HTTP/1.1
      Host: example.com

   **Redirect Response**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/octet-stream

      ;Generated with Cura_SteamEngine 13.11.2
      M109 T0 S220.000000
      T0
      ;Sliced at: Wed 11-12-2013 16:53:12
      ;Basic settings: Layer height: 0.2 Walls: 0.8 Fill: 20
      ;Print time: #P_TIME#
      ;Filament used: #F_AMNT#m #F_WGHT#g
      ;Filament cost: #F_COST#
      ;M190 S70 ;Uncomment to add your own bed temperature line
      ;M109 S220 ;Uncomment to add your own temperature line
      G21        ;metric values
      G90        ;absolute positioning
      ...

   :param filename: The filename of the file for which to retrieve the contents
   :resheader Location: The statically served download location for the file of the format ``/downloads/files/<filename>``
   :statuscode 302: No error, regular redirect to statically served download location

.. _sec-api-fileops-filecommand:

Issue a file command
====================

.. http:post:: /api/files/(string:target)/(path:filename)

   Issue a file command to an existing file. Currently supported commands are:

   load
     Selects a file for printing. Additional parameters are:

     * ``print``: Optional, if set to ``true`` the file will start printing directly after selection.

   **Example Request**

   .. sourcecode:: http

      POST /api/files/local/whistle_v2.gcode HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "load",
        "print": true
      }

   **Example Response**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {}

   :param target:        The target location on which to delete the file, either ``local`` (for OctoPrint's ``uploads``
                         folder) or ``sdcard`` for the printer's SD card (if available)
   :param filename:      The filename of the file for which to issue the command
   :json string command: The command to issue for the file, currently only ``load`` is supported
   :json boolean print:  ``load`` command: Optional, whether to start printing the file directly after selection,
                         defaults to ``false``.
   :statuscode 200:      No error
   :statuscode 400:      If `target` is neither ``local`` nor ``sdcard``, the `command` is unknown or the request is
                         otherwise invalid

.. _sec-api-fileops-delete:

Delete file
===========

.. http:delete:: /api/files/(string:target)/(path:filename)

   Delete the selected `filename` on the selected `target`.

   Returns a :ref:`Retrieve Response <sec-api-fileops-datamodel-retrieveresponse>` corresponding to the updated
   file list after successful deletion.

   **Example Request**

   .. sourcecode:: http

      DELETE /api/files/local/whistle_v2.gcode HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   **Example Response**

   .. sourcecode:: http

      HTTP/1.1 200 Ok
      Content-Type: application/json

      {
        "files": [
          ...
        ],
        "free": "3.2GB"
      }

   :param target:   The target location on which to delete the file, either ``local`` (for OctoPrint's ``uploads``
                    folder) or ``sdcard`` for the printer's SD card (if available)
   :param filename: The filename of the file to delete
       :statuscode 200: No error
       :statuscode 400: If `target` is neither ``local`` nor ``sdcard`` or the request is otherwise invalid
   :statuscode 403: If the file to be deleted is currently being printed

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

.. _sec-api-fileops-datamodel-uploadresponse:

Upload response
---------------

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
     - The list of files available in the system. Might be an empty list if no files are available
   * - ``done``
     - 1
     - Boolean
     - Whether the file is directly available for printing after receiving the response (``true``) or not, e.g. due
       to first needing to be sliced into GCODE (``false``)
   * - ``filename``
     - 1
     - String
     - The name of the file that was just uploaded

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
