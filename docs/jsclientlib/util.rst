.. _sec-jsclientlib-util:

:mod:`OctoPrintClient.util`
---------------------------

.. note::

   All methods here require that the used API token or the existing browser session
   has admin rights.

.. js:function:: OctoPrintClient.util.test(command, parameters, opts)

   Execute a :ref:`test command <sec-api-util-test>`.

   See below for the more specialized versions of this.

   :param string command: The command to execute (currently either ``path`` or ``url``)
   :param object parameters: The parameters for the command
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.util.testPath(path, additional, opts)

   Test the provided ``path`` for existence. More test criteria supported by the :ref:`path test command <sec-api-util-test-path>`
   can be provided via the ``additional`` object.

   **Example 1**

   Test if ``/some/path/to/a/file`` exists.

   .. code-block:: javascript

      OctoPrint.util.testPath("/some/path/to/a/file")
          .done(function(response) {
              if (response.result) {
                  // check passed
              } else {
                  // check failed
              }
          });

   **Example 2**

   Test if ``/some/path/to/a/file`` exists, is a file and OctoPrint has read and executable rights on it.

   .. code-block:: javascript

      OctoPrint.util.testPath("/some/path/to/a/file", {"check_type": "file", "check_access": ["r", "x"]})
          .done(function(response) {
              if (response.result) {
                  // check passed
              } else {
                  // check failed
              }
          });

   :param string path: Path to test
   :param object additional: Additional parameters for the test command
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.util.testExecutable(path, opts)

   Shortcut to test if a provided ``path`` exists and is executable by OctoPrint.

   **Example**

   Test if ``/some/path/to/a/file`` exists and can be executed by OctoPrint.

   .. code-block:: javascript

      OctoPrint.util.testExecutable("/some/path/to/a/file")
          .done(function(response) {
              if (response.result) {
                  // check passed
              } else {
                  // check failed
              }
          });

   This is equivalent to calling :js:func:`OctoPrint.util.testPath` like this:

   .. code-block:: javascript

      OctoPrint.util.testPath("/some/path/to/a/file", {"access": "x"})
          .done(function(response) {
              if (response.result) {
                  // check passed
              } else {
                  // check failed
              }
          });

   :param string path: Path to test
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.util.testUrl(url, additional, opts)

   Test if a URL can be accessed. More test criteria supported by the :ref:`URL test command <sec-api-util-test-url>`
   can be provided via the ``additional`` object.

   **Example 1**

   Test if ``http://octopi.local/online.gif`` can be accessed and returns a non-error status code within the default timeout.

   .. code-block:: javascript

      OctoPrint.util.testUrl("http://octopi.local/online.gif")
          .done(function(response) {
              if (response.result) {
                  // check passed
              } else {
                  // check failed
              }
          });

   **Example 2**

   Test if ``http://octopi.local/webcam/?action=snapshot`` can be accessed and returns a non-error status code. Return the
   raw response data and headers from the check as well.

   .. code-block:: javascript

      OctoPrint.util.testUrl("http://octopi.local/webcam/?action=snapshot", {"response": "bytes", "method": "GET"})
          .done(function(response) {
              if (response.result) {
                  // check passed
                  var content = response.response.content;
                  var mimeType = "image/jpeg";

                  var headers = response.response.headers;
                  if (headers && headers["content-type"]) {
                      mimeType = headers["content-type"].split(";")[0];
                  }

                  var image = $("#someimage");
                  image.src = "data:" + mimeType + ";base64," + content;
              } else {
                  // check failed
              }
          });

   **Example 3**

   Test if a "GET" request against ``http://example.com/idonotexist`` returns either a :http:statuscode:`404` or a :http:statuscode:`400`.

   .. code-block:: javascript

      OctoPrint.util.testUrl("http://example.com/idonotexist", {"status": [400, 404], "method": "GET"})
          .done(function(response) {
              if (response.result) {
                  // check passed
              } else {
                  // check failed
              }
          });

   :param string url: URL to test
   :param object additional: Additional parameters for the test command
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.util.testServer(host, port, additional, opts)

   Test if a server is reachable. More options supported by the :ref:`server test command <sec-api-util-test-server>`
   can be provided via the ``additional`` object.

   **Example 1**

   Test if ``8.8.8.8`` is reachable on port 53 within the default timeout.

   .. code-block:: javascript

      OctoPrint.util.testServer("8.8.8.8", 53)
          .done(function(response) {
              if (response.result) {
                  // check passed
              } else {
                  // check failed
              }
          });

   **Example 2**

   Test if ``127.0.0.1`` is reachable on port 1234 and UDP.

   .. code-block:: javascript

      OctoPrint.util.testServer("127.0.0.1", 1234, {"protocol": "udp"})
          .done(function(response) {
              if (response.result) {
                  // check passed
              } else {
                  // check failed
              }
          });


   :param string url: Host to test
   :param int port: Port to test
   :param object additional: Additional parameters for the test command
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.util.testResolution(name, additional, opts)

   Test if a host name can be resolved.

   **Example**

   Test if ``octoprint.org`` can be resolved.

   .. code-block:: javascript

      OctoPrint.util.testResolution("octoprint.org")
          .done(function(response) {
              if (response.result) {
                  // check passed
              } else {
                  // check failed
              }
          });

   :param string name: Host name to test
   :param object additional: Additional parameters for the test command
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. seealso::

   :ref:`Util API <sec-api-util>`
     Documentation of the underlying util API.
