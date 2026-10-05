__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


def normalize(path, expand_user=True, expand_vars=True, real=True, **kwargs):
    import os

    if path is None:
        return None

    if expand_user:
        path = os.path.expanduser(path)
    if expand_vars:
        path = os.path.expandvars(path)
    path = os.path.abspath(path)
    if real:
        path = os.path.realpath(path)
    return path


def is_sub_path_of(path: str, prefix: str) -> bool:
    """
    Tests if `path` is a sub path (or identical) to `path`.

    >>> is_sub_path_of("/a/b/c", "/a/b")
    True
    >>> is_sub_path_of("/a/b/c", "/a/b2")
    False
    >>> is_sub_path_of("/a/b/c", "/b/c")
    False
    >>> is_sub_path_of("/foo/bar/../../a/b/c", "/a/b")
    True
    >>> is_sub_path_of("/foo/bar/../../a2/b2/c2", "/a/b")
    False
    >>> is_sub_path_of("/a/b", "/a/b")
    True
    >>> is_sub_path_of("/a", "/")
    True
    >>> is_sub_path_of("/a2/b", "/a")
    False
    """
    import os.path

    path = os.path.realpath(path)
    prefix = os.path.realpath(prefix)
    return path == prefix or path.startswith(os.path.join(prefix, ""))
