.. _sec-features-plugins:

*******
Plugins
*******

Starting with OctoPrint 1.2.0, there's now a plugin system in place which allows to individually
extend OctoPrint's functionality.

Right now plugins can be used to extend OctoPrint's web interface, to execute specific tasks on server startup and
shutdown, to provide custom (API) endpoints or whole user interfaces with special functionality, to react to system
events or progress reports or to add support for additional slicers. More plugin types are planned for the future.

.. _sec-features-plugins-available:

Finding Plugins
===============

The official OctoPrint Plugin Repository can be found at `plugins.octoprint.org <http://plugins.octoprint.org>`_.

Some plugins may also be found in the list provided in `the OctoPrint wiki <https://github.com/foosel/OctoPrint/wiki#plugins>`_
and on the `OctoPrint organization Github page <https://github.com/OctoPrint>`_.

.. _sec-features-plugins-installing:

Installing Plugins
==================

Plugins can be installed through the bundled Plugin Manager, which allows installing plugins available in the
`OctoPrint Plugin Repository <http://plugins.octoprint.org>`_, from a web address or from an uploaded file archive.

Please refer to the documentation of the plugin for additional installations instructions.

Manual Installation
-------------------

If you don't want or can't use the Plugin Manager, plugins may also be installed manually either by copying and
unpacking them into one of the configured plugin folders (regularly those are ``<octoprint source root>/plugins`` and
``<octoprint config folder>/plugins`` [#f1]_ or by installing them as regular python modules via ``pip`` [#f2]_.

For a plugin available on the Python Package Index (PyPi), the process is as simple as issuing a

.. code-block:: bash

   pip install <plugin_name>

For plugins not available on PyPi, you'll have to give ``pip`` an URL from which to install the package (e.g. the URL to
a ZIP file of the current master branch of a Github repository hosting a plugin, or even a ``git+https`` URL), example:

.. code-block:: bash

   pip install https://github.com/OctoPrint/OctoPrint-Growl/archive/master.zip

See `the pip install documentation <http://pip.readthedocs.org/en/latest/reference/pip_install.html>`_ for what URL
types are possible.

.. _sec-features-plugins-developing:

Developing Plugins
==================

See :ref:`Developing Plugins <sec-plugins>`.

.. rubric:: Footnotes

.. [#f1] For Linux that will be ``~/.octoprint/plugins``, for Windows it will be ``%APPDATA%/OctoPrint/plugins`` and for
         Mac ``~/Library/Application Support/OctoPrint/plugins``
.. [#f2] Make sure to use the exact same Python installation for installing the plugin that you also used for
         installing & running OctoPrint. For OctoPi this means using ``~/oprint/bin/pip`` for installing plugins
         instead of just ``pip``.
