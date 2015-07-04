.. _sec-features-access_control:

Access Control
==============

When Access Control is enabled, anonymous users (not logged in) will only see
the read-only parts of the UI which are the following:

  * printer state
  * available gcode files and stats (upload is disabled)
  * temperature
  * webcam
  * gcode viewer
  * terminal output (sending commands is disabled)
  * available timelapse movies
  * any components provided through plugins which are enabled for anonymous
    users

Logged in users will get access to everything besides the Settings and System
Commands, which are admin-only.

If Access Control is disabled, everything is directly accessible. **That also
includes all administrative functionality as well as full control over the
printer!**

Upon first start a configuration wizard is provided which allows configuration
of the first administrator account or alternatively disabling Access Control
(which is **NOT** recommended for systems that are directly accessible via the
Internet!).

.. hint::

   If you plan to have your OctoPrint instance accessible over the internet,
   **always enable Access Control**.

.. _sec-features-access_control-rerunning_wizard:

Rerunning the wizard
--------------------

In case Access Control was disabled in the configuration wizard, it is
possibly to re-run it by editing ``config.yaml`` [#f1]_ and setting ``firstRun``
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
