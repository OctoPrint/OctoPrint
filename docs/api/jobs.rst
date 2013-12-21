.. _sec-api-jobs:

***********
Job Control
***********

.. contents::

.. _sec-api-jobs-command:

Issue a job command
===================

.. http:post:: /api/control/job

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
