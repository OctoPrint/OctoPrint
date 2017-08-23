.. _sec-bundledplugins_cura:

Cura
====

The Cura Plugin allows slicing of STL files uploaded to OctoPrint directly via
the `CuraEngine <http://github.com/Ultimaker/CuraEngine>`_ **up to and
including version 15.04.x** and supersedes the slicing support integrated into
OctoPrint so far. It comes bundled with OctoPrint starting with version 1.2.0.

.. note::

   Versions of CuraEngine later than 15.04.x have changed their calling
   parameters in such a way that the current implementation of OctoPrint's Cura plugin
   is not compatible to it. For this reason, please use only CuraEngine versions up to
   and including 15.04 for now, as available in the ``legacy`` branch of the CuraEngine
   repository on Github.

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

   OctoPi 0.12.0 and later ships with steps 1 and 2 already done, you only need to
   supply one or more slicing profiles to get going :)

.. _sec-bundledplugins-cura-installing:

Installing CuraEngine
---------------------

You'll need a build of ``legacy`` branch of `CuraEngine <http://github.com/Ultimaker/CuraEngine>`_
in order to be able to use the Cura OctoPrint plugin. You can find the ``legacy`` branch
`here <https://github.com/ultimaker/curaengine/tree/legacy>`__.

If you previously used the `old variant of the Cura integration <https://github.com/foosel/OctoPrint/wiki/Cura-Integration>`_,
you probably still have a fully functional binary lying around in the
installation folder of the full install of Cura you used then -- just put the
path to that in the plugin settings.

.. _sec-bundledplugins-cura-installing-raspbian:

Compiling for Raspbian
++++++++++++++++++++++

.. note::

   A binary of CuraEngine 15.04.06 precompiled on Raspbian Jessie Lite 2016-03-18 is available
   `here <http://bit.ly/octopi_cura_engine_150406>`__. Don't forget to make it
   executable after copying it to your preferred destination on your Pi
   (suggestion: ``/usr/local/bin``) with ``chmod +x cura_engine``. Use at your
   own risk.

Raspbian Jessie
~~~~~~~~~~~~~~~

Building on Raspbian Jessie is as easy as::

    sudo apt-get -y install gcc-4.7 g++-4.7
    git clone -b legacy https://github.com/Ultimaker/CuraEngine.git
    cd CuraEngine
    make

After this has completed, you'll find your shiny new build of CuraEngine in
the `build` folder (full path for above example:
``~/CuraEngine/build/CuraEngine``).

Raspbian Wheezy
~~~~~~~~~~~~~~~

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
including Cura 15.04.x**. Newer Cura releases (e.g. 15.06 or 2.x) use a different
internal format that will *not* work with the current version of the Cura Plugin.

You can find downloads of Cura 15.04.x for Windows, Mac and Linux `on Ultimaker's download page <https://ultimaker.com/en/products/cura-software/list>`_.

In order to export a slicing profile from the Cura desktop UI, open it,
set up your profile, then click on "File" and there on "Save Profile". You can
import the .ini-file this creates via the "Import Profile" button in the
Cura Settings within OctoPrint.

.. _sec-bundledplugins-cura-sourcecode:

Source code
-----------

The source of the Cura plugin is bundled with OctoPrint and can be found in
its source repository under ``src/octoprint/plugins/cura``.
