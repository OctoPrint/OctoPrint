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
``%APPDATA%\OctoPrint\plugins`` on Windows and ``~/Library/Application Support/OctoPrint`` on Mac). In this case your plugin will be distributed directly
as a Python module (a single ``.py`` file containing all of your plugin's code directly and named
like your plugin) or a package (a folder named like your plugin + ``__init.py__`` contained within).

.. _sec-plugins-distribution-pip:

Proper packages installable via pip
-----------------------------------

You can have your users install it via ``pip`` and register it for the `entry point <http://setuptools.readthedocs.io/en/latest/setuptools.html#dynamic-discovery-of-services-and-plugins>`_ ``octoprint.plugin`` via
your plugin's ``setup.py``, this way it will be found automatically by OctoPrint upon initialization of the
plugin subsystem [#f1]_.

For an example of how the directory structure and related files would look like in this case, please take a
look at the `helloworld example from OctoPrint's example plugins <https://github.com/OctoPrint/Plugin-Examples/tree/master/helloworld>`_.

This variant is highly recommended for pretty much any plugin besides the most basic ones since it also allows
requirements management and pretty much any thing else that Python's setuptools provide to the developer.

.. seealso::

   `OctoPrint Plugin Cookiecutter Template <https://github.com/OctoPrint/cookiecutter-octoprint-plugin>`_
       A `Cookiecutter Template <https://github.com/audreyr/cookiecutter>`_ providing
       you with all you need to get started with writing a properly packaged OctoPrint plugin. See the
       :ref:`Plugin Tutorial <sec-plugins-gettingstarted>` for an :ref:`example <sec-plugins-gettingstarted-growingup>`
       on how to use this.

.. rubric:: Footnotes

.. [#f1] The automatic registration will only work within the same Python installation (this also includes virtual
         environments), so make sure to instruct your users to use the exact same Python installation for installing
         the plugin that they also used for installing & running OctoPrint. For OctoPi this means using
         ``~/oprint/bin/pip`` for installing plugins instead of just ``pip``.

.. _sec-plugins-distribution-pluginrepo:

Registering with the official plugin repository
-----------------------------------------------

Once it is ready for general consumption, you might want to register your plugin with the
`official OctoPrint Plugin Repository <http://plugins.octoprint.org>`_. You can find instructions on how to do
that in the `Plugin Repository's help pages <http://plugins.octoprint.org/help/registering/>`_.

If you used the `OctoPrint Plugin Cookiecutter Template <https://github.com/OctoPrint/cookiecutter-octoprint-plugin>`_
when creating your plugin, you can find a prepared registration entry ``.md`` file in the ``extras`` folder of your
plugin.

Version management after the official plugin repository release
---------------------------------------------------------------

Once your plugin is available in the official plugin repository, you probably want to create and distribute new versions.
For "beta" users you can use the manual file distribution method, or a more elegant release channels (see below).
After you finalized a new plugin version, don't forget to actually update the version in the ``setup.py``,
and `submit a new release on github <https://docs.github.com/en/free-pro-team@latest/github/administering-a-repository/managing-releases-in-a-repository#creating-a-release>`_.

After you published the new release, you can verify it on your installed octoprint,
with force checking the updates under the advanced options (in the software updates menu in the settings).
The new versions will appear to the plugin users in the next 24 hours (it depends on their cache refreshes).

The `Software Update Plugin <https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html#>`_ has options to define multiple release channels,
and you can let the users decide if they want to test your pre-releases or not.
This can be achieved with defining ``stable_branch`` and ``prerelease_branches`` in the ``get_update_information`` function,
and creating github releases to the newly configured branches too.
For more information you can check the `Software Update Plugin documentation <https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html#version-checks>`_
or read a more step-by-step writeup `here <https://github.com/cp2004/OctoPrint-Knowledge/blob/main/release-channels.md>`_.
