#!/bin/env python

__author__ = "Gina Haeussge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import errno
import sys
import time
import traceback

# default close_fds settings
if sys.platform == "win32" and sys.version_info < (3, 7):
    CLOSE_FDS = False
else:
    CLOSE_FDS = True


def _log_call(*lines):
    _log(lines, prefix=">", stream="call")


def _log_stdout(*lines):
    _log(lines, prefix=" ", stream="stdout")


def _log_stderr(*lines):
    _log(lines, prefix=" ", stream="stderr")


def _log(lines, prefix=None, stream=None):
    output_stream = sys.stdout
    if stream == "stderr":
        output_stream = sys.stderr

    for line in lines:
        to_print = _to_bytes(
            "{} {}".format(prefix, _to_unicode(line.rstrip(), errors="replace")),
            errors="replace",
        )
        print(to_print, file=output_stream)


def _to_unicode(s_or_u, encoding="utf-8", errors="strict"):
    """Make sure ``s_or_u`` is a unicode string."""
    if isinstance(s_or_u, bytes):
        return s_or_u.decode(encoding, errors=errors)
    else:
        return s_or_u


def _to_bytes(s_or_u, encoding="utf-8", errors="strict"):
    """Make sure ``s_or_u`` is a str."""
    if isinstance(s_or_u, str):
        return s_or_u.encode(encoding, errors=errors)
    else:
        return s_or_u


def _execute(command, **kwargs):
    import sarge

    if isinstance(command, (list, tuple)):
        joined_command = " ".join(command)
    else:
        joined_command = command
    _log_call(joined_command)

    kwargs.update(
        {
            "close_fds": CLOSE_FDS,
            "async_": True,
            "stdout": sarge.Capture(),
            "stderr": sarge.Capture(),
        }
    )

    try:
        p = sarge.run(command, **kwargs)
        while len(p.commands) == 0:
            # somewhat ugly... we can't use wait_events because
            # the events might not be all set if an exception
            # by sarge is triggered within the async process
            # thread
            time.sleep(0.01)

        # by now we should have a command, let's wait for its
        # process to have been prepared
        p.commands[0].process_ready.wait()

        if not p.commands[0].process:
            # the process might have been set to None in case of any exception
            print(
                f"Error while trying to run command {joined_command}",
                file=sys.stderr,
            )
            return None, [], []
    except Exception:
        print(f"Error while trying to run command {joined_command}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None, [], []

    all_stdout = []
    all_stderr = []
    try:
        while p.commands[0].poll() is None:
            lines = p.stderr.readlines(timeout=0.5)
            if lines:
                lines = list(map(lambda x: _to_unicode(x, errors="replace"), lines))
                _log_stderr(*lines)
                all_stderr += lines

            lines = p.stdout.readlines(timeout=0.5)
            if lines:
                lines = list(map(lambda x: _to_unicode(x, errors="replace"), lines))
                _log_stdout(*lines)
                all_stdout += lines

    finally:
        p.close()

    lines = p.stderr.readlines()
    if lines:
        lines = list(map(lambda x: _to_unicode(x, errors="replace"), lines))
        _log_stderr(*lines)
        all_stderr += lines

    lines = p.stdout.readlines()
    if lines:
        lines = list(map(lambda x: _to_unicode(x, errors="replace"), lines))
        _log_stdout(*lines)
        all_stdout += lines

    return p.returncode, all_stdout, all_stderr


def _get_git_executables():
    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]
    return GITS


def _git(args, cwd, git_executable=None):
    if git_executable is not None:
        commands = [git_executable]
    else:
        commands = _get_git_executables()

    for c in commands:
        command = [c] + args
        try:
            return _execute(command, cwd=cwd)
        except OSError:
            e = sys.exc_info()[1]
            if e.errno == errno.ENOENT:
                continue

            print(
                "Error while trying to run command {}".format(" ".join(command)),
                file=sys.stderr,
            )
            traceback.print_exc(file=sys.stderr)
            return None, [], []
        except Exception:
            print(
                "Error while trying to run command {}".format(" ".join(command)),
                file=sys.stderr,
            )
            traceback.print_exc(file=sys.stderr)
            return None, [], []
    else:
        print(
            "Unable to find git command, tried {}".format(", ".join(commands)),
            file=sys.stderr,
        )
        return None, [], []


def _python(args, cwd, python_executable, sudo=False):
    command = [python_executable] + args
    if sudo:
        command = ["sudo"] + command
    try:
        return _execute(command, cwd=cwd)
    except Exception:
        import traceback

        print(
            "Error while trying to run command {}".format(" ".join(command)),
            file=sys.stderr,
        )
        traceback.print_exc(file=sys.stderr)
        return None, [], []


def _to_error(*lines):
    if len(lines) == 1:
        if isinstance(lines[0], (list, tuple)):
            lines = lines[0]
        elif not isinstance(lines[0], (str, bytes)):
            lines = [
                repr(lines[0]),
            ]
    return "\n".join(map(lambda x: _to_unicode(x, errors="replace"), lines))


def _rescue_changes(git_executable, folder):
    print(">>> Running: git diff --shortstat")
    returncode, stdout, stderr = _git(
        ["diff", "--shortstat"], folder, git_executable=git_executable
    )
    if returncode is None or returncode != 0:
        raise RuntimeError(
            f'Could not update, "git diff" failed with returncode {returncode}'
        )
    if stdout and "".join(stdout).strip():
        # we got changes in the working tree, maybe from the user, so we'll now rescue those into a patch
        import os
        import time

        timestamp = time.strftime("%Y%m%d%H%M")
        patch = os.path.join(folder, f"{timestamp}-preupdate.patch")

        print(f">>> Running: git diff and saving output to {patch}")
        returncode, stdout, stderr = _git(["diff"], folder, git_executable=git_executable)
        if returncode is None or returncode != 0:
            raise RuntimeError(
                "Could not update, installation directory was dirty and state could not be persisted as a patch to {}".format(
                    patch
                )
            )

        with open(patch, "w", encoding="utf-8", errors="replace") as f:
            for line in stdout:
                f.write(line)

        return True

    return False


def update_source(git_executable, folder, target, force=False, branch=None):
    if _rescue_changes(git_executable, folder):
        print(">>> Running: git reset --hard")
        returncode, stdout, stderr = _git(
            ["reset", "--hard"], folder, git_executable=git_executable
        )
        if returncode is None or returncode != 0:
            raise RuntimeError(
                'Could not update, "git reset --hard" failed with returncode {}'.format(
                    returncode
                )
            )

        print(">>> Running: git clean -f -d -e *-preupdate.patch")
        returncode, stdout, stderr = _git(
            ["clean", "-f", "-d", "-e", "*-preupdate.patch"],
            folder,
            git_executable=git_executable,
        )
        if returncode is None or returncode != 0:
            raise RuntimeError(
                'Could not update, "git clean -f" failed with returncode {}'.format(
                    returncode
                )
            )

    print(">>> Running: git fetch")
    returncode, stdout, stderr = _git(["fetch"], folder, git_executable=git_executable)
    if returncode is None or returncode != 0:
        raise RuntimeError(
            f'Could not update, "git fetch" failed with returncode {returncode}'
        )

    if branch is not None and branch.strip() != "":
        print(f">>> Running: git checkout {branch}")
        returncode, stdout, stderr = _git(
            ["checkout", branch], folder, git_executable=git_executable
        )
        if returncode is None or returncode != 0:
            raise RuntimeError(
                'Could not update, "git checkout" failed with returncode {}'.format(
                    returncode
                )
            )

    print(">>> Running: git pull")
    returncode, stdout, stderr = _git(["pull"], folder, git_executable=git_executable)
    if returncode is None or returncode != 0:
        raise RuntimeError(
            f'Could not update, "git pull" failed with returncode {returncode}'
        )

    if force:
        reset_command = ["reset", "--hard"]
        reset_command += [target]

        print(">>> Running: git {}".format(" ".join(reset_command)))
        returncode, stdout, stderr = _git(
            reset_command, folder, git_executable=git_executable
        )
        if returncode is None or returncode != 0:
            raise RuntimeError(
                'Error while updating, "git {}" failed with returncode {}'.format(
                    " ".join(reset_command), returncode
                )
            )


def install_source(python_executable, folder, user=False, sudo=False):
    print(">>> Running: python setup.py clean")
    returncode, stdout, stderr = _python(["setup.py", "clean"], folder, python_executable)
    if returncode is None or returncode != 0:
        print(f'"python setup.py clean" failed with returncode {returncode}')
        print("Continuing anyways")

    print(">>> Running: python setup.py install")
    args = ["setup.py", "install"]
    if user:
        args.append("--user")
    returncode, stdout, stderr = _python(args, folder, python_executable, sudo=sudo)
    if returncode is None or returncode != 0:
        raise RuntimeError(
            'Could not update, "python setup.py install" failed with returncode {}'.format(
                returncode
            )
        )


def parse_arguments():
    import argparse

    boolean_trues = ["true", "yes", "1"]

    parser = argparse.ArgumentParser(prog="update-octoprint.py")

    parser.add_argument(
        "--git",
        action="store",
        type=str,
        dest="git_executable",
        help="Specify git executable to use",
    )
    parser.add_argument(
        "--python",
        action="store",
        type=str,
        dest="python_executable",
        help="Specify python executable to use",
    )
    parser.add_argument(
        "--force",
        action="store",
        type=lambda x: x in boolean_trues,
        dest="force",
        default=False,
        help="Set this to true to force the update to only the specified version (nothing newer, nothing older)",
    )
    parser.add_argument(
        "--sudo", action="store_true", dest="sudo", help="Install with sudo"
    )
    parser.add_argument(
        "--user",
        action="store_true",
        dest="user",
        help="Install to the user site directory instead of the general site directory",
    )
    parser.add_argument(
        "--branch",
        action="store",
        type=str,
        dest="branch",
        default=None,
        help="Specify the branch to make sure is checked out",
    )
    parser.add_argument(
        "folder",
        type=str,
        help="Specify the base folder of the OctoPrint installation to update",
    )
    parser.add_argument(
        "target", type=str, help="Specify the commit or tag to which to update"
    )

    args = parser.parse_args()

    return args


def main():
    args = parse_arguments()

    git_executable = None
    if args.git_executable:
        git_executable = args.git_executable

    python_executable = sys.executable
    if args.python_executable:
        python_executable = args.python_executable
        if python_executable.startswith('"'):
            python_executable = python_executable[1:]
        if python_executable.endswith('"'):
            python_executable = python_executable[:-1]

    print(f"Python executable: {python_executable!r}")

    folder = args.folder

    import os

    if not os.access(folder, os.W_OK):
        raise RuntimeError("Could not update, base folder is not writable")

    update_source(
        git_executable, folder, args.target, force=args.force, branch=args.branch
    )
    install_source(python_executable, folder, user=args.user, sudo=args.sudo)


if __name__ == "__main__":
    main()
