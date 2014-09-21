.. _sec-api-version:

*******************
Version information
*******************

.. http:get:: /api/version

   Retrieve information regarding server and API version. Returns a JSON object with two keys, ``api`` containing
   the API version, ``server`` containing the server version.

   **Example Request**

   .. sourcecode:: http

      GET /api/version HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...

   **Example Response**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "api": "0.1",
        "server": "1.1.0"
      }

   :statuscode 200: No error
