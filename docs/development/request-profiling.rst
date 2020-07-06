.. _sec-request-profiling:

Profiling requests
==================

Once you have a development environment set up, you will need to launch
OctoPrint using ``serve --debug`` as parameters.

At this point, you are able to make the exact same requests as before. To
profile a specific request, just add ``?perfprofile`` or ``&perfprofile`` to the
request parameters. The request will be rendered as usual, but you will receive
an html document with the profiling results instead of the contents of the
response.

Errors
------

If you receive a ``500: Internal Server Error`` and a ``ModuleNotFoundError: No
module named 'pyinstrument'`` in the console, you didn't install development
dependencies. Do that now using ``pip install -e '.[develop]'``.
