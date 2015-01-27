.. _sec-plugins-distribution:

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

