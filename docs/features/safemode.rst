.. _sec-features-safemode:

*********
Safe mode
*********

With the advent of support for plugins in OctoPrint, it quickly became apparent that some of the bugs
reported on OctoPrint's bug tracker were actually bugs with installed third party plugins instead of
OctoPrint itself.

To allow an easier identification of these cases, OctoPrint 1.3.0 introduced safe mode. Starting
OctoPrint in safe mode disables all plugins that are not bundled with OctoPrint, allowing to easier
identify most cases where a third party plugin is the culprit of an observed issue.

Additionally, OctoPrint allows uninstalling plugins in this mode, allowing recovery from cases where
a third party plugin causes the server to not start up or the web interface to not render or function
correctly anymore.

Whenever reporting an issue with OctoPrint, please always attempt to reproduce it in safe mode as well to
ensure it really is an issue in OctoPrint itself and now caused by one of your installed third party plugins.

.. _sec-features-safemode-how:

How to start OctoPrint in safe mode
===================================

There exist three ways to start OctoPrint in safe mode:

  * by selecting "Restart OctoPrint in safe mode" from the "System" menu,
    if the "Restart OctoPrint" server command has been correctly configured (since OctoPrint 1.3.2,
    see :numref:`fig-features-safemode-systemmenu`)
  * by setting the flag ``server.startOnceInSafeMode`` in :ref:`config.yaml <sec-configuration-config_yaml>`
    to ``true`` and restarting. To set this flag you have the following options:

    * from command line run ``octoprint safemode`` (since OctoPrint 1.3.6)
    * from command line run ``octoprint config set --bool server.startOnceInSafeMode true`` (fixed in OctoPrint 1.3.6)
    * use the `Yamlpatcher Plugin <http://plugins.octoprint.org/plugins/yamlpatcher/>`_ and enter & apply the patch
      ``[["set", "server.startOnceInSafeMode", true]]``
    * edit ``config.yaml`` manually with a text editor, locate the ``server`` block if it already exists or create it
      if it doesn't and add ``startOnceInSafeMode: true`` to it:

      .. code-block:: yaml

         # ...
         server:
           startOnceInSafeMode: true
         # ...

      Please also refer to the :ref:`YAML primer <sec-configuration-yaml>`.
  * by starting OctoPrint with the command line parameter ``--safe``, e.g. ``octoprint serve --safe`` (don't forget to
    shutdown OctoPrint first before doing this)

The last two options will have OctoPrint enable safe mode only for the next server start - once you
restart OctoPrint again, safe mode will be disabled again.

.. note::

   **OctoPi users**: For you that's ``~/oprint/bin/octoprint`` wherever it says just ``octoprint``.

.. _fig-features-safemode-systemmenu:
.. figure:: ../images/features-safemode-systemmenu.png
   :align: center
   :alt: "Restart OctoPrint in safe mode" in the "System" menu

   "Restart OctoPrint in safe mode" in the "System" menu

.. _sec-features-safemode-differences:

Differences of safe mode vs normal operation mode
=================================================

When OctoPrint is running in safe mode the following changes to its normal operation mode apply:

  * OctoPrint will not enable any of the installed third party plugins. OctoPrint considers all plugins third
    party plugins that do not ship with OctoPrint's sources, so any plugins installed either via `pip` or
    into OctoPrint's plugin folder at ``~/.octoprint/plugins`` (Linux), ``%APPDATA%/OctoPrint`` (Windows) and
    ``~/Library/Application Support/OctoPrint`` (MacOS).
  * OctoPrint will still allow to uninstall third party plugins through the built-in Plugin Manager.
  * OctoPrint will still allow to disable (bundled) plugins that are still enabled.
  * OctoPrint will not allow to enable third party plugins.
  * OctoPrint's web interface will display a notification to remind you that it is running in
    safe mode.

.. _fig-features-safemode-notification:
.. figure:: ../images/features-safemode-notification.png
   :align: center
   :alt: Safe mode notification

   Safe mode notification
