__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging
import os
from concurrent.futures import ThreadPoolExecutor, wait

import click

from octoprint import FatalStartupError, init_pluginsystem, init_settings
from octoprint.cli import get_ctx_obj_option, standard_options
from octoprint.timelapse import create_thumbnail_path, valid_timelapse
from octoprint.util import is_hidden_path

click.disable_unicode_literals_warning = True


@click.group()
@click.pass_context
def cli(ctx):
    """Basic config manipulation."""
    logging.basicConfig(
        level=logging.DEBUG
        if get_ctx_obj_option(ctx, "verbosity", 0) > 0
        else logging.WARN
    )
    try:
        ctx.obj.settings = init_settings(
            get_ctx_obj_option(ctx, "basedir", None),
            get_ctx_obj_option(ctx, "configfile", None),
            overlays=get_ctx_obj_option(ctx, "overlays", None),
        )
        ctx.obj.plugin_manager = init_pluginsystem(
            ctx.obj.settings, safe_mode=get_ctx_obj_option(ctx, "safe_mode", False)
        )
    except FatalStartupError as e:
        click.echo(str(e), err=True)
        click.echo("There was a fatal error initializing the settings manager.", err=True)
        ctx.exit(-1)


@cli.command(name="create_thumbnails")
@standard_options(hidden=True)
@click.option(
    "--missing",
    is_flag=True,
    help="Create thumbnails for all timelapses that don't yet have one",
)
@click.option(
    "--processes",
    type=int,
    help="Number of processes to use for creating thumbnails",
    default=1,
)
@click.argument("paths", nargs=-1, type=click.Path())
@click.pass_context
def extract_thumbnails(ctx, missing, processes, paths):
    """Extract missing thumbnails from timelapses."""

    if not paths and not missing:
        click.echo(
            "No paths specified and no --missing flag either, nothing to do.", err=True
        )
        ctx.exit(-1)

    if missing:
        paths = []
        timelapse_folder = ctx.obj.settings.getBaseFolder("timelapse")
        for entry in os.scandir(timelapse_folder):
            if is_hidden_path(entry.path) or not valid_timelapse(entry.path):
                continue

            thumb = create_thumbnail_path(entry.path)
            if not os.path.isfile(thumb):
                paths.append(entry.path)

    ffmpeg = ctx.obj.settings.get(["webcam", "ffmpeg"])

    click.echo(f"Creating thumbnails for {len(paths)} timelapses")
    executor = ThreadPoolExecutor(max_workers=processes)
    futures = [executor.submit(_create_thumbnail, ffmpeg, path) for path in paths]
    wait(futures)
    click.echo("Done!")


def _create_thumbnail(ffmpeg, path):
    from octoprint.timelapse import TimelapseRenderJob

    click.echo(f"Creating thumbnail for {path}...")
    return TimelapseRenderJob._try_generate_thumbnail(ffmpeg, path)
