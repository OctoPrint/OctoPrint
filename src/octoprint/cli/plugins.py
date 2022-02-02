__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging
import logging.config

import click

from octoprint.cli import OctoPrintContext, get_ctx_obj_option, pass_octoprint_ctx
from octoprint.util import dict_merge

click.disable_unicode_literals_warning = True
LOGGING_CONFIG = {
    "version": 1,
    "formatters": {"brief": {"format": "%(message)s"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "brief",
            "stream": "ext://sys.stdout",
        }
    },
    "loggers": {"octoprint.plugin.core": {"level": logging.ERROR}},
    "root": {"level": logging.WARNING},
}

# ~~ "octoprint plugin:command" commands


class OctoPrintPluginCommands(click.MultiCommand):
    """
    Custom `click.MultiCommand <http://click.pocoo.org/5/api/#click.MultiCommand>`_
    implementation that collects commands from the plugin hook
    :ref:`octoprint.cli.commands <sec-plugins-hook-cli-commands>`.

    .. attribute:: settings

       The global :class:`~octoprint.settings.Settings` instance.

    .. attribute:: plugin_manager

       The :class:`~octoprint.plugin.core.PluginManager` instance.
    """

    sep = ":"

    def __init__(self, *args, **kwargs):
        click.MultiCommand.__init__(self, *args, **kwargs)

        self.settings = None
        self.plugin_manager = None
        self.hooks = {}

        self._logger = logging.getLogger(__name__)
        self._initialized = False

    def _initialize(self, ctx):
        if self._initialized:
            return

        click.echo("Initializing settings & plugin subsystem...")
        if ctx.obj is None:
            ctx.obj = OctoPrintContext()

        logging_config = dict_merge(
            LOGGING_CONFIG,
            {
                "root": {
                    "level": logging.DEBUG if ctx.obj.verbosity > 0 else logging.WARNING
                }
            },
        )
        logging.config.dictConfig(logging_config)

        # initialize settings and plugin manager based on provided
        # context (basedir and configfile)
        from octoprint import FatalStartupError, init_pluginsystem, init_settings

        try:
            self.settings = init_settings(
                get_ctx_obj_option(ctx, "basedir", None),
                get_ctx_obj_option(ctx, "configfile", None),
                overlays=get_ctx_obj_option(ctx, "overlays", None),
            )
            self.plugin_manager = init_pluginsystem(
                self.settings, safe_mode=get_ctx_obj_option(ctx, "safe_mode", False)
            )
        except FatalStartupError as e:
            click.echo(str(e), err=True)
            click.echo(
                "There was a fatal error initializing the settings or the plugin system.",
                err=True,
            )
            ctx.exit(-1)

        # fetch registered hooks
        self.hooks = self.plugin_manager.get_hooks("octoprint.cli.commands")

        self._initialized = True

    def list_commands(self, ctx):
        self._initialize(ctx)
        result = [name for name in self._get_commands()]
        result.sort()
        return result

    def get_command(self, ctx, cmd_name):
        self._initialize(ctx)
        commands = self._get_commands()
        return commands.get(cmd_name, None)

    def _get_commands(self):
        """Fetch all commands from plugins providing any."""

        import collections

        result = collections.OrderedDict()

        for name, hook in self.hooks.items():
            try:
                commands = hook(self, pass_octoprint_ctx)
                for command in commands:
                    if not isinstance(command, click.Command):
                        self._logger.warning(
                            "Plugin {} provided invalid CLI command, ignoring it: {!r}".format(
                                name, command
                            )
                        )
                        continue
                    result[name + self.sep + command.name] = command
            except Exception:
                self._logger.exception(
                    f"Error while retrieving cli commands for plugin {name}",
                    extra={"plugin": name},
                )

        return result


@click.group(cls=OctoPrintPluginCommands)
@pass_octoprint_ctx
def cli(obj):
    """Additional commands provided by plugins."""
    pass
