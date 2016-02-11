from __future__ import print_function
import shutil
import os, sys
import time
import logging

from webassets.loaders import PythonLoader, YAMLLoader
from webassets.bundle import get_all_bundle_files
from webassets.exceptions import BuildError
from webassets.updater import TimestampUpdater
from webassets.merge import MemoryHunk
from webassets.version import get_manifest
from webassets.cache import FilesystemCache
from webassets.utils import set, StringIO


__all__ = ('CommandError', 'CommandLineEnvironment', 'main')


# logging has WARNING as default level, for the CLI we want INFO. Set this
# as early as possible, so that user customizations will not be overwritten.
logging.getLogger('webassets.script').setLevel(logging.INFO)


class CommandError(Exception):
    pass


class Command(object):
    """Base-class for a command used by :class:`CommandLineEnvironment`.

    Each command being a class opens up certain possibilities with respect to
    subclassing and customizing the default CLI.
    """

    def __init__(self, cmd_env):
        self.cmd = cmd_env

    def __getattr__(self, name):
        # Make stuff from cmd environment easier to access
        return getattr(self.cmd, name)

    def __call__(self, *args, **kwargs):
        raise NotImplementedError()


class BuildCommand(Command):

    def __call__(self, bundles=None, output=None, directory=None, no_cache=None,
              manifest=None, production=None):
        """Build assets.

        ``bundles``
            A list of bundle names. If given, only this list of bundles
            should be built.

        ``output``
            List of (bundle, filename) 2-tuples. If given, only these
            bundles will be built, using the custom output filenames.
            Cannot be used with ``bundles``.

        ``directory``
            Custom output directory to use for the bundles. The original
            basenames defined in the bundle ``output`` attribute will be
            used. If the ``output`` of the bundles are pointing to different
            directories, they will be offset by their common prefix.
            Cannot be used with ``output``.

        ``no_cache``
            If set, a cache (if one is configured) will not be used.

        ``manifest``
            If set, the given manifest instance will be used, instead of
            any that might have been configured in the Environment. The value
            passed will be resolved through ``get_manifest()``. If this fails,
            a file-based manifest will be used using the given value as the
            filename.

        ``production``
            If set to ``True``, then :attr:`Environment.debug`` will forcibly
            be disabled (set to ``False``) during the build.
        """

        # Validate arguments
        if bundles and output:
            raise CommandError(
                'When specifying explicit output filenames you must '
                'do so for all bundles you want to build.')
        if directory and output:
            raise CommandError('A custom output directory cannot be '
                               'combined with explicit output filenames '
                               'for individual bundles.')

        if production:
            # TODO: Reset again (refactor commands to be classes)
            self.environment.debug = False

        # TODO: Oh how nice it would be to use the future options stack.
        if manifest is not None:
            try:
                manifest = get_manifest(manifest, env=self.environment)
            except ValueError:
                manifest = get_manifest(
                    # abspath() is important, or this will be considered
                    # relative to Environment.directory.
                    "file:%s" % os.path.abspath(manifest),
                    env=self.environment)
            self.environment.manifest = manifest

        # Use output as a dict.
        if output:
            output = dict(output)

        # Validate bundle names
        bundle_names = bundles if bundles else (output.keys() if output else [])
        for name in bundle_names:
            if not name in self.environment:
                raise CommandError(
                    'I do not know a bundle name named "%s".' % name)

        # Make a list of bundles to build, and the filename to write to.
        if bundle_names:
            # TODO: It's not ok to use an internal property here.
            bundles = [(n,b) for n, b in self.environment._named_bundles.items()
                             if n in bundle_names]
        else:
            # Includes unnamed bundles as well.
            bundles = [(None, b) for b in self.environment]

        # Determine common prefix for use with ``directory`` option.
        if directory:
            prefix = os.path.commonprefix(
                [os.path.normpath(b.resolve_output())
                 for _, b in bundles if b.output])
            # dirname() gives the right value for a single file.
            prefix = os.path.dirname(prefix)

        to_build = []
        for name, bundle in bundles:
            # TODO: We really should support this. This error here
            # is just in place of a less understandable error that would
            # otherwise occur.
            if bundle.is_container and directory:
                raise CommandError(
                    'A custom output directory cannot currently be '
                    'used with container bundles.')

            # Determine which filename to use, if not the default.
            overwrite_filename = None
            if output:
                overwrite_filename = output[name]
            elif directory:
                offset = os.path.normpath(
                    bundle.resolve_output())[len(prefix)+1:]
                overwrite_filename = os.path.join(directory, offset)
            to_build.append((bundle, overwrite_filename, name,))

        # Build.
        built = []
        for bundle, overwrite_filename, name in to_build:
            if name:
                # A name is not necessary available of the bundle was
                # registered without one.
                self.log.info("Building bundle: %s (to %s)" % (
                    name, overwrite_filename or bundle.output))
            else:
                self.log.info("Building bundle: %s" % bundle.output)

            try:
                if not overwrite_filename:
                    with bundle.bind(self.environment):
                        bundle.build(force=True, disable_cache=no_cache)
                else:
                    # TODO: Rethink how we deal with container bundles here.
                    # As it currently stands, we write all child bundles
                    # to the target output, merged (which is also why we
                    # create and force writing to a StringIO instead of just
                    # using the ``Hunk`` objects that build() would return
                    # anyway.
                    output = StringIO()
                    with bundle.bind(self.environment):
                        bundle.build(force=True, output=output,
                            disable_cache=no_cache)
                    if directory:
                        # Only auto-create directories in this mode.
                        output_dir = os.path.dirname(overwrite_filename)
                        if not os.path.exists(output_dir):
                            os.makedirs(output_dir)
                    MemoryHunk(output.getvalue()).save(overwrite_filename)
                built.append(bundle)
            except BuildError as e:
                self.log.error("Failed, error was: %s" % e)
        if len(built):
            self.event_handlers['post_build']()
        if len(built) != len(to_build):
            return 2


class WatchCommand(Command):

    def __call__(self, loop=None):
        """Watch assets for changes.

        ``loop``
            A callback, taking no arguments, to be called once every loop
            iteration. Can be useful to integrate the command with other code.
            If not specified, the loop wil call ``time.sleep()``.
        """
        # TODO: This should probably also restart when the code changes.
        mtimes = {}

        try:
            # Before starting to watch for changes, also recognize changes
            # made while we did not run, and apply those immediately.
            for bundle in self.environment:
                print('Bringing up to date: %s' % bundle.output)
                bundle.build(force=False)

            self.log.info("Watching %d bundles for changes..." %
                          len(self.environment))

            while True:
                changed_bundles = self.check_for_changes(mtimes)

                built = []
                for bundle in changed_bundles:
                    print("Building bundle: %s ..." % bundle.output, end=' ')
                    sys.stdout.flush()
                    try:
                        bundle.build(force=True)
                        built.append(bundle)
                    except BuildError as e:
                        print("")
                        print("Failed: %s" % e)
                    else:
                        print("done")

                if len(built):
                    self.event_handlers['post_build']()

                do_end = loop() if loop else time.sleep(0.1)
                if do_end:
                    break
        except KeyboardInterrupt:
            pass

    def check_for_changes(self, mtimes):
        # Do not update original mtimes dict right away, so that we detect
        # all bundle changes if a file is in multiple bundles.
        _new_mtimes = mtimes.copy()

        changed_bundles = set()
        # TODO: An optimization was lost here, skipping a bundle once
        # a single file has been found to have changed. Bring back.
        for filename, bundles_to_update in self.yield_files_to_watch():
            stat = os.stat(filename)
            mtime = stat.st_mtime
            if sys.platform == "win32":
                mtime -= stat.st_ctime

            if mtimes.get(filename, mtime) != mtime:
                if callable(bundles_to_update):
                    # Hook for when file has changed
                    try:
                        bundles_to_update = bundles_to_update()
                    except EnvironmentError:
                        # EnvironmentError is what the hooks is allowed to
                        # raise for a temporary problem, like an invalid config
                        import traceback
                        traceback.print_exc()
                        # Don't update anything, wait for another change
                        bundles_to_update = set()

                if bundles_to_update is True:
                    # Indicates all bundles should be rebuilt for the change
                    bundles_to_update = set(self.environment)
                changed_bundles |= bundles_to_update
                _new_mtimes[filename] = mtime
            _new_mtimes[filename] = mtime

        mtimes.update(_new_mtimes)
        return changed_bundles

    def yield_files_to_watch(self):
        for bundle in self.environment:
            for filename in get_all_bundle_files(bundle):
                yield filename, set([bundle])


class CleanCommand(Command):

    def __call__(self):
        """Delete generated assets.
        """
        self.log.info('Cleaning generated assets...')
        for bundle in self.environment:
            if not bundle.output:
                continue
            file_path = bundle.resolve_output(self.environment)
            if os.path.exists(file_path):
                os.unlink(file_path)
                self.log.info("Deleted asset: %s" % bundle.output)
        if isinstance(self.environment.cache, FilesystemCache):
            shutil.rmtree(self.environment.cache.directory)


class CheckCommand(Command):

    def __call__(self):
        """Check to see if assets need to be rebuilt.

        A non-zero exit status will be returned if any of the input files are
        newer (based on mtime) than their output file. This is intended to be
        used in pre-commit hooks.
        """
        needsupdate = False
        updater = self.environment.updater
        if not updater:
            self.log.debug('no updater configured, using TimestampUpdater')
            updater = TimestampUpdater()
        for bundle in self.environment:
            self.log.info('Checking asset: %s', bundle.output)
            if updater.needs_rebuild(bundle, self.environment):
                self.log.info('  needs update')
                needsupdate = True
        if needsupdate:
            sys.exit(-1)


class CommandLineEnvironment(object):
    """Implements the core functionality for a command line frontend to
    ``webassets``, abstracted in a way to allow frameworks to integrate the
    functionality into their own tools, for example, as a Django management
    command, or a command for ``Flask-Script``.
    """

    def __init__(self, env, log, post_build=None, commands=None):
        self.environment = env
        self.log = log
        self.event_handlers = dict(post_build=lambda: True)
        if callable(post_build):
            self.event_handlers['post_build'] = post_build

        # Instantiate each command
        command_def = self.DefaultCommands.copy()
        command_def.update(commands or {})
        self.commands = {}
        for name, construct in command_def.items():
            if not construct:
                continue
            if not isinstance(construct, (list, tuple)):
                construct = [construct, (), {}]
            self.commands[name] = construct[0](
                self, *construct[1], **construct[2])

    def __getattr__(self, item):
        # Allow method-like access to commands.
        if item in self.commands:
            return self.commands[item]
        raise AttributeError(item)

    def invoke(self, command, args):
        """Invoke ``command``, or throw a CommandError.

        This is essentially a simple validation mechanism. Feel free
        to call the individual command methods manually.
        """
        try:
            function = self.commands[command]
        except KeyError as e:
            raise CommandError('unknown command: %s' % e)
        else:
            return function(**args)

    # List of commands installed
    DefaultCommands = {
        'build': BuildCommand,
        'watch': WatchCommand,
        'clean': CleanCommand,
        'check': CheckCommand
    }


class GenericArgparseImplementation(object):
    """Generic command line utility to interact with an webassets environment.

    This is effectively a reference implementation of a command line utility
    based on the ``CommandLineEnvironment`` class. Implementers may find it
    feasible to simple base their own command line utility on this, rather than
    implementing something custom on top of ``CommandLineEnvironment``. In
    fact, if that is possible, you are encouraged to do so for greater
    consistency across implementations.
    """

    class WatchCommand(WatchCommand):
        """Extended watch command that also looks at the config file itself."""

        def __init__(self, cmd_env, argparse_ns):
            WatchCommand.__init__(self, cmd_env)
            self.ns = argparse_ns

        def yield_files_to_watch(self):
            for result in WatchCommand.yield_files_to_watch(self):
                yield result
            # If the config changes, rebuild all bundles
            if getattr(self.ns, 'config', None):
                yield self.ns.config, self.reload_config

        def reload_config(self):
            try:
                self.cmd.environment = YAMLLoader(self.ns.config).load_environment()
            except Exception as e:
                raise EnvironmentError(e)
            return True


    def __init__(self, env=None, log=None, prog=None, no_global_options=False):
        try:
            import argparse
        except ImportError:
            raise RuntimeError(
                'The webassets command line now requires the '
                '"argparse" library on Python versions <= 2.6.')
        else:
            self.argparse = argparse
        self.env = env
        self.log = log
        self._construct_parser(prog, no_global_options)

    def _construct_parser(self, prog=None, no_global_options=False):
        self.parser = parser = self.argparse.ArgumentParser(
            description="Manage assets.",
            prog=prog)

        if not no_global_options:
            # Start with the base arguments that are valid for any command.
            # XXX: Add those to the subparser?
            parser.add_argument("-v", dest="verbose", action="store_true",
                help="be verbose")
            parser.add_argument("-q", action="store_true", dest="quiet",
                help="be quiet")
            if self.env is None:
                loadenv = parser.add_mutually_exclusive_group()
                loadenv.add_argument("-c", "--config", dest="config",
                    help="read environment from a YAML file")
                loadenv.add_argument("-m", "--module", dest="module",
                    help="read environment from a Python module")

        # Add subparsers.
        subparsers = parser.add_subparsers(dest='command')
        for command in CommandLineEnvironment.DefaultCommands.keys():
            command_parser = subparsers.add_parser(command)
            maker = getattr(self, 'make_%s_parser' % command, False)
            if maker:
                maker(command_parser)

    @staticmethod
    def make_build_parser(parser):
        parser.add_argument(
            'bundles', nargs='*', metavar='BUNDLE',
            help='Optional bundle names to process. If none are '
                 'specified, then all known bundles will be built.')
        parser.add_argument(
            '--output', '-o', nargs=2, action='append',
            metavar=('BUNDLE', 'FILE'),
            help='Build the given bundle, and use a custom output '
                 'file. Can be given multiple times.')
        parser.add_argument(
            '--directory', '-d',
            help='Write built files to this directory, using the '
                 'basename defined by the bundle. Will offset '
                 'the original bundle output paths on their common '
                 'prefix. Cannot be used with --output.')
        parser.add_argument(
            '--no-cache', action='store_true',
            help='Do not use a cache that might be configured.')
        parser.add_argument(
            '--manifest',
            help='Write a manifest to the given file. Also supports '
                 'the id:arg format, if you want to use a different '
                 'manifest implementation.')
        parser.add_argument(
            '--production', action='store_true',
            help='Forcably turn off debug mode for the build. This '
                 'only has an effect if debug is set to "merge".')

    def _setup_logging(self, ns):
        if self.log:
            log = self.log
        else:
            log = logging.getLogger('webassets.script')
            if not log.handlers:
                # In theory, this could run multiple times (e.g. tests)
                handler = logging.StreamHandler()
                log.addHandler(handler)
                # Note that setting the level filter at the handler level is
                # better than the logger level, since this is "our" handler,
                # we create it, for the purposes of having a default output.
                # The logger itself the user may be modifying.
                handler.setLevel(logging.DEBUG if ns.verbose else (
                    logging.WARNING if ns.quiet else logging.INFO))
        return log

    def _setup_assets_env(self, ns, log):
        env = self.env
        if env is None:
            assert not (ns.module and ns.config)
            if ns.module:
                env = PythonLoader(ns.module).load_environment()
            if ns.config:
                env = YAMLLoader(ns.config).load_environment()
        return env

    def _setup_cmd_env(self, assets_env, log, ns):
        return CommandLineEnvironment(assets_env, log, commands={
            'watch': (GenericArgparseImplementation.WatchCommand, (ns,), {})
        })

    def _prepare_command_args(self, ns):
        # Prepare a dict of arguments cleaned of values that are not
        # command-specific, and which the command method would not accept.
        args = vars(ns).copy()
        for action in self.parser._actions:
            dest = action.dest
            if dest in args:
                del args[dest]
        return args

    def run_with_ns(self, ns):
        log = self._setup_logging(ns)
        env = self._setup_assets_env(ns, log)
        if env is None:
            raise CommandError(
                "Error: No environment given or found. Maybe use -m?")
        cmd = self._setup_cmd_env(env, log, ns)

        # Run the selected command
        args = self._prepare_command_args(ns)
        return cmd.invoke(ns.command, args)

    def run_with_argv(self, argv):
        try:
            ns = self.parser.parse_args(argv)
        except SystemExit as e:
            # We do not want the main() function to exit the program.
            # See run() instead.
            return e.args[0]

        return self.run_with_ns(ns)

    def main(self, argv):
        """Parse the given command line.

        The commandline is expected to NOT including what would be sys.argv[0].
        """
        try:
            return self.run_with_argv(argv)
        except CommandError as e:
            print(e)
            return 1


def main(argv, env=None):
    """Execute the generic version of the command line interface.

    You only need to work directly with ``GenericArgparseImplementation`` if
    you desire to customize things.

    If no environment is given, additional arguments will be supported to allow
    the user to specify/construct the environment on the command line.
    """
    return GenericArgparseImplementation(env).main(argv)


def run():
    """Runs the command line interface via ``main``, then exits the process
    with a proper return code."""
    sys.exit(main(sys.argv[1:]) or 0)


if __name__ == '__main__':
    run()
