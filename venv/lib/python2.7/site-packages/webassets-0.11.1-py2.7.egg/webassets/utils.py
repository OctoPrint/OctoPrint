from webassets import six
import contextlib
import os
import sys
import re
from itertools import takewhile

from .exceptions import BundleError


__all__ = ('md5_constructor', 'pickle', 'set', 'StringIO',
           'common_path_prefix', 'working_directory', 'is_url')


if sys.version_info >= (2, 5):
    import hashlib
    md5_constructor = hashlib.md5
else:
    import md5
    md5_constructor = md5.new


try:
    import cPickle as pickle
except ImportError:
    import pickle


try:
    set
except NameError:
    from sets import Set as set
else:
    set = set


from webassets.six import StringIO


try:
    from urllib import parse as urlparse
except ImportError:     # Python 2
    import urlparse
    import urllib

def hash_func(data):
    from .cache import make_md5
    return make_md5(data)


_directory_separator_re = re.compile(r"[/\\]+")


def common_path_prefix(paths, sep=os.path.sep):
    """os.path.commonpath() is completely in the wrong place; it's
    useless with paths since it only looks at one character at a time,
    see http://bugs.python.org/issue10395

    This replacement is from:
        http://rosettacode.org/wiki/Find_Common_Directory_Path#Python
    """
    def allnamesequal(name):
        return all(n==name[0] for n in name[1:])

    # The regex splits the paths on both / and \ characters, whereas the
    # rosettacode.org algorithm only uses os.path.sep
    bydirectorylevels = zip(*[_directory_separator_re.split(p) for p in paths])
    return sep.join(x[0] for x in takewhile(allnamesequal, bydirectorylevels))


@contextlib.contextmanager
def working_directory(directory=None, filename=None):
    """A context manager which changes the working directory to the given
    path, and then changes it back to its previous value on exit.

    Filters will often find this helpful.

    Instead of a ``directory``, you may also give a ``filename``, and the
    working directory will be set to the directory that file is in.s
    """
    assert bool(directory) != bool(filename)   # xor
    if not directory:
        directory = os.path.dirname(filename)
    prev_cwd = os.getcwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def make_option_resolver(clazz=None, attribute=None, classes=None,
                         allow_none=True, desc=None):
    """Returns a function which can resolve an option to an object.

    The option may given as an instance or a class (of ``clazz``, or
    duck-typed with an attribute ``attribute``), or a string value referring
    to a class as defined by the registry in ``classes``.

    This support arguments, so an option may look like this:

        cache:/tmp/cachedir

    If this must instantiate a class, it will pass such an argument along,
    if given. In addition, if the class to be instantiated has a classmethod
    ``make()``, this method will be used as a factory, and will be given an
    Environment object (if one has been passed to the resolver). This allows
    classes that need it to initialize themselves based on an Environment.
    """
    assert clazz or attribute or classes
    desc_string = ' to %s' % desc if desc else None

    def instantiate(clazz, env, *a, **kw):
        # Create an instance of clazz, via the Factory if one is defined,
        # passing along the Environment, or creating the class directly.
        if hasattr(clazz, 'make'):
            # make() protocol is that if e.g. the get_manifest() resolver takes
            # an env, then the first argument of the factory is the env.
            args = (env,) + a if env is not None else a
            return clazz.make(*args, **kw)
        return clazz(*a, **kw)

    def resolve_option(option, env=None):
        the_clazz = clazz() if callable(clazz) and not isinstance(option, type) else clazz

        if not option and allow_none:
            return None

        # If the value has one of the support attributes (duck-typing).
        if attribute and hasattr(option, attribute):
            if isinstance(option, type):
                return instantiate(option, env)
            return option

        # If it is the class we support.
        if the_clazz and isinstance(option, the_clazz):
            return option
        elif isinstance(option, type) and issubclass(option, the_clazz):
            return instantiate(option, env)

        # If it is a string
        elif isinstance(option, six.string_types):
            parts = option.split(':', 1)
            key = parts[0]
            arg = parts[1] if len(parts) > 1 else None
            if key in classes:
                return instantiate(classes[key], env, *([arg] if arg else []))

        raise ValueError('%s cannot be resolved%s' % (option, desc_string))
    resolve_option.__doc__ = """Resolve ``option``%s.""" % desc_string

    return resolve_option


def RegistryMetaclass(clazz=None, attribute=None, allow_none=True, desc=None):
    """Returns a metaclass which will keep a registry of all subclasses, keyed
    by their ``id`` attribute.

    The metaclass will also have a ``resolve`` method which can turn a string
    into an instance of one of the classes (based on ``make_option_resolver``).
    """
    def eq(self, other):
        """Return equality with config values that instantiate this."""
        return (hasattr(self, 'id') and self.id == other) or\
               id(self) == id(other)
    def unicode(self):
        return "%s" % (self.id if hasattr(self, 'id') else repr(self))

    class Metaclass(type):
        REGISTRY = {}

        def __new__(mcs, name, bases, attrs):
            if not '__eq__' in attrs:
                attrs['__eq__'] = eq
            if not '__unicode__' in attrs:
                attrs['__unicode__'] = unicode
            if not '__str__' in attrs:
                attrs['__str__'] = unicode
            new_klass = type.__new__(mcs, name, bases, attrs)
            if hasattr(new_klass, 'id'):
                mcs.REGISTRY[new_klass.id] = new_klass
            return new_klass

        resolve = staticmethod(make_option_resolver(
            clazz=clazz,
            attribute=attribute,
            allow_none=allow_none,
            desc=desc,
            classes=REGISTRY
        ))
    return Metaclass


def cmp_debug_levels(level1, level2):
    """cmp() for debug levels, returns True if ``level1`` is higher
    than ``level2``."""
    level_ints = {False: 0, 'merge': 1, True: 2}
    try:
        cmp = lambda a, b: (a > b) - (a < b)  # 333
        return cmp(level_ints[level1], level_ints[level2])
    except KeyError as e:
        # Not sure if a dependency on BundleError is proper here. Validating
        # debug values should probably be done on assign. But because this
        # needs to happen in two places (Environment and Bundle) we do it here.
        raise BundleError('Invalid debug value: %s' % e)


def is_url(s):
    if not isinstance(s, str):
        return False
    parsed = urlparse.urlsplit(s)
    return bool(parsed.scheme and parsed.netloc) and len(parsed.scheme) > 1
