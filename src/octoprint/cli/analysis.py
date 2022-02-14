__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 The OctoPrint Project - Released under terms of the AGPLv3 License"

import sys

import click

from octoprint.util import yaml

click.disable_unicode_literals_warning = True

# ~~ "octoprint util" commands


dimensions = ("depth", "height", "width")
printing_area = ("maxX", "maxY", "maxZ", "minX", "minY", "minZ")


def empty_result(result):
    dims = result.get("dimensions", {})
    return all(map(lambda x: dims.get(x) == 0.0, dimensions))


def validate_result(result):
    def validate_list(data):
        return not any(map(invalid_float, data))

    def validate_dict(data, keys):
        for k in keys:
            if k not in data or invalid_float(data[k]):
                return False
        return True

    def invalid_float(value):
        return value is None or value == float("inf") or value == float("-inf")

    if "dimensions" not in result or not validate_dict(result["dimensions"], dimensions):
        return False

    if "extrusion_length" not in result or not validate_list(result["extrusion_length"]):
        return False

    if "extrusion_volume" not in result or not validate_list(result["extrusion_volume"]):
        return False

    if "printing_area" not in result or not validate_dict(
        result["printing_area"], printing_area
    ):
        return False

    if "total_time" not in result or invalid_float(result["total_time"]):
        return False

    return True


@click.group()
def cli():
    """Analysis tools."""
    pass


@cli.command(name="gcode")
@click.option("--throttle", "throttle", type=float, default=None)
@click.option("--throttle-lines", "throttle_lines", type=int, default=None)
@click.option("--speed-x", "speedx", type=float, default=6000)
@click.option("--speed-y", "speedy", type=float, default=6000)
@click.option("--speed-z", "speedz", type=float, default=300)
@click.option("--offset", "offset", type=(float, float), multiple=True)
@click.option("--max-t", "maxt", type=int, default=10)
@click.option("--g90-extruder", "g90_extruder", is_flag=True)
@click.option("--bed-z", "bedz", type=float, default=0)
@click.option("--progress", "progress", is_flag=True)
@click.option("--layers", "layers", is_flag=True)
@click.argument("path", type=click.Path())
def gcode_command(
    path,
    speedx,
    speedy,
    speedz,
    offset,
    maxt,
    throttle,
    throttle_lines,
    g90_extruder,
    bedz,
    progress,
    layers,
):
    """Runs a GCODE file analysis."""

    import time

    from octoprint.util.gcodeInterpreter import gcode

    throttle_callback = None
    if throttle:

        def throttle_callback(filePos, readBytes):
            if filePos % throttle_lines == 0:
                # only apply throttle every $throttle_lines lines
                time.sleep(throttle)

    offsets = offset
    if offsets is None:
        offsets = []
    elif isinstance(offset, tuple):
        offsets = list(offsets)
    offsets = [(0, 0)] + offsets
    if len(offsets) < maxt:
        offsets += [(0, 0)] * (maxt - len(offsets))

    start_time = time.monotonic()

    progress_callback = None
    if progress:

        def progress_callback(percentage):
            click.echo(f"PROGRESS:{percentage}")

    interpreter = gcode(progress_callback=progress_callback, incl_layers=layers)

    interpreter.load(
        path,
        speedx=speedx,
        speedy=speedy,
        offsets=offsets,
        throttle=throttle_callback,
        max_extruders=maxt,
        g90_extruder=g90_extruder,
        bed_z=bedz,
    )

    click.echo(f"DONE:{time.monotonic() - start_time}s")

    result = interpreter.get_result()
    if empty_result(result):
        click.echo("EMPTY:There are no extrusions in the file, nothing to analyse")
        sys.exit(0)

    if not validate_result(result):
        click.echo(
            "ERROR:Invalid analysis result, please create a bug report in OctoPrint's "
            "issue tracker and be sure to also include the GCODE file with which this "
            "happened"
        )
        sys.exit(-1)

    click.echo("RESULTS:")
    click.echo(yaml.dump(interpreter.get_result(), pretty=True))


if __name__ == "__main__":
    gcode_command()
