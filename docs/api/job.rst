.. _sec-api-jobs:

**************
Job operations
**************

.. contents::

.. _sec-api-jobs-command:

Issue a job command
===================

.. http:post:: /api/job

   Job commands allow starting, pausing and cancelling print jobs. Available commands are:

   start
     Starts the print of the currently selected file. For selecting a file, see :ref:`Issue a file command <sec-api-fileops-filecommand>`.
     If a print job is already active, a :http:statuscode:`409` will be returned.

   restart
     Restart the print of the currently selected file from the beginning. There must be an active print job for this to work
     and the print job must currently be paused. If either is not the case, a :http:statuscode:`409` will be returned.

   pause
     Pauses/unpauses the current print job. If no print job is active (either paused or printing), a :http:statuscode:`409`
     will be returned.

   cancel
     Cancels the current print job.  If no print job is active (either paused or printing), a :http:statuscode:`409`
     will be returned.

   Upon success, a status code of :http:statuscode:`204` and an empty body is returned.

   **Example Start Request**

   .. sourcecode:: http

      POST /api/control/job HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "start"
      }

   **Example Restart Request**

   .. sourcecode:: http

      POST /api/control/job HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "restart"
      }

   **Example Pause Request**

   .. sourcecode:: http

      POST /api/control/job HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "pause"
      }

   **Example Cancel Request**

   .. sourcecode:: http

      POST /api/control/job HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "cancel"
      }

   :json string command: The command to issue, either ``start``, ``restart``, ``pause`` or ``cancel``
   :statuscode 204:      No error
   :statuscode 409:      If the printer is not operational or the current print job state does not match the preconditions
                         for the command.

.. _sec-api-job-information:

Retrieve information about the current job
==========================================

.. http:get:: /api/job

   Retrieve information about the current job (if there is one).

   Returns a :http:statuscode:`200` with a :ref:`sec-api-job-datamodel-response` in the body.

   **Example Request**

   .. sourcecode:: http

      GET /api/job HTTP/1.1
      Host: example.com

   **Example Response**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "job": {
          "file": {
            "name": "whistle_v2.gcode",
            "origin": "local",
            "size": 1468987,
            "date": 1378847754
          },
          "estimatedPrintTime": 8811,
          "filament": {
            "length": 810,
            "volume": 5.36
          }
        },
        "progress": {
          "completion": 0.2298468264184775,
          "filepos": 337942,
          "printTime": 276,
          "printTimeLeft": 912
        }
      }

   :statuscode 200: No error

.. _sec-api-job-datamodel:

Datamodel
=========

.. _sec-api-job-datamodel-response:

Job information response
------------------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``job``
     - 1
     - :ref:`sec-api-job-datamodel-job`
     - Information regarding the target of the current print job
   * - ``progress``
     - 1
     - :ref:`sec-api-job-datamodel-progress`
     - Information regarding the progress of the current print job

.. _sec-api-job-datamodel-job:

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
     - Object
     - The file that is the target of the current print job
   * - ``file.name``
     - 1
     - String
     - The file's name
   * - ``file.origin``
     - 1
     - String, either ``local`` or ``sdcard``
     - The file's origin, either ``local`` or ``sdcard``
   * - ``file.size``
     - 0..1
     - Integer
     - The file's size, in bytes. Only available for files stored locally.
   * - ``file.date``
     - 0..1
     - Unix timestamp
     - The file's upload date. Only available for files stored locally.
   * - ``estimatedPrintTime``
     - 0..1
     - Integer
     - The estimated print time for the file, in seconds.
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

.. _sec-api-job-datamodel-progress:

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

