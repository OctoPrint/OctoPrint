"""
Place in ~/.octoprint/plugins & restart server to test:

  * python_checker and python_updater mechanism
  * demotion of pip and python setup.py clean output that
    gets written to stderr but isn't as severe as that would
    look

Plugin will always demand to update itself, multiple
consecutive runs are not a problem.
"""

import time

NAME = "Always Update"
OLD_VERSION = "1.0.0"
NEW_VERSION = "2.0.0"


class Foo:
    def get_latest(self, target, check, full_data=None):
        information = {
            "local": {"name": OLD_VERSION, "value": OLD_VERSION},
            "remote": {"name": NEW_VERSION, "value": NEW_VERSION},
        }
        current = False
        return information, current

    def can_perform_update(self, target, check):
        return True

    def perform_update(self, target, check, target_version, log_cb=None):
        if not callable(log_cb):
            import sys

            def log_cb(lines, prefix=None, stream=None, strip=True):
                if stream == "stdout":
                    f = sys.stdout
                elif stream == "stderr":
                    f = sys.stderr
                else:
                    f = None

                for line in lines:
                    print(line, file=f)

        log_cb(["Updating Always Update..."])
        time.sleep(1)
        log_cb(
            ["running clean", "recursively removing *.pyc from 'src'"], stream="stdout"
        )
        log_cb(
            [
                "'build/lib' does not exist -- can't clean it",
                "'build/bdist.win32' does not exist -- can't clean it",
                "'build/scripts-2.7' does not exist -- can't clean it",
            ],
            stream="stderr",
        )
        log_cb(
            [
                "removing 'Development\\OctoPrint\\OctoPrint\\src\\octoprint_setuptools\\__init__.pyc'"
            ],
            stream="stdout",
        )
        time.sleep(1)
        log_cb(["This should be red"], stream="stderr")
        log_cb(
            [
                "You are using pip version 7.1.2, however version 9.0.1 is available.",
                "You should consider upgrading via the 'python -m pip install --upgrade pip' command.",
            ],
            stream="stderr",
        )
        time.sleep(3)
        log_cb(["Done!"])


def get_update_information():
    foo = Foo()
    return {
        "always_update": {
            "displayName": NAME,
            "displayVersion": OLD_VERSION,
            "type": "python_checker",
            "python_checker": foo,
            "python_updater": foo,
        }
    }


__plugin_name__ = NAME
__plugin_hooks__ = {
    "octoprint.plugin.softwareupdate.check_config": get_update_information,
}
