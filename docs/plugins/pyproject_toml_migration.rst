.. _sec-plugins-pyproject_toml:

Migrating to ``pyproject.toml`` and build isolation
===================================================

Python's packaging has come a long ways in recent years with regards to getting modernized. The old ``setup.py`` based approach of configuring your
package for packaging has been replaced by a ``pyproject.toml`` that supports a whole lot more build systems beyond ``setuptools`` as well
as configuring the various development tools that are part of the Python ecosystem. In addition to that, current versions of
``pip`` (25.3+) by default install packages - including OctoPrint plugins - in what's called "build isolation", to ensure less of a
dependency nightmare by building an installable "wheel" for a package in an isolated environment with the barest minimum of dependencies, as
defined by the package.

This build isolation causes issues with OctoPrint plugins that still use the old ``setup.py`` based plugin template, as that requires
a dependency provided by OctoPrint during installation - when build isolation is active, that cannot be pulled in and the
installation fails. Thankfully, ``pip`` provides a workaround in the shape of the parameters ``--use-pep517 --no-build-isolation``
and OctoPrint 1.11.4+ detects automatically whether these parameters are needed to install or update a plugin package.

However, it would be good if plugin developers make sure their code gets updated to more modern tooling. Not only has it
various advantages, all of Python's ecosystem is fully going into that direction and long term even the above workaround
might at some point vanish. We don't know, so we should modernize!

With ``octoprint-plugin-tool`` there's a quick solution to migrate most plugins still using the legacy packaging approach
to a more modern setup.

.. contents::
   :local:

.. _sec-plugins-pyproject_toml-install_tool:

Obtaining ``octoprint-plugin-tool``
-----------------------------------

``octoprint-plugin-tool`` is available on the official Python package Index PyPI and thus can easily be obtained
through pip:

.. code-block::

   pip install octoprint-plugin-tool

Alternatively, you may also run it directly through ``pipx run``:

.. code-block::

   pipx run octoprint-plugin-tool

or ``uv tool run``:

.. code-block::

   uv tool run octoprint-plugin-tool

Note that it requires Python 3.9 and newer.

OctoPrint 1.12.0 will also include it and offer its functionality on its command line:

.. code-block::

   octoprint dev plugin:migrate-to-pyproject

.. _sec-plugins-pyproject_toml-use_tool:

How to use ``octoprint-plugin-tool``
------------------------------------

In most cases, migrating your plugin to ``pyproject.toml`` is as easy as running

.. code-block::

   octoprint-plugin-tool to-pyproject --path /path/to/your/plugin/checkout

That will do the necessary conversion steps and you'll end up with a modified source tree that
should already work fine.

**If there's any reason the tool cannot do the migration, it will tell you why.** Also take
note of any warnings and instructions on how to proceed it outputs.

It is strongly advised to test packaging and installing your plugin now the way you usually would. Once
you are satisfied everything is still working like it should, release your changes as a new version
of your plugin.

.. _sec-plugins-pyproject_toml-furtherreading:

Further reading
---------------

.. seealso::

   `Writing your pyproject.toml <https://packaging.python.org/en/latest/guides/writing-pyproject-toml/>`__
      The official Python 3 packaging guide explains how a ``pyproject.toml`` file should look.

   `octoprint-plugin-tool <https://github.com/OctoPrint/octoprint-plugin-tool>`__
      The repository and README of ``octoprint-plugin-tool``.
