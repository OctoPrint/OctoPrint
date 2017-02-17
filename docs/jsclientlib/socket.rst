.. _sec-jsclientlib-socket:

:mod:`OctoPrintClient.socket`
-----------------------------

.. js:attribute:: OctoPrintClient.socket.options

   The socket client's options.

   ``OctoPrintClient.socket.options.timeouts``
       A list of consecutive timeouts after which to attempt reconnecting to a
       disconnected sockets, in seconds. Defaults to ``[1, 1, 2, 3, 5, 8, 13, 20, 40, 100]``.
       The default setting here makes the client slowly back off after the first couple of very
       fast connection attempts don't succeed, and give up after 10 tries.

   ``OctoPrintClient.socket.options.rateSlidingWindowSize``
       Number of last rate measurements to take into account for timing analysis and
       communication throttling. See :ref:`Communication Throttling <sec-jsclient-socket-throttling>`
       below.

.. js:function:: OctoPrintClient.socket.connect(opts)

   Connects the socket client to OctoPrint's `SockJS <http://sockjs.org/>`_ socket.

   The optional parameter ``opts`` may be used to provide additional configuration options
   to the SockJS constructor. See the `SockJS documentation <https://github.com/sockjs/sockjs-client#sockjs-class>`_ on potential options.

   :param object opts: Additional options for the SockJS constructor.

.. js:function:: OctoPrintClient.socket.reconnect()

   Reconnects the socket client. If the socket is currently connected it will be disconnected first.

.. js:function:: OctoPrintClient.socket.disconnect()

   Disconnects the socket client.

.. js:function:: OctoPrintClient.socket.onMessage(message, handler)

   Registers the ``handler`` for messages of type ``message``.

   To register for all message types, provide ``*`` as the type to register for.

   ``handler`` is expected to be a function accepting one object parameter ``eventObj``, consisting
   of the received message as property ``key`` and the received payload (if any) as property ``data``.

   .. code-block:: javascript

      OctoPrint.socket.onMessage("*", function(message) {
          // do something with the message object
      });

   The socket client will measure how long message processing over all handlers will take and utilize
   that measurement to determine if the :ref:`communication throttling <sec-jsclient-socket-throttling>`
   needs to be adjusted or not.

   Please refer to the :ref:`Push API documentation <sec-api-push>`
   for details on the possible message types and their payloads.

   :param string message: The type of message for which to register
   :param function handler: The handler function

.. js:function:: OctoPrintClient.socket.sendMessage(type, payload)

   Sends a message of type ``type`` with the provided ``payload`` to the server.

   Note that at the time of writing, OctoPrint only supports the ``throttle`` message. See
   also the :ref:`Push API documentation <sec-api-push>`.

   :param string type: Type of message to send
   :param object payload: Payload to send

.. js:function:: OctoPrintClient.socket.onRateTooLow(measured, minimum)

   Called by the socket client when the measured message round trip times have been lower than
   the current lower processing limit over the full sliding window, indicating that messages
   are now processed faster than the current rate and a faster rate might be possible.

   Can be overwritten with custom handler methods. The default implementation will call
   :js:func:`OctoPrint.socket.increaseRate`.

   :param Number measured: Maximal measured message round trip time
   :param Number minimum: Lower round trip time limit for keeping the rate

.. js:function:: OctoPrintClient.socket.onRateTooHigh(measured, maximum)

   Called by the socket client when the last measured round trip time was higher than the
   current upper procesisng limit, indicating that the messages are now processed slower than
   the current rate requires and a slower rate might be necessary.

   Can be overwritten with custom handler methods. The default implementation will call
   :js:func:`OctoPrint.socket.decreaseRate`.

   :param Number measured: Measured message round trip time
   :param Number minimum: Upper round trip time limit for keeping the rate

.. js:function:: OctoPrintClient.socket.increaseRate()

   Instructs the server to increase the message rate by 500ms.

.. js:function:: OctoPrintClient.socket.decreaseRate()

   Instructs the server to decrease the message rate by 500ms.

.. _sec-jsclient-socket-throttling:

Communication Throttling
========================

The socket client supports communication throttling. It will measure how long each incoming message takes
to be processed by all registered handlers. If the processing times in a sliding window are longer than
the current rate limit configured on the socket (default: 500ms between messages), the socket client will
instruct the server to send slower. If the messages are handled faster than half the current rate limit,
the socket client will instruct the server to send faster.
