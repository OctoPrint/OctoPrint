.. _sec-api-connection:

*******************
Connection handling
*******************

.. _sec-api-connection-current:

Get connection settings
=======================

.. md-tab-set::

   .. md-tab-item:: API version 1.12.0+

      .. http:get:: /api/connection

         Retrieve the current connection settings, including information regarding the connectors plugins
         their parameter options and the current connection state.
 
         Requires the ``STATUS`` permission.
 
         **Example**
 
         .. sourcecode:: http
 
             GET /api/connection HTTP/1.1
             Host: example.com
             Authorization: Bearer abcdef...
             X-OctoPrint-Api-Version: 1.12.0
 
         .. sourcecode:: http
 
             HTTP/1.1 200 OK
             Content-Type: application/json
 
             {
               "current": {
                 "state": "Operational",
                 "connector": "serial",
                 "parameters": {
                   "port": "/dev/ttyACM0",
                   "baudrate": 115200,
                 },
                 "capabilities": {
                   "job_on_hold": true,
                   "temperature_offsets": true
                 },
                 "profile": "_default"
               },
               "options": {
                 "connectors": [
                   {
                     "connector": "serial",
                     "name": "Serial Connection",
                     "parameters": {
                       "port": [
                         "VIRTUAL",
                         "/dev/ttyACM0",
                         ...
                       ],
                       "baudrate": [
                         115200,
                         250000,
                         ...
                       ]
                     }
                   },
                   {
                     "connector": "moonraker",
                     "name": "Klipper (Moonraker)",
                     "parameters": {}
                   },
                   {
                     "connector": "bambu",
                     "name": "Bambu (local)",
                     "parameters": {}
                   }
                 ],
                 "profiles": [
                   {
                     "id": "_default",
                     "name": "Default Profile"
                   }
                 ],
                 "preferredConnector": {
                   "connector": "serial",
                   "parameters": {
                     "port": "/dev/ttyACM0",
                     "baudrate": 115200
                   }
                 },
                 "preferredProfile": "_default"
               }
             }
 
         :statuscode 200: No error

   .. md-tab-item:: API version pre 1.12.0

      .. http:get:: /api/connection

         Retrieve the current connection settings, including information regarding the available baudrates and
         serial ports and the current connection state.
 
         Requires the ``STATUS`` permission.
 
         .. note::
 
            This version of the API doesn't yet support other connectors than the serial connector. If you want to
            support OctoPrint's printer connector model as available from 1.12.0 onward, you need to :ref:`version <sec-api-general-versioning>`
            your API requests accordingly to access the 1.12.0+ version of this API!
 
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
                 "baudrate": 250000,
                 "printerProfile": "_default"
               },
               "options": {
                 "ports": ["/dev/ttyACM0", "VIRTUAL"],
                 "baudrates": [250000, 230400, 115200, 57600, 38400, 19200, 9600],
                 "printerProfiles": [{"name": "Default", "id": "_default"}],
                 "portPreference": "/dev/ttyACM0",
                 "baudratePreference": 250000,
                 "printerProfilePreference": "_default",
                 "autoconnect": true
               }
             }
 
         :statuscode 200: No error

.. _sec-api-connection-command:

Issue a connection command
==========================

.. md-tab-set::

   .. md-tab-item:: API version 1.12.0+

      .. http:post:: /api/connection

         Issue a connection command. Currently available commands are:
 
         connect
           Instructs OctoPrint to connect or, if already connected, reconnect to the printer. Additional parameters are:
 
           * ``connector``: The connector to use for connecting to the printer.
           * ``parameters``: The connection parameters to use for connecting to the printer. Which specific
             parameters should be provided here depends on the selected connector!
           * ``printerProfile`` Optional, specific printer profile to use for connection. If not set the current default printer
             profile will be used.
           * ``save``: Optional, whether to save the request's ``connector`` and ``parameters`` as new preferences. Defaults
             to ``false`` if not set.
           * ``autoconnect``: Optional, whether to automatically connect to the printer on OctoPrint's startup in the future.
             If not set no changes will be made to the current configuration.
 
         disconnect
           Instructs OctoPrint to disconnect from the printer.
 
         repair
           Attempts to repair the connection if it gets stuck. Availability and functionality depends on the currently
           active connector.
 
           .. note::
              
              This used to be called ``fake_ack``. This is also still supported.
 
         Requires the ``CONNECTION`` permission.
 
         **Example Connect Request**
 
         .. sourcecode:: http
 
             POST /api/connection HTTP/1.1
             Host: example.com
             Content-Type: application/json
             Authorization: Bearer abcdef...
             X-OctoPrint-Api-Version: 1.12.0
 
             {
               "command": "connect",
               "connector": "serial",
               "parameters": {
                 "port": "/dev/ttyACM0",
                 "baudrate": 115200
               },
               "printerProfile": "my_printer_profile",
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
             Authorization: Bearer abcdef...
             X-OctoPrint-Api-Version: 1.12.0
 
             {
               "command": "disconnect"
             }
 
         .. sourcecode:: http
 
             HTTP/1.1 204 No Content
 
         **Example Repair Request**
 
         .. sourcecode:: http
 
             POST /api/connection HTTP/1.1
             Host: example.com
             Content-Type: application/json
             Authorization: Bearer abcdef...
             X-OctoPrint-Api-Version: 1.12.0
 
             {
               "command": "repair"
             }
 
         .. sourcecode:: http
 
             HTTP/1.1 204 No Content
 
         :json string command:      The command to issue, either ``connect``, ``disconnect`` or ``repair``.
         :json string connector:    ``connect`` command: The connector to use for connecting to the printer.
         :json object parameters:   ``connect`` command: The connection parameters to use for connecting to the printer.
         :json string printerProfile: ``connect`` command: The id of the printer profile to use for the connection. If left out the current
                                       default printer profile will be used. Must be part of the available printer profiles.
         :json boolean save:        ``connect`` command: Whether to save the supplied connection settings as the new preference.
                                     Defaults to ``false`` if not set.
         :json boolean autoconnect: ``connect`` command: Whether to attempt to automatically connect to the printer on server
                                     startup. If not set no changes will be made to the current setting.
         :statuscode 204:           No error
         :statuscode 400:           If the selected `port` or `baudrate` for a ``connect`` command are not part of the available
                                     options.
         :statuscode 412:           It was not possible to connect to the printer due to unmet preconditions (e.g. port unavailable, host unavailable, ...)

   .. md-tab-item:: API version pre 1.12.0

      .. http:post:: /api/connection

         Issue a connection command. Currently available commands are:

         connect
           Instructs OctoPrint to connect or, if already connected, reconnect to the printer. Additional parameters are:

           * ``port``: Optional, specific port to connect to. If not set the current ``portPreference`` will be used, or if
             no preference is available auto detection will be attempted.
           * ``baudrate``: Optional, specific baudrate to connect with. If not set the current ``baudratePreference`` will
             be used, or if no preference is available auto detection will be attempted.
           * ``printerProfile`` Optional, specific printer profile to use for connection. If not set the current default printer
             profile will be used.
           * ``save``: Optional, whether to save the request's ``port`` and ``baudrate`` settings as new preferences. Defaults
             to ``false`` if not set.
           * ``autoconnect``: Optional, whether to automatically connect to the printer on OctoPrint's startup in the future.
             If not set no changes will be made to the current configuration.

         disconnect
           Instructs OctoPrint to disconnect from the printer.

         fake_ack
           Fakes an acknowledgment message for OctoPrint in case one got lost on the serial line and the communication
           with the printer since stalled. This should only be used in "emergencies" (e.g. to save prints), the reason
           for the lost acknowledgment should always be properly investigated and removed instead of depending on this
           "symptom solver".

         Requires the ``CONNECTION`` permission.

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
               "printerProfile": "my_printer_profile",
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

         **Example FakeAck Request**

         .. sourcecode:: http

             POST /api/connection HTTP/1.1
             Host: example.com
             Content-Type: application/json
             X-Api-Key: abcdef...

             {
               "command": "fake_ack"
             }

         .. sourcecode:: http

             HTTP/1.1 204 No Content
             
         :json string command:      The command to issue, either ``connect``, ``disconnect`` or ``fake_ack``.
         :json string port:         ``connect`` command: The port to connect to. If left out either the existing ``portPreference``
                                     will be used, or if that is not available OctoPrint will attempt auto detection. Must be part
                                     of the available ports.
         :json number baudrate:     ``connect`` command: The baudrate to connect with. If left out either the existing
                                     ``baudratePreference`` will be used, or if that is not available OctoPrint will attempt
                                     autodetection. Must be part of the available baudrates.
         :json string printerProfile: ``connect`` command: The id of the printer profile to use for the connection. If left out the current
                                       default printer profile will be used. Must be part of the available printer profiles.
         :json boolean save:        ``connect`` command: Whether to save the supplied connection settings as the new preference.
                                     Defaults to ``false`` if not set.
         :json boolean autoconnect: ``connect`` command: Whether to attempt to automatically connect to the printer on server
                                     startup. If not set no changes will be made to the current setting.
         :statuscode 204:           No error
         :statuscode 400:           If the selected `port` or `baudrate` for a ``connect`` command are not part of the available
                                     options.
