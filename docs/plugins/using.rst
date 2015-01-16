.. _sec-plugins-using:

*************
Using Plugins
*************

.. _sec-plugins-using-available:

Finding Plugins
===============

Currently there's no such thing as a centralized plugin repository for available plugins.

Plugins may be found in the lists provided in `the OctoPrint wiki <https://github.com/foosel/OctoPrint/wiki#plugins>`_
and on the `OctoPrint organization Github page <https://github.com/OctoPrint>`_.

.. _sec-plugins-using-installing:

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

