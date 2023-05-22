.. _sec-plugins-python3:

Migrating to Python 3
=====================

Python 2 is now EOL as of January 1st 2020. With the release of 1.4.0 OctoPrint will be compatible to both Python 2 and
Python 3.

However, the same doesn't automatically hold true for all of the third party plugins for OctoPrint out there - it will
fall to their authors to ensure compatibility to both Python versions.

This guide is supposed to help plugin authors in making sure their plugins run under Python 2 as well as Python 3,
which for now is the goal for OctoPrint's ecosystem, as we'll have to live with existing legacy Python 2 installations
for a while to come (the plan is to stay Python 2 compatible until roughly a year after the release of 1.4.0).

.. contents::
   :local:

.. _sec-plugins-python3-venv:

How to get a Python 3 virtual environment with OctoPrint
--------------------------------------------------------

In order to test your plugins for Python 3 compatibility and also to allow for ongoing maintenance against both Python
versions, you should create a Python 3 virtual environment next to your Python 2 one. You can then quickly switch between
Python 2 and Python 3 simply by ``activate``-ing whichever one you need.

You can create a Python 3 virtualenv next to your (existing) Python 2 virtualenv and then just activate which one you
currently want to use.

After installing Python 3 on your development system it's as easy as supplying ``--python=/path/to/python3executable``
to ``virtualenv``, e.g.:

.. code-block:: none

   virtualenv --python=/usr/bin/python3 venv3

That will have the virtualenv be created based on Python 3, regardless of whether it's currently running under Python
2 or 3. The same works for Python 2 btw:

.. code-block:: none

   virtualenv --python=/usr/bin/python2 venv2

After creating the virtual environment, make sure to activate & install OctoPrint into it:

.. code-block:: none

   source venv3/bin/activate
   pip install "OctoPrint>=1.4.0rc1"

Then create an editable install of your plugin, start the server and start testing:

.. code-block:: none

   pip install -e path/to/your/plugin
   octoprint serve --debug

.. note::

   On Windows that will probably look something like this instead:

   .. code-block:: none

      virtualenv --python=C:/Python37/python.exe venv37
      venv3/Script/activate.bat
      pip install "OctoPrint>=1.4.0rc1"
      pip install -e path/to/your/plugin
      octoprint serve --debug

.. note::

   If you want to migrate your existing OctoPrint install *on OctoPi 0.17.0* to Python 3, I suggest to first make a
   :ref:`backup <sec-bundledplugins-backup>`, then move the existing venv ``/home/pi/oprint`` out of the way and
   create a new one based on Python 3 (which should already be present on current OctoPi images):

   .. code-block:: none

      mv ~/oprint ~/oprint.py2
      virtualenv --python=/usr/bin/python3 oprint
      source ~/oprint/bin/activate
      pip install "OctoPrint>=1.4.0"
      sudo service octoprint restart

.. _sec-plugins-python3-markup:

Telling OctoPrint your plugin is Python 3 ready
-----------------------------------------------

In order for OctoPrint to even load your plugin when it's running under Python 3, it first needs to know your plugin is
compatible to a Python 3 environment. By default OctoPrint will assume your plugin isn't and refuse to load it when
running under Python 3 itself.

To tell OctoPrint about this, all you need is to set the ``__plugin_pythoncompat__`` property in your plugins's ``__init__.py``
accordingly, e.g.

.. code-block:: python

   __plugin_pythoncompat__ = ">=2.7,<4"

This would tell OctoPrint that your plugin is compatible to all Python versions between 2.7 and 3.x. This should be
your target compatibility range for now.

If at a later date you want to go all-in on Python 3 and mark your plugin as no longer supporting Python 2, tell
OctoPrint about this as well:

.. code-block:: python

   __plugin_pythoncompat__ = ">=3,<4"

.. note::

   You can also tell OctoPrint to ignore the Python compatibility flags for a specific plugin via `config.yaml`:

   .. code-block:: yaml

      plugins:
        _forcedCompatible:
        - "myplugin"
        - "anotherplugin"

   Note that this should only be used temporarily during testing and migration, or to mark an important plugin
   not under your own control that actually works fine under Python 3 out of the box as compatible while waiting
   until the plugin author has pushed an update including the needed flags. Do not just blindly mark third party
   plugins as compatible and then open support requests if that causes issues in your setup.

Once your plugin is ensured to be compatible and you've released a new version that includes the necessary compatibility
flag and changes, is done you also need to mark up your plugin in the Official Plugin Repository (if it's registered
therein) so that OctoPrint's built-in Plugin Manager will see that your plugin is compatible as well and allow users
to install it through it. In order to do that, you need to add a new flag compatibility.python to the front matter in
your plugin registration file and file a pull request for that. Adjust the markdown file so that it contains this:

.. code-block:: yaml

   compatibility:
     python: ">=2.7,<3"

The value here follows the same mechanism as the ``__plugin_pythoncompat__`` property, so ``>=2.7,<3`` for 2 and 3
support and ``>=3,<4`` for 3+ support.

.. warning::

   Do **not** just mark your plugin as compatible without diligent testing that it actually does work as expected and
   without flooding ``octoprint.log`` with warnings and errors!

.. _sec-plugins-python3-pitfalls:

Common pitfalls during migration
--------------------------------

Some of the changes in Python 3 compared to Python 2 are sadly backwards incompatible and usually cause a number of
common issues in code written for Python 2 when run under Python 3. By now they are pretty well documented and there
exist a number of helpful and comprehensive migration guides, three of which I want to mention here.

One is the official Python 3 porting guide `Porting Python 2 Code to Python 3 <https://docs.python.org/3/howto/pyporting.html>`__
which sums up all the important changes and also gives hints on how best to go about running a project which supports
both versions for now.

The second is the `Writing Python 2-3 compatible code <https://python-future.org/compatible_idioms.html>`__ cheat sheet
from the Python-Future project, which is a comprehensive list of idioms that are compatible to both Python 2 and 3 and
will make your code run under both, utilizing `future <https://python-future.org/>`__ and `six <https://six.readthedocs.io/>`__.
I can strongly recommend this cheat sheet, it's what primarily guided me during the migration phase as well.

The third one is the free online book `Support Python 3: An in-depth guide <http://python3porting.com/toc.html>`__, and
especially its chapter on `Common migration problems <http://python3porting.com/problems.html>`__ in which you'll find
extensive descriptions of the most troublesome changes in Python 3 and how to overcome them. Please note that with
regards to the contents of this book, we are aiming for the "Python 2 and Python 3 without conversion" strategy, so
code that runs in both environments. Sadly this book is a bit outdated by now and still references some long-out versions
as "upcoming", so with regards to compatible idioms to use, best stick to the Python-Future cheat sheet.

Looking at the issues encountered by some plugin authors and also my own experiences during the Python 3 migration of
OctoPrint's code, the most common problems for these scenarios seem to be byte vs unicode issues, trouble with absolute
imports, changes in integer division behaviour and the switch of map, filter and zip to return iterators instead of
lists and causing issues in the following code due to that.

.. _sec-plugins-python3-pitfalls-strings:

Bytes vs unicode
................

One of if not the most problematic change between Python 2 and 3 surely must be the change in string handling. Under
Python 2 your basic string was a byte string, but it could also magically turn into a unicode string depending on what
you wrote into it. That did cause some confusion, especially in APIs, and caused quite a mess, which is why the decision
was made to go for distinct text and binary types instead, and making the string literal always be a (unicode) text.

.. note::

   Please note that these changes in string handling also affect several Python APIs that operate on files and streams
   and thus might also affect parts of OctoPrint's plugin interface that inherit from these APIs. Currently only one such
   case has been reported, as OctoPrint's :py:class:`~octoprint.filemanager.util.LineProcessorStream` will return bytes
   instead of str on its ``process_line`` function under Python 3 - so here's a heads-up if your plugin happens to utilize that.

Obviously, that will lead to issues in code using "just strings" when run under Python 2 vs 3. The first step to solve
these problems would be to make your scripts behave the same under Python 2 and 3 by putting this right at the top of
all your plugin's python files:

.. code-block:: python

   from __future__ import unicode_literals

That will make your files behave as if they were running under Python 3, even when run under Python 2, and your string
literals will now be the text data type, which - annoyingly - is a different one under Python 2 vs 3, ``unicode`` vs ``str`` to
be exact. Heads-up here - under Python 2 there's also a ``str`` type, but that one is for binary data. Yes, I know, this
ain't fun.

In any case, once you've done this, make sure that everything in your code that should be text is text (``unicode`` under
Python 2, ``str`` under Python 3), and everything that should be binary is binary (``str`` under Python 2, ``bytes`` under Python 3).
A good rule of thumb is that you usually want to use text as much as possible within your application and only convert
to/from bytes at the outskirts, e.g. when writing to a file, a socket or something else machine like. Note that you do
NOT need to convert to bytes when implementing API endpoints that return JSON, as that should use text with unicode
anyhow.

OctoPrint includes two utility methods you should use to ensure your strings enter/exit your code in the right format,
under both Python versions: :py:func:`octoprint.util.to_bytes` and :py:func:`octoprint.util.to_unicode`. Use them to ensure the correct data
types and to avoid weird conversion and encoding issues during runtime.

You can read more about this specific issue in the corresponding section of the
`Python porting guide <https://docs.python.org/3/howto/pyporting.html#text-versus-binary-data>`__ and also in the
`cheat sheet <https://python-future.org/compatible_idioms.html#strings-and-bytes>`__.

.. _sec-plugins-python3-pitfalls-absolute-imports:

Absolute imports
................

Python 3 now defaults to absolute imports, meaning that trying to import a sub package with a

.. code-block:: python

   import my_sub_package

will now fail with an error. You'll need to explicitly make the import a relative one:

.. code-block:: python

   from . import my_sub_package

To make your code behave the same in that regard in both Python 2 and Python 3, you should add the corresponding
future import:

.. code-block:: python

   from __future__ import absolute_imports

You can read more about this specific issue in the
`cheat sheet <https://python-future.org/compatible_idioms.html#imports-relative-to-a-package>`__ and also in
`the book <http://python3porting.com/problems.html#relative-import-problems>`__.

.. _sec-plugins-python3-pitfalls-version-specific-imports:

Version specific imports
........................

Sometimes it is necessary to use an import statement that is explicitly related to a specific Python version, e.g. due to
a package change between Python 2 and 3. You can do this by first trying the Python 3 import and if that doesn't work
out trying the Python 2 import instead:

.. code-block:: python

   try:
      import queue
   except ImportError:
      import Queue as queue

This should be the preferred method of handling situations like this. If you actually do need to do explicit version
specific imports that cannot be handled this way, you can check for the Python version like this:

.. code-block:: python

   import sys
   if sys.version[0] == '2':
      # Python 2 specific imports
   else:
      # Python 3 specific imports

.. _sec-plugins-python3-pitfalls-intdiv:

Integer division
................

When you divide two integers in Python 2 you'll get back an integer, rounded down. In Python 3 however you'll now get
a float. That means you might have to revisit some places where you do integer divisions and might rely on the result
to be an integer as well (e.g. when using a calculation result as an index in an array or something like that).

Yet again there's a future-import to apply to your files in order to at least have them behave the same in that regard
under both Python 2 and Python 3:

.. code-block:: python

   from __future__ import division

You can read more about this specific issue in the `Python porting guide <https://docs.python.org/3/howto/pyporting.html#division>`__
and in the `cheat sheet <https://python-future.org/compatible_idioms.html#division>`__.

.. _sec-plugins-python3-pitfalls-iterators:

Iterators instead of list from map, filter, zip
...............................................

The built-in functions ``map``, ``filter`` and ``zip`` return a ``list`` with their result in Python 2. In Python 3 they have been
switched to returning iterators. That can cause trouble with code handling the result (e.g. if you try to return it as
part of a JSON response on an API endpoint).

The easiest way to solve this is to make sure to wrap any ``map``/``filter``/``zip`` calls into a ``list`` constructor if the result is
to be used outside of the calling code (even though that comes with a small performance penalty under Python 2):

.. code-block:: python

   result1 = filter(lambda x: x is not None, my_collection)
   result2 = list(filter(lambda x: x is not None, my_collection))

   assert(isinstance(result1, list)) # Python 2 passes, Python 3 fails
   assert(isinstance(result2, list)) # Python 2 and 3 pass

There also exist further options, take a look at the `cheat sheet <https://python-future.org/compatible_idioms.html#map>`__.

.. _sec-plugins-python3-checklist:

Checklist
---------

As a summary, follow this checklist to migrate your plugin to be compatible to both Python 2 and 3:

  * Create a Python 3 virtualenv and install OctoPrint and your plugin into it for testing.
  * Tell OctoPrint your plugin is Python 2 and 3 compatible by adding a new property ``__plugin_pycompat__`` to its
    ``__init__.py``:

    .. code-block:: python

       __plugin_pythoncompat__ = ">=2.7,<4"

  * Add a compatibility header to all `py` files to ensure similar basic behaviour under Python 2 and Python 3:

    .. code-block:: python

       # -*- coding: utf-8 -*-
       from __future__ import absolute_import, division, print_function, unicode_literals

  * Thoroughly test your plugin under Python 3. Pay special attention to any kind of string handling issues, integer
    division, relative imports from your plugin package and how the results of ``map``, ``filter`` and ``zip`` are
    used in your code, as those have proven to be the biggest issues during past migrations.
  * Once everything works under both Python versions and you've prepared a new release of your plugin (don't forget to
    increment the version!), update your registration file in the Official Plugin Repository to include the correct
    Python compatibility information as well:

    .. code-block:: yaml

       compatibility:
         python: ">=2.7,<4"

.. _sec-plugins-python3-furtherreading:

Further reading
---------------

.. seealso::

   `Porting Python 2 Code to Python 3 <https://docs.python.org/3/howto/pyporting.html>`__
      The official Python 3 porting guide which sums up all the important changes and also gives hints on how best to
      go about running a project which supports both versions for now.

   `Cheat Sheet: Writing Python 2-3 compatible code <https://python-future.org/compatible_idioms.html>`__
      A comprehensive list of idioms that are compatible to both Python 2 and 3 and will make your code run under both,
      utilizing `future <https://python-future.org/>`__ and `six <https://six.readthedocs.io/>`__. Strongly recommended.

   `Supporting Python 3: An in-depth guide <http://python3porting.com/bookindex.html>`__
      A free online book on the switch to Python 3. Sadly seems a bit outdated by now, so with regards to compatible
      idioms to use, best stick to the cheat sheet. Gives some interesting background however.

   `Towards Python 3 and OctoPrint 1.4.0 <https://community.octoprint.org/t/towards-python-3-and-octoprint-1-4-0/12382?u=foosel>`__
      Forum topic discussing OctoPrint 1.4.0's roadmap including Python 3 compatibility and time frame.

   `Migrating plugins to Python 2 & 3 compatibility - experiences? <https://community.octoprint.org/t/migrating-plugins-to-python-2-3-compatibility-experiences/16294?u=foosel>`__
      Forum topic collecting experiences by plugin developers in migrating their plugins to achieve Python 2 & 3
      compatibility.
