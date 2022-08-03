__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging
import os
import site
import sys
import threading
from typing import List

import pkg_resources
import sarge

from octoprint.util.platform import CLOSE_FDS

from .commandline import CommandlineCaller, clean_ansi

_cache = {"version": {}, "setup": {}}
_cache_mutex = threading.RLock()


OUTPUT_SUCCESS = "Successfully installed"
"""Start of successful result line"""

OUTPUT_FAILURE = "Could not install"
"""Start of failure result line"""

OUTPUT_ALREADY_INSTALLED = "Requirement already satisfied"
"""Start of a line indicating some package was already installed in this version"""

OUTPUT_PYTHON_MISMATCH = "requires a different Python:"
"""Line segment indicating a mismatch of python_requires version"""

OUTPUT_PYTHON_SYNTAX = "SyntaxError: invalid syntax"
"""Line segment indicating a syntax error, could be a python mismatch, e.g. f-strings"""

OUTPUT_POTENTIAL_EGG_PROBLEM_POSIX = "No such file or directory"
"""Line indicating a potential egg problem on Posix"""

OUTPUT_POTENTIAL_EGG_PROBLEM_WINDOWS = "The system cannot find the file specified"
"""Line indicating a potential egg problem on Windows"""


def is_already_installed(lines):
    """
    Returns whether the given output lines indicates the packages was already installed
    or not.

    This is currently determined by an empty result line and any line starting with
    "Requirement already satisfied".

    Args:
        lines (list of str): the output to parse, stdout or stderr

    Returns:
        bool: True if detected, False otherwise
    """
    result_line = get_result_line(lines)  # neither success nor failure reported
    return not result_line and any(
        line.strip().startswith(OUTPUT_ALREADY_INSTALLED) for line in lines
    )


def is_python_mismatch(lines):
    """
    Returns whether the given output lines indicates a Python version mismatch.

    This is currently determined by either a syntax error or an explicit "requires a
    different Python" line.

    Args:
        lines (list of str): the output to parse, stdout or stderr

    Returns:
        bool: True if detected, False otherwise
    """
    return any(
        OUTPUT_PYTHON_MISMATCH in line or OUTPUT_PYTHON_SYNTAX in line for line in lines
    )


def is_egg_problem(lines):
    """
    Returns whether the given output lines indicates an occurrence of the "egg-problem".

    If something (target or dependency of target) was installed as an egg at an earlier
    date (e.g. thanks to just running python setup.py install), pip install will throw an
    error after updating that something to a newer (non-egg) version since it will still
    have the egg on its sys.path and expect to read data from it.

    See commit 8ad0aadb52b9ef354cad1b33bd4882ae2fbdb8d6 for more details.

    Args:
        lines (list of str): the output to parse, stdout or stderr

    Returns:
        bool: True if detected, False otherwise
    """
    return any(
        ".egg" in line
        and (
            OUTPUT_POTENTIAL_EGG_PROBLEM_POSIX in line
            or OUTPUT_POTENTIAL_EGG_PROBLEM_WINDOWS in line
        )
        for line in lines
    )


def get_result_line(lines):
    """
    Returns the success or failure line contained in the output.

    pip might generate more lines after the actual result line, which is why
    we can't just take the final line. So instead we look for the last line
    starting with either "Successfully installed" or "Could not installed".
    If neither can be found, an empty string will be returned, which should also
    be considered a failure to install.

    Args:
        lines (list of str): the output to parse, stdout or stderr

    Returns:
        str: the last result line, or an empty string if none was found, in which case
             failure should be resumed
    """
    possible_results = list(
        filter(
            lambda x: x.startswith(OUTPUT_SUCCESS) or x.startswith(OUTPUT_FAILURE),
            lines,
        )
    )
    if not possible_results:
        return ""
    return possible_results[-1]


class UnknownPip(Exception):
    pass


class PipCaller(CommandlineCaller):
    process_dependency_links = pkg_resources.Requirement.parse("pip>=1.5")
    no_cache_dir = pkg_resources.Requirement.parse("pip>=1.6")
    disable_pip_version_check = pkg_resources.Requirement.parse("pip>=6.0")
    no_use_wheel = pkg_resources.Requirement.parse("pip==1.5.0")
    broken = pkg_resources.Requirement.parse("pip>=6.0.1,<=6.0.3")

    @classmethod
    def clean_install_command(cls, args, pip_version, virtual_env, use_user, force_user):
        logger = logging.getLogger(__name__)
        args = list(args)

        # strip --process-dependency-links for versions that don't support it
        if (
            pip_version not in cls.process_dependency_links
            and "--process-dependency-links" in args
        ):
            logger.debug(
                "Found --process-dependency-links flag, version {} doesn't need that yet though, removing.".format(
                    pip_version
                )
            )
            args.remove("--process-dependency-links")

        # strip --no-cache-dir for versions that don't support it
        if pip_version not in cls.no_cache_dir and "--no-cache-dir" in args:
            logger.debug(
                "Found --no-cache-dir flag, version {} doesn't support that yet though, removing.".format(
                    pip_version
                )
            )
            args.remove("--no-cache-dir")

        # strip --disable-pip-version-check for versions that don't support it
        if (
            pip_version not in cls.disable_pip_version_check
            and "--disable-pip-version-check" in args
        ):
            logger.debug(
                "Found --disable-pip-version-check flag, version {} doesn't support that yet though, removing.".format(
                    pip_version
                )
            )
            args.remove("--disable-pip-version-check")

        # add --no-use-wheel for versions that otherwise break
        if pip_version in cls.no_use_wheel and "--no-use-wheel" not in args:
            logger.debug(f"Version {pip_version} needs --no-use-wheel to properly work.")
            args.append("--no-use-wheel")

        # remove --user if it's present and a virtual env is detected
        if "--user" in args:
            if virtual_env or not site.ENABLE_USER_SITE:
                logger.debug("Virtual environment detected, removing --user flag.")
                args.remove("--user")
        # otherwise add it if necessary
        elif not virtual_env and site.ENABLE_USER_SITE and (use_user or force_user):
            logger.debug("pip needs --user flag for installations.")
            args.append("--user")

        return args

    def __init__(
        self, configured=None, ignore_cache=False, force_sudo=False, force_user=False
    ):
        CommandlineCaller.__init__(self)
        self._logger = logging.getLogger(__name__)

        self.configured = configured
        self.refresh = False
        self.ignore_cache = ignore_cache

        self.force_sudo = force_sudo
        self.force_user = force_user

        self._command = None
        self._version = None
        self._version_string = None
        self._use_sudo = False
        self._use_user = False
        self._virtual_env = False
        self._install_dir = None

        self.trigger_refresh()

        self.on_log_call = lambda *args, **kwargs: None
        self.on_log_stdout = lambda *args, **kwargs: None
        self.on_log_stderr = lambda *args, **kwargs: None

    def _reset(self):
        self._command = None
        self._version = None
        self._version_string = None
        self._use_sudo = False
        self._use_user = False
        self._install_dir = None

    def __le__(self, other):
        return self.version is not None and self.version <= other

    def __lt__(self, other):
        return self.version is not None and self.version < other

    def __ge__(self, other):
        return self.version is not None and self.version >= other

    def __gt__(self, other):
        return self.version is not None and self.version > other

    @property
    def command(self):
        return self._command

    @property
    def version(self):
        return self._version

    @property
    def version_string(self):
        return self._version_string

    @property
    def install_dir(self):
        return self._install_dir

    @property
    def use_sudo(self):
        return self._use_sudo

    @property
    def use_user(self):
        return self._use_user

    @property
    def virtual_env(self):
        return self._virtual_env

    @property
    def available(self):
        return self._command is not None

    def trigger_refresh(self):
        self._reset()
        try:
            self._setup_pip()
        except Exception:
            self._logger.exception("Error while discovering pip command")
            self._command = None
            self._version = None
        self.refresh = False

    def execute(self, *args, **kwargs):
        if self.refresh:
            self.trigger_refresh()

        if self._command is None:
            raise UnknownPip()

        arg_list = list(args)

        if "install" in arg_list:
            arg_list = self.clean_install_command(
                arg_list, self.version, self._virtual_env, self.use_user, self.force_user
            )

        # add args to command
        if isinstance(self._command, list):
            command = self._command + list(arg_list)
        else:
            command = [self._command] + list(arg_list)

        # add sudo if necessary
        if self._use_sudo or self.force_sudo:
            command = ["sudo"] + command

        return self.call(command, **kwargs)

    def _setup_pip(self):
        pip_command, pip_sudo = self._get_pip_command()
        if pip_command is None:
            return

        # Determine the pip version

        self._logger.debug("Going to figure out pip's version")

        pip_version, version_segment = self._get_pip_version(pip_command)
        if pip_version is None:
            return

        if pip_version in self.__class__.broken:
            self._logger.error(
                "This version of pip is known to have bugs that make it incompatible with how it needs "
                "to be used by OctoPrint. Please upgrade your pip version."
            )
            return

        # Now figure out if pip belongs to a virtual environment and if the
        # default installation directory is writable.
        #
        # The idea is the following: If OctoPrint is installed globally,
        # the site-packages folder is probably not writable by our user.
        # However, the user site-packages folder as usable by providing the
        # --user parameter during install is. This we may not use though if
        # the provided pip belongs to a virtual env (since that hiccups hard).
        #
        # So we figure out the installation directory, check if it's writable
        # and if not if pip belongs to a virtual environment. Only if the
        # installation directory is NOT writable by us but we also don't run
        # in a virtual environment may we proceed with the --user parameter.

        ok, pip_user, pip_virtual_env, pip_install_dir = self._check_pip_setup(
            pip_command
        )
        if not ok:
            if pip_install_dir:
                self._logger.error(
                    "Cannot use this pip install, can't write to the install dir and also can't use "
                    "--user for installing. Check your setup and the permissions on {}.".format(
                        pip_install_dir
                    )
                )
            else:
                self._logger.error(
                    "Cannot use this pip install, something's wrong with the python environment. "
                    "Check the lines before."
                )
            return

        self._command = pip_command
        self._version = pip_version
        self._version_string = version_segment
        self._use_sudo = pip_sudo
        self._use_user = pip_user
        self._virtual_env = pip_virtual_env
        self._install_dir = pip_install_dir

    def _get_pip_command(self):
        pip_command = self.configured

        if pip_command is not None and pip_command.startswith("sudo "):
            pip_command = pip_command[len("sudo ") :]
            pip_sudo = True
        else:
            pip_sudo = False

        if pip_command is None:
            pip_command = self.autodetect_pip()

        return pip_command, pip_sudo

    @classmethod
    def autodetect_pip(cls):
        commands = [
            [sys.executable, "-m", "pip"],
            [
                os.path.join(
                    os.path.dirname(sys.executable),
                    "pip.exe" if sys.platform == "win32" else "pip",
                )
            ],
            # this should be our last resort since it might fail thanks to using pip programmatically like
            # that is not officially supported or sanctioned by the pip developers
            [
                sys.executable,
                "-c",
                "import sys; sys.argv = ['pip'] + sys.argv[1:]; import pip; pip.main()",
            ],
        ]

        for command in commands:
            p = sarge.run(
                command + ["--version"],
                close_fds=CLOSE_FDS,
                stdout=sarge.Capture(),
                stderr=sarge.Capture(),
            )
            if p.returncode == 0:
                logging.getLogger(__name__).info(
                    'Using "{}" as command to invoke pip'.format(" ".join(command))
                )
                return command

        return None

    @classmethod
    def to_sarge_command(cls, pip_command, *args):
        if isinstance(pip_command, list):
            sarge_command = pip_command
        else:
            sarge_command = [pip_command]
        return sarge_command + list(args)

    def _get_pip_version(self, pip_command):
        # Debugging this with PyCharm/IntelliJ with Python plugin and no output is being
        # generated? PyCharm bug. Disable "Attach to subprocess automatically when debugging"
        # in IDE Settings or patch pydevd.py
        # -> https://youtrack.jetbrains.com/issue/PY-18365#comment=27-1290453

        pip_command_str = pip_command
        if isinstance(pip_command_str, list):
            pip_command_str = " ".join(pip_command_str)

        with _cache_mutex:
            if not self.ignore_cache and pip_command_str in _cache["version"]:
                self._logger.debug(
                    f"Using cached pip version information for {pip_command_str}"
                )
                return _cache["version"][pip_command_str]

            sarge_command = self.to_sarge_command(pip_command, "--version")
            p = sarge.run(
                sarge_command,
                close_fds=CLOSE_FDS,
                stdout=sarge.Capture(),
                stderr=sarge.Capture(),
            )

            if p.returncode != 0:
                self._logger.warning(
                    f"Error while trying to run pip --version: {p.stderr.text}"
                )
                return None, None

            output = PipCaller._preprocess(p.stdout.text)
            # output should look something like this:
            #
            #     pip <version> from <path> (<python version>)
            #
            # we'll just split on whitespace and then try to use the second entry

            if not output.startswith("pip"):
                self._logger.warning(
                    "pip command returned unparsable output, can't determine version: {}".format(
                        output
                    )
                )

            split_output = list(map(lambda x: x.strip(), output.split()))
            if len(split_output) < 2:
                self._logger.warning(
                    "pip command returned unparsable output, can't determine version: {}".format(
                        output
                    )
                )

            version_segment = split_output[1]

            try:
                pip_version = pkg_resources.parse_version(version_segment)
            except Exception:
                self._logger.exception(
                    "Error while trying to parse version string from pip command"
                )
                return None, None

            self._logger.info(f"Version of pip is {version_segment}")

            result = pip_version, version_segment
            _cache["version"][pip_command_str] = result
            return result

    def _check_pip_setup(self, pip_command):
        pip_command_str = pip_command
        if isinstance(pip_command_str, list):
            pip_command_str = " ".join(pip_command_str)

        with _cache_mutex:
            if not self.ignore_cache and pip_command_str in _cache["setup"]:
                self._logger.debug(
                    f"Using cached pip setup information for {pip_command_str}"
                )
                return _cache["setup"][pip_command_str]

            # This is horribly ugly and I'm sorry...
            #
            # While we can figure out the install directory, if that's writable and if a virtual environment
            # is active for pip that belongs to our sys.executable python instance by just checking some
            # variables, we can't for stuff like third party software we allow to update via the software
            # update plugin.
            #
            # What we do instead for these situations is try to install the testballoon dummy package, which
            # collects that information for us. The install fails expectedly and pip prints the required
            # information together with its STDOUT (until pip v19) or STDERR (from pip v20 on).
            #
            # Yeah, I'm not happy with that either. But as long as there's no way to otherwise figure
            # out for a generic pip command whether OctoPrint can even install anything with that
            # and if so how, well, that's how we'll have to do things.

            import os

            testballoon = os.path.join(
                os.path.realpath(os.path.dirname(__file__)), "piptestballoon"
            )

            sarge_command = self.to_sarge_command(pip_command, "install", ".")
            try:
                # our testballoon is no real package, so this command will fail - that's ok though,
                # we only need the output produced within the pip environment
                p = sarge.run(
                    sarge_command,
                    close_fds=CLOSE_FDS,
                    stdout=sarge.Capture(),
                    stderr=sarge.Capture(),
                    cwd=testballoon,
                )
            except Exception:
                self._logger.exception(
                    "Error while trying to install testballoon to figure out pip setup"
                )
                return False, False, False, None

            output = p.stdout.text + p.stderr.text
            data = {}
            for line in output.split("\n"):
                if (
                    "PIP_INSTALL_DIR=" in line
                    or "PIP_VIRTUAL_ENV=" in line
                    or "PIP_WRITABLE=" in line
                ):
                    key, value = line.split("=", 2)
                    data[key.strip()] = value.strip()

            install_dir_str = data.get("PIP_INSTALL_DIR", None)
            virtual_env_str = data.get("PIP_VIRTUAL_ENV", None)
            writable_str = data.get("PIP_WRITABLE", None)

            if (
                install_dir_str is not None
                and virtual_env_str is not None
                and writable_str is not None
            ):
                install_dir = install_dir_str
                virtual_env = virtual_env_str == "True"
                writable = writable_str == "True"

                can_use_user_flag = not virtual_env and site.ENABLE_USER_SITE

                ok = writable or can_use_user_flag
                user_flag = not writable and can_use_user_flag

                self._logger.info(
                    "pip installs to {} (writable -> {}), --user flag needed -> {}, "
                    "virtual env -> {}".format(
                        install_dir,
                        "yes" if writable else "no",
                        "yes" if user_flag else "no",
                        "yes" if virtual_env else "no",
                    )
                )
                self._logger.info("==> pip ok -> {}".format("yes" if ok else "NO!"))

                # ok, enable user flag, virtual env yes/no, installation dir
                result = ok, user_flag, virtual_env, install_dir
                _cache["setup"][pip_command_str] = result
                return result
            else:
                self._logger.error(
                    "Could not detect desired output from testballoon install, got this instead: {!r}".format(
                        data
                    )
                )
                return False, False, False, None

    def _preprocess_lines(self, *lines: List[str]) -> List[str]:
        return list(map(self._preprocess, lines))

    @staticmethod
    def _preprocess(text: str) -> str:
        """
        Strips ANSI and VT100 cursor control characters from line.

        Parameters:
            text (str): The text to process

        Returns:
            (str) The processed text, stripped of ANSI and VT100 cursor show/hide codes

        Example::

            >>> text = 'some text with some\x1b[?25h ANSI codes for \x1b[31mred words\x1b[39m and\x1b[?25l also some cursor control codes'
            >>> PipCaller._preprocess(text)
            'some text with some ANSI codes for red words and also some cursor control codes'
        """
        return clean_ansi(text)


class LocalPipCaller(PipCaller):
    """
    The LocalPipCaller always uses the pip instance associated with
    sys.executable.
    """

    def _get_pip_command(self):
        return self.autodetect_pip(), False

    def _check_pip_setup(self, pip_command):
        import os
        import sys
        from distutils.sysconfig import get_python_lib

        virtual_env = hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        )
        install_dir = get_python_lib()
        writable = os.access(install_dir, os.W_OK)

        can_use_user_flag = not virtual_env and site.ENABLE_USER_SITE
        user_flag = not writable and can_use_user_flag

        ok = writable or can_use_user_flag

        self._logger.info(
            "pip installs to {} (writable -> {}), --user flag needed -> {}, "
            "virtual env -> {}".format(
                install_dir,
                "yes" if writable else "no",
                "yes" if user_flag else "no",
                "yes" if virtual_env else "no",
            )
        )
        self._logger.info("==> pip ok -> {}".format("yes" if ok else "NO!"))

        return ok, user_flag, virtual_env, install_dir


def create_pip_caller(command=None, **kwargs):
    if command is None:
        return LocalPipCaller(**kwargs)
    else:
        return PipCaller(configured=command, **kwargs)
