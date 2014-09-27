.. _sec-api-connection:

*******************
Connection handling
*******************

.. contents::

.. _sec-api-connection-current:

Get connection settings
=======================

.. http:get:: /api/connection

   Retrieve the current connection settings, including information regarding the available baudrates and
   serial ports and the current connection state.

   **Example**

   .. sourcecode:: http

      GET /api/connection HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "current": {
          "state": "Operational",
          "port": "/dev/ttyACM0",
          "baudrate": 250000
        },
        "options": {
          "ports": ["/dev/ttyACM0", "VIRTUAL"],
          "baudrates": [250000, 230400, 115200, 57600, 38400, 19200, 9600],
          "portPreference": "/dev/ttyACM0",
          "baudratePreference": 250000,
          "autoconnect": true
        }
      }

   :statuscode 200: No error

.. _sec-api-connection-command:

Issue a connection command
==========================

.. http:post:: /api/connection

   Issue a connection command. Currently available command are:

   connect
     Instructs OctoPrint to connect to the printer. Additional parameters are:

     * ``port``: Optional, specific port to connect to. If not set the current ``portPreference`` will be used, or if
       no preference is available auto detection will be attempted.
     * ``baudrate``: Optional, specific baudrate to connect with. If not set the current ``baudratePreference`` will
       be used, or if no preference is available auto detection will be attempted.
     * ``save``: Optional, whether to save the request's ``port`` and ``baudrate`` settings as new preferences. Defaults
       to ``false`` if not set.
     * ``autoconnect``: Optional, whether to automatically connect to the printer on OctoPrint's startup in the future.
       If not set no changes will be made to the current configuration.

   disconnect
     Instructs OctoPrint to disconnect from the printer.

   **Example Connect Request**

   .. sourcecode:: http

      POST /api/connection HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "connect",
        "port": "/dev/ttyACM0",
        "baudrate": 115200,
        "save": true,
        "autoconnect": true
      }

   .. sourcecode:: http

      HTTP/1.1 204 No Content

   **Example Disconnect Request**

   .. sourcecode:: http

      POST /api/connection HTTP/1.1
      Host: example.com
      Content-Type: application/json
      X-Api-Key: abcdef...

      {
        "command": "disconnect"
      }

   .. sourcecode:: http

      HTTP/1.1 204 No Content

   :json string command:      The command to issue, either ``connect`` or ``disconnect``
   :json string port:         ``connect`` command: The port to connect to. If left out either the existing ``portPreference``
                              will be used, or if that is not available OctoPrint will attempt auto detection. Must be part
                              of the available ports.
   :json number baudrate:     ``connect`` command: The baudrate to connect with. If left out either the existing
                              ``baudratePreference`` will be used, or if that is not available OctoPrint will attempt
                              autodetection. Must be part of the available baudrates.
   :json boolean save:        ``connect`` command: Whether to save the supplied connection settings as the new preference.
                              Defaults to ``false`` if not set.
   :json boolean autoconnect: ``connect`` command: Whether to attempt to automatically connect to the printer on server
                              startup. If not set no changes will be made to the current setting.
   :statuscode 204:           No error
   :statuscode 400:           If the selected `port` or `baudrate` for a ``connect`` command are not part of the available
                              options.