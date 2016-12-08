.. _sec-jsclientlib:

#########################
JavaScript Client Library
#########################

The JS Client Library provides an interface to all of OctoPrint's API, including the SockJS based socket to send
push messages from the server to connected clients. It is available as packed web
asset file at ``/static/webassets/packed_client.js`` or as individual
component files at ``/static/js/app/client/<component>.js`` relative to your
OctoPrint instance's base URL (e.g. ``http://octopi.local/static/webassets/packed_client.js``).

If you are using it from a web page hosted on OctoPrint as a Jinja2 template, you should use one of the following
methods to embed it instead of manually entering the URL, in order to have OctoPrint take care of setting the
correct URL prefix:

.. code-block:: html

   <!--
     full client library or all individual files, depending
     on the server mode - should be the preferred variant
   -->
   {% assets "js_client" %}<script type="text/javascript" src="{{ ASSET_URL }}"></script>{% endassets %}

   <!--
     full client library
   -->
   <script type="text/javascript" src="{{ url_for("static", filename="webassets/packed_client.js") }}"></script>

   <!--
     individual components (do not forget base!)
   -->
   <script type="text/javascript" src="{{ url_for("static", filename="js/app/client/<component>.js") }}"></script>

Regardless of which way you use to include the library, you'll also need to make sure you included JQuery and lodash,
because the library depends on those to be available (as ``$`` and ``_``). You can embed those like this:

.. code-block:: html

   <script src="{{ url_for("static", filename="js/lib/jquery/jquery.min.js") }}"></script>
   <script src="{{ url_for("static", filename="js/lib/lodash.min.js") }}"></script>

Note that all components depend on the ``base`` component to be present, so if you are only including a select
number of components, make sure to at the very least include that one to be able to utilize the client.

.. seealso::

   `OctoPrint-ForceLogin <https://github.com/OctoPrint/OctoPrint-ForceLogin>`_
       A plugin that disables anonymous access to the regular OctoPrint UI by implementing a custom UI. Utilizes the
       client library's :ref:`browser component <sec-jsclientlib-browser>` to login the user.

.. toctree::
   :maxdepth: 3

   base.rst
   browser.rst
   connection.rst
   control.rst
   files.rst
   job.rst
   languages.rst
   logs.rst
   printer.rst
   printerprofiles.rst
   settings.rst
   slicing.rst
   socket.rst
   system.rst
   timelapse.rst
   users.rst
   util.rst
   wizard.rst
