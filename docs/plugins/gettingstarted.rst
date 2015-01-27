.. _sec-plugins-gettingstarted:

Getting Started
===============

Over the course of this little tutorial we'll build a full fledged, installable OctoPrint plugin that displays "Hello World!"
at various places throughout OctoPrint.

We'll start at the most basic form a plugin can take - just a couple of simple lines of Python code:

.. code-block:: python

   # coding=utf-8
   from __future__ import absolute_import

   __plugin_name__ = "Hello World"
   __plugin_version__ = "1.0"
   __plugin_description__ = "A quick \"Hello World\" example plugin for OctoPrint"

Saving this as ``helloworld.py`` in ``~/.octoprint/plugins`` yields you something resembling these log entries upon server startup::

   2015-01-27 11:14:35,124 - octoprint.server - INFO - Starting OctoPrint 1.2.0-dev-448-gd96e56e (devel branch)
   2015-01-27 11:14:35,124 - octoprint.plugin.core - INFO - Loading plugins from /home/pi/.octoprint/plugins, /home/pi/OctoPrint/src/octoprint/plugins and installed plugin packages...
   2015-01-27 11:14:36,135 - octoprint.plugin.core - INFO - Found 3 plugin(s): Hello World (1.0), CuraEngine (0.1), Discovery (0.1)

OctoPrint found that plugin in the folder and took a look into it. The name and the version it displays in that log
entry it got from the ``__plugin_name__`` and ``__plugin_version__`` lines. It also read the description from
``__plugin_description__`` and stored it in an internal data structure, but we'll just ignore this for now.

Saying hello: How to make the plugin actually do something
----------------------------------------------------------

Apart from being discovered by OctoPrint, our plugin does nothing yet. We want to change that. Let's make it print
"Hello World!" to the log upon server startup. Modify our ``helloworld.py`` like this:

.. code-block:: python

   # coding=utf-8
   from __future__ import absolute_import

   import octoprint.plugin

   class HelloWorldPlugin(octoprint.plugin.StartupPlugin):
       def on_after_startup(self):
           self._logger.info("Hello World!")

   __plugin_name__ = "Hello World"
   __plugin_version__ = "1.0"
   __plugin_description__ = "A quick \"Hello World\" example plugin for OctoPrint"
   __plugin_implementations__ = [HelloWorldPlugin()]

and restart OctoPrint. You now get this output in the log::

   2015-01-27 11:17:10,792 - octoprint.plugins.helloworld - INFO - Hello World!

Neat, isn't it? We added a custom class that subclasses one of OctoPrint's :ref:`plugin mixins <sec-plugins-mixins>`
with :class:`StartupPlugin` and another control property, ``__plugin_implementations__``, that instantiates
our plugin class and tells OctoPrint about it. Taking a look at the documentation of :class:`StartupPlugin` we see that
this mixin offers two methods that get called by OctoPrint during startup of the server, ``on_startup`` and
``on_after_startup``. We decided to add our logging output by overriding ``on_after_startup``, but we could also have
used ``on_startup`` instead, in which case our logging statement would be executed before the server was done starting
up and ready to serve requests.

You'll also note that we are using ``self._logger`` for logging. Where did that one come from? OctoPrint's plugin system
injects :ref:`a couple of useful objects <sec-plugins-infrastructure-injections>` into our plugin implementation classes,
one of those being a fully instantiated `python logger <https://docs.python.org/2/library/logging.html>`_ ready to be
used by your plugin. As you can see in the log output above, that logger uses the namespace ``octoprint.plugins.helloworld``
for our little plugin here, or more generally ``octoprint.plugins.<plugin identifier>``.

Growing up: How to make it distributable
----------------------------------------

If you now want to distribute this plugin to other OctoPrint users (since it is so awesome to be greeted upon server
startup), let's take a look at how you'd go about that now before our plugin gets more complicated.

You basically have two options to distribute your plugin. One would be about the exact same way we are using it now,
as a simple python file following the naming convention ``<plugin identifier>.py`` that your users add to their
``~/.octoprint/plugins`` folder. You already know how that works. But let's say you have more than just a simple plugin
that can be done in one file. Distributing multiple files and getting your users to install them in the right way
so that OctoPrint will be able to actually find and load them is certainly not impossible (see :ref:`the plugin distribution
documentation <sec-plugins-distribution>` if you want to take a closer look at that option), but we want to do it in the
best way possible, meaning we want to make our plugin a fully installable python module that your users will be able to
install directly via Python's standard package manager ``pip`` or alternatively via `OctoPrint's own plugin manager <https://github.com/OctoPrint/OctoPrint-PluginManager>`_.

So let's begin. First checkout the `Plugin Skeleton <https://github.com/OctoPrint/OctoPrint-PluginSkeleton>`_ and rename
the ``octoprint_skeleton`` folder to something better suited to our "Hello World" plugin::

   git clone https://github.com/OctoPrint/OctoPrint-PluginSkeleton.git OctoPrint-HelloWorld
   cd OctoPrint-HelloWorld
   mv octoprint_skeleton octoprint_helloworld

Then edit the configuration in the ``setup.py`` file to mirror our own "Hello World" plugin. The configuration should
look something like this:

.. code-block:: python

   plugin_identifier = "helloworld"
   plugin_name = "OctoPrint-HelloWorld"
   plugin_version = "1.0"
   plugin_description = "A quick \"Hello World\" example plugin for OctoPrint"
   plugin_author = "You"
   plugin_author_email = "you@somewhere.net"
   plugin_url = "https://github.com/you/OctoPrint-HelloWorld"

Now all that's left to do is to move our ``helloworld.py`` into the ``octoprint_helloworld`` folder and renaming it to
``__init__.py``. Make sure to delete the copy under ``~/.octoprint/plugins`` in the process, including the `.pyc` file!

The plugin is now ready to be installed via ``python setup.py install``. However, since we are still
working on our plugin, it makes more sense to use ``python setup.py develop`` for now -- this way the plugin becomes
discoverable by OctoPrint, however we don't have to reinstall it after any changes we will still do::

   $ python setup.py develop
   running develop
   running egg_info
   creating OctoPrint_HelloWorld.egg-info
   [...]
   Finished processing dependencies for OctoPrint-HelloWorld==1.0

Restart OctoPrint. Your plugin should still be properly discovered and the log line should be printed::

   2015-01-27 13:43:34,134 - octoprint.server - INFO - Starting OctoPrint 1.2.0-dev-448-gd96e56e (devel branch)
   2015-01-27 13:43:34,134 - octoprint.plugin.core - INFO - Loading plugins from /home/pi/.octoprint/plugins, /home/pi/OctoPrint/src/octoprint/plugins and installed plugin packages...
   2015-01-27 13:43:34,818 - octoprint.plugin.core - INFO - Found 3 plugin(s): Hello World (1.0), CuraEngine (0.1), Discovery (0.1)
   [...]
   2015-01-27 13:43:38,997 - octoprint.plugins.helloworld - INFO - Hello World!

Looks like it still works!

Something is still a bit ugly though. Take a look into ``__init__.py`` and ``setup.py``. It seems like we have a bunch
of information now defined twice:

.. code-block:: python

   # __init__.py:
   __plugin_name__ = "Hello World"
   __plugin_version__ = "1.0"
   __plugin_description__ = "A quick \"Hello World\" example plugin for OctoPrint"

   # setup.py
   plugin_name = "OctoPrint-HelloWorld"
   plugin_version = "1.0"
   plugin_description = "A quick \"Hello World\" example plugin for OctoPrint"

The nice thing about our plugin now being a proper python package is that OctoPrint can and will access the metadata defined
within ``setup.py``! So, we don't really need to define all this data twice. Remove it:

.. code-block:: python

   # coding=utf-8
   from __future__ import absolute_import

   import octoprint.plugin

   class HelloWorldPlugin(octoprint.plugin.StartupPlugin):
       def on_after_startup(self):
           self._logger.info("Hello World!")

   __plugin_implementations__ = [HelloWorldPlugin()]

and restart OctoPrint::

   2015-01-27 13:46:33,786 - octoprint.plugin.core - INFO - Found 3 plugin(s): OctoPrint-HelloWorld (1.0), CuraEngine (0.1), Discovery (0.1)

Our "Hello World" Plugin still gets detected fine, but it's now listed under the same name it's installed under,
"OctoPrint-HelloWorld". That's a bit ugly, so we'll override that bit via ``__plugin_name__`` again:

.. code-block:: python

   # coding=utf-8
   from __future__ import absolute_import

   import octoprint.plugin

   class HelloWorldPlugin(octoprint.plugin.StartupPlugin):
       def on_after_startup(self):
           self._logger.info("Hello World!")

   __plugin_name__ = "Hello World"
   __plugin_implementations__ = [HelloWorldPlugin()]


Restart OctoPrint again::

   2015-01-27 13:48:54,122 - octoprint.plugin.core - INFO - Found 3 plugin(s): Hello World (1.0), CuraEngine (0.1), Discovery (0.1)

Much better! You can override pretty much all of the metadata defined within ``setup.py`` from within your Plugin itself --
take a look at :ref:`the available control properties <sec-plugins-infrastructure-controlproperties>` for all available
overrides.

Following the README of the `Plugin Skeleton <https://github.com/OctoPrint/OctoPrint-PluginSkeleton>`_ you could now
already publish your plugin on Github and it would be directly installable by others using pip::

   pip install https://github.com/you/OctoPrint-HelloWorld/archive/master.zip

But let's add some more features instead.

Frontend or get out: How to add functionality to OctoPrint's web interface
--------------------------------------------------------------------------

Outputting a log line upon server startup is all nice and well, but we want to greet not only the administrator of
our OctoPrint instance but actually everyone that opens OctoPrint in their browser. Therefore, we need to modify
OctoPrint's web interface itself.

We can do this using the :class:`TemplatePlugin` mixin. For now, let's start with a little "Hello World!" in OctoPrint's
navigation bar right at the top. For this we'll first add the :class:`TemplatePlugin` to our ``HelloWorldPlugin`` class:

.. code-block:: python

   # coding=utf-8
   from __future__ import absolute_import

   import octoprint.plugin

   class HelloWorldPlugin(octoprint.plugin.StartupPlugin, octoprint.plugin.TemplatePlugin):
       def on_after_startup(self):
           self._logger.info("Hello World!")

   __plugin_name__ = "Hello World"
   __plugin_implementations__ = [HelloWorldPlugin()]

Next, we'll create a sub folder ``templates`` underneath our ``octoprint_helloworld`` folder, and within that a file
``helloworld_navbar.jinja2`` like so:

.. code-block:: html

   <a href="https://en.wikipedia.org/wiki/Hello_world">Hello World!</a>

Our plugin's directory structure should now look like this::

   |-+ octoprint_helloworld
   | |-+ templates
   | | `- helloworld_navbar.jinja2
   | `- __init__.py
   |- README.md
   |- requirements.txt
   `- setup.py

Restart OctoPrint and open the web interface in your browser (make sure to clear your browser's cache!).

.. _fig-plugins-gettingstarted-helloworld_navbar:
.. figure:: ../images/plugins_gettingstarted_helloworld_navbar.png
   :align: center
   :alt: Our "Hello World" navigation bar element in action

Now look at that!