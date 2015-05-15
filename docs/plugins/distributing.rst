.. _sec-plugins-distribution:

Distributing your plugin
========================

You can distribute a plugin with OctoPrint via two ways.

.. contents::
   :local:

.. _sec-plugins-distribution-manual:

Manual file distribution
------------------------

You can have your users copy it to OctoPrint's plugin folder (normally located at ``~/.octoprint/plugins`` under Linux,
``%APPDATA%\OctoPrint\plugins`` on Windows and ... on Mac). In this case your plugin will be distributed directly
as a Python module (a single ``.py`` file containing all of your plugin's code directly and named
like your plugin) or a package (a folder named like your plugin + ``__init.py__`` contained within).

.. _sec-plugins-distribution-pip:

Proper packages installable via pip
-----------------------------------

You can have your users install it via ``pip`` and register it for the `entry point <https://pythonhosted.org/setuptools/setuptools.html#dynamic-discovery-of-services-and-plugins>`_ ``octoprint.plugin`` via
your plugin's ``setup.py``, this way it will be found automatically by OctoPrint upon initialization of the
plugin subsystem [#f1]_.

For an example of how the directory structure and related files would look like in this case, please take a
look at the `helloworld example from OctoPrint's example plugins <https://github.com/OctoPrint/Plugin-Examples/tree/master/helloworld>`_.

This variant is highly recommended for pretty much any plugin besides the most basic ones since it also allows
requirements management and pretty much any thing else that Python's setuptools provide to the developer.

.. seealso::

   `OctoPrint Plugin Skeleton <https://github.com/OctoPrint/OctoPrint-PluginSkeleton>`_
       A basic plugin skeleton providing you with all you need to get started with distributing your plugin as a proper
       package. See the :ref:`Getting Started Guide <sec-plugins-gettingstarted>` for an
       :ref:`example <sec-plugins-gettingstarted-growingup>` on how to use this.

.. rubric:: Footnotes

.. [#f1] The automatic registration will only work within the same Python installation (this also includes virtual
         environments), so make sure to instruct your users to use the exact same Python installation for installing
         the plugin that they also used for installing & running OctoPrint. For OctoPi this means using
         ``~/oprint/bin/pip`` for installing plugins instead of just ``pip``.

