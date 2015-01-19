.. _sec-plugins-developing:

******************
Developing Plugins
******************

.. todo::

   A section on how to develop plugins yourself, including a tutorial creating an exemplary plugin as well as
   a documentation of the plugin API, will be added in the near future.

.. note::

   This section is still a heavy WIP, so take it with a bit of caution ;)

.. _sec-plugins-developing-structure:

OctoPrint Plugin Structure
==========================

OctoPrint plugins are simple `Python modules or packages <https://docs.python.org/2/tutorial/modules.html>`_ providing
a couple of properties describing the module:

``__plugin_name__``
  Name of your plugin
``__plugin_version__``
  Version of your plugin
``__plugin_description__``
  Description of your plugin
``__plugin_implementations__``
  Instances of one or more of the various :ref:`plugin mixins <sec-plugins-developing-mixins>`
``__plugin_hooks__``
  Handlers for one or more of the various :ref:`plugin hooks <sec-plugins-developing-hooks>`
``__plugin_check__``
  Method called upon discovery of the plugin by the plugin subsystem, should return ``True`` if the
  plugin can be instantiated later on, ``False`` if there are reasons why not, e.g. if dependencies
  are missing.
``__plugin_init__``
  Method called upon initializing of the plugin by the plugin subsystem, can be used to instantiate
  plugin implementations, connecting them to hooks etc.

A very simple example plugin which only hooks into OctoPrint's startup sequence and logs "Oh hello!" would
be the following snippet:

.. code-block:: python

   # coding=utf-8
   from __future__ import absolute_import

   import octoprint.plugin

   __plugin_name__ = "Example Plugin"
   __plugin_version__ = "0.1"
   __plugin_description__ = "Logs \"Oh hello!\" upon OctoPrint's startup"

   def __plugin_init__():
       global __plugin_implementations__
       __plugin_implementations__ = [ExamplePlugin()]

   class ExamplePlugin(octoprint.plugin.StartupPlugin):
       def on_startup(self, host, port):
           self._logger.info("Oh hello!")

.. _sec-plugins-developing-distribution:

Distributing your plugin
========================

You can distribute a plugin with OctoPrint via two ways:

  - You can have your users copy it to OctoPrint's plugin folder (normally located at ``~/.octoprint/plugins`` under Linux,
    ``%APPDATA%\OctoPrint\plugins`` on Windows and ... on Mac). In this case your plugin will be distributed directly
    as a Python module (a single ``.py`` file containing all of your plugin's code directly and named
    like your plugin) or a package (a folder named like your plugin + ``__init.py__`` contained within).
  - You can have your users install it via ``pip`` and register it for the `entry point <https://pythonhosted.org/setuptools/setuptools.html#dynamic-discovery-of-services-and-plugins>`_ ``octoprint.plugin`` via
    your plugin's ``setup.py``, this way it will be found automatically by OctoPrint upon initialization of the
    plugin subsystem [#f1]_.

    For an example of how the directory structure and related files would look like in this case, please take a
    look at the `helloworld example from OctoPrint's example plugins <https://github.com/OctoPrint/Plugin-Examples/tree/master/helloworld>`_.

    This variant is highly recommended for pretty much any plugin besides the most basic ones since it also allows
    requirements management and pretty much any thing else that Python's setuptools provide to the developer.

.. rubric:: Footnotes

.. [#f1] The automatic registration will only work within the same Python installation (this also includes virtual
         environments), so make sure to instruct your users to use the exact same Python installation for installing
         the plugin that they also used for installing & running OctoPrint.

.. _sec-plugins-developing-mixins:

Available plugin mixins
=======================

.. automodule:: octoprint.plugin.types
   :members:
   :undoc-members:
