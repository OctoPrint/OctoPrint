__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2020 The OctoPrint Project - Released under terms of the AGPLv3 License"

import ast
import logging
import os
import shutil
import tempfile

from octoprint.settings import settings
from octoprint.util.net import download_file

from .. import exceptions

logger = logging.getLogger(
    "octoprint.plugins.softwareupdate.updaters.download_single_file_plugin"
)


def can_perform_update(target, check, online=True):
    return online or check.get("offline", False)


def perform_update(target, check, target_version, log_cb=None, online=True, force=False):
    if not online and not check.get("offline", False):
        raise exceptions.CannotUpdateOffline()

    url = check.get("url")
    if url is None:
        raise exceptions.ConfigurationInvalid(
            "download_single_file_plugin updater needs url set"
        )

    def _log_call(*lines):
        _log(lines, prefix=" ", stream="call")

    def _log_message(*lines):
        _log(lines, prefix="#", stream="message")

    def _log(lines, prefix=None, stream=None):
        if log_cb is None:
            return
        log_cb(lines, prefix=prefix, stream=stream)

    folder = None
    try:
        try:
            _log_message(f"Download file from {url}")
            folder = tempfile.TemporaryDirectory()
            path = download_file(url, folder.name)
        except Exception as exc:
            raise exceptions.NetworkError(cause=exc)

        filename = os.path.basename(path)
        _, ext = os.path.splitext(filename)
        if ext not in (".py",):
            raise exceptions.UpdateError(f"File is not a python file: {filename}", None)

        try:
            with open(path, "rb") as f:
                ast.parse(f.read(), filename=path)
        except Exception:
            logger.exception(f"Could not parse {path} as python file", None)
            raise exceptions.UpdateError(
                f"Could not parse {filename} as python file.", None
            )

        destination = os.path.join(settings().getBaseFolder("plugins"), filename)

        try:
            _log_message(f"Copy {path} to {destination}")
            shutil.copy(path, destination)
        except Exception:
            logger.exception(f"Could not copy {path} to {destination}")
            raise exceptions.UpdateError(f"Could not copy {path} to {destination}", None)

        return "ok"
    finally:
        if folder is not None:
            folder.cleanup()
