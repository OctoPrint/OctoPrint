.. _sec-plugins-helpers:

Helpers
=======

Helpers are methods that plugin can exposed to other plugins in order to make common functionality available on the
system. They are registered with the OctoPrint plugin system through the use of the control property ``__plugin_helpers__``.

An example for providing some helper functions to the system can be found in the
`Discovery Plugin <https://github.com/foosel/OctoPrint/wiki/Plugin:-Discovery>`_,
which provides it's SSDP browsing and Zeroconf browsing and publishing functions as helper methods.

.. code-block:: python
   :linenos:
   :emphasize-lines: 11-20
   :caption: Excerpt from the Discovery Plugin showing the declaration of its exported helpers.
   :name: sec-plugin-concepts-helpers-example-export

   def __plugin_load__():
       if not pybonjour:
           # no pybonjour available, we can't use that
           logging.getLogger("octoprint.plugins." + __name__).info("pybonjour is not installed, Zeroconf Discovery won't be available")

       plugin = DiscoveryPlugin()

       global __plugin_implementation__
       __plugin_implementation__ = plugin

       global __plugin_helpers__
       __plugin_helpers__ = dict(
           ssdp_browse=plugin.ssdp_browse
       )
       if pybonjour:
           __plugin_helpers__.update(dict(
               zeroconf_browse=plugin.zeroconf_browse,
               zeroconf_register=plugin.zeroconf_register,
               zeroconf_unregister=plugin.zeroconf_unregister
           ))

An example of how to use helpers can be found in the `Growl Plugin <https://github.com/OctoPrint/OctoPrint-Growl>`_.
Using :meth:`~octoprint.plugin.code.PluginManager.get_helpers` plugins can retrieve exported helper methods and call
them as (hopefully) documented.

.. code-block:: python
   :linenos:
   :emphasize-lines: 6-8,20
   :caption: Excerpt from the Growl Plugin showing utilization of the helpers published by the Discovery Plugin.
   :name: sec-plugin-concepts-helpers-example-usage

   def on_after_startup(self):
       host = self._settings.get(["hostname"])
       port = self._settings.getInt(["port"])
       password = self._settings.get(["password"])

       helpers = self._plugin_manager.get_helpers("discovery", "zeroconf_browse")
       if helpers and "zeroconf_browse" in helpers:
           self.zeroconf_browse = helpers["zeroconf_browse"]

       self.growl, _ = self._register_growl(host, port, password=password)

   # ...

   def on_api_get(self, request):
       if not self.zeroconf_browse:
           return flask.jsonify(dict(
               browsing_enabled=False
           ))

       browse_results = self.zeroconf_browse("_gntp._tcp", block=True)
       growl_instances = [dict(name=v["name"], host=v["host"], port=v["port"]) for v in browse_results]

       return flask.jsonify(dict(
           browsing_enabled=True,
           growl_instances=growl_instances
       ))

