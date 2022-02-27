.. _sec-api-server:

******************
Server information
******************

.. http:get:: /api/server

   .. versionadded:: 1.5.0

   Retrieve information regarding server status. Returns a JSON object with two keys, ``version`` containing
   the server version and ``safemode`` containing one of ``settings``, ``incomplete_startup`` or ``flag``
   to indicate the reason the server is running in safe mode, or the boolean value of ``false`` if it's not
   running in safe mode.

   **Example Request**

   .. sourcecode:: http

      GET /api/server HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   **Example Response**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "version": "1.5.0",
        "safemode": "incomplete_startup"
      }

   :statuscode 200: No error
