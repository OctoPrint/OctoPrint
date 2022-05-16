__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021 The OctoPrint Project - Released under terms of the AGPLv3 License"

import itertools
import os.path
import re


def _sfn_really_universal(name):
    from octoprint.util.text import sanitize

    ### taken from pathvalidate library

    _WINDOWS_RESERVED_FILE_NAMES = ("CON", "PRN", "AUX", "CLOCK$", "NUL") + tuple(
        f"{name:s}{num:d}"
        for name, num in itertools.product(("COM", "LPT"), range(1, 10))
    )
    _MACOS_RESERVED_FILE_NAMES = (":",)

    result = sanitize(name, safe_chars="-_.()[] ").replace(" ", "_")
    root, ext = os.path.splitext(result)
    if root.upper() in (_WINDOWS_RESERVED_FILE_NAMES + _MACOS_RESERVED_FILE_NAMES):
        root += "_"
    return root + ext


def sanitize_filename(name, really_universal=False):
    """
    Sanitizes the provided filename. Implementation differs between Python versions.

    Under normal operation, ``pathvalidate.sanitize_filename`` will be used, leaving the
    name as intact as possible while still being a legal file name under all operating
    systems.

    Behaviour can be changed by setting ``really_universal`` to ``True``. In this case,
    the name will be ASCII-fied, using ``octoprint.util.text.sanitize`` with
    safe chars ``-_.()[] `` and all spaces replaced by ``_``. This is the old behaviour.

    In all cases, a single leading ``.`` will be removed (as it denotes hidden files
    on *nix).

    Args:
        name:          The file name to sanitize. Only the name, no path elements.
        really_universal: If ``True``, the old method of sanitization will always
                          be used. Defaults to ``False``.

    Returns:
        the sanitized file name
    """
    from octoprint.util import to_unicode

    name = to_unicode(name)

    if name is None:
        return None

    if "/" in name or "\\" in name:
        raise ValueError("name must not contain / or \\")

    from pathvalidate import sanitize_filename as sfn

    if really_universal:
        result = _sfn_really_universal(name)
    else:
        result = sfn(name)

    return result.lstrip(".")


def get_dos_filename(
    input, existing_filenames=None, extension=None, whitelisted_extensions=None, **kwargs
):
    """
    Converts the provided input filename to a 8.3 DOS compatible filename. If ``existing_filenames`` is provided, the
    conversion result will be guaranteed not to collide with any of the filenames provided thus.

    Uses :func:`find_collision_free_name` internally.

    Arguments:
        input (string): The original filename incl. extension to convert to the 8.3 format.
        existing_filenames (list): A list of existing filenames with which the generated 8.3 name must not collide.
            Optional.
        extension (string): The .3 file extension to use for the generated filename. If not provided, the extension of
            the provided ``filename`` will simply be truncated to 3 characters.
        whitelisted_extensions (list): A list of extensions on ``input`` that will be left as-is instead of
            exchanging for ``extension``.
        kwargs (dict): Additional keyword arguments to provide to :func:`find_collision_free_name`.

    Returns:
        string: A 8.3 compatible translation of the original filename, not colliding with the optionally provided
            ``existing_filenames`` and with the provided ``extension`` or the original extension shortened to
            a maximum of 3 characters.

    Raises:
        ValueError: No 8.3 compatible name could be found that doesn't collide with the provided ``existing_filenames``.

    Examples:

        >>> get_dos_filename("test1234.gco")
        'test1234.gco'
        >>> get_dos_filename("test1234.gcode")
        'test1234.gco'
        >>> get_dos_filename("test12345.gco")
        'test12~1.gco'
        >>> get_dos_filename("Wölfe 🐺.gcode")
        'wolfe_~1.gco'
        >>> get_dos_filename("💚.gcode")
        'green_~1.gco'
        >>> get_dos_filename("test1234.fnord", extension="gco")
        'test1234.gco'
        >>> get_dos_filename("auto0.g", extension="gco")
        'auto0.gco'
        >>> get_dos_filename("auto0.g", extension="gco", whitelisted_extensions=["g"])
        'auto0.g'
        >>> get_dos_filename(None)
        >>> get_dos_filename("foo")
        'foo'
    """

    if input is None:
        return None

    input = sanitize_filename(input, really_universal=True)

    if existing_filenames is None:
        existing_filenames = []

    if extension is not None:
        extension = extension.lower()

    if whitelisted_extensions is None:
        whitelisted_extensions = []

    filename, ext = os.path.splitext(input)

    ext = ext.lower()
    ext = ext[1:] if ext.startswith(".") else ext
    if ext in whitelisted_extensions or extension is None:
        extension = ext

    return find_collision_free_name(filename, extension, existing_filenames, **kwargs)


def find_collision_free_name(filename, extension, existing_filenames, max_power=2):
    """
    Tries to find a collision free translation of "<filename>.<extension>" to the 8.3 DOS compatible format,
    preventing collisions with any of the ``existing_filenames``.

    First strips all of ``."/\\[]:;=,`` from the filename and extensions, converts them to lower case and truncates
    the ``extension`` to a maximum length of 3 characters.

    If the filename is already equal or less than 8 characters in length after that procedure and "<filename>.<extension>"
    are not contained in the ``existing_files``, that concatenation will be returned as the result.

    If not, the following algorithm will be applied to try to find a collision free name::

        set counter := power := 1
        while counter < 10^max_power:
            set truncated := substr(filename, 0, 6 - power + 1) + "~" + counter
            set result := "<truncated>.<extension>"
            if result is collision free:
                return result
            counter++
            if counter >= 10 ** power:
                power++
        raise ValueError

    This will basically -- for a given original filename of ``some_filename`` and an extension of ``gco`` -- iterate
    through names of the format ``some_f~1.gco``, ``some_f~2.gco``, ..., ``some_~10.gco``, ``some_~11.gco``, ...,
    ``<prefix>~<n>.gco`` for ``n`` less than 10 ^ ``max_power``, returning as soon as one is found that is not colliding.

    Arguments:
        filename (string): The filename without the extension to convert to 8.3.
        extension (string): The extension to convert to 8.3 -- will be truncated to 3 characters if it's longer than
            that.
        existing_filenames (list): A list of existing filenames to prevent name collisions with.
        max_power (int): Limits the possible attempts of generating a collision free name to 10 ^ ``max_power``
            variations. Defaults to 2, so the name generation will maximally reach ``<name>~99.<ext>`` before
            aborting and raising an exception.

    Returns:
        string: A 8.3 representation of the provided original filename, ensured to not collide with the provided
            ``existing_filenames``

    Raises:
        ValueError: No collision free name could be found.

    Examples:

        >>> find_collision_free_name("test1234", "gco", [])
        'test1234.gco'
        >>> find_collision_free_name("test1234", "gcode", [])
        'test1234.gco'
        >>> find_collision_free_name("test12345", "gco", [])
        'test12~1.gco'
        >>> find_collision_free_name("test 123", "gco", [])
        'test_123.gco'
        >>> find_collision_free_name("test1234", "g o", [])
        'test1234.g_o'
        >>> find_collision_free_name("test12345", "gco", ["/test12~1.gco"])
        'test12~2.gco'
        >>> many_files = ["/test12~{}.gco".format(x) for x in range(10)[1:]]
        >>> find_collision_free_name("test12345", "gco", many_files)
        'test1~10.gco'
        >>> many_more_files = many_files + ["/test1~{}.gco".format(x) for x in range(10, 99)]
        >>> find_collision_free_name("test12345", "gco", many_more_files)
        'test1~99.gco'
        >>> many_more_files_plus_one = many_more_files + ["/test1~99.gco"]
        >>> find_collision_free_name("test12345", "gco", many_more_files_plus_one)
        Traceback (most recent call last):
        ...
        ValueError: Can't create a collision free filename
        >>> find_collision_free_name("test12345", "gco", many_more_files_plus_one, max_power=3)
        'test~100.gco'

    """
    from octoprint.util import to_unicode

    filename = to_unicode(filename)
    extension = to_unicode(extension)

    if filename.startswith("/"):
        filename = filename[1:]
    existing_filenames = [
        to_unicode(x[1:] if x.startswith("/") else x) for x in existing_filenames
    ]

    def make_valid(text):
        return re.sub(
            r"\s+", "_", text.translate({ord(i): None for i in r".\"/\[]:;=,"})
        ).lower()

    filename = make_valid(filename)
    extension = make_valid(extension)
    extension = extension[:3] if len(extension) > 3 else extension

    full_name_format = "{filename}.{extension}" if extension else "{filename}"

    result = full_name_format.format(filename=filename, extension=extension)
    if len(filename) <= 8 and result not in existing_filenames:
        # early exit
        return result

    counter = 1
    power = 1
    prefix_format = "{segment}~{counter}"
    while counter < (10**max_power):
        prefix = prefix_format.format(
            segment=filename[: (6 - power + 1)], counter=str(counter)
        )
        result = full_name_format.format(filename=prefix, extension=extension)
        if result not in existing_filenames:
            return result
        counter += 1
        if counter >= 10**power:
            power += 1

    raise ValueError("Can't create a collision free filename")


def silent_remove(file):
    """
    Silently removes a file. Does not raise an error if the file doesn't exist.

    Arguments:
        file (string): The path of the file to be removed
    """

    try:
        os.remove(file)
    except OSError:
        pass
