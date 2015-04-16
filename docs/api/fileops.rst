.. _sec-api-fileops:

***************
File operations
***************

.. contents::

.. _sec-api-fileops-retrieveall:

Retrieve all files
==================

.. http:get:: /api/files

   Retrieve information regarding all files currently available and regarding the disk space still available
   locally in the system.

   Returns a :ref:`Retrieve response <sec-api-fileops-datamodel-retrieveresponse>`.

   **Example**:

   .. sourcecode:: http

      GET /api/files HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "files": [
          {
            "name": "whistle_v2.gcode",
            "size": 1468987,
            "date": 1378847754,
            "origin": "local",
            "refs": {
              "resource": "http://example.com/api/files/local/whistle_v2.gcode",
              "download": "http://example.com/downloads/files/local/whistle_v2.gcode"
            },
            "gcodeAnalysis": {
              "estimatedPrintTime": 1188,
              "filament": {
                "length": 810,
                "volume": 5.36
              }
            },
            "print": {
              "failure": 4,
              "success": 23,
              "last": {
                "date": 1387144346,
                "success": true
              }
            }
          },
          {
            "name": "whistle_.gco",
            "origin": "sdcard",
            "refs": {
              "resource": "http://example.com/api/files/sdcard/whistle_.gco"
            }
          }
        ],
        "free": "3.2GB"
      }

   :statuscode 200: No error

.. _sec-api-fileops-retrievelocation:

Retrieve files from specific location
=====================================

.. http:get:: /api/files/(string:location)

   Retrieve information regarding the files currently available on the selected `location` and -- if targeting
   the ``local`` location -- regarding the disk space still available locally in the system.

   Returns a :ref:`Retrieve response <sec-api-fileops-datamodel-retrieveresponse>`.

   **Example**:

   .. sourcecode:: http

      GET /api/files/local HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "files": [
          {
            "name": "whistle_v2.gcode",
            "size": 1468987,
            "date": 1378847754,
            "origin": "local",
            "refs": {
              "resource": "http://example.com/api/files/local/whistle_v2.gcode",
              "download": "http://example.com/downloads/files/local/whistle_v2.gcode"
            },
            "gcodeAnalysis": {
              "estimatedPrintTime": 1188,
              "filament": {
                "length": 810,
                "volume": 5.36
              }
            },
            "print": {
              "failure": 4,
              "success": 23,
              "last": {
                "date": 1387144346,
                "success": true
              }
            }
          }
        ],
        "free": "3.2GB"
      }

   :param location: The origin location from which to retrieve the files. Currently only ``local`` and ``sdcard`` are
                    supported, with ``local`` referring to files stored in OctoPrint's ``uploads`` folder and ``sdcard``
                    referring to files stored on the printer's SD card (if available).
   :statuscode 200: No error
   :statuscode 404: If `location` is neither ``local`` nor ``sdcard``

.. _sec-api-fileops-uploadfile:

Upload file
===========

.. http:post:: /api/files/(string:location)

   Upload a file to the selected `location`.

   Other than most of the other requests on OctoPrint's API which are expected as JSON, this request is expected as
   ``Content-Type: multipart/form-data`` due to the included file upload.

   Returns a :http:statuscode:`201` response with a ``Location`` header set to the management URL of the uploaded
   file and an :ref:`Upload Response <sec-api-fileops-datamodel-uploadresponse>` as the body upon successful completion.

   **Example**

   .. sourcecode:: http

      POST /api/files/sdcard HTTP/1.1
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

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json
      Location: http://example.com/api/files/sdcard/whistle_.gcode

      {
        "files": {
          "local": {
            "name": "whistle_v2.gcode",
            "origin": "local",
            "refs": {
              "resource": "http://example.com/api/files/local/whistle_v2.gcode",
              "download": "http://example.com/downloads/files/local/whistle_v2.gcode"
            }
          },
          "sdcard": {
            "name": "whistle_.gco",
            "origin": "sdcard",
            "refs": {
              "resource": "http://example.com/api/files/sdcard/whistle_.gco"
            }
          }
        },
        "done": true
      }

   :param location: The target location to which to upload the file. Currently only ``local`` and ``sdcard`` are supported
                    here, with ``local`` referring to OctoPrint's ``uploads`` folder and ``sdcard`` referring to
                    the printer's SD card. If an upload targets the SD card, it will also be stored locally first.
   :form file:      The file to upload, including a valid ``filename``.
   :form select:    Whether to select the file directly after upload (``true``) or not (``false``). Optional, defaults
                    to ``false``.
   :form print:     Whether to start printing the file directly after upload (``true``) or not (``false``). If set, `select`
                    is implicitely ``true`` as well. Optional, defaults to ``false``.
   :form userdata:  [Optional] An optional string that if specified will be interpreted as JSON and then saved along
                    with the file as metadata (metadata key ``userdata``)
   :statuscode 201: No error
   :statuscode 400: If no `file` is included in the request, `userdata` was provided but could not be parsed as JSON
                    or the request is otherwise invalid.
   :statuscode 404: If `location` is neither ``local`` nor ``sdcard`` or trying to upload to SD card and SD card support
                    is disabled
   :statuscode 409: If the upload of the file would override the file that is currently being printed or if an upload
                    to SD card was requested and the printer is either not operational or currently busy with a print job.
   :statuscode 415: If the file is neither a ``gcode`` nor an ``stl`` file (or it is an ``stl`` file but slicing support
                    is disabled)
   :statuscode 500: If the upload failed internally

.. _sec-api-fileops-retrievefileinfo:

Retrieve a specific file's information
======================================

.. http:get:: /api/files/(string:location)/(path:filename)

   Retrieves the selected file's information.

   If the file is unknown, a :http:statuscode:`404` is returned.

   On success, a :http:statuscode:`200` is returned, with a :ref:`file information item <sec-api-datamodel-files-file>`
   as the response body.

   **Example**

   .. sourcecode:: http

      GET /api/files/local/whistle_v2.gcode HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "name": "whistle_v2.gcode",
        "size": 1468987,
        "date": 1378847754,
        "origin": "local",
        "refs": {
          "resource": "http://example.com/api/files/local/whistle_v2.gcode",
          "download": "http://example.com/downloads/files/local/whistle_v2.gcode"
        },
        "gcodeAnalysis": {
          "estimatedPrintTime": 1188,
          "filament": {
            "length": 810,
            "volume": 5.36
          }
        },
        "print": {
          "failure": 4,
          "success": 23,
          "last": {
            "date": 1387144346,
            "success": true
          }
        }
      }

   :param location: The location of the file for which to retrieve the information, either ``local`` or ``sdcard``.
   :param filename: The filename of the file for which to retrieve the information
   :statuscode 200: No error
   :statuscode 404: If `target` is neither ``local`` nor ``sdcard``, ``sdcard`` but SD card support is disabled or the
                    requested file was not found

.. _sec-api-fileops-filecommand:

Issue a file command
====================

.. http:post:: /api/files/(string:target)/(path:filename)

   Issue a file command to an existing file. Currently supported commands are:

   select
     Selects a file for printing. Additional parameters are:

     * ``print``: Optional, if set to ``true`` the file will start printing directly after selection. If the printer
       is not operational when this parameter is present and set to ``true``, the request will fail with a response
       of ``409 Conflict``.

   slice
     Slices an STL file into GCODE. Note that this is an asynchronous operation that will take place in the background
     after the response has been sent back to the client. Additional parameters are:

     * ``slicer``: The slicing engine to use, defaults to ``cura`` if not set, which is also the only supported slicer right now.
     * ``gcode``: Name of the GCODE file to generated, in the same location as the STL file. Defaults to the STL file name
       with extension ``.gco`` if not set.
     * ``position``: Position of the object-to-slice's center on the print bed. A dictionary containing both ``x`` and ``y``
       coordinate in mm is expected
     * ``printerProfile``: Name of the printer profile to use, if not set the default printer profile will be used.
     * ``profile``: Name of the slicing profile to use, if not set the default slicing profile of the slicer will be used.
     * ``profile.*``: Override parameters, the ``profile.`` prefix will be stripped and the matching profile key will
       be overridden with the supplied value. Use this if you want to specify things that change often like a different
       temperature, filament diameter or infill percentage. Profile keys are slicer specific.
     * ``select``: Optional, if set to ``true`` the file be selected for printing right after the slicing has finished. If the
       printer is not operational or already printing when this parameter is present and set to ``true``, the request will
       fail with a response of ``409 Conflict``
     * ``print``: Optional, if set to ``true`` the file be selected and start printing right after the slicing has finished.
       If the printer is not operational or already printing when this parameter is present and set to ``true``, the request
       will fail with a response of ``409 Conflict``. Note that if this parameter is set, the parameter ``select`` does not
       need to be set, it is automatically assumed to be ``true`` too, otherwise no printing would be possible.

     If consecutive slicing calls are made targeting the same GCODE filename (that also holds true if the default is used),
     the slicing job already running in the background will be cancelled before the new one is started. Note that this will
     also mean that if it was supposed to be directly selected and start printing after the slicing finished, this will not
     take place anymore and whether this will happen with the new sliced file depends entirely on the new request!

   Upon success, a status code of :http:statuscode:`204` and an empty body is returned, unless specified otherwise.

   **Example Select Request**

   .. sourcecode:: http

      POST /api/files/local/whistle_v2.gcode HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "select",
        "print": true
      }

   .. sourcecode:: http

      HTTP/1.1 204 No Content

   **Example Slice Request**

   .. sourcecode:: http

      POST /api/files/local/some_model.stl HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "slice",
        "slicer": "cura",
        "gcode": "some_model.first_try.gcode",
        "printerProfile": "my_custom_reprap",
        "profile": "high_quality",
        "profile.infill": 75,
        "profile.fill_density": 15,
        "position": {"x": 100, "y": 100},
        "print": true
      }

   .. sourcecode:: http

      HTTP/1.1 202 Accepted
      Content-Type: application/json

      {
        "origin": "local",
        "name": "some_model.first_try.gcode",
        "refs": {
          "download": "http://example.com/downloads/files/local/some_model.first_try.gcode",
          "resource": "http://example.com/api/files/local/some_model.first_try.gcode"
        }
      }


   :param target:               The target location on which to delete the file, either ``local`` (for OctoPrint's ``uploads``
                                folder) or ``sdcard`` for the printer's SD card (if available)
   :param filename:             The filename of the file for which to issue the command
   :json string command:        The command to issue for the file, currently only ``select`` is supported
   :json boolean print:         ``select`` and ``slice`` command: Optional, whether to start printing the file directly after selection
                                or slicing, defaults to ``false``.
   :json string slicer:         ``slice`` command: The slicer to use, defaults to the default slicer.
   :json string gcode:          ``slice`` command: The name of the gcode file to create, defaults to the targeted stl's file name
                                with its extension changed to ``.gco`` (e.g. "test.stl" will be sliced to "test.gco" if not specified
                                otherwise)
   :json string profile:        ``slice`` command: The slicing profile to use, defaults to the selected slicer's default profile.
   :json string profile.*:      ``slice`` command: Overrides for the selected slicing profile, e.g. to specify a different temperature
                                or filament diameter.
   :json string printerProfile: ``slice`` command: The printer profile to use, defaults to the default printer profile.
   :json boolean select:        ``slice`` command: Optional, whether to select the file for printing directly after slicing,
                                defaults to ``false``
   :statuscode 200:             No error for a ``select`` command.
   :statuscode 202:             No error for a ``slice`` command.
   :statuscode 400:             If the ``command`` is unknown or the request is otherwise invalid
   :statuscode 415:             If a ``slice`` command was issued against something other than an STL file.
   :statuscode 404:             If `target` is neither ``local`` nor ``sdcard`` or the requested file was not found
   :statuscode 409:             If a selected file is supposed to start printing directly but the printer is not operational or
                                if a file to be sliced is supposed to be selected or start printing directly but the printer
                                is not operational or already printing.

.. _sec-api-fileops-delete:

Delete file
===========

.. http:delete:: /api/files/(string:target)/(path:filename)

   Delete the selected `filename` on the selected `target`.

   If the file to be deleted is currently being printed, a :http:statuscode:`409` will be returned.

   Returns a :http:statuscode:`204` after successful deletion.

   **Example Request**

   .. sourcecode:: http

      DELETE /api/files/local/whistle_v2.gcode HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   :param target:   The target location on which to delete the file, either ``local`` (for OctoPrint's ``uploads``
                    folder) or ``sdcard`` for the printer's SD card (if available)
   :param filename: The filename of the file to delete
   :statuscode 204: No error
   :statuscode 404: If `target` is neither ``local`` nor ``sdcard`` or the requested file was not found
   :statuscode 409: If the file to be deleted is currently being printed

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
     - Array of :ref:`File information items <sec-api-datamodel-files-file>`
     - The list of requested files. Might be an empty list if no files are available
   * - ``free``
     - 0..1
     - String
     - The amount of disk space in bytes available in the local disk space (refers to OctoPrint's ``uploads`` folder). Only
       returned if file list was requested for origin ``local`` or all origins.

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
     - 1
     - Object
     - Abridged information regarding the file that was just uploaded. If only uploaded to ``local`` this will only
       contain the ``local`` property. If uploaded to SD card, this will contain both ``local`` and ``sdcard`` properties.
   * - ``files.local``
     - 1
     - :ref:`sec-api-datamodel-files-file`
     - The information regarding the file that was just uploaded to the local storage (only the fields ``name``,
       ``origin`` and ``refs`` will be set).
   * - ``files.sdcard``
     - 0..1
     - :ref:`sec-api-datamodel-files-file`
     - The information regarding the file that was just uploaded to the printer's SD card (only the fields ``name``,
       ``origin`` and ``refs`` will be set).
   * - ``done``
     - 1
     - Boolean
     - Whether the file processing after upload has already finished (``true``) or not, e.g. due to first needing
       to perform a slicing step (``false``). Clients may use this information to direct progress displays related to
       the upload.

