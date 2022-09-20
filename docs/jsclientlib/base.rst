.. _sec-jsclientlib-base:

:mod:`OctoPrintClient`
----------------------

.. js:class:: OctoPrintClient([options])

   Instantiates a new instance of the client library. Note that by default there's always an instance registered
   globally called ``OctoPrint``.

   :param object options: An optional object of options to set :js:attr:`OctoPrintClient.options` to.

.. js:attribute:: OctoPrintClient.options

   The client library instance's options. The following keys are currently supported:

   ``baseurl``
       The base URL of the OctoPrint API

   ``apikey``
       The API Key to use for requests against the OctoPrint API. If left unset, you'll
       need to authenticate your session through a login.

   ``locale``
       The locale to set in ``X-Locale`` headers on API requests. Useful for API
       endpoints that might return localized content.

.. js:attribute:: OctoPrintClient.plugins

   Registration of client library components provided by plugins.

   OctoPrint plugins should always register their client classes here using their plugin identifier as key via
   :js:func:`OctoPrintClient.registerPluginComponent`.

   .. note::

      The registration mechanism has changed slightly with OctoPrint 1.3.2 due to an otherwise unsolvable issue with
      allowing multiple clients to exist concurrently and still keeping the existing architecture intact.

      The old mechanism works fine as long as you are only planning to offer your plugin client implementation on the
      default client instance ``OctoPrint``, however if you also want to support additional clients you'll need to
      use the implementation and registration approach as described below.

   **Example:**

   .. code-block:: javascript

      (function (global, factory) {
          if (typeof define === "function" && define.amd) {
              define(["OctoPrintClient"], factory);
          } else {
              factory(window.OctoPrintClient);
          }
      })(window || this, function(OctoPrintClient) {
          var MyPluginClient = function(base) {
              this.base = base;
          };

          MyPluginClient.prototype.someFunction = function() {
              // do something
          };

          // further define API

          OctoPrintClient.registerPluginComponent("myplugin", MyPluginClient);
          return MyPluginClient;
      });

.. js:function:: OctoPrintClient.getBaseUrl()

   Returns the canonical base URL to use for OctoPrint's API. Uses the current value of
   :js:data:`OctoPrint.options.baseurl <OctoPrint.options>`. If that doesn't end in a ``/``,
   a trailing ``/`` will be appended to the URL before the result is returned.

   :returns string: The base url to use to access OctoPrint's API.

.. js:function:: OctoPrintClient.getCookie(name)

   .. versionadded:: 1.8.3

   Returns the value of the cookie with name ``name``. The port based cookie suffix and if
   necessary also the script root based suffix will be automatically applied to the ``name``
   prior to looking up the value.

   :return string: The value of the cookie, if set & accessible, else an empty string.

.. js:function:: OctoPrintClient.getRequestHeaders(method, additional, opts)

   .. versionchanged:: 1.8.3

   Generates a dictionary of HTTP headers to use for API requests against OctoPrint with all
   necessary headers and any additionally provided ones.

   At the moment this entails setting the ``X-Api-Key`` header based on the current value of
   ``OctoPrint.options.apikey``, if set. Otherwise, for non-cross-domain requests targeting
   methods other than ``GET``, ``HEAD`` or ``OPTIONS``, the current CSRF token is read from the
   associated cookie and set as ``X-CSRF-Token``.

   .. note::

      Up until OctoPrint 1.8.3, this method's signature consisted only of the ``additional``
      parameter. It has been changed in a backward compatible way so that calling it with the
      first parameter being the set of additional headers will still work. This mode of operation
      is deprecated however and will be removed in a future version.
      A warning will be logged to the debug console accordingly.

   :param str method: Method of the request for which to set headers
   :param object additional: Additional headers to add to the request, optional.
   :param object opts: Additional opts passed to the request, used to read cross domain setting, optional.
   :returns object: HTTP headers to use for requests.

.. js:function:: OctoPrintClient.ajax(method, url, opts)

   Performs an AJAX request against the OctoPrint API, utilizing `jQuery's own ajax function <http://api.jquery.com/jquery.ajax/>`_.

   The HTTP method to use may be defined through ``opts.method`` or - if that is not provided -- through the
   ``method`` parameter. If neither is available, ``GET`` will be used.

   The URL to perform the request against may be defined through ``opts.url`` or -- if that is not provided --
   through the ``url`` parameter. If neither is available, an empty string will be used (plain base URL). If the
   URL starts with ``http://`` or ``https://`` it will be used directly. Otherwise the return value of :js:func:`OctoPrint.getBaseUrl`
   will be prepended.

   As headers everything returned by :js:func:`OctoPrint.getRequestHeaders` will be used. Additional headers to set
   may be defined by providing them through ``opts.headers``.

   If ``opts.dataType`` is set, it will be used for setting the corresponding option on the jQuery ``ajax`` call, otherwise
   ``json`` will be used.

   Anything provided in the ``opts`` parameter will also be passed on to the jQuery ``ajax`` call.

   :param string method: The HTTP method to use for the request (optional)
   :param string url: The URL to perform the request against (optional)
   :param object opts: Additional options to use for the request, see above for details (optional)
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.ajaxWithData(method, url, data, opts)

   Performs an AJAX request against the OctoPrint API, including the provided ``data`` in the body of the request.

   Utilizes :js:func:`OctoPrint.ajax`, see that for more details.

   :param string method: The HTTP method to use for the request (optional)
   :param string url: The URL to perform the request against (optional)
   :param object data: The data to send in the request body (optional)
   :param object opts: Additional options to use for the request (optional)
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.get(url, opts)

   Performs a ``GET`` request against ``url``.

   **Example:**

   .. code-block:: javascript

      OctoPrint.get("api/version")
          .done(function(response) {
              console.log("API:", response.api, "Server:", response.server);
          });

   :param string url: URL against which to make the request, relative to base url or absolute
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.getWithQuery(url, data, opts)

   Performs a ``GET`` request against ``url`` using the provided ``data`` as URL query.

   **Example:**

   .. code-block:: javascript

      // this should perform a GET of "api/timelapse?unrendered=true"
      OctoPrint.getWithQuery("api/timelapse", {"unrendered": true});

   :param string url: URL against which to make the request, relative to base url or absolute
   :param object data: An object containing the key/value pairs of the query data OR a string representation of the query
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.post(url, data, opts)

   Performs a ``POST`` request against ``url`` using the provided ``data`` as request body.

   **Example:**

   .. code-block:: javascript

      var url = OctoPrint.getBlueprintUrl("myplugin") + "endpoint";
      OctoPrint.post(url, "a whole lot of data", {"contentType": "application/octet-stream"})
          .done(function(response) {
              // do something with the response
          });

   :param string url: URL against which to make the request, relative to base url or absolute
   :param string data: Data to post as request body
   :param object opts: Additional options for the request
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.postJson(url, data, opts)

   Performs a ``POST`` request against ``url`` using the provided ``data`` object as request body
   after serializing it to JSON.

   **Example:**

   .. code-block:: javascript

      var url = OctoPrint.getBlueprintUrl("myplugin") + "endpoint";
      OctoPrint.postJson(url, {"someKey": "someValue"})
          .done(function(response) {
              // do something with the response
          });

   :param string url: URL against which to make the request, relative to base url or absolute
   :param object data: Data to post as request body after serialization to JSON
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.put(url, data, opts)

   Performs ``PUT`` request against ``url`` using the provided ``data`` as request body.

   See :js:func:`OctoPrint.post` for details.

.. js:function:: OctoPrintClient.putJson(url, data, opts)

   Performs ``PUT`` request against ``url`` using the provided ``data`` as request body after
   serializing it to JSON.

   See :js:func:`OctoPrint.postJson` for details.

.. js:function:: OctoPrintClient.patch(url, data, opts)

   Performs ``PATCH`` request against ``url`` using the provided ``data`` as request body.

   See :js:func:`OctoPrint.post` for details.

.. js:function:: OctoPrintClient.patchJson(url, data, opts)

   Performs ``PATCH`` request against ``url`` using the provided ``data`` as request body after
   serializing it to JSON.

   See :js:func:`OctoPrint.postJson` for details.

.. js:function:: OctoPrintClient.delete(url, opts)

   Performs a ``DELETE`` request against ``url``.

   :param string url: URL against which to make the request, relative to base url or absolute
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.download(url, opts)

   Downloads a file from ``url``, returning the response body as data type ``text``.

   Use this if you need to download a file from the server in order to process it further in the client. The
   response body returned on successful completion of the returned `jQuery Promise <http://api.jquery.com/Types/#Promise>`_
   will contain the requested file as raw string/binary.

   :param string url: URL to download
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.upload(url, file, filename, additional)

   Uploads a ``file`` to ``url`` using a ``multipart/form-data`` ``POST`` request.

   ``file`` should be either of

     * a jQuery element pointing at a file input of the page of which the first
       `File instance <https://developer.mozilla.org/en-US/docs/Web/API/File>`_ will be used,
     * a string usable as selector to address a file input of the page of which the first
       `File instance <https://developer.mozilla.org/en-US/docs/Web/API/File>`_ will be used or
     * a `File instance <https://developer.mozilla.org/en-US/docs/Web/API/File>`_

   If ``filename`` is provided, the file upload data will contain its value as file name for the
   upload, otherwise the ``name`` property from the `File instance <https://developer.mozilla.org/en-US/docs/Web/API/File>`_.

   The function will return a `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ which will also be
   notified on the upload progress with an object containing the following properties:

   loaded
       The number of bytes already uploaded
   total
       The total number of bytes to upload

   This can be used to populate progress bars or other types of progress visualization.

   It is important to note that contrary to all the other request methods in this module, ``OctoPrint.upload``
   is implemented using ``XMLHttpRequest`` directly instead of relying on jQuery's ``ajax`` function. It still
   tries to replicate its behaviour on the returned `jQuery Promise <http://api.jquery.com/Types/#Promise>`_
   however, meaning that the ``resolve`` and ``reject`` methods will be called with ``(data, textStatus, request)``
   and ``(request, textStatus, error)`` parameters respectively.

   Additional form elements for the POSTed form can be supplied through the ``additional`` parameters.
   This should be an object of key/value pairs that are set as field name and value on the `FormData <https://developer.mozilla.org/en/docs/Web/API/FormData>`_
   object that will be used in the request.

   **Example:**

   Uploading a file to ``some/path`` on the blueprint of plugin ``myplugin``, from a file input element,
   updating a label with the current upload progress.

   .. code-block:: javascript

      var fileInput = $("#my-file-input");
      var progressOutput = $("#progress-output");

      OctoPrint.upload(OctoPrint.getBlueprintUrl("myplugin") + "some/path",
                       fileInput,
                       "myfilename.dat",
                       {"somekey": "somevalue"})
          .progress(function(data) {
              if (data.total) {
                  var percentage = Math.round(data.loaded * 100 / data.total);
                  if (percentage || percentage == 0) {
                      progressOutput.text(percentage + "%");
                      return;
                  }
              }
              progressOutput.text("");
          })
          .done(function(response, textStatus, request) {
              progressOutput.text("Uploaded!");
          });

   :param string url: URL to which to POST the upload, relative to base url or absolute
   :param object file: The file to object, see description for details
   :param string filename: An optional file name to use for the upload
   :param object additional: An optional object of additional key/value pairs to set on the uploaded form data

.. js:function:: OctoPrintClient.issueCommand(url, command, payload, opts)

   Issues a command against an OctoPrint command API endpoint.

   OctoPrint contains various API endpoints which follow a specific pattern: The payload of the request body is
   a JSON object which contains at least one property ``command`` and depending on the provided command additional
   parameters as further properties for the command. See the :ref:`Issue a file command <sec-api-fileops-filecommand>`
   for an example of an API endpoint following this pattern.

   Using this function sending commands to such API endpoints becomes a trivial task. The function expects
   the ``url`` of the endpoint, the ``command`` to send, and optional ``payload`` and additional ``opts``.

   The function will take care of wrapping the ``command`` and the ``payload`` into one JSON object and
   POSTing that to the endpoint with the correct JSON content type.

   **Example:**

   .. code-block:: javascript

      var url = OctoPrint.getBlueprintUrl("myplugin") + "myendpoint";
      OctoPrint.issueCommand(url, "mycommand", {"someParameter": "someValue",
                                                "someOtherParameter": "someOtherValue"})
          .done(function(response) {
              // do something with the response
          });

   :param string url: The URL to ``POST`` the command to
   :param string command: The command to issue
   :param object payload: Additional payload data for the command
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.getSimpleApiUrl(plugin)

   Returns the proper URL for the endpoint of a :class:`~octoprint.plugin.SimpleApiPlugin`, based on the
   plugin identifier.

   **Example:**

   .. code-block:: javascript

      // prints "api/plugin/myplugin"
      console.log(OctoPrint.getSimpleApiUrl("myplugin")

   :param string plugin: The identifier of the plugin for which to return the URL
   :returns string: The URL to use as endpoint

.. js:function:: OctoPrintClient.simpleApiGet(plugin, opts)

   Performs a ``GET`` request against the endpoint of a :class:`~octoprint.plugin.SimpleApiPlugin` with
   identifier ``plugin``.

   .. code-block:: javascript

      OctoPrint.simpleApiGet("myplugin")
          .done(function(response) {
              // do something with the response
          });

   :param string plugin: The identifier of the plugin
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.simpleApiCommand(plugin, command, payload, opts)

   Performs the API command ``command`` against the endpoint of a :class:`~octoprint.plugin.SimpleApiPlugin` with
   identifier ``plugin``, including the optional ``payload``.

   **Example:**

   .. code-block:: javascript

      OctoPrint.simpleApiCommand("myplugin", "mycommand", {"someParameter": "someValue",
                                                           "otherParameter": "otherValue"})
          .done(function(response) {
              // do something with the response
          });

   :param string plugin: The identifier of the plugin
   :param string command: The command to issue
   :param object payload: Additional payload data for the command
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrintClient.getBlueprintUrl(plugin)

   Returns the proper base URL for blueprint endpoints of a :class:`~octoprint.plugin.BlueprintPlugin` with
   identifier ``plugin``.

   **Example:**

   .. code-block:: javascript

      // prints "plugin/myplugin/"
      console.log(OctoPrint.getBlueprintUrl("myplugin"));

.. js:function:: OctoPrintClient.createRejectedDeferred()

   Static method.

   Shortcut for creating a rejected `jQuery Deferred <http://api.jquery.com/category/deferred-object/>`_.

.. js:function:: OctoPrintClient.createCustomException(name)

   Static method.

   Creates a custom exception class. ``name`` may be either a function in which case it will be used
   as constructor for the new exception class, or a string, in which case a constructor with proper
   ``name``, ``message`` and ``stack`` attributes will be created. The class hierarchy will be properly
   setup to subclass ``Error``.

   **Example:**

   .. code-block:: javascript

      MyCustomException = OctoPrintClient.createCustomException("MyCustomException");
      throw new MyCustomException("Something went horribly wrong!");

.. js:function:: OctoPrintClient.registerPluginComponent(identifier, clientClass)

   Static method.

   Registers the plugin client component ``clientClass`` under the name ``identifier`` on the
   :js:attr:`OctoPrintClient.plugins` registry.

   ``clientClass`` must have a constructor that follows the signature ``ClientClass(base)`` and in which it sets
   the attribute ``base`` on the instance to:

   .. code-block:: javascript

      var MyPluginClient = function(base) {
          this.base = base;
      }

   Each :js:class:`OctoPrintClient` will create its own instance of registered plugin classes and make them available
   under :js:attr:`OctoPrintClient.plugins`. It will inject itself into those instances in order to allow plugin
   clients to access its functionality via ``this.base``:

   .. code-block:: javascript

      MyPluginClient.prototype.doSomething = function(data, opts) {
          return this.base.simpleApiCommand("myplugin", "doSomething", data, opts);
      };

   :param string identifier: The identifier of the plugin for which ``clientClass`` is the client
   :param class clientClass: The client class to register. Constructor must follow the signature ``ClientClass(base)``
       where ``base`` will be assigned to the instance as ``this.base`` and be the :js:class:`OctoPrintClient`
       instance to use for API calls etc via ``this.base``.

.. js:class:: OctoPrintClient.InvalidArgumentError

   Exception to use when functions are called with invalid arguments.
