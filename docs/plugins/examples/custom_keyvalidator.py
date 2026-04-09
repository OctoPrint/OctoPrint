# Needs OctoPrint 1.4.0 or newer


def hook(apikey, *args, **kwargs):
    from octoprint.server import userManager

    return userManager.find_user(userid=apikey)


__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_hooks__ = {"octoprint.accesscontrol.keyvalidator": hook}
