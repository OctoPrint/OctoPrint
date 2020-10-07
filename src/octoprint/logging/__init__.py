# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from typing import Union

from past.builtins import basestring, unicode

from octoprint.logging import handlers  # noqa: F401


def log_to_handler(logger, handler, level, msg, exc_info=None, extra=None, *args):
    """
    Logs to the provided handler only.

    Arguments:
            logger: logger to log to
            handler: handler to restrict logging to
            level: level to log at
            msg: message to log
            exc_info: optional exception info
            extra: optional extra data
            *args: log args
    """
    import sys

    try:
        from logging import _srcfile
    except ImportError:
        _srcfile = None

    # this is just the same as logging.Logger._log

    if _srcfile:
        # IronPython doesn't track Python frames, so findCaller raises an
        # exception on some versions of IronPython. We trap it here so that
        # IronPython can use logging.
        try:
            fn, lno, func = logger.findCaller()
        except ValueError:
            fn, lno, func = "(unknown file)", 0, "(unknown function)"
    else:
        fn, lno, func = "(unknown file)", 0, "(unknown function)"
    if exc_info:
        if not isinstance(exc_info, tuple):
            exc_info = sys.exc_info()

    record = logger.makeRecord(
        logger.name, level, fn, lno, msg, args, exc_info, func, extra
    )

    # and this is a mixture of logging.Logger.handle and logging.Logger.callHandlers

    if (not logger.disabled) and logger.filter(record):
        if record.levelno >= handler.level:
            handler.handle(record)


def get_handler(name, logger=None):
    """
    Retrieves the handler named ``name``.

    If optional ``logger`` is provided, search will be
    limited to that logger, otherwise the root logger will be
    searched.

    Arguments:
            name: the name of the handler to look for
            logger: (optional) the logger to search in, root logger if not provided

    Returns:
        the handler if it could be found, None otherwise
    """
    import logging

    if logger is None:
        logger = logging.getLogger()

    for handler in logger.handlers:
        if handler.get_name() == name:
            return handler

    return None


def get_divider_line(c, message=None, length=78, indent=3):
    """
    Generate a divider line for logging, optionally with included message.

    Examples:

        >>> get_divider_line("-") # doctest: +ALLOW_UNICODE
        '------------------------------------------------------------------------------'
        >>> get_divider_line("=", length=10) # doctest: +ALLOW_UNICODE
        '=========='
        >>> get_divider_line("-", message="Hi", length=10) # doctest: +ALLOW_UNICODE
        '--- Hi ---'
        >>> get_divider_line("-", message="A slightly longer text") # doctest: +ALLOW_UNICODE
        '--- A slightly longer text ---------------------------------------------------'
        >>> get_divider_line("-", message="A slightly longer text", indent=5) # doctest: +ALLOW_UNICODE
        '----- A slightly longer text -------------------------------------------------'
        >>> get_divider_line("-", message="Hello World!", length=10) # doctest: +ALLOW_UNICODE
        '--- Hello World!'
        >>> get_divider_line(None)
        Traceback (most recent call last):
          ...
        AssertionError: c is not text
        >>> get_divider_line("´`")
        Traceback (most recent call last):
          ...
        AssertionError: c is not a single character
        >>> get_divider_line("-", message=3)
        Traceback (most recent call last):
          ...
        AssertionError: message is not text
        >>> get_divider_line("-", length="hello")
        Traceback (most recent call last):
          ...
        AssertionError: length is not an int
        >>> get_divider_line("-", indent="hi")
        Traceback (most recent call last):
          ...
        AssertionError: indent is not an int

    Arguments:
            c: character to use for the line
            message: message to print in the line
            length: length of the line
            indent: indentation of message in line

    Returns:
            formatted divider line
    """

    assert isinstance(c, basestring), "c is not text"
    assert len(c) == 1, "c is not a single character"
    assert isinstance(length, int), "length is not an int"
    assert isinstance(indent, int), "indent is not an int"

    if message is None:
        return c * length

    assert isinstance(message, basestring), "message is not text"

    space = length - 2 * (indent + 1)
    if space >= len(message):
        return c * indent + " " + message + " " + c * (length - indent - 2 - len(message))
    else:
        return c * indent + " " + message


def prefix_multilines(text, prefix=": "):
    # type: (Union[unicode, bytes], unicode) -> unicode
    from octoprint.util import to_unicode

    lines = text.splitlines()
    if not lines:
        return ""

    if len(lines) == 1:
        return to_unicode(lines[0])

    return (
        to_unicode(lines[0])
        + "\n"
        + "\n".join(map(lambda line: prefix + to_unicode(line), lines[1:]))
    )
