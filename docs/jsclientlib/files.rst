.. sec-jsclientlib-files:

:mod:`OctoPrint.files`
----------------------

.. js:function:: OctoPrint.files.get(location, filename, opts)

   Retrieves information about the file ``filename`` at ``location``.

   See :ref:`Retrieve a specific file's information <sec-api-fileops-retrievefileinfo>` for more details.

   :param string location: The location of the file
   :param string filename: The name of the file
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.files.list(recursively, opts)

   Retrieves a list of all files from the server.

   The response from the server will be preprocessed such that all contained entries (recursively)
   will be guaranteed to have a ``parent``, ``size`` and ``date`` property set at least with a value
   of ``undefined``.

   For folders, all children will have their ``parent`` property set to the folder entry.

   **Example:**

   .. code-block:: javascript

      var recursivelyPrintNames = function(entry, depth) {
          depth = depth || 0;

          var isFolder = entry.type == "folder";
          var name = (isFolder ? "+ " + entry.name : entry.name);
          console.log(_.repeat("| ", depth - 1) + (depth ? "|-" : "") + name);

          if (isFolder) {
              _.each(entry.children, function(child) {
                  recursivelyPrintNames(child, depth + 1);
              });
          }
      };

      OctoPrint.files.list(true)
          .done(function(response) {
              console.log("### Files:");
              _.each(response.files, function(entry) {
                  recursivelyPrintNames(entry);
              });
          });

   See :ref:`Retrieve all files <sec-api-fileops-retrieveall>` for more details.

   :param boolean recursively: Whether to list the files recursively (including all sub folders, true) or not (false, default)
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.files.listForLocation(location, recursively, opts)

   Retrieves a list of all files stored at the specified ``location`` from the server.

   The response from the server will be preprocessed such that all contained entries (recursively)
   will be guaranteed to have a ``parent``, ``size`` and ``date`` property set at least with a value
   of ``undefined``.

   For folders, all children will have their ``parent`` property set to the folder entry.

   See :ref:`Retrieve files from specific location <sec-api-fileops-retrievelocation>` for more details.

   :param string location: The location for which to retrieve the list
   :param boolean recursively: Whether to list the files recursively (including all sub folders, true) or not (false, default)
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.files.select(location, path, print, opts)

   Selects a file at ``location`` named ``filename`` for printing. If ``print`` is supplied and
   truthy, also starts printing the file immediately.

   See the ``select`` command in :ref:`Issue a file command <sec-api-fileops-filecommand>` for more details.

   :param string location: The location of the file to select
   :param string path: The name of the file to select
   :param boolean print: Whether to print the file after selection (true) or not (false, default)
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.files.slice(location, path, parameters, opts)

   Slices a file at ``location`` called ``filename``, using the supplied slice command ``parameters``.

   See the ``slice`` command in :ref:`Issue a file command <sec-api-fileops-filecommand>` for more details.

   :param string location: The location of the file to slice
   :param string path: The path of the file to slice
   :param object parameters: Additional parameters for the ``slice`` command
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.files.delete(location, path, opts)

   Deletes the file or folder at ``location`` and ``path``.

   See :ref:`Delete file <sec-api-fileops-delete>` for more details.

   :param string location: The location of the file to delete
   :param string path: The path of the file to delete
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.files.copy(location, path, destination, opts)

   Copies file or folder ``path`` on ``location`` to new parent folder ``destination`` on ``location``.

   ``destination`` must already exist.

   **Example:**

   .. code-block:: javascript

      OctoPrint.files.copy("local", "some/file.gco", "other/folder");

   See :ref:`Issue a file command <sec-api-fileops-filecommand>` for more details.

   :param string location: The location of the file to copy, currently only "local" is supported
   :param string path: The path of the file or folder to copy
   :param string destination: The path of the parent to which to copy the file or folder
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.files.move(location, filename, destination, opts)

   Moves file or folder ``path`` on ``location`` to new parent folder ``destination`` on ``location``.

   ``destination`` must already exist.

   **Example:**

   .. code-block:: javascript

      OctoPrint.files.move("local", "some/file.gco", "other/folder");

   See :ref:`Issue a file command <sec-api-fileops-filecommand>` for more details.

   :param string location: The location of the file to move, currently only "local" is supported
   :param string path: The path of the file or folder to move
   :param string destination: The path of the parent to which to copy the file or folder
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.files.createFolder(location, name, path, opts)

   Creates a new folder ``name`` on ``location``. If ``path`` is provided and not empty the folder
   will be created as a new child of it.

   **Example:**

   .. code-block:: javascript

      // creates new folder "folder" in the root of "local"
      OctoPrint.files.createFolder("local", "folder");

      // creates new folder "subfolder" in parent "some/existing/folder" on "local"
      OctoPrint.files.createFolder("local", "subfolder", "some/existing/folder");

   See :ref:`Upload file or create folder <sec-api-fileops-uploadfile>` for more details on the folder creation API.

   :param string location: The location to create the folder on (currently only "local" is supported)
   :param string name: The name of the new folder
   :param string path: The path to the parent folder in which to create the new folder. May be left unset in which
                       case the folder will be created in the root directory of ``location``.
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.files.upload(location, file, data)

   Uploads a ``file`` to the specified ``location``.

   Additional command ``data`` may be provided. Supported properties are:

   filename
       A string value, the filename to assign to the uploaded file. Optional, if not provided the filename
       will be taken from the provided ``file`` object's ``name`` property.
   select
       A boolean value, specifies whether to immediately select the uploaded file for printing once
       the upload completes (true) or not (false, default)
   print
       A boolean value, specifies whether to immediately start printing the file after the upload
       completes (true) or not (false, default)
   userdata
       An optional object or a serialized JSON string of additional user supplised data to associate with
       the uploaded file.

   See :ref:`Upload file or create folder <sec-api-fileops-uploadfile>` for more details on the file upload API and
   :js:func:`OctoPrint.upload` for more details on the underlying library upload mechanism, including
   what values are accepted for the ``file`` parameter.

   :param string location: The location to upload the file to
   :param object or string file: The file to upload, see :js:func:`OctoPrint.upload` for more details
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response

.. js:function:: OctoPrint.files.download(location, path, opts)

   Downloads the file at ``path`` in ``location``.

   The downloaded file will be returned as response body in the completed `Promise <http://api.jquery.com/Types/#Promise>`_.
   Note that not all locations support downloading of files (``sdcard`` for example doesn't).

   **Example:**

   .. code-block:: javascript

      OctoPrint.files.download("local", "somefile.gco")
          .done(function(response) {
              var contents = response;
              // do something with the file contents
          });

   :param string location: The location of the file to download
   :param string path: The path of the file to download
   :param object opts: Additional options for the request
   :returns Promise: A `jQuery Promise <http://api.jquery.com/Types/#Promise>`_ for the request's response
