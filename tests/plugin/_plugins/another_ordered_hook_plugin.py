def callback(*args, **kwargs):
    pass


__plugin_hooks__ = {"some.ordered.callback": (callback, 100)}
__plugin_pythoncompat__ = ">=2.7,<4"
