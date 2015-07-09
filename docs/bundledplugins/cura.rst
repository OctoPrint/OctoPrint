.. _sec-bundledplugins_cura:

Cura
====

The Cura Plugin allows slicing of STL files uploaded to OctoPrint directly via
the `CuraEngine <http://github.com/Ultimaker/CuraEngine>`_ **up to and
including version 15.04** and supersedes the slicing support integrated into
OctoPrint so far.

.. note::

   The current development version of CuraEngine has changed its calling
   parameters in such a way that the current implementation of the Cura plugin
   is not compatible to it. Until the plugin can be updated to be compatible
   to these changes, please use only CuraEngine versions up to and including
   15.04 (or the ``legacy`` branch in the CuraEngine repository).

The plugin offers a settings module that allows configuring the path to the
CuraEngine executable to use, as well as importing and managing slicing
profiles to be used. Please note that the Cura Plugin will use the printer
parameters you configured within OctoPrint (meaning bed size and extruder
count and offsets) for slicing.

.. _sec-bundledplugins-cura-firststeps:

First Steps
-----------

Before you can slice from within OctoPrint, you'll need to

  #. :ref:`Install CuraEngine <sec-bundledplugins-cura-installing>`
  #. :ref:`Configure the path to CuraEngine within OctoPrint <sec-bundledplugins-cura-configuring>`
  #. :ref:`Export a slicing profile from Cura and import it within OctoPrint <sec-bundledplugins-cura-profiles>`

.. note::

   OctoPi 0.12.0 ships with steps 1 and 2 already done, you only need to
   supply one or more slicing profiles to get going :)

.. _sec-bundledplugins-cura-installing:

Installing CuraEngine
---------------------

You'll need a current build of `CuraEngine <http://github.com/Ultimaker/CuraEngine>`_
in order to be able to use the Cura OctoPrint plugin. If you are running OctoPrint
on a desktop PC (Window, Mac, i386 Linux), you can take this from a full
install of `Cura <http://github.com/daid/Cura>`_ (you'll find it in the
installation directory). Otherwise you'll need to compile it yourself.

If you previously used the `old variant of the Cura integration <https://github.com/foosel/OctoPrint/wiki/Cura-Integration>`_,
you probably still have a fully functional binary lying around in the
installation folder of the full install of Cura you used then -- just put the
path to that in the plugin settings.

.. _sec-bundledplugins-cura-installing-raspbian:

Compiling for Raspbian
++++++++++++++++++++++

.. note::

   A binary of CuraEngine 14.12 precompiled on Raspbian 2015-01-31 is available
   `here <http://bit.ly/octopi_cura_engine_1412>`_. Don't forget to make it
   executable after copying it to your preferred destination on your Pi
   (suggestion: ``/usr/local/bin``) with ``chmod +x cura_engine``. Use at your
   own risk.

You'll need to install a new version of gcc and g++ and patch CuraEngine's
Makefile (see `this post <http://umforum.ultimaker.com/index.php?/topic/5943-recent-build-of-curaengine-wont-compile-on-raspberry-pi/#entry58539>`_)
in order for the compilation to work on current Raspbian builds (e.g. OctoPi)::

    sudo apt-get -y install gcc-4.7 g++-4.7
    git clone -b legacy https://github.com/Ultimaker/CuraEngine.git
    cd CuraEngine
    wget http://bit.ly/curaengine_makefile_patch -O CuraEngine.patch
    patch < CuraEngine.patch
    make CXX=g++-4.7

After this has completed, you'll find your shiny new build of CuraEngine in
the `build` folder (full path for above example:
``~/CuraEngine/build/CuraEngine``).

.. _sec-bundledplugins-cura-configuring:

Configuring the plugin
----------------------

The Cura plugin needs to be configured with the full path to your copy of the
CuraEngine executable that it's supposed to use. You can do this either via
the Cura plugin settings dialog or by manually configuring the path to the
executable via ``config.yaml``, example:

.. code-block:: yaml

   plugins:
     cura:
       cura_engine: /path/to/CuraEngine

.. _sec-bundledplugins-cura-profiles:

Using Cura Profiles
-------------------

The Cura Plugin supports importing your existing profiles for Cura **up to and
including Cura 15.04**. Newer Cura releases (e.g. 15.06) do not allow to
export the slicing profile anymore and also use a different internal format
that will *not* work with the current version of the Cura Plugin.

In order to export a slicing profile from the Cura desktop UI, open it,
set up your profile, then click on "File" and there on "Save Profile". You can
import the .ini-file this creates via the "Import Profile" button in the
Cura Settings within OctoPrint.

.. _sec-bundledplugins-cura-sourcecode:

Source code
-----------

The source of the Cura plugin is bundled with OctoPrint and can be found in
its source repository under ``src/octoprint/plugins/cura``.
