.. _sec-features-access_control:

Access Control
==============

.. versionchanged:: 1.5.0

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

Upon first start a configuration wizard is provided which allows configuration
of the first administrator account to be used for OctoPrint. After initial setup, 
you can then create more users under Settings > Access Control for customisation of
the granular permission system.

.. hint::

   If you plan to have your OctoPrint instance accessible over the internet,
   **please use additional security measures** and ideally **don't make it accessible to
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
