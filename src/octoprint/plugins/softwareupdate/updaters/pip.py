__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import collections
import logging
import threading

from octoprint.util.pip import (
    UnknownPip,
    create_pip_caller,
    is_already_installed,
    is_egg_problem,
)
from octoprint.util.version import get_comparable_version

from .. import exceptions

logger = logging.getLogger("octoprint.plugins.softwareupdate.updaters.pip")
console_logger = logging.getLogger(
    "octoprint.plugins.softwareupdate.updaters.pip.console"
)

_pip_callers = {}
_pip_caller_mutex = collections.defaultdict(threading.RLock)


def can_perform_update(target, check, online=True):
    from .. import MINIMUM_PIP

    pip_caller = _get_pip_caller(
        command=check["pip_command"] if "pip_command" in check else None
    )
    return (
        "pip" in check
        and pip_caller is not None
        and pip_caller.available
        and pip_caller.version >= get_comparable_version(MINIMUM_PIP)
        and (online or check.get("offline", False))
    )


def _get_pip_caller(command=None):
    global _pip_callers
    global _pip_caller_mutex

    key = command
    if command is None:
        key = "__default"

    with _pip_caller_mutex[key]:
        if key not in _pip_callers:
            try:
                _pip_callers[key] = create_pip_caller(command=command)
            except UnknownPip:
                pass

        return _pip_callers.get(key)


def perform_update(target, check, target_version, log_cb=None, online=True, force=False):
    pip_command = check.get("pip_command")
    pip_working_directory = check.get("pip_cwd")

    if not online and not check.get("offline", False):
        raise exceptions.CannotUpdateOffline()

    force = force or check.get("force_reinstall", False)

    pip_caller = _get_pip_caller(command=pip_command)
    if pip_caller is None:
        raise exceptions.UpdateError("Can't run pip", None)

    def _log_call(*lines):
        _log(lines, prefix=" ", stream="call")

    def _log_stdout(*lines):
        _log(lines, prefix=">", stream="stdout")

    def _log_stderr(*lines):
        _log(lines, prefix="!", stream="stderr")

    def _log_message(*lines):
        _log(lines, prefix="#", stream="message")

    def _log(lines, prefix=None, stream=None):
        if log_cb is None:
            return
        log_cb(lines, prefix=prefix, stream=stream)

    if log_cb is not None:
        pip_caller.on_log_call = _log_call
        pip_caller.on_log_stdout = _log_stdout
        pip_caller.on_log_stderr = _log_stderr

    install_arg = check["pip"].format(
        target_version=target_version, target=target_version
    )

    logger.debug(f"Target: {target}, executing pip install {install_arg}")
    pip_args = ["--disable-pip-version-check", "install", install_arg, "--no-cache-dir"]
    pip_kwargs = {
        "env": {"PYTHONWARNINGS": "ignore:DEPRECATION::pip._internal.cli.base_command"}
    }
    if pip_working_directory is not None:
        pip_kwargs.update(cwd=pip_working_directory)

    if "dependency_links" in check and check["dependency_links"]:
        pip_args += ["--process-dependency-links"]

    returncode, stdout, stderr = pip_caller.execute(*pip_args, **pip_kwargs)
    if returncode != 0:
        if is_egg_problem(stdout) or is_egg_problem(stderr):
            _log_message(
                'This looks like an error caused by a specific issue in upgrading Python "eggs"',
                "via current versions of pip.",
                "Performing a second install attempt as a work around.",
            )
            returncode, stdout, stderr = pip_caller.execute(*pip_args, **pip_kwargs)
            if returncode != 0:
                raise exceptions.UpdateError(
                    "Error while executing pip install", (stdout, stderr)
                )
        else:
            raise exceptions.UpdateError(
                "Error while executing pip install", (stdout, stderr)
            )

    if not force and is_already_installed(stdout):
        _log_message(
            "Looks like we were already installed in this version. Forcing a reinstall."
        )
        force = True

    if force:
        logger.debug(
            "Target: %s, executing pip install %s --ignore-reinstalled --force-reinstall --no-deps"
            % (target, install_arg)
        )
        pip_args += ["--ignore-installed", "--force-reinstall", "--no-deps"]

        returncode, stdout, stderr = pip_caller.execute(*pip_args, **pip_kwargs)
        if returncode != 0:
            raise exceptions.UpdateError(
                "Error while executing pip install --force-reinstall", (stdout, stderr)
            )

    return "ok"
