.. _sec-api-util:

****
Util
****

.. _sec-api-util-test:

Test paths or URLs
==================

.. http:post:: /api/util/test

   Provides commands to test paths or URLs for correctness.

   Used by OctoPrint to validate paths or URLs that the user needs to enter in the
   settings.

   The following commands are supported at the moment:

   .. _sec-api-util-test-path:

   path
     Tests whether or provided path exists and optionally if it also is either a file
     or a directory and whether OctoPrint's user has read, write and/or execute permissions
     on it. Supported parameters are:

       * ``path``: The file system path to test. Mandatory.
       * ``check_type``: ``file`` or ``dir`` if the path should not only be checked for
         existence but also whether it is of the specified type. Optional.
       * ``check_access``: A list of any of ``r``, ``w`` and ``x``. If present it will also
         be checked if OctoPrint has read, write, execute permissions on the specified path.

     The ``path`` command returns a :http:statuscode:`200` with a :ref:`path test result <sec-api-util-datamodel-pathtestresult>`
     when the test could be performed. The status code of the response does NOT reflect the
     test result!

   .. _sec-api-util-test-url:

   url
     Tests whether a provided url responds. Request method and expected status codes can
     optionally be specified as well. Supported parameters are:

       * ``url``: The url to test. Mandatory.
       * ``method``: The request method to use for the test. Optional, defaults to ``HEAD``.
       * ``timeout``: A timeout for the request, in seconds. If no reply from the tested URL has been
         received within this time frame, the check will be considered a failure. Optional, defaults to 3 seconds.
       * ``status``: The status code(s) or named status range(s) to test for. Can be either a single
         value or a list of either HTTP status codes or any of the following named status ranges:

           * ``informational``: Status codes from 100 to 199
           * ``success``: Status codes from 200 to 299
           * ``redirection``: Status codes from 300 to 399
           * ``client_error``: Status codes from 400 to 499
           * ``server_error``: Status codes from 500 to 599
           * ``normal``: Status codes from 100 to 399
           * ``error``: Status codes from 400 to 599
           * ``any``: Any status code starting from 100

         The test will past the status code check if the status returned by the URL is within any of
         the specified ranges.
       * ``response``: If set to either ``true``, ``json`` or ``bytes``, the response body and the response headers
         from the URL check will be returned as part of the check result as well. ``json`` will attempt
         to parse the response as json and return the parsed result. ``true`` or ``bytes`` will base64 encode the body
         and return that.

     The ``url`` command returns :http:statuscode:`200` with a :ref:`URL test result <sec-api-util-datamodel-urltestresult>`
     when the test could be performed. The status code of the response does NOT reflect the
     test result!

   .. _sec-api-util-test-server:

   server
     Tests whether a provided server identified by host and port can be reached. Protocol can optionally be specified
     as well. Supported parameters are:

       * ``host``: The host to test. IP or host name. Mandatory.
       * ``port``: The port to test. Integer. Mandatory.
       * ``protocol``: The protocol to test with. ``tcp`` or ``udp``. Optional, defaults to ``tcp``.
       * ``timeout``: A timeout for the test, in seconds. If no successful connection to the server could be established
         within this time frame, the check will be considered a failure. Optional, defaults to 3.05 seconds.

     The ``server`` command returns :http:statuscode:`200` with a :ref:`Server test result <sec-api-util-datamodel-servertestresult>`
     when the test could be performed. The status code of the response does NOT reflect the test result!

   Requires admin rights.

   **Example 1**

   Test whether a path exists and is a file readable and executable by OctoPrint.

   .. sourcecode:: http

      POST /api/util/test HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...
      Content-Type: application/json

      {
        "command": "path",
        "path": "/some/path/to/a/file",
        "check_type": "file",
        "check_access": ["r", "x"]
      }

   .. sourcecode:: HTTP

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "path": "/some/path/to/a/file",
        "exists": true,
        "typeok": true,
        "access": true,
        "result": true
      }

   **Example 2**

   Test whether a path exists which doesn't exist.

   .. sourcecode:: http

      POST /api/util/test HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...
      Content-Type: application/json

      {
        "command": "path",
        "path": "/some/path/to/a/missing_file",
        "check_type": "file",
        "check_access": ["r", "x"]
      }

   .. sourcecode:: HTTP

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "path": "/some/path/to/a/missing_file",
        "exists": false,
        "typeok": false,
        "access": false,
        "result": false
      }

   **Example 3**

   Test whether a path exists and is a file which is a directory.

   .. sourcecode:: http

      POST /api/util/test HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...
      Content-Type: application/json

      {
        "command": "path",
        "path": "/some/path/to/a/folder",
        "check_type": "file"
      }

   .. sourcecode:: HTTP

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "path": "/some/path/to/a/folder",
        "exists": true,
        "typeok": false,
        "access": true,
        "result": false
      }

   **Example 4**

   Test whether a URL returns a normal status code for a HEAD request.

   .. sourcecode:: http

      POST /api/util/test HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...
      Content-Type: application/json

      {
        "command": "url",
        "url": "http://example.com/some/url"
      }

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "url": "http://example.com/some/url",
        "status": 200,
        "result": true
      }

   **Example 5**

   Test whether a URL can be called at all via GET request, provide its raw body. Set a timeout of 1s.

   .. sourcecode:: http

      POST /api/util/test HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...
      Content-Type: application/json

      {
        "command": "url",
        "url": "http://example.com/some/url",
        "method": "GET",
        "timeout": 1.0,
        "status": "any",
        "response": true
      }

   .. sourcecode:: HTTP

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "url": "http://example.com/some/url",
        "status": 200,
        "result": true,
        "response": {
          "headers": {
            "content-type": "image/gif"
          },
          "content": "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
        }
      }

   **Example 6**

   Test whether a server is reachable on a given port via TCP.

   .. sourcecode:: http

      POST /api/util/test HTTP/1.1
      Host: example.com
      X-Api-Key: abcdef...
      Content-Type: application/json

      {
        "command": "server",
        "host": "8.8.8.8",
        "port": 53
      }

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "host": "8.8.8.8",
        "port": 53,
        "protocol": "tcp",
        "result": true
      }

   :json command:      The command to execute, currently either ``path`` or ``url``
   :json path:         ``path`` command only: the path to test
   :json check_type:   ``path`` command only: the type of path to test for, either ``file`` or ``dir``
   :json check_access: ``path`` command only: a list of access permissions to check for
   :json url:          ``url`` command only: the URL to test
   :json status:       ``url`` command only: one or more expected status codes
   :json method:       ``url`` command only: the HTTP method to use for the check
   :json timeout:      ``url`` and ``server`` commands only: the timeout for the test request
   :json response:     ``url`` command only: whether to include response data and if so in what form
   :json host:         ``server`` command only: the server to test
   :json port:         ``server`` command only: the port to test
   :json protocol:     ``server`` command only: the protocol to test
   :statuscode 200:    No error occurred

.. _sec-api-util-datamodel:

Data model
==========

.. _sec-api-util-datamodel-pathtestresult:

Path test result
----------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``path``
     - 1
     - string
     - The path that was tested.
   * - ``exists``
     - 1
     - bool
     - ``true`` if the path exists, ``false`` otherwise.
   * - ``typeok``
     - 1
     - bool
     - ``true`` if a type check was not requested or it passed, ``false`` otherwise
   * - ``access``
     - 1
     - bool
     - ``true`` if a permission check was not requested or it passed, ``false`` otherwise
   * - ``result``
     - 1
     - bool
     - ``true`` if the overall check passed, ``false`` otherwise

.. _sec-api-util-datamodel-urltestresult:

URL test result
---------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``url``
     - 1
     - string
     - The URL that was tested.
   * - ``status``
     - 1
     - int
     - The status code returned by the URL, 0 in case of a timeout.
   * - ``result``
     - 1
     - bool
     - ``true`` if the check passed.
   * - ``response``
     - 0..1
     - string or object
     - If ``response`` in the request was set to ``bytes``: The base64 encoded body of the checked URL's response.
       If ``response`` in the request was set to ``json``: The json decoded body of the checked URL's response.
       Not present if ``response`` in the request was not set.
   * - ``headers``
     - 0..1
     - object
     - A dictionary with all headers of the checked URL's response. Only present if ``response`` in the
       request was set.

.. _sec-api-util-datamodel-servertestresult:

Server test result
------------------

.. list-table::
   :widths: 15 5 10 30
   :header-rows: 1

   * - Name
     - Multiplicity
     - Type
     - Description
   * - ``host``
     - 1
     - string
     - The host that was tested.
   * - ``port``
     - 1
     - int
     - The port that was tested
   * - ``protocol``
     - 1
     - string
     - The protocol that was tested, ``tcp`` or ``udp``
   * - ``result``
     - 1
     - bool
     - ``true`` if the check passed.
