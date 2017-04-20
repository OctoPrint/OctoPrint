.. _sec-jsclientlib-connection:

:mod:`OctoPrintClient.connection`
---------------------------------

.. js:function:: OctoPrintClient.connection.getSettings(opts)

   Retrieves the available connection options for connection to a printer.

   See :ref:`Get connection settings <sec-api-connection-current>` for the response format.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.connection.connect(data, opts)

   Connects to the printer, optionally using the provided connection ``data`` as parameters.

   If ``data`` is provided it's expected to be an object specifying one or more of

     * ``port``
     * ``baudrate``
     * ``printerProfile``
     * ``save``
     * ``autoconnect``

   See :ref:`Issue a connection command <sec-api-connection-command>` for more details.

   :param object data: Connection data to use
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.connection.disconnect(opts)

   Disconnects from the printer.

   See :ref:`Issue a connection command <sec-api-connection-command>` for more details.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.connection.fakeAck(opts)

   Triggers a fake acknowledgement (``ok``) on the printer.

   See :ref:`Issue a connection command <sec-api-connection-command>` for more details.

   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response
