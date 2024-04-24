__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2020 The OctoPrint Project - Released under terms of the AGPLv3 License"


import datetime
import logging
import os

import click
from zipstream.ng import ZIP_DEFLATED, ZipStream

from octoprint.cli import init_platform_for_cli, standard_options

click.disable_unicode_literals_warning = True


def get_systeminfo(
    environment_detector, connectivity_checker, settings, additional_fields=None
):
    from octoprint import __version__
    from octoprint.util import dict_flatten

    if additional_fields is None:
        additional_fields = {}

    environment_detector.run_detection(notify_plugins=False)

    safe_mode_file = os.path.join(settings.getBaseFolder("data"), "last_safe_mode")
    last_safe_mode = {"date": "unknown", "reason": "unknown"}
    try:
        if os.path.exists(safe_mode_file):
            with open(safe_mode_file) as f:
                last_safe_mode["reason"] = f.readline().strip()
            last_safe_mode["date"] = (
                datetime.datetime.utcfromtimestamp(
                    os.path.getmtime(safe_mode_file)
                ).isoformat()[:19]
                + "Z"
            )
    except Exception as ex:
        logging.getLogger(__name__).error(
            "Error while retrieving last safe mode information from {}: {}".format(
                safe_mode_file, ex
            )
        )

    systeminfo = {
        "octoprint": {"version": __version__, "last_safe_mode": last_safe_mode},
        "connectivity": connectivity_checker.as_dict(),
        "env": environment_detector.environment,
        "systeminfo": {"generated": datetime.datetime.utcnow().isoformat()[:19] + "Z"},
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

    try:
        z = ZipStream(compress_type=ZIP_DEFLATED)
    except RuntimeError:
        # no zlib support
        z = ZipStream(sized=True)

    if printer and printer.is_operational():
        firmware_info = printer.firmware_info
        if firmware_info:
            # add firmware to systeminfo so it's included in systeminfo.txt
            systeminfo["printer.firmware"] = firmware_info["name"]

        # Add printer log, if available
        if hasattr(printer, "_log"):
            z.add(to_bytes("\n".join(printer._log)), arcname="terminal.txt")

        # Add reconstructed M115 response, if available
        if printer._comm and printer._comm._firmware_info:
            comm = printer._comm
            m115 = "Reconstructed M115 response:\n\n>>> M115\n<<< "
            m115 += " ".join([f"{k}:{v}" for k, v in comm._firmware_info.items()])

            if comm._firmware_capabilities:
                m115 += (
                    "\n<<< "
                    + "\n<<< ".join(
                        [
                            f"Cap:{k}:{'1' if v else '0'}"
                            for k, v in comm._firmware_capabilities.items()
                        ]
                    )
                    + "\n\n"
                )
            z.add(to_bytes(m115), arcname="m115.txt")

    # add systeminfo
    systeminfotxt = []
    for k in sorted(systeminfo.keys()):
        systeminfotxt.append(f"{k}: {systeminfo[k]}")

    z.add(to_bytes("\n".join(systeminfotxt)), arcname="systeminfo.txt")

    # add logs
    for log in (
        "octoprint.log",
        "serial.log",
        "tornado.log",
    ):
        logpath = os.path.join(logbase, log)
        if os.path.exists(logpath):
            z.add_path(logpath, arcname=log)

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
                            z.add_path(content, arcname=log)
                    elif callable(content):
                        # content generating callable
                        try:
                            z.add(to_bytes(content()), arcname=log)
                        except Exception:
                            logging.getLogger(__name__).exception(
                                f"Error while executing callable for additional bundle content {log} for plugin {name}",
                                extra={"plugin": name},
                            )
            except Exception:
                logging.getLogger(__name__).exception(
                    f"Error while retrieving additional bundle contents for plugin {name}",
                    extra={"plugin": name},
                )

    return z


def get_systeminfo_bundle_name():
    import time

    return "octoprint-systeminfo-{}.zip".format(time.strftime("%Y%m%d%H%M%S"))


@click.group()
def cli():
    pass


@cli.command(name="systeminfo")
@standard_options()
@click.option(
    "--short",
    is_flag=True,
    help="Only output an abridged version of the systeminfo.",
)
@click.argument(
    "path",
    nargs=1,
    required=False,
    type=click.Path(writable=True, dir_okay=True, resolve_path=True),
)
@click.pass_context
def systeminfo_command(ctx, short, path, **kwargs):
    """
    Creates a system info bundle at PATH.

    If PATH is not provided, the system info bundle will be created in the
    current working directory.

    If --short is provided, only an abridged version of the systeminfo will be
    output to the console.
    """
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
            environment_detector,
            connectivity_checker,
            settings,
            additional_fields={"systeminfo.generator": "cli"},
        )

        if short:
            # output abridged systeminfo to console
            for k in sorted(systeminfo.keys()):
                click.echo(f"{k}: {systeminfo[k]}")

        else:
            if not path:
                path = "."

            # create zip at path
            zipfilename = os.path.abspath(
                os.path.join(path, get_systeminfo_bundle_name())
            )
            click.echo(f"Writing systeminfo bundle to {zipfilename}...")

            z = get_systeminfo_bundle(
                systeminfo, settings.getBaseFolder("logs"), plugin_manager=plugin_manager
            )
            try:
                with open(zipfilename, "wb") as f:
                    f.writelines(z)
            except Exception as e:
                click.echo(str(e), err=True)
                click.echo(f"There was an error writing to {zipfilename}.", err=True)
                ctx.exit(-1)

            click.echo("Done!")
            click.echo(zipfilename)

    ctx.exit(0)
