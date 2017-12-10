.. _sec-api-jobs:

**************
Job operations
**************

Use these operations to query the currently selected file and start/cancel/restart/pause the
actual print job.

.. contents::

.. _sec-api-jobs-command:

Issue a job command
===================

.. http:post:: /api/job

   Job commands allow starting, pausing and cancelling print jobs. Available commands are:

   start
     Starts the print of the currently selected file. For selecting a file, see :ref:`Issue a file command <sec-api-fileops-filecommand>`.
     If a print job is already active, a :http:statuscode:`409` will be returned.

   cancel
     Cancels the current print job.  If no print job is active (either paused or printing), a :http:statuscode:`409`
     will be returned.

   restart
     Restart the print of the currently selected file from the beginning. There must be an active print job for this to work
     and the print job must currently be paused. If either is not the case, a :http:statuscode:`409` will be returned.

     Equivalent to issuing a ``cancel`` command while paused, directly followed by a ``start`` command.

   pause
     Pauses/resumes/toggles the current print job. Accepts one optional additional parameter ``action``
     specifying which action to take. Valid values for this parameter are:

     pause
         Pauses the current job if it's printing, does nothing if it's already paused.
     resume
         Resumes the current job if it's paused, does nothing if it's printing.
     toggle
         Toggles the pause state of the job, pausing it if it's printing and resuming it if it's currently paused.

     In order to stay backwards compatible to earlier iterations of this API, the default
     action to take if no ``action`` parameter is supplied is to toggle the print job status.

     If no print job is active (either paused or printing), a :http:statuscode:`409` will be returned.

     .. note::

        While the approach to implement pause/resume/toggle behaviour through sub commands via the ``action``
        parameter instead of having dedicated ``pause``, ``resume`` and ``toggle`` commands seems clumsy, this path
        was chosen to have the API stay backwards compatible to prior versions which only offered the toggle
        behaviour under the ``pause`` command.

   Upon success, a status code of :http:statuscode:`204` and an empty body is returned.

   Requires user rights.

   **Example Start Request**

   .. sourcecode:: http

      POST /api/job HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "start"
      }

   .. sourcecode:: http

      HTTP/1.1 204 No Content

   **Example Cancel Request**

   .. sourcecode:: http

      POST /api/job HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "cancel"
      }

   .. sourcecode:: http

      HTTP/1.1 204 No Content

   **Example Restart Request**

   .. sourcecode:: http

      POST /api/job HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "restart"
      }

   .. sourcecode:: http

      HTTP/1.1 204 No Content

   **Example Pause Request**

   .. sourcecode:: http

      POST /api/job HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "pause",
        "action": "pause"
      }

   .. sourcecode:: http

      HTTP/1.1 204 No Content

   **Example Resume Request**

   .. sourcecode:: http

      POST /api/job HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "pause",
        "action": "resume"
      }

   .. sourcecode:: http

      HTTP/1.1 204 No Content

   **Example Pause Toggle Request**

   .. sourcecode:: http

      POST /api/job HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "pause",
        "action": "toggle"
      }

   .. sourcecode:: http

      HTTP/1.1 204 No Content

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

   **Example**

   .. sourcecode:: http

      GET /api/job HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

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

Data model
==========

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
     - :ref:`sec-api-datamodel-jobs-job`
     - Information regarding the target of the current print job
   * - ``progress``
     - 1
     - :ref:`sec-api-datamodel-jobs-progress`
     - Information regarding the progress of the current print job

