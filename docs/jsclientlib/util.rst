.. sec-jsclientlib-util:

:mod:`OctoPrint.util`
---------------------

.. note::

   All methods here require that the used API token or a the existing browser session
   has admin rights.

.. js:function:: OctoPrint.util.test(command, parameters, opts)

   Execute a :ref:`test command <sec-api-util-test>`.

   See below for the more specialized versions of this.

   :param string command: The command to execute (currently either ``path`` or ``url``)
   :param object parameters: The parameters for the command
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.util.testPath(path, additional, opts)

   Test the provided ``path`` for existance. More test criteria supported by the :ref:`path test command <sec-api-util-test-path>`
   can be provided via the ``additional`` object.

   **Example 1**

   Test if ``/some/path/to/a/file`` exists.

   .. code-block:: javascript

      OctoPrint.util.testPath("/som/path/to/a/file")
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

      OctoPrint.util.testPath("/som/path/to/a/file", {"check_type": "file", "check_access": ["r", "x"]})
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

.. js:function:: OctoPrint.util.testExecutable(path, opts)

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

.. js:function:: OctoPrint.util.testUrl(url, additional, opts)

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
                  var image = $("#someimage");
                  image.
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

.. seealso::

   :ref:`Util API <sec-api-util>`
     Documentation of the underlying util API
