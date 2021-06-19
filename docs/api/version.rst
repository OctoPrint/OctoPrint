.. _sec-api-version:

*******************
Version information
*******************

.. http:get:: /api/version

   Retrieve information regarding server and API version. Returns a JSON object with three keys, ``api`` containing
   the API version, ``server`` containing the server version, ``text`` containing the server version including
   the prefix ``OctoPrint`` (to determine that this is indeed a genuine OctoPrint instance).

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
        "server": "1.3.10",
        "text": "OctoPrint 1.3.10"
      }

   :statuscode 200: No error
