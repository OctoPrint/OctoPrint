"""Assets can be filtered through one or multiple filters, modifying their
contents (think minification, compression).
"""

from __future__ import with_statement

import os
import subprocess
import inspect
import shlex
import tempfile
from webassets import six
from webassets.six.moves import map
from webassets.six.moves import zip
try:
    frozenset
except NameError:
    from sets import ImmutableSet as frozenset
from webassets.exceptions import FilterError
from webassets.importlib import import_module
from webassets.utils import hash_func


__all__ = ('Filter', 'CallableFilter', 'get_filter', 'register_filter',
           'ExternalTool', 'JavaTool')


def freezedicts(obj):
    """Recursively iterate over ``obj``, supporting dicts, tuples
    and lists, and freeze ``dicts`` such that ``obj`` can be used
    with hash().
    """
    if isinstance(obj, (list, tuple)):
        return type(obj)([freezedicts(sub) for sub in obj])
    if isinstance(obj, dict):
        return frozenset(six.iteritems(obj))
    return obj


def smartsplit(string, sep):
    """Split while allowing escaping.

    So far, this seems to do what I expect - split at the separator,
    allow escaping via \, and allow the backslash itself to be escaped.

    One problem is that it can raise a ValueError when given a backslash
    without a character to escape. I'd really like a smart splitter
    without manually scan the string. But maybe that is exactly what should
    be done.
    """
    assert string is not None   # or shlex will read from stdin
    if not six.PY3:
        # On 2.6, shlex fails miserably with unicode input
        is_unicode = isinstance(string, unicode)
        if is_unicode:
            string = string.encode('utf8')
    l = shlex.shlex(string, posix=True)
    l.whitespace += ','
    l.whitespace_split = True
    l.quotes = ''
    if not six.PY3 and is_unicode:
        return map(lambda s: s.decode('utf8'), list(l))
    else:
        return list(l)


class option(tuple):
    """Micro option system. I want this to remain small and simple,
    which is why this class is lower-case.

    See ``parse_options()`` and ``Filter.options``.
    """
    def __new__(cls, initarg, configvar=None, type=None):
        # If only one argument given, it is the configvar
        if configvar is None:  
            configvar = initarg
            initarg = None
        return tuple.__new__(cls, (initarg, configvar, type))


def parse_options(options):
    """Parses the filter ``options`` dict attribute.
    The result is a dict of ``option`` tuples.
    """
    # Normalize different ways to specify the dict items:
    #    attribute: option()
    #    attribute: ('__init__ arg', 'config variable')
    #    attribute: ('config variable,')
    #    attribute: 'config variable'
    result = {}
    for internal, external in options.items():
        if not isinstance(external, option):
            if not isinstance(external, (list, tuple)):
                external = (external,)
            external = option(*external)
        result[internal] = external
    return result


class Filter(object):
    """Base class for a filter.

    Subclasses should allow the creation of an instance without any
    arguments, i.e. no required arguments for __init__(), so that the
    filter can be specified by name only. In fact, the taking of
    arguments will normally be the exception.
    """

    # Name by which this filter can be referred to.
    name = None

    # Options the filter supports. The base class will ensure that
    # these are both accepted by __init__ as kwargs, and may also be
    # defined in the environment config, or the OS environment (i.e.
    # a setup() implementation will be generated which uses
    # get_config() calls).
    #
    # Can look like this:
    #    options = {
    #        'binary': 'COMPASS_BINARY',
    #        'plugins': option('COMPASS_PLUGINS', type=list),
    #    }
    options = {}

    # The maximum debug level under which this filter should run.
    # Most filters only run in production mode (debug=False), so this is the
    # default value. However, a filter like ``cssrewrite`` needs to run in
    # ``merge`` mode. Further, compiler-type filters (like less/sass) would
    # say ``None``, indicating that they have to run **always**.
    # There is an interesting and convenient twist here: If you use such a
    # filter, the bundle will automatically be merged, even in debug mode.
    # It couldn't work any other way of course, the output needs to be written
    # somewhere. If you have other files that do not need compiling, and you
    # don't want them pulled into the merge, you can use a nested bundle with
    # it's own output target just for those files that need the compilation.
    max_debug_level = False

    def __init__(self, **kwargs):
        self.ctx = None
        self._options = parse_options(self.__class__.options)

        # Resolve options given directly to the filter. This
        # allows creating filter instances with options that
        # deviate from the global default.
        # TODO: can the metaclass generate a init signature?
        for attribute, (initarg, _, _) in self._options.items():
            arg = initarg if initarg is not None else attribute
            if arg in kwargs:
                setattr(self, attribute, kwargs.pop(arg))
            else:
                setattr(self, attribute, None)
        if kwargs:
            raise TypeError('got an unexpected keyword argument: %s' %
                            list(kwargs.keys())[0])

    def __eq__(self, other):
        if isinstance(other, Filter):
            return self.id() == other.id()
        return NotImplemented

    def set_context(self, ctx):
        """This is called before the filter is used."""
        self.ctx = ctx

    def get_config(self, setting=False, env=None, require=True,
                   what='dependency', type=None):
        """Helper function that subclasses can use if they have
        dependencies which they cannot automatically resolve, like
        an external binary.

        Using this function will give the user the ability to  resolve
        these dependencies in a common way through either a Django
        setting, or an environment variable.

        You may specify different names for ``setting`` and ``env``.
        If only the former is given, the latter is considered to use
        the same name. If either argument is ``False``, the respective
        source is not used.

        By default, if the value is not found, an error is raised. If
        ``required`` is ``False``, then ``None`` is returned instead.

        ``what`` is a string that is used in the exception message;
        you can use it to give the user an idea what he is lacking,
        i.e. 'xyz filter binary'.

        Specifying values via the OS environment is obviously limited. If
        you are expecting a special type, you may set the ``type`` argument
        and a value from the OS environment will be parsed into that type.
        Currently only ``list`` is supported.
        """
        assert type in (None, list), "%s not supported for type" % type

        if env is None:
            env = setting

        assert setting or env

        value = None
        if not setting is False:
            value = self.ctx.get(setting, None)

        if value is None and not env is False:
            value = os.environ.get(env)
            if value is not None:
                if not six.PY3:
                    # TODO: What charset should we use? What does Python 3 use?
                    value = value.decode('utf8')
                if type == list:
                    value = smartsplit(value, ',')

        if value is None and require:
            err_msg = '%s was not found. Define a ' % what
            options = []
            if setting:
                options.append('%s setting' % setting)
            if env:
                options.append('%s environment variable' % env)
            err_msg += ' or '.join(options)
            raise EnvironmentError(err_msg)
        return value

    def unique(self):
        """This function is used to determine if two filter instances
        represent the same filter and can be merged. Only one of the
        filters will be applied.

        If your filter takes options, you might want to override this
        and return a hashable object containing all the data unique
        to your current instance. This will allow your filter to be applied
        multiple times with differing values for those options.
        """
        return False

    def id(self):
        """Unique identifier for the filter instance.

        Among other things, this is used as part of the caching key.
        It should therefore not depend on instance data, but yield
        the same result across multiple python invocations.
        """
        # freezedicts() allows filters to return dict objects as part
        # of unique(), which are not per-se supported by hash().
        return hash_func((self.name, freezedicts(self.unique()),))

    def setup(self):
        """Overwrite this to have the filter do initial setup work,
        like determining whether required modules are available etc.

        Since this will only be called when the user actually
        attempts to use the filter, you can raise an error here if
        dependencies are not matched.

        Note: In most cases, it should be enough to simply define
        the ``options`` attribute. If you override this method and
        want to use options as well, don't forget to call super().

        Note: This may be called multiple times if one filter instance
        is used with different asset environment instances.
        """
        for attribute, (_, configvar, type) in self._options.items():
            if not configvar:
                continue
            if getattr(self, attribute) is None:
                # No value specified for this filter instance ,
                # specifically attempt to load it from the environment.
                setattr(self, attribute,
                        self.get_config(setting=configvar, require=False,
                                        type=type))

    def input(self, _in, out, **kw):
        """Implement your actual filter here.

        This will be called for every source file.
        """

    def output(self, _in, out, **kw):
        """Implement your actual filter here.

        This will be called for every output file.
        """

    def open(self, out, source_path, **kw):
        """Implement your actual filter here.

        This is like input(), but only one filter may provide this.
        Use this if your filter needs to read from the source file
        directly, and would ignore any processing by earlier filters.
        """

    def concat(self, out, hunks, **kw):
        """Implement your actual filter here.

       Will be called once between the input() and output()
       steps, and should concat all the source files (given as hunks)
       together, writing the result to the ``out`` stream.

       Only one such filter is allowed.
       """

    def get_additional_cache_keys(self, **kw):
        """Additional cache keys dependent on keyword arguments.

        If your filter's output is dependent on some or all of the
        keyword arguments, you can return these arguments here as a list.
        This will make sure the caching behavior is correct.

        For example, the CSSRewrite filter depends not only on the
        contents of the file it applies to, but also the output path
        of the final file. If the CSSRewrite filter doesn't correctly
        override this method, a certain output file with a certain base
        directory might potentially get a CSSRewriten file from cache
        that is meant for an output file in a different base directory.
        """

        return []

    # We just declared those for demonstration purposes
    del input
    del output
    del open
    del concat


class CallableFilter(Filter):
    """Helper class that create a simple filter wrapping around
    callable.
    """

    def __init__(self, callable):
        super(CallableFilter, self).__init__()
        self.callable = callable

    def unique(self):
        # XXX This means the cache will never work for those filters.
        # This is actually a deeper problem: Originally unique() was
        # used to remove duplicate filters. Now it is also for the cache
        # key. The latter would benefit from ALL the filter's options being
        # included. Possibly this might just be what we should do, at the
        # expense of the "remove duplicates" functionality (because it
        # is never really needed anyway). It's also illdefined when a filter
        # should be a removable duplicate - most options probably SHOULD make
        # a filter no longer being considered duplicate.
        return self.callable

    def output(self, _in, out, **kw):
        return self.callable(_in, out)


class ExternalToolMetaclass(type):
    def __new__(cls, name, bases, attrs):
        # First, determine the method defined for this very class. We
        # need to pop the ``method`` attribute from ``attrs``, so that we
        # create the class without the argument; allowing us then to look
        # at a ``method`` attribute that parents may have defined.
        #
        # method defaults to 'output' if argv is set, to "implement
        # no default method" without an argv.
        if not 'method' in attrs and 'argv' in attrs:
            chosen = 'output'
        else:
            chosen = attrs.pop('method', False)

        # Create the class first, since this helps us look at any
        # method attributes defined in the parent hierarchy.
        klass = type.__new__(cls, name, bases, attrs)
        parent_method = getattr(klass, 'method', None)

        # Assign the method argument that we initially popped again.
        klass.method = chosen

        try:
            # Don't do anything for this class itself
            ExternalTool
        except NameError:
            return klass

        # If the class already has a method attribute, this indicates
        # that a parent class already dealt with it and enabled/disabled
        # the methods, and we won't again.
        if parent_method is not None:
            return klass

        methods = ('output', 'input', 'open')

        if chosen is not None:
            assert not chosen or chosen in methods, \
                '%s not a supported filter method' % chosen
            # Disable those methods not chosen.
            for m in methods:
                if m != chosen:
                    # setdefault = Don't override actual methods the
                    # class has in fact provided itself.
                    if not m in klass.__dict__:
                        setattr(klass, m, None)

        return klass


class ExternalTool(six.with_metaclass(ExternalToolMetaclass, Filter)):
    """Subclass that helps creating filters that need to run an external
    program.

    You are encouraged to use this when possible, as it helps consistency.

    In the simplest possible case, subclasses only have to define one or more
    of the following attributes, without needing to write any code:

    ``argv``
       The command line that will be passed to subprocess.Popen. New-style
       format strings can be used to access all kinds of data: The arguments
       to the filter method, as well as the filter instance via ``self``:

            argv = ['{self.binary}', '--input', '{source_path}', '--cwd',
                    '{self.env.directory}']

    ``method``
        The filter method to implement. One of ``input``, ``output`` or
        ``open``.
    """

    argv = []
    method = None

    def open(self, out, source_path, **kw):
        self._evaluate([out, source_path], kw, out)

    def input(self, _in, out, **kw):
        self._evaluate([_in, out], kw, out, _in)

    def output(self, _in, out, **kw):
        self._evaluate([_in, out], kw, out, _in)

    def _evaluate(self, args, kwargs, out, data=None):
        # For now, still support Python 2.5, but the format strings in argv
        # are not supported (making the feature mostly useless). For this
        # reason none of the builtin filters is using argv currently.
        if hasattr(str, 'format'):
            # Add 'self' to the keywords available in format strings
            kwargs = kwargs.copy()
            kwargs.update({'self': self})

            # Resolve all the format strings in argv
            def replace(arg):
                try:
                    return arg.format(*args, **kwargs)
                except KeyError as e:
                    # Treat "output" and "input" variables special, they
                    # are dealt with in :meth:`subprocess` instead.
                    if e.args[0] not in ('input', 'output'):
                        raise
                    return arg
            argv = list(map(replace, self.argv))
        else:
            argv = self.argv
        self.subprocess(argv, out, data=data)

    @classmethod
    def subprocess(cls, argv, out, data=None):
        """Execute the commandline given by the list in ``argv``.

        If a byestring is given via ``data``, it is piped into data.

        ``argv`` may contain two placeholders:

        ``{input}``
            If given, ``data`` will be written to a temporary file instead
            of data. The placeholder is then replaced with that file.

        ``{output}``
            Will be replaced by a temporary filename. The return value then
            will be the content of this file, rather than stdout.
        """

        class tempfile_on_demand(object):
            def __repr__(self):
                if not hasattr(self, 'filename'):
                    fd, self.filename = tempfile.mkstemp()
                    os.close(fd)
                return self.filename

            @property
            def created(self):
                return hasattr(self, 'filename')

        # Replace input and output placeholders
        input_file = tempfile_on_demand()
        output_file = tempfile_on_demand()
        if hasattr(str, 'format'):   # Support Python 2.5 without the feature
            argv = list(map(lambda item:
                       item.format(input=input_file, output=output_file), argv))

        try:
            data = (data.read() if hasattr(data, 'read') else data)
            if data is not None:
                data = data.encode('utf-8')

            if input_file.created:
                if data is None:
                    raise ValueError(
                        '{input} placeholder given, but no data passed')
                with open(input_file.filename, 'wb') as f:
                    f.write(data)
                    # No longer pass to stdin
                    data = None
            try:
                proc = subprocess.Popen(
                    argv,
                    # we cannot use the in/out streams directly, as they might be
                    # StringIO objects (which are not supported by subprocess)
                    stdout=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=os.name == 'nt')
            except OSError:
                raise FilterError('Program file not found: %s.' % argv[0])
            stdout, stderr = proc.communicate(data)
            if proc.returncode:
                raise FilterError(
                    '%s: subprocess returned a non-success result code: '
                    '%s, stdout=%s, stderr=%s' % (
                        cls.name or cls.__name__, 
                        proc.returncode, stdout, stderr))
            else:
                if output_file.created:
                    with open(output_file.filename, 'rb') as f:
                        out.write(f.read().decode('utf-8'))
                else:
                    out.write(stdout.decode('utf-8'))
        finally:
            if output_file.created:
                os.unlink(output_file.filename)
            if input_file.created:
                os.unlink(input_file.filename)


class JavaTool(ExternalTool):
    """Helper class for filters which are implemented as Java ARchives (JARs).

    The subclass is expected to define a ``jar`` attribute in :meth:`setup`.

    If the ``argv`` definition is used, it is expected to contain only the
    arguments to be passed to the Java tool. The path to the java binary and
    the jar file are added by the base class.
    """

    method = None

    def setup(self):
        super(JavaTool, self).setup()

        # We can reasonably expect that java is just on the path, so
        # don't require it, but hope for the best.
        path = self.get_config(env='JAVA_HOME', require=False)
        if path is not None:
            self.java_bin = os.path.join(path, 'bin/java')
        else:
            self.java_bin = 'java'

    def subprocess(self, args, out, data=None):
        ExternalTool.subprocess(
            [self.java_bin, '-jar', self.jar] + args, out, data)


_FILTERS = {}


def register_filter(f):
    """Add the given filter to the list of know filters.
    """
    if not issubclass(f, Filter):
        raise ValueError("Must be a subclass of 'Filter'")
    if not f.name:
        raise ValueError('Must have a name')
    _FILTERS[f.name] = f


def get_filter(f, *args, **kwargs):
    """Resolves ``f`` to a filter instance.

    Different ways of specifying a filter are supported, for example by
    giving the class, or a filter name.

    *args and **kwargs are passed along to the filter when it's
    instantiated.
    """
    if isinstance(f, Filter):
        # Don't need to do anything.
        assert not args and not kwargs
        return f
    elif isinstance(f, six.string_types):
        if f in _FILTERS:
            klass = _FILTERS[f]
        else:
            raise ValueError('No filter \'%s\'' % f)
    elif inspect.isclass(f) and issubclass(f, Filter):
        klass = f
    elif callable(f):
        assert not args and not kwargs
        return CallableFilter(f)
    else:
        raise ValueError('Unable to resolve to a filter: %s' % f)

    return klass(*args, **kwargs)

CODE_FILES = ['.py', '.pyc', '.so']


def is_module(name):
    """Is this a recognized module type?
    
    Does this name end in one of the recognized CODE_FILES extensions?
    
    The file is assumed to exist, as unique_modules has found it using 
    an os.listdir() call.
    
    returns the name with the extension stripped (the module name) or 
        None if the name does not appear to be a module
    """
    for ext in CODE_FILES:
        if name.endswith(ext):
            return name[:-len(ext)]


def is_package(directory):
    """Is the (fully qualified) directory a python package?
    
    """
    for ext in ['.py', '.pyc']:
        if os.path.exists(os.path.join(directory, '__init__'+ext)):
            return True 


def unique_modules(directory):
    """Find all unique module names within a directory 
    
    For each entry in the directory, check if it is a source 
    code file-type (using is_code(entry)), or a directory with 
    a source-code file-type at entry/__init__.py[c]?
    
    Filter the results to only produce a single entry for each 
    module name.
    
    Filter the results to not include '_' prefixed names.
    
    yields each entry as it is encountered
    """
    found = {}
    for entry in sorted(os.listdir(directory)):
        if entry.startswith('_'):
            continue 
        module = is_module(entry)
        if module:
            if module not in found:
                found[module] = entry
                yield module
        elif is_package(os.path.join(directory, entry)):
            if entry not in found:
                found[entry] = entry 
                yield entry 


def load_builtin_filters():
    from os import path
    import warnings

    current_dir = path.dirname(__file__)
    for name in unique_modules(current_dir):

        module_name = 'webassets.filter.%s' % name
        try:
            module = import_module(module_name)
        except Exception as e:
            warnings.warn('Error while loading builtin filter '
                          'module \'%s\': %s' % (module_name, e))
        else:
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if inspect.isclass(attr) and issubclass(attr, Filter):
                    if not attr.name:
                        # Skip if filter has no name; those are
                        # considered abstract base classes.
                        continue
                    register_filter(attr)
load_builtin_filters()
