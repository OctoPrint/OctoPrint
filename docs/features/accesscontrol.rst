.. _sec-features-access_control:

Access Control
==============

.. versionchanged:: 1.4.0

OctoPrint's bundled access control feature allows granular permission control
over which users or user groups are allowed to access which parts of OctoPrint.

The default permissions will deny any kind of access to anonymous (not logged in)
users out of the box.

.. warning::

   Please note that OctoPrint does *not* control the webcam and merely embeds it, and
   thus also cannot limit access to it. If an anonymous user correctly guesses the
   webcam URL, they will thus be able to see it.

If read-only access for anonymous users is enabled, anonymous users will have
read-only access to the following parts of the UI:

  * printer state
  * available gcode files and stats (upload is disabled)
  * temperature
  * webcam
  * gcode viewer
  * terminal output (sending commands is disabled)
  * available timelapse movies
  * any components provided through plugins which are enabled for anonymous
    users

Logged in users without admin flag will be allowed to access everything besides the
Settings and System Commands, which are admin-only.

If Access Control is disabled, everything is directly accessible. **That also
includes all administrative functionality as well as full control over the
printer**, and without the need for an :ref:`API key <sec-api-general-authorization>`!

Upon first start a configuration wizard is provided which allows configuration
of the first administrator account or alternatively disabling Access Control
(which is **NOT** recommended for systems that are directly accessible via the
internet or other untrusted networks!).

.. hint::

   If you plan to have your OctoPrint instance accessible over the internet,
   **always enable Access Control** and ideally **don't make it accessible to
   everyone over the internet but instead use a VPN** or at the very least
   HTTP basic authentication on a layer above OctoPrint.

   A physical device that includes heaters and stepper motors really should not be
   publicly reachable by everyone with an internet connection, even with access
   control enabled.

.. _sec-features-access_control-hooks:

Available Extension Hooks
-------------------------

There are two hooks for plugins to utilize in order to
add new configurable permissions into the system and/or adjust the styling of the
login dialog.

.. _sec-features-access_control-hooks-permissions:

octoprint.access.permissions
............................

See :ref:`here <sec-plugins-hook-permissions>`.

.. _sec-features-access_control-hooks-loginui:

octoprint.plugin.loginui.theming
................................

See :ref:`here <sec-bundledplugins-loginui-hooks-theming>`.

.. _sec-features-access_control-rerunning_wizard:

Rerunning the wizard
--------------------

In case Access Control was disabled in the configuration wizard, it is
possible to re-run it by editing ``config.yaml`` [#f1]_ and setting ``firstRun``
in the ``server`` section and ``enabled`` in the ``accessControl`` section to
``true``:

.. code-block-ext:: yaml

   accessControl:
     enabled: true
   # ...
   server:
     firstRun: true

Then restart the server and connect to the web interface - the wizard should
be shown again.

.. note::

   If user accounts were created prior to disabling Access Control and those
   user accounts are not to be used any more, remove ``.octoprint/users.yaml``.
   If you don't remove this file, the above changes won't lead to the
   configuration being shown again, instead Access Control will just be
   enabled using the already existing login data. This is to prevent you from
   resetting access control by accident.

.. rubric:: Footnotes

.. [#f1] For Linux that will be ``~/.octoprint/config.yaml``, for Windows it will be ``%APPDATA%/OctoPrint/config.yaml`` and for
         Mac ``~/Library/Application Support/OctoPrint/config.yaml``
