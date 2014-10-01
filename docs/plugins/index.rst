.. _sec-plugins:

#####################
Plugins Documentation
#####################

Starting with OctoPrint 1.2.0, there's now a plugin system in place which allows to individually
extend OctoPrint's functionality.

Right now plugins can be used to extend OctoPrint's settings dialog, to execute specific tasks on server startup and
shutdown, to provide custom (API) endpoints with special functionality, to react on system events or to add support for
additional slicers. More plugin types are planned for the future.

.. _sec-plugins-installation:

Installing Plugins
==================

Plugins can be installed either by unpacking them into one of the configured plugin folders (regularly those are
``<octoprint-root>/plugins`` and ``~/.octoprint/plugins`` or by installing them as regular python modules via ``pip``.
Please refer to the documentation of the plugin for installations instructions.

The latter is the more common case since all currently published plugins not bundled with OctoPrint can and should be installed
this way.

For a plugin available on the Python Package Index (PyPi), the process is as simple as issuing a

.. code-block:: bash

   pip install <plugin_name>

For plugins not available on PyPi, you'll have to give ``pip`` an URL from which to install the package (e.g. the URL to
a ZIP file of the current master branch of a Github repository hosting a plugin, or even a ``git+https`` URL), example:

.. code-block:: bash

   pip install https://github.com/OctoPrint/OctoPrint-Growl/archive/master.zip

See `the pip install documentation <http://pip.readthedocs.org/en/latest/reference/pip_install.html>`_ for what URL
types are possible.

.. _sec-plugins-available:

Available Plugins
=================

Currently there's no such thing as a centralized plugin repository for available plugins.

Plugins may be found in the lists provided in `the OctoPrint wiki <https://github.com/foosel/OctoPrint/wiki#plugins>`_
and on the `OctoPrint organization Github page <https://github.com/OctoPrint>`_.

Developing Plugins
==================

Please see the following sub topics for information on how to develop your own OctoPrint plugins.

.. toctree::
   :maxdepth: 2

   developing.rst
