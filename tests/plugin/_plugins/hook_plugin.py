# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals


def hook_startup():
    return "success"


__plugin_name__ = "Hook Plugin"
__plugin_description__ = "Test hook plugin"
__plugin_hooks__ = {
    "octoprint.core.startup": hook_startup,
    "some.ordered.callback": hook_startup,
}
__plugin_pythoncompat__ = ">=2.7,<4"
