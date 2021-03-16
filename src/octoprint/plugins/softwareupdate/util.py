__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging

from octoprint.util.platform import CLOSE_FDS

from .exceptions import ScriptError


def execute(command, cwd=None, evaluate_returncode=True, **kwargs):
    do_async = kwargs.get("do_async", kwargs.get("async", False))

    import sarge

    p = None

    try:
        p = sarge.run(
            command,
            close_fds=CLOSE_FDS,
            cwd=cwd,
            stdout=sarge.Capture(),
            stderr=sarge.Capture(),
            async_=do_async,
        )
    except Exception:
        logging.getLogger(__name__).exception(f"Error while executing command: {command}")
        returncode = p.returncode if p is not None else None
        stdout = p.stdout.text if p is not None and p.stdout is not None else ""
        stderr = p.stderr.text if p is not None and p.stderr is not None else ""
        raise ScriptError(returncode, stdout, stderr)

    if evaluate_returncode and p.returncode != 0:
        raise ScriptError(p.returncode, p.stdout.text, p.stderr.text)

    if not do_async:
        return p.returncode, p.stdout.text, p.stderr.text
