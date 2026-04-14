.. _sec-api-version:

*******************
Version information
*******************

.. versionchanged:: 2.0.0

   API versioning

   For requested versions of 2.0.0 or higher the ``api`` key on the response has been dropped.

.. md-tab-set::

   .. md-tab-item:: API version 2.0.0+

      .. http:get:: /api/version

         Retrieve information regarding server and API version. 
         
         Returns a JSON object with two keys, ``server`` containing the server version and
         ``text`` containing the server version including the prefix ``OctoPrint`` (to determine that this is indeed a genuine OctoPrint instance).

         **Example**

         .. sourcecode:: http

            GET /api/version HTTP/1.1
            Host: example.com
            Authorization: Bearer abcdef...
            X-OctoPrint-Api-Version: 2.0.0

         .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
              "server": "2.0.0",
              "text": "OctoPrint 2.0.0"
            }

         :statuscode 200: No error

   .. md-tab-item:: API version pre 2.0.0

      .. http:get:: /api/version

         Retrieve information regarding server and API version. 
         
         Returns a JSON object with three keys, ``api`` set to ``0.1``, 
         ``server`` containing the server version, ``text`` containing the server version including the prefix ``OctoPrint`` (to determine that this is indeed 
         a genuine OctoPrint instance).

         **Example**

         .. sourcecode:: http

            GET /api/version HTTP/1.1
            Host: example.com
            X-Api-Key: abcdef...

         .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
              "api": "0.1",
              "server": "2.0.0",
              "text": "OctoPrint 2.0.0"
            }

         :statuscode 200: No error

