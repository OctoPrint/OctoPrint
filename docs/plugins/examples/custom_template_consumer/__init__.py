import octoprint.plugin


class CustomTemplateTypeConsumer(octoprint.plugin.TemplatePlugin):
    def get_template_configs(self):
        if "custom_template_provider" not in self._plugin_manager.enabled_plugins:
            # if our custom template provider is not registered, we'll act as a regular settings plugin
            return [
                dict(
                    type="settings",
                    template="custom_template_consumer_awesometemplate.jinja2",
                )
            ]
        else:
            # else we'll inject ourselves as an awesometemplate type instead - since we named our jinja2 file
            # accordingly we don't have to explicitly define that here, it will be picked up automatically
            return []


__plugin_name__ = "Custom Template Consumer"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_implementation__ = CustomTemplateTypeConsumer()
