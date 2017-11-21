.. _sec-api-system:

******
System
******

.. note::

   All system operations require admin rights.

.. _sec-api-system-command-list:

List all registered system commands
===================================

.. http:get:: /api/system/commands

   Retrieves all configured system commands.

   A :http:statuscode:`200` with a :ref:`List all response <sec-api-system-commands-listall>`
   will be returned.

   **Example**

   .. sourcecode:: http

      GET /api/system/commands/core HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   .. sourcecode:: http

      HTTP/1.1 200 Ok
      Content-Type: application/json

      {
        "core": [
          {
            "action": "shutdown",
            "name": "Shutdown",
            "command": "sudo shutdown -h now",
            "confirm": "<strong>You are about to shutdown the system.</strong></p><p>This action may disrupt any ongoing print jobs (depending on your printer's controller and general setup that might also apply to prints run directly from your printer's internal storage).",
            "async": true,
            "ignore": true,
            "source": "core",
            "resource": "http://example.com/api/system/commands/core/shutdown"
          },
          {
            "action": "reboot",
            "name": "Reboot",
            "command": "sudo reboot",
            "confirm": "<strong>You are about to reboot the system.</strong></p><p>This action may disrupt any ongoing print jobs (depending on your printer's controller and general setup that might also apply to prints run directly from your printer's internal storage).",
            "async": true,
            "ignore": true,
            "source": "core",
            "resource": "http://example.com/api/system/commands/core/reboot"
          },
          {
            "action": "restart",
            "name": "Restart OctoPrint",
            "command": "sudo service octoprint restart",
            "confirm": "<strong>You are about to restart the OctoPrint server.</strong></p><p>This action may disrupt any ongoing print jobs (depending on your printer's controller and general setup that might also apply to prints run directly from your printer's internal storage).",
            "async": true,
            "ignore": true,
            "source": "core",
            "resource": "http://example.com/api/system/commands/core/restart"
          }
        ],
        "custom": []
      }

   :statuscode 200: No error

.. _sec-api-system-command-listsource:

List all registered system commands for a source
================================================

.. http:get:: /api/system/commands/(string:source)

   Retrieves the configured system commands for the specified source.

   The response will contain a list of :ref:`command definitions <sec-api-system-commands-definiton>`.

   **Example**

   .. sourcecode:: http

      GET /api/system/commands/core HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   .. sourcecode:: http

      HTTP/1.1 200 Ok
      Content-Type: application/json

      [
        {
          "action": "shutdown",
          "name": "Shutdown",
          "command": "sudo shutdown -h now",
          "confirm": "<b>You are about to shutdown the system.</b></p><p> This action may disrupt any ongoing print jobs (depending on your printer's controller and general setup that might also apply to prints run directly from your printer's internal storage).",
          "async": true,
          "ignore": true,
          "source": "core",
          "resource": "http://example.com/api/system/commands/core/shutdown"
        },
        {
          "action": "reboot",
          "name": "Reboot",
          "command": "sudo reboot",
          "confirm": "<b>You are about to reboot the system.</b></p><p> This action may disrupt any ongoing print jobs (depending on your printer's controller and general setup that might also apply to prints run directly from your printer's internal storage).",
          "async": true,
          "ignore": true,
          "source": "core",
          "resource": "http://example.com/api/system/commands/core/reboot"
        },
        {
          "action": "restart",
          "name": "Restart OctoPrint",
          "command": "sudo service octoprint restart",
          "confirm": "<b>You are about to restart the OctoPrint server.</b></p><p> This action may disrupt any ongoing print jobs (depending on your printer's controller and general setup that might also apply to prints run directly from your printer's internal storage).",
          "async": true,
          "ignore": true,
          "source": "core",
          "resource": "http://example.com/api/system/commands/core/restart"
        }
      ]

   :param source: The source for which to list commands, currently either ``core`` or ``custom``
   :statuscode 200: No error
   :statuscode 404: If a ``source`` other than ``core`` or ``custom`` is specified.

.. _sec-api-system-command-execute:

Execute a registered system command
===================================

.. http:post:: /api/system/commands/(string:source)/(string:action)

   Execute the system command ``action`` on defined in ``source``.

   **Example**

   Restart OctoPrint via the core system command ``restart`` (which is available if the server
   restart command is configured).

   .. sourcecode:: http

      POST /api/system/commands/core/restart HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   .. sourcecode:: http

      HTTP/1.1 204 No Content

   :param source: The source for which to list commands, currently either ``core`` or ``custom``
   :param action: The identifier of the command, ``action`` from its definition
   :statuscode 204: No error
   :statuscode 400: If a ``divider`` is supposed to be executed or if the request is malformed otherwise
   :statuscode 404: If the command could not be found for ``source`` and ``action``
   :statuscode 500: If the command didn't define a ``command`` to execute, the command returned a non-zero
                    return code and ``ignore`` was not ``true`` or some other internal server error occurred

.. _sec-api-system-datamodel:

Data model
==========

.. _sec-api-system-commands-listall:

List all response
-----------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``core``
     - 0..n
     - List of :ref:`command definitions <sec-api-system-commands-definiton>`
     - List of all core commands defined.
   * - ``custom``
     - 0..n
     - List of :ref:`command definitions <sec-api-system-commands-definiton>`
     - List of all custom commands defined in ``config.yaml``.

.. _sec-api-system-commands-definiton:

Command definition
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
     - The name of the command to display in the System menu.
   * - ``command``
     - 1
     - string
     - The full command line to execute for the command.
   * - ``action``
     - 1
     - string
     - An identifier to refer to the command programmatically. The special ``action`` string
       ``divider`` signifies a divider in the menu.
   * - ``confirm``
     - 0..1
     - string
     - If present and set, this text will be displayed to the user in a confirmation dialog
       they have to acknowledge in order to really execute the command.
   * - ``async``
     - 0..1
     - bool
     - Whether to execute the command asynchronously or wait for its result before responding
       to the HTTP execution request.
   * - ``ignore``
     - 0..1
     - bool
     - Whether to ignore the return code of the command's execution.
   * - ``source``
     - 1
     - string
     - Source of the command definition, currently either ``core`` (for system actions defined by
       OctoPrint itself) or ``custom`` (for custom system commands defined by the user through ``config.yaml``).
   * - ``resource``
     - 1
     - string
     - The URL of the command to use for executing it.
