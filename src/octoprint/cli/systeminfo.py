# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging
import os

import click
import zipstream

from octoprint.cli import init_platform_for_cli, standard_options

click.disable_unicode_literals_warning = True


def get_systeminfo(environment_detector, connectivity_checker, additional_fields=None):
    from octoprint import __version__
    from octoprint.util import dict_flatten

    if additional_fields is None:
        additional_fields = {}

    environment_detector.run_detection(notify_plugins=False)

    systeminfo = {
        "octoprint": {"version": __version__},
        "connectivity": connectivity_checker.as_dict(),
        "env": environment_detector.environment,
    }

    # flatten and filter
    flattened = dict_flatten(systeminfo)
    flattened["env.python.virtualenv"] = "env.python.virtualenv" in flattened

    for k, v in additional_fields.items():
        if k not in flattened:
            flattened[k] = v

    return flattened


def get_systeminfo_bundle(systeminfo, logbase, printer=None, plugin_manager=None):
    from octoprint.util import to_bytes

    systeminfotxt = []
    for k in sorted(systeminfo.keys()):
        systeminfotxt.append("{}: {}".format(k, systeminfo[k]))

    terminaltxt = None
    if printer and printer.is_operational():
        firmware_info = printer.firmware_info
        if firmware_info:
            systeminfo["printer.firmware"] = firmware_info["name"]

        if hasattr(printer, "_log"):
            terminaltxt = list(printer._log)

    try:
        import zlib  # noqa: F401

        compress_type = zipstream.ZIP_DEFLATED
    except ImportError:
        # no zlib, no compression
        compress_type = zipstream.ZIP_STORED

    z = zipstream.ZipFile()

    # add systeminfo
    z.writestr(
        "systeminfo.txt", to_bytes("\n".join(systeminfotxt)), compress_type=compress_type
    )

    # add terminal.txt, if available
    if terminaltxt:
        z.writestr(
            "terminal.txt", to_bytes("\n".join(terminaltxt)), compress_type=compress_type
        )

    # add logs
    for log in (
        "octoprint.log",
        "serial.log",
    ):
        logpath = os.path.join(logbase, log)
        if os.path.exists(logpath):
            z.write(logpath, arcname=log, compress_type=compress_type)

    # add additional bundle contents from bundled plugins
    if plugin_manager:
        for name, hook in plugin_manager.get_hooks(
            "octoprint.systeminfo.additional_bundle_files"
        ).items():
            try:
                plugin = plugin_manager.get_plugin_info(name)
                if not plugin.bundled:
                    # we only support this for bundled plugins because we don't want
                    # third party logs to blow up the bundles
                    continue

                logs = hook()

                for log, content in logs.items():
                    if isinstance(content, str):
                        # log path
                        if os.path.exists(content) and os.access(content, os.R_OK):
                            z.write(content, arcname=log, compress_type=compress_type)
                    elif callable(content):
                        # content generating callable
                        z.writestr(log, to_bytes(content()), compress_type=compress_type)
            except Exception:
                logging.getLogger(__name__).exception(
                    "Error while retrieving additional bundle contents for plugin {}".format(
                        name
                    ),
                    extra={"plugin": name},
                )

    return z


def get_systeminfo_bundle_name():
    import time

    return "octoprint-systeminfo-{}.zip".format(time.strftime("%Y%m%d%H%M%S"))


@click.group()
def systeminfo_commands():
    pass


@systeminfo_commands.command(name="systeminfo")
@standard_options()
@click.argument(
    "path",
    nargs=1,
    required=False,
    type=click.Path(writable=True, dir_okay=True, resolve_path=True),
)
@click.pass_context
def systeminfo_command(ctx, path, **kwargs):
    """Retrieves and prints the system info."""
    logging.disable(logging.ERROR)
    try:
        (
            settings,
            logger,
            safe_mode,
            event_manager,
            connectivity_checker,
            plugin_manager,
            environment_detector,
        ) = init_platform_for_cli(ctx)
    except Exception as e:
        click.echo(str(e), err=True)
        click.echo("There was a fatal error initializing the platform.", err=True)
        ctx.exit(-1)
    else:
        systeminfo = get_systeminfo(
            environment_detector, connectivity_checker, {"systeminfo.generator": "cli"}
        )

        if path:
            # create zip at path
            zipfilename = os.path.join(path, get_systeminfo_bundle_name())
            click.echo("Writing systeminfo bundle to {}...".format(zipfilename))

            z = get_systeminfo_bundle(
                systeminfo, settings.getBaseFolder("logs"), plugin_manager=plugin_manager
            )
            try:
                with open(zipfilename, "wb") as f:
                    for data in z:
                        f.write(data)
            except Exception as e:
                click.echo(str(e), err=True)
                click.echo(
                    "There was an error writing to {}.".format(zipfilename), err=True
                )
                ctx.exit(-1)

            click.echo("Done!")
            click.echo(zipfilename)

        else:
            # output systeminfo to console
            for k in sorted(systeminfo.keys()):
                click.echo("{}: {}".format(k, systeminfo[k]))
    ctx.exit(0)
