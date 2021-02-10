.. _sec-configuration-cli:

CLI
===

.. versionadded:: 1.3.0

OctoPrint provides a basic command line interface for manipulation of :ref:`config.yaml <sec-configuration-config_yaml>`:

.. code-block::

   $ octoprint config --help
   Usage: octoprint config [OPTIONS] COMMAND [ARGS]...

     Basic config manipulation.

   Options:
     --help  Show this message and exit.

   Commands:
     append_value  Appends value to list behind config path.
     effective     Retrieves the full effective config.
     get           Retrieves value from config path.
     insert_value  Inserts value at index of list behind config key.
     remove        Removes a config path.
     remove_value  Removes value from list at config path.
     set           Sets a config path to the provided value.

.. code-block::

   $ octoprint config append_value --help
   Usage: octoprint config append_value [OPTIONS] PATH VALUE

     Appends value to list behind config path.

   Options:
     --json
     --help  Show this message and exit.

.. code-block::

   $ octoprint config effective --help
   Usage: octoprint config effective [OPTIONS]

     Retrieves the full effective config.

   Options:
     --json  Output value formatted as JSON
     --yaml  Output value formatted as YAML
     --raw   Output value as raw string representation
     --help  Show this message and exit.

.. code-block::

   $ octoprint config get --help
   Usage: octoprint config get [OPTIONS] PATH

     Retrieves value from config path.

   Options:
     --json  Output value formatted as JSON
     --yaml  Output value formatted as YAML
     --raw   Output value as raw string representation
     --help  Show this message and exit.

.. code-block::

   $ octoprint config insert_value --help
   Usage: octoprint config insert_value [OPTIONS] PATH INDEX VALUE

     Inserts value at index of list behind config key.

   Options:
     --json
     --help  Show this message and exit.

.. code-block::

   $ octoprint config remove --help
   Usage: octoprint config remove [OPTIONS] PATH

     Removes a config path.

   Options:
     --help  Show this message and exit.

.. code-block::

   $ octoprint config remove_value --help
   Usage: octoprint config remove_value [OPTIONS] PATH VALUE

     Removes value from list at config path.

   Options:
     --json
     --help  Show this message and exit.

.. code-block::

   $ octoprint config set --help
   Usage: octoprint config set [OPTIONS] PATH VALUE

     Sets a config path to the provided value.

   Options:
     --bool   Interpret value as bool
     --float  Interpret value as float
     --int    Interpret value as int
     --json   Parse value from json
     --help   Show this message and exit.
