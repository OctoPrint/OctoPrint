.. sec-bundledplugins-softwareupdate:

Software Update Plugin
======================

The Software Update Plugin allows receiving notifications about new releases
of OctoPrint or installed plugins which registered with it and -- if properly
configured -- also applying the found updates.

.. sec-bundledplugins-softwareupdate-firststeps:

First Steps
-----------

Out of the box the Software Update Plugin will be able to notify you of any
updates that might be available for your OctoPrint installation or any plugins
that registered themselves with it. In order to also be able to update
your OctoPrint installation, you'll need to :ref:`configure <sec-bundledplugins-softwareupdate-octoprintsetup>`
at least OctoPrint's checkout folder, and you also should
configure the restart commands for OctoPrint and the whole server.

.. sec-bundledplugins-softwareupdate-octoprintsetup:

Making OctoPrint updateable on existing installations
+++++++++++++++++++++++++++++++++++++++++++++++++++++

.. note::

   OctoPi releases 0.12.0 and later ship with this already setup for you!

.. note::

   **OctoPi 0.11.0 users**: Please also take a look at
   `the note at the very end of this FAQ entry <https://github.com/foosel/OctoPrint/wiki/FAQ#how-can-i-update-the-octoprint-installation-on-my-octopi-image>`_.
   Due to a little issue in that OctoPi release 0.11.0 you might have to fix
   the URL your OctoPrint checkout is using for updating. This can easily be
   done by SSHing into your OctoPi instance and doing this::

       cd ~/OctoPrint
       git remote set-url origin https://github.com/foosel/OctoPrint.git

If you updated OctoPrint to 1.2.0 or later from a previous existing install,
you'll probably want to set up its software update configuration to allow it
to update itself from now on. For this you'll need to edit ``config.yaml`` and
make it look like this (``# ...`` indicates where your ``config.yaml`` might
contain additional lines that are not of interest here):

.. code-block:: yaml

   # ...
   plugins:
     # ...
     softwareupdate:
       # ...
       checks:
         # ...
         octoprint:
           update_folder: /home/pi/OctoPrint
         # ...
       octoprint_restart_command: sudo service octoprint restart
       environment_restart_command: sudo shutdown -r now
   # ...

.. note::

   You can copy and paste this YAML snippet into the `Yamlpatcher <http://plugins.octoprint.org/plugins/yamlpatcher/>`_
   to apply it to your ``config.yaml`` without having to edit it manually. Your
   preview should look something like the screenshot below.

   .. image:: ../images/bundledplugins-softwareupdate-yaml_octoprintsetup.png
      :align: center
      :alt: Yamlpatcher preview

If you are not running OctoPi or didn't setup OctoPrint following the
`Raspberry Pi setup guide <https://github.com/foosel/OctoPrint/wiki/Setup-on-a-Raspberry-Pi-running-Raspbian>`_
you'll need to substitute ``/home/pi/OctoPrint`` with the folder you originally
cloned OctoPrint into during initial setup.

Save the file, exit the editor, restart OctoPrint. Whenever new releases
become available, you should now be able to update right from the update
notification.

.. sec-bundledplugins-softwareupdate-configuration:

Configuring the Plugin
----------------------

.. code-block:: yaml

    plugins:
      softwareupdate:
        # the time-to-live of the version cache, in minutes
        cache_ttl: 60

        # command to restart OctoPrint (no automatic restart if unset)
        octoprint_restart_command: sudo service octoprint restart

        # command to reboot OctoPrint's host (no automatic reboot if unset)
        environment_restart_command: sudo shutdown -r now

        # configured version check and update methods
        checks:
          # "octoprint" is reserved for OctoPrint
          octoprint:
            # this defines an version check that will check against releases
            # published on OctoPrint's Github repository and an update method
            # utilizing an (included) update script that will be run on
            # OctoPrint's checkout folder
            type: github_release
            user: foosel
            repo: OctoPrint
            update_script: '{python} "/path/to/octoprint-update.py" --python="{python}" "{folder}" "{target}"'
            update_folder: /path/to/octoprint/checkout/folder

          # further checks may be define here

.. sec-bundledplugins-softwareupdate-configuration-versionchecks:

Version checks
++++++++++++++

  * ``github_release``: Checks against releases published on Github. Additional
    config parameters:

    * ``user``: (mandatory) Github user the repository to check belongs to
    * ``repo``: (mandatory) Github repository to check
    * ``prerelease``: ``True`` or ``False``, default ``False``, set to
      ``True`` to also include releases on Github marked as prerelease.
    * ``release_compare``: Method to use to compare between current version
      information and release versions on Github. One of ``python`` (version
      comparison using ``pkg_resources.parse_version``, newer version detected
      if remote > current), ``semantic`` (version comparison using
      ``semantic_version`` package, newer version detected if remote > current)
      and ``unequal`` (string comparison, newer version detected if
      remote != current).

  * ``github_commit``: Checks against commits pushed to Github. Additional
    config parameters:

    * ``user``: (mandatory) Github user the repository to check belongs to
    * ``repo``: (mandatory) Github repository to check
    * ``branch``: Branch of the Github repository to check, defaults to
      ``master`` if not set.

  * ``git_commit``: Checks a local git repository for new commits on its
    configured remote. Additional config parameters:

    * ``checkout_folder``: (mandatory) The full path to the folder with a valid git
      repository to check.

  * ``command_line``: Uses a provided script to determine whether an update
    is available. Additional config parameters:

    * ``command``: (mandatory) The full path to the script to execute. The script is
      expected to return a ``0`` return code if an update is available and to
      return the display name of the available version as the final and
      optionally the display name of the current version as the next to final
      line on stdout.

  * ``python_checker``: Can only be specified by plugins through the
    :ref:`hook <sec-bundledplugins-softwareupdate-hooks>`. Additional config
    parameters:

    * ``python_checker``: (mandatory) A python callable which returns version
      information and whether the current version is up-to-date or not, see
      below for details.

.. sec-bundledplugins-softwareupdate-configuration-updatemethods:

Update methods
++++++++++++++

  * ``pip``: An URL to provide to ``pip install`` in order to perform the
    update. May contain a placeholder ``{target}`` which will be the most
    recent version specifier as retrieved from the update check.
  * ``update_script``: A script to execute in order to perform the update. May
    contain placeholders ``{target}`` (for the most recent version specified
    as retrieved from the update check), ``{folder}`` for the working directory
    of the script and ``{python}`` for the python executable OctoPrint is
    running under. The working directory must be specified either by an
    ``update_folder`` setting or if the ``git_commit`` check is used its
    ``checkout_folder`` setting.
  * ``python_updater``: Can only be specified by plugins through the
    :ref:`hook <sec-bundledplugins-softwareupdate-hooks>`. A python callable
    which performs the update, see below for details.

.. sec-bundledplugins-softwareupdate-configuration-patterns:

Common configuration patterns
+++++++++++++++++++++++++++++

Example for a setup that allows "bleeding edge" updates of OctoPrint under
OctoPi (the ``update_script`` gets configured correctly automatically by the
plugin itself):

.. code-block:: yaml

   plugins:
     softwareupdate:
       checks:
         octoprint:
           type: github_commit
           user: foosel
           repo: OctoPrint
           branch: devel
           update_folder: /home/pi/OctoPrint

Plugin installed via pip and hosted on Github under
``https://github.com/someUser/OctoPrint-SomePlugin``, only releases should be
tracked:

.. code-block:: yaml

   plugins:
     softwareupdate:
       checks:
         some_plugin:
           type: github_release
           user: someUser
           repo: OctoPrint-SomePlugin
           pip: 'https://github.com/someUser/OctoPrint-SomePlugin/archive/{target}.zip'

The same, but tracking all commits pushed to branch ``devel`` (thus allowing
"bleeding edge" updates):

.. code-block:: yaml

   plugins:
     softwareupdate:
       checks:
         some_plugin:
           type: github_commit
           user: someUser
           repo: OctoPrint-SomePlugin
           branch: devel
           pip: 'https://github.com/someUser/OctoPrint-SomePlugin/archive/{target}.zip'

.. sec-bundledplugins-softwareupdate-hooks:

Hooks
-----

.. sec-bundledplugins-softwareupdate-hooks-check_config:

octoprint.plugin.softwareupdate.check_config
++++++++++++++++++++++++++++++++++++++++++++

.. py:function:: update_config_hook(*args, **kwargs)

   Returns additional check configurations for the Software Update plugin.

   Handlers should return a Python dict containing one entry per check. Usually
   this will probably only be the check configuration for the plugin providing
   the handler itself, using the plugin's identifier as key.

   The check configuration must match the format expected in the configuration
   (see description above). Handlers may also utilize the ``python_checker``
   and ``python_updater`` properties to return Python callables that take care
   of performing the version check or the update.

   ``python_checker`` is expected to be a callable matching signature and return
   value of the ``get_latest`` methods found in the provided version checkers in
   ``src/octoprint/plugins/softwareupdate/version_checks``. ``python_updater``
   is expected to be a callable matching signature and return value of the
   ``perform_update`` methods found in the provided updaters in
   ``src/octoprint/plugins/softwareupdate/updaters``.

   **Example**

   The example single-file-plugin updates itself from Github releases published
   at the (fictional) repository ``https://github.com/someUser/OctoPrint-UpdatePluginDemo``.

   .. code-block:: python

      # coding=utf-8
      from __future__ import absolute_import

      def get_update_information(*args, **kwargs):
          return dict(
              updateplugindemo=dict(
                  displayName=self._plugin_name,
                  displayVersion=self._plugin_version,

                  type="github_release",
                  current=self._plugin_version,
                  user="someUser",
                  repo="OctoPrint-UpdatePluginDemo",

                  pip="https://github.com/someUser/OctoPrint-UpdatePluginDemo/archive/{target}.zip"
              )
          )

      __plugin_hooks__ = {
      "octoprint.plugin.softwareupdate.check_config": get_update_information
      }

   :return: A dictionary of check configurations as described above
   :rtype: dict

.. sec-bundledplugins-softwareupdate-helpers:

Helpers
-------

.. sec-bundledplugins-softwareupdate-helpers-version_checks:

version_checks
++++++++++++++

``version_checks`` module of the Software Update plugin, allows reusing the
bundled version check variants from plugins (e.g. wrapped in a ``python_checker``).

.. sec-bundledplugins-softwareupdate-helpers-updaters:

updaters
++++++++

``updaters`` module of the Software Update plugin, allows reusing the bundled
updater variants from plugins (e.g. wrapped in a ``python_updater``).

.. sec-bundledplugins-softwareupdate-helpers-exceptions:

exceptions
++++++++++

``exceptions`` module of the Software Update plugin.

.. sec-bundledplugins-softwareupdate-helpers-util:

util
++++

``util`` module of the Software Update plugin.

.. sec-bundledplugins-softwareupdate-source:

Source Code
-----------

The source of the Software Update plugin is bundled with OctoPrint and can be
found in its source repository under ``src/octoprint/plugins/softwareupdate``.
