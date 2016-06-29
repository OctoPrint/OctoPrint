.. sec-jsclientlib-connection:

:mod:`OctoPrint.connection`
---------------------------

.. js:function:: OctoPrint.connection.getSettings(opts)

   Retrieves the available connection options for connection to a printer.

   See :ref:`Get connection settings <sec-api-connection-current>` for the response format.

.. js:function:: OctoPrint.connection.connect(data, opts)

   Connects to the printer, optionally using the provided connection ``data`` as parameters.

   If ``data`` is provided it's expected to be an object specifying one or more of

     * ``port``
     * ``baudrate``
     * ``printerProfile``
     * ``save``
     * ``autoconnect``

   See :ref:`Issue a connection command <sec-api-connection-command>` for more details.

.. js:function:: OctoPrint.connection.disconnect(opts)

   Disconnects from the printer.

   See :ref:`Issue a connection command <sec-api-connection-command>` for more details.

.. js:function:: OctoPrint.connection.fakeAck(opts)

   Triggers a fake acknowledgement (``ok``) on the printer.

   See :ref:`Issue a connection command <sec-api-connection-command>` for more details.

