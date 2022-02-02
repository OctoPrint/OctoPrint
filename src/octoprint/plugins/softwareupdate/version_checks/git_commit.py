__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import errno
import logging
import subprocess
import sys

from ..exceptions import ConfigurationInvalid


def _get_git_executables():
    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]
    return GITS


def _git(args, cwd, hide_stderr=False):
    commands = _get_git_executables()

    for c in commands:
        try:
            p = subprocess.Popen(
                [c] + args,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=(subprocess.PIPE if hide_stderr else None),
            )
            break
        except OSError:
            e = sys.exc_info()[1]
            if e.errno == errno.ENOENT:
                continue
            return None, None
    else:
        return None, None

    stdout = p.communicate()[0].strip()
    if sys.version >= "3":
        stdout = stdout.decode()

    if p.returncode != 0:
        return p.returncode, None

    return p.returncode, stdout


def get_latest(target, check, online=True, *args, **kwargs):
    checkout_folder = check.get("checkout_folder")
    if checkout_folder is None:
        raise ConfigurationInvalid(
            "Update configuration for {} of type git_commit needs checkout_folder set and not None".format(
                target
            )
        )

    returncode, local_commit = _git(["rev-parse", "@{0}"], checkout_folder)
    if returncode != 0:
        return None, True

    information = {
        "local": {"name": "Commit %s" % local_commit, "value": local_commit},
        "remote": {"name": "?", "value": "?"},
        "needs_online": not check.get("offline", False),
    }
    if not online and information["needs_online"]:
        return information, True

    returncode, _ = _git(["fetch"], checkout_folder)
    if returncode != 0:
        return information, True

    returncode, remote_commit = _git(["rev-parse", "@{u}"], checkout_folder)
    if returncode != 0:
        return information, True

    returncode, base = _git(["merge-base", "@{0}", "@{u}"], checkout_folder)
    if returncode != 0:
        return information, True

    if local_commit == remote_commit or remote_commit == base:
        information["remote"] = {
            "name": "Commit %s" % local_commit,
            "value": local_commit,
        }
        is_current = True
    else:
        information["remote"] = {
            "name": "Commit %s" % remote_commit,
            "value": remote_commit,
        }
        is_current = local_commit == remote_commit

    logger = logging.getLogger(
        "octoprint.plugins.softwareupdate.version_checks.git_commit"
    )
    logger.debug(f"Target: {target}, local: {local_commit}, remote: {remote_commit}")

    return information, is_current
