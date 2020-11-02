# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging

import click

from octoprint.cli import get_ctx_obj_option, standard_options

click.disable_unicode_literals_warning = True


def get_systeminfo(environment_detector, connectivity_checker):
    from octoprint import __version__
    from octoprint.util import dict_flatten

    environment_detector.run_detection(notify_plugins=False)

    systeminfo = {
        "octoprint": {"version": __version__},
        "connectivity": connectivity_checker.as_dict(),
        "env": environment_detector.environment,
    }

    # flatten and filter
    flattened = dict_flatten(systeminfo)
    flattened["env.python.virtualenv"] = "env.python.virtualenv" in flattened

    return flattened


@click.group()
def systeminfo_commands():
    pass


@systeminfo_commands.command(name="systeminfo")
@standard_options()
@click.pass_context
def systeminfo_command(ctx, **kwargs):
    """Retrieves and prints the system info."""
    from octoprint import FatalStartupError, init_platform

    logging.disable(logging.ERROR)
    try:
        components = init_platform(
            get_ctx_obj_option(ctx, "basedir", None),
            get_ctx_obj_option(ctx, "configfile", None),
            safe_mode=True,
        )
    except FatalStartupError as e:
        click.echo(str(e), err=True)
        click.echo("There was a fatal error initializing the settings manager.", err=True)
        ctx.exit(-1)
    else:
        (
            settings,
            logger,
            safe_mode,
            event_manager,
            connectivity_checker,
            plugin_manager,
            environment_detector,
        ) = components
        systeminfo = get_systeminfo(environment_detector, connectivity_checker)

        for k in sorted(systeminfo.keys()):
            click.echo("{}: {}".format(k, systeminfo[k]))
