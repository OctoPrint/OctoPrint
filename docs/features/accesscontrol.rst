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

Upon first start a configuration wizard is provided which allows configuration
of the first administrator account to be used for OctoPrint. After initial setup,
you can then create more users and groups under Settings > Access Control for
customisation of the granular permission system.

The predefined "Guests" group can be used to configure default permissions of anonymous
users, that is those who have not logged in. By default, no permissions are granted to
these users.

A predefined "Read-only Access" group with no users is configured which by default grants
read-only access to the following parts of the UI to any users assigned to this group:

  * printer state
  * available gcode files and stats (upload is disabled)
  * temperature
  * webcam
  * gcode viewer
  * terminal output (sending commands is disabled)
  * available timelapse movies
  * any components provided through plugins which are enabled for anonymous
    users

Another predefined "Operator" group is the default group for newly created users and
by default gives access to all aspects of OctoPrint that involve regular printer
operation. It matches the old "user" role from OctoPrint prior to 1.4.0.

Finally, the predefined "Admins" group gives full admin access to the platform. You should
be careful of who you put into that. It matches the old "admin" role from OctoPrint prior
to 1.4.0.

.. hint::

   If you plan to have your OctoPrint instance accessible over the internet,
   **please use additional security measures** and ideally **don't make it accessible to
   everyone over the internet but instead use a VPN** or at the very least
   HTTP basic authentication on a layer above OctoPrint. Unless you are using a VPN
   **please do not** enable any permissions for the Guest group or the auto-login feature
   described below.

   A physical device that includes heaters and stepper motors really should not be
   publicly reachable by everyone with an internet connection, even with access
   control enabled.

.. _sec-features-access_control-autologin:

Autologin
---------

While access control cannot be disabled as of OctoPrint 1.5+, the Autologin feature can
be used to bypass authentication for hosts on the network(s) that you trust.

Starting with OctoPrint 1.5.0, OctoPrint makes enabled access control mandatory. This
might be an inconvience for some who run OctoPrint in an isolated setup where a login is
not required to ensure security, at a benefit for a huge number of users out there who
continue to underestimate or simply ignore the risk of keeping their OctoPrint instance
unsecured and then happily exposing it on the public internet.

That being said, even as far back as OctoPrint 1.0.0 (released in 2013) there has existed
a way to have OctoPrint automatically log you in, if you connect from a trusted local
network address. This functionality has not been exposed on the UI, and for now also won't
be (to make it a bit harder to once again create an insecure setup for those who simply
won't listen to common sense), but it's easy to set up with a bit of configuration
editing.

When set up properly, it will make sure to automatically log you in as a configured user
whenever you connect from a device on your local network. To get back pretty much the same
behaviour as with disabled access control, you'll only need to create a single (admin)
account and then set up autologin for it.


.. warning::

   **Do not do this if you cannot trust EVERYONE on your local network.** And that really
   means mean everyone. If you ignore this and then someone takes over your OctoPrint
   instance, installs malware on it and makes your printer print an endless stream of
   benchies, that's on you.

.. _sec-features-access_control-autologin-gather_config_info:

Gather configuration information
................................

You can configure Autologin via a plugin (the easy way), or manually (the hard way), but
in either case you will need to specify which user should be automatically logged in, and
which hosts are permitted access this way.

**Improperly setting this subnet option can lead to the compromise of your system, or even
your entire network. Proceed with extreme caution.**

The subnet to use is usually the IP address range of your LAN, which sounds scary but
actually isn't. Just `figure out your PC's IP address and subnet mask <https://lifehacker.com/how-to-find-your-local-and-external-ip-address-5833108>`_
and then combine both with a / in between.

On OctoPi (or another Linux distribution) you can use the following command:

.. code-block::

   ip route | grep -P 'eth0|wlan0' | awk '{print $1}'

Or, for IPv6, use this:

.. code-block::

   ip -6 route | grep -P 'eth0|wlan0' | awk '{print $1}'

This will be what you set as the subnet in the plugin, or where it says
``<yourAddressRange>`` below on the manual configuration instructions.

Example: Your PC has an IP address of ``192.168.23.42`` and a subnet mask of
``255.255.255.0``. Your address range is ``192.168.23.42/255.255.255.0``.

.. _sec-features-access_control-autologin-plugin:

The easy way: Using the OctoPrint-AutoLoginConfig plugin
........................................................

The easiest way to configure AutoLogin is to install the
`OctoPrint-AutoLoginConfig plugin <https://plugins.octoprint.org/plugins/autologin_config/>`_
via the plugin manager.

Open its settings and follow the instructions on the screen.

.. _sec-features-access_control-autologin-manual:

The hard way: Manual editing of config.yaml
...........................................

Preparation
***********

First of all, read :ref:`the YAML primer <sec-configuration-yaml>`. You
will have to edit OctoPrint's main configuration file, and thus should make sure
you understand at least roughly how things work and that you should keep your
hands off the Tab key. If you don't, you might break your config file, and
while the steps include making a backup, this still can be easily avoided by
learning about the DOs and DONTs first.

Then, take a look at :ref:`the docs on config.yaml <sec-configuration-config_yaml>`
on where to find that central configuration file of OctoPrint.

Configuration
*************

Ready? Let's do some editing then. I'll outline what to do and where first, and then
further down there's also a dedicated list of steps for OctoPi specifically.

1. Shutdown OctoPrint
2. Make a backup of your config.yaml
3. Open it in a text editor (e.g. nano). Look if right at the very top it says something like
   this:

   .. code-block:: yaml

      accessControl:
          salt: aabbccddee1234523452345

   If so, edit this, adding lines so it looks like this (making absolutely sure not to touch the
   salt line):

   .. code-block:: yaml

      accessControl:
          salt: aabbccddee1234523452345
          autologinLocal: true
          autologinAs: "<yourUsername>"
          localNetworks:
          - "127.0.0.0/8"
          - "::1/128"
          - "<yourAddressRange>"

   Otherwise, add the following lines to the very top of the file, making sure to keep the
   indentation:

   .. code-block:: yaml

      accessControl:
          autologinLocal: true
          autologinAs: "<yourUsername>"
          localNetworks:
          - "127.0.0.0/8"
          - "::1/128"
          - "<yourAddressRange>"

4. Restart OctoPrint, check that everything works.

This will automatically log you in as the user you specified whenever you connect to
OctoPrint from an address in the address range (e.g. a device on your local network).

OctoPi specific steps
*********************

If you are running OctoPi you will have to SSH into your Raspberry Pi. Then issue
the following commands:

1. ``sudo service octoprint stop``
2. ``cp ~/.octoprint/config.yaml ~/.octoprint/config.yaml.back``
3. ``nano ~/.octoprint/config.yaml``, make the edits as described above
4. ``sudo service octoprint start``

If something went wrong, you can restore the config backup with

.. code-block::

   cp ~/.octoprint/config.yaml.back ~/.octoprint/config.yaml


If you are using a VPN and your setup ABSOLUTELY REQUIRES disabling internal OctoPrint access controls
......................................................................................................

.. warning::

   You probably shouldn't do this, EVER. There are usually other options. Don't even
   THINK about it, unless you have a VPN layer for security. Only consider proceeding
   with this configuration after exhausting ALL other possibilities, and even then, you
   should think long and hard about whether this is a good idea. You almost certainly
   don't need or want to do this.

While access controls can no longer be disabled in OctoPrint 1.5+, this can be
approximated by an Autologin configuration that automatically logs in all users, that is
by using subnets that match all possible IP addresses. By specifying the ``0.0.0.0/0``
subnet (for IPv4) and ``::/0`` for IPv6 in the AutoLogin configuration, you can achieve
this. This configuration is permitted, but highly, highly discouraged.

Please don't do this. You will almost certainly regret it. You alone are responsible for
your actions.

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

octoprint.theming.login
.......................

See :ref:`here <sec-plugins-hook-theming-dialog>`.
