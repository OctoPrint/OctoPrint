"""
This module bundles all of OctoPrint's supported plugin implementation types as well as their common parent
class, :class:`OctoPrintPlugin`.

Please note that the plugin implementation types are documented in the section
:ref:`Available plugin mixins <sec-plugins-mixins>`.

.. autoclass:: OctoPrintPlugin
   :show-inheritance:
   :members:

.. autoclass:: ReloadNeedingPlugin
   :show-inheritance:
   :members:

"""

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


from .core import Plugin, RestartNeedingPlugin, SortablePlugin


class OctoPrintPlugin(Plugin):
    """
    The parent class of all OctoPrint plugin mixins.

    .. attribute:: _plugin_manager

       The :class:`~octoprint.plugin.core.PluginManager` instance. Injected by the plugin core system upon
       initialization of the implementation.

    .. attribute:: _printer_profile_manager

       The :class:`~octoprint.printer.profile.PrinterProfileManager` instance. Injected by the plugin core system upon
       initialization of the implementation.

    .. attribute:: _event_bus

       The :class:`~octoprint.events.EventManager` instance. Injected by the plugin core system upon initialization of
       the implementation.

    .. attribute:: _analysis_queue

       The :class:`~octoprint.filemanager.analysis.AnalysisQueue` instance. Injected by the plugin core system upon
       initialization of the implementation.

    .. attribute:: _slicing_manager

       The :class:`~octoprint.slicing.SlicingManager` instance. Injected by the plugin core system upon initialization
       of the implementation.

    .. attribute:: _file_manager

       The :class:`~octoprint.filemanager.FileManager` instance. Injected by the plugin core system upon initialization
       of the implementation.

    .. attribute:: _printer

       The :class:`~octoprint.printer.PrinterInterface` instance. Injected by the plugin core system upon initialization
       of the implementation.

    .. attribute:: _app_session_manager

       The :class:`~octoprint.access.users.SessionManager` instance. Injected by the plugin core system upon initialization of
       the implementation.

    .. attribute:: _plugin_lifecycle_manager

       The :class:`~octoprint.server.LifecycleManager` instance. Injected by the plugin core system upon initialization
       of the implementation.

    .. attribute:: _user_manager

       The :class:`~octoprint.access.users.UserManager` instance. Injected by the plugin core system upon initialization
       of the implementation.

    .. attribute:: _connectivity_checker

       The :class:`~octoprint.util.ConnectivityChecker` instance. Injected by the plugin core system upon initialization
       of the implementation.

    .. attribute:: _data_folder

       Path to the data folder for the plugin to use for any data it might have to persist. Should always be accessed
       through :meth:`get_plugin_data_folder` since that function will also ensure that the data folder actually exists
       and if not creating it before returning it. Injected by the plugin core system upon initialization of the
       implementation.
    """

    # noinspection PyMissingConstructor
    def __init__(self):
        self._plugin_manager = None
        self._printer_profile_manager = None
        self._event_bus = None
        self._analysis_queue = None
        self._slicing_manager = None
        self._file_manager = None
        self._printer = None
        self._app_session_manager = None
        self._plugin_lifecycle_manager = None
        self._user_manager = None
        self._connectivity_checker = None
        self._data_folder = None

    def get_plugin_data_folder(self):
        """
        Retrieves the path to a data folder specifically for the plugin, ensuring it exists and if not creating it
        before returning it.

        Plugins may use this folder for storing additional data they need for their operation.
        """
        if self._data_folder is None:
            raise RuntimeError(
                "self._plugin_data_folder is None, has the plugin been initialized yet?"
            )

        import os

        os.makedirs(self._data_folder, exist_ok=True)
        return self._data_folder

    def on_plugin_pending_uninstall(self):
        """
        Called by the plugin manager when the plugin is pending uninstall. Override this to react to the event.

        NOT called during plugin uninstalls triggered outside of OctoPrint!
        """
        pass


class ReloadNeedingPlugin(Plugin):
    """
    Mixin for plugin types that need a reload of the UI after enabling/disabling them.
    """


class EnvironmentDetectionPlugin(OctoPrintPlugin, RestartNeedingPlugin):
    """
    .. versionadded:: 1.3.6
    """

    def get_additional_environment(self):
        pass

    def on_environment_detected(self, environment, *args, **kwargs):
        pass


class StartupPlugin(OctoPrintPlugin, SortablePlugin):
    """
    The ``StartupPlugin`` allows hooking into the startup of OctoPrint. It can be used to start up additional services
    on or just after the startup of the server.

    ``StartupPlugin`` is a :class:`~octoprint.plugin.core.SortablePlugin` and provides
    sorting contexts for :meth:`~octoprint.plugin.StartupPlugin.on_startup` as well as
    :meth:`~octoprint.plugin.StartupPlugin.on_after_startup`.
    """

    def on_startup(self, host, port):
        """
        Called just before the server is actually launched. Plugins get supplied with the ``host`` and ``port`` the server
        will listen on. Note that the ``host`` may be ``0.0.0.0`` if it will listen on all interfaces, so you can't just
        blindly use this for constructing publicly reachable URLs. Also note that when this method is called, the server
        is not actually up yet and none of your plugin's APIs or blueprints will be reachable yet. If you need to be
        externally reachable, use :func:`on_after_startup` instead or additionally.

        .. warning::

           Do not perform long-running or even blocking operations in your implementation or you **will** block and break the server.

        The relevant sorting context is ``StartupPlugin.on_startup``.

        :param string host: the host the server will listen on, may be ``0.0.0.0``
        :param int port:    the port the server will listen on
        """

        pass

    def on_after_startup(self):
        """
        Called just after launch of the server, so when the listen loop is actually running already.

        .. warning::

           Do not perform long-running or even blocking operations in your implementation or you **will** block and break the server.

        The relevant sorting context is ``StartupPlugin.on_after_startup``.
        """

        pass


class ShutdownPlugin(OctoPrintPlugin, SortablePlugin):
    """
    The ``ShutdownPlugin`` allows hooking into the shutdown of OctoPrint. It's usually used in conjunction with the
    :class:`StartupPlugin` mixin, to cleanly shut down additional services again that where started by the :class:`StartupPlugin`
    part of the plugin.

    ``ShutdownPlugin`` is a :class:`~octoprint.plugin.core.SortablePlugin` and provides a sorting context for
    :meth:`~octoprint.plugin.ShutdownPlugin.on_shutdown`.
    """

    def on_shutdown(self):
        """
        Called upon the imminent shutdown of OctoPrint.

        .. warning::

           Do not perform long-running or even blocking operations in your implementation or you **will** block and break the server.

        The relevant sorting context is ``ShutdownPlugin.on_shutdown``.
        """
        pass


class AssetPlugin(OctoPrintPlugin, RestartNeedingPlugin):
    """
    The ``AssetPlugin`` mixin allows plugins to define additional static assets such as JavaScript or CSS files to
    be automatically embedded into the pages delivered by the server to be used within the client sided part of
    the plugin.

    A typical usage of the ``AssetPlugin`` functionality is to embed a custom view model to be used by templates injected
    through a :class:`TemplatePlugin`.

    ``AssetPlugin`` is a :class:`~octoprint.plugins.core.RestartNeedingPlugin`.
    """

    def get_asset_folder(self):
        """
        Defines the folder where the plugin stores its static assets as defined in :func:`get_assets`. Override this if
        your plugin stores its assets at some other place than the ``static`` sub folder in the plugin base directory.

        :return string: the absolute path to the folder where the plugin stores its static assets
        """
        import os

        return os.path.join(self._basefolder, "static")

    def get_assets(self):
        """
        Defines the static assets the plugin offers. The following asset types are recognized and automatically
        imported at the appropriate places to be available:

        js
           JavaScript files, such as additional view models
        jsclient
           JavaScript files containing additional parts for the JS Client Library (since 1.3.10)
        css
           CSS files with additional styles, will be embedded into delivered pages when not running in LESS mode.
        less
           LESS files with additional styles, will be embedded into delivered pages when running in LESS mode.

        The expected format to be returned is a dictionary mapping one or more of these keys to a list of files of that
        type, the files being represented as relative paths from the asset folder as defined via :func:`get_asset_folder`.
        Example:

        .. code-block:: python

           def get_assets(self):
               return dict(
                   js=['js/my_file.js', 'js/my_other_file.js'],
                   clientjs=['clientjs/my_file.js'],
                   css=['css/my_styles.css'],
                   less=['less/my_styles.less']
                )

        The assets will be made available by OctoPrint under the URL ``/plugin/<plugin identifier>/static/<path>``, with
        ``plugin identifier`` being the plugin's identifier and ``path`` being the path as defined in the asset dictionary.

        Assets of the types ``js``, ``css`` and ``less`` will be automatically bundled by OctoPrint using
        `Flask-Assets <http://flask-assets.readthedocs.org/en/latest/>`_.

        :return dict: a dictionary describing the static assets to publish for the plugin
        """
        return {}


class TemplatePlugin(OctoPrintPlugin, ReloadNeedingPlugin):
    """
    Using the ``TemplatePlugin`` mixin plugins may inject their own components into the OctoPrint web interface.

    Currently OctoPrint supports the following types of injections out of the box:

    Navbar
       The right part of the navigation bar located at the top of the UI can be enriched with additional links. Note that
       with the current implementation, plugins will always be located *to the left* of the existing links.

       The included template must be called ``<plugin identifier>_navbar.jinja2`` (e.g. ``myplugin_navbar.jinja2``) unless
       overridden by the configuration supplied through :func:`get_template_configs`.

       The template will be already wrapped into the necessary structure, plugins just need to supply the pure content. The
       wrapper structure will have all additional classes and styles applied as specified via the configuration supplied
       through :func:`get_template_configs`.

    Sidebar
       The left side bar containing Connection, State and Files sections can be enriched with additional sections. Note
       that with the current implementations, plugins will always be located *beneath* the existing sections.

       The included template must be called ``<plugin identifier>_sidebar.jinja2`` (e.g. ``myplugin_sidebar.jinja2``) unless
       overridden by the configuration supplied through :func:`get_template_configs`.

       The template will be already wrapped into the necessary structure, plugins just need to supply the pure content. The
       wrapper divs for both the whole box as well as the content pane will have all additional classes and styles applied
       as specified via the configuration supplied through :func:`get_template_configs`.

    Tabs
       The available tabs of the main part of the interface may be extended with additional tabs originating from within
       plugins. Note that with the current implementation, plugins will always be located *to the right* of the existing
       tabs.

       The included template must be called ``<plugin identifier>_tab.jinja2`` (e.g. ``myplugin_tab.jinja2``) unless
       overridden by the configuration supplied through :func:`get_template_configs`.

       The template will be already wrapped into the necessary structure, plugins just need to supply the pure content. The
       wrapper div and the link in the navigation will have the additional classes and styles applied as specified via the
       configuration supplied through :func:`get_template_configs`.

    Settings
       Plugins may inject a dialog into the existing settings view. Note that with the current implementation, plugins
       will always be listed beneath the "Plugins" header in the settings link list, ordered alphabetically after
       their displayed name.

       The included template must be called ``<plugin identifier>_settings.jinja2`` (e.g. ``myplugin_settings.jinja2``) unless
       overridden by the configuration supplied through :func:`get_template_configs`.

       The template will be already wrapped into the necessary structure, plugins just need to supply the pure content. The
       wrapper div and the link in the navigation will have the additional classes and styles applied as defined via the
       configuration through :func:`get_template_configs`.

    Webcam
       Plugins can provide a custom webcam view for watching a camera stream, which will be embedded into the "Control"
       panel of OctoPrint's default UI.

       The included template must be called ``<plugin identifier>_webcam.jinja2`` (e.g. ``myplugin_webcam.jinja2``) unless
       overridden by the configuration supplied through :func:`get_template_configs`.

       The template will be already wrapped into the necessary structure, plugins just need to supply the pure content. The
       wrapper div will have the additional classes and styles applied as defined via the configuration through :func:`get_template_configs`.

       .. versionadded:: 1.9.0

    Wizards
       Plugins may define wizard dialogs to display to the user if necessary (e.g. in case of missing information that
       needs to be queried from the user to make the plugin work). Note that with the current implementation, all
       wizard dialogs will be will always be sorted by their ``mandatory`` attribute (which defaults to ``False``) and then
       alphabetically by their ``name``. Hence, mandatory wizard steps will come first, sorted alphabetically, then the
       optional steps will follow, also alphabetically. A wizard dialog provided through a plugin will only be displayed
       if the plugin reports the wizard as being required through :meth:`~octoprint.plugin.WizardPlugin.is_wizard_required`.
       Please also refer to the :class:`~octoprint.plugin.WizardPlugin` mixin for further details on this.

       The included template must be called ``<plugin identifier>_wizard.jinja2`` (e.g. ``myplugin_wizard.jinja2``) unless
       overridden by the configuration supplied through :func:`get_template_configs`.

       The template will be already wrapped into the necessary structure, plugins just need to supply the pure content.
       The wrapper div and the link in the wizard navigation will have the additional classes and styles applied as defined
       via the configuration supplied through :func:`get_template_configs`.

       .. note::

          A note about ``mandatory`` wizard steps: In the current implementation, marking a wizard step as
          mandatory will *only* make it styled accordingly. It is the task of the :ref:`view model <sec-plugins-viewmodels>`
          to actually prevent the user from skipping the dialog by implementing the ``onWizardTabChange``
          callback and returning ``false`` there if it is detected that the user hasn't yet filled in the
          wizard step.

       .. versionadded:: 1.3.0

    About
       Plugins may define additional panels into OctoPrint's "About" dialog. Note that with the current implementation
       further about dialog panels will be sorted alphabetically by their name and sorted after the predefined ones.

       The included template must be called ``<plugin identifier>_about.jinja2`` (e.g. ``myplugin_about.jinja2``) unless
       overridden by the configuration supplied through :func:`get_template_configs`.

       The template will be already wrapped into the necessary structure, plugins just need to supply the pure content. The
       wrapped div and the link in the navigation will have the additional classes and styles applied as defined via
       the configuration supplied through :func:`get_template_configs`.

       .. versionadded:: 1.3.0

    Generic
       Plugins may also inject arbitrary templates into the page of the web interface itself, e.g. in order to
       add overlays or dialogs to be called from within the plugin's JavaScript code.

    .. figure:: ../images/template-plugin-types-main.png
       :align: center
       :alt: Template injection types in the main part of the interface

       Template injection types in the main part of the interface

    .. figure:: ../images/template-plugin-types-settings.png
       :align: center
       :alt: Template injection types in the settings

       Template injection types in the settings

    You can find an example for a simple plugin which injects navbar, tab and settings content into the interface in
    the "helloworld" plugin in OctoPrint's :ref:`Plugin Tutorial <sec-plugins-gettingstarted>`.

    Plugins may replace existing components, see the ``replaces`` keyword in the template configurations returned by
    :meth:`.get_template_configs` below. Note that if a plugin replaces a core component, it is the plugin's
    responsibility to ensure that all core functionality is still maintained.

    Plugins can also add additional template types by implementing the :ref:`octoprint.ui.web.templatetypes <sec-plugins-hook-ui-web-templatetypes>` hook.

    ``TemplatePlugin`` is a :class:`~octoprint.plugin.core.ReloadNeedingPlugin`.
    """

    @property
    def template_folder_key(self):
        return f"plugin_{self._identifier}"

    def get_template_configs(self):
        """
        Allows configuration of injected navbar, sidebar, tab and settings templates (and also additional templates of
        types specified by plugins through the :ref:`octoprint.ui.web.templatetypes <sec-plugins-hook-ui-web-templatetypes>` hook).
        Should be a list containing one configuration object per template to inject. Each configuration object is
        represented by a dictionary which may contain the following keys:

        .. list-table::
           :widths: 5 95

           * - type
             - The template type the configuration is targeting. Possible values here are ``navbar``, ``sidebar``,
               ``tab``, ``settings`` and ``generic``. Mandatory.
           * - name
             - The name of the component, if not set the name of the plugin will be used. The name will be visible at
               a location depending on the ``type``:

                 * ``navbar``: unused
                 * ``sidebar``: sidebar heading
                 * ``tab``: tab heading
                 * ``settings``: settings link
                 * ``wizard``: wizard link
                 * ``about``: about link
                 * ``generic``: unused

           * - template
             - Name of the template to inject, default value depends on the ``type``:

                 * ``navbar``: ``<plugin identifier>_navbar.jinja2``
                 * ``sidebar``: ``<plugin identifier>_sidebar.jinja2``
                 * ``tab``: ``<plugin identifier>_tab.jinja2``
                 * ``settings``: ``<plugin identifier>_settings.jinja2``
                 * ``wizard``: ``<plugin identifier>_wizard.jinja2``
                 * ``about``: ``<plugin identifier>_about.jinja2``
                 * ``generic``: ``<plugin identifier>.jinja2``

           * - suffix
             - Suffix to attach to the component identifier and the div identifier of the injected template. Will be
               ``_<index>`` if not provided and not the first template of the type, with ``index`` counting from 1 and
               increasing for each template of the same type.

               Example: If your plugin with identifier ``myplugin`` defines two tab components like this:

               .. code-block:: python

                  return [
                      dict(type="tab", template="myplugin_first_tab.jinja2"),
                      dict(type="tab", template="myplugin_second_tab.jinja2")
                  ]

               then the first tab will have the component identifier ``plugin_myplugin`` and the second one will have
               the component identifier ``plugin_myplugin_2`` (the generated divs will be ``tab_plugin_myplugin`` and
               ``tab_plugin_myplugin_2`` accordingly). Notice that the first tab is *not* called ``plugin_myplugin_1`` --
               as stated above while the ``index`` used as default suffix starts counting at 1, it will not be applied
               for the first component of a given type.

               If on the other hand your plugin's definition looks like this:

               .. code-block:: python

                  return [
                      dict(type="tab", template="myplugin_first_tab_jinja2", suffix="_1st"),
                      dict(type="tab", template="myplugin_second_tab_jinja2", suffix="_2nd")
                  ]

               then the generated component identifier will be ``plugin_myplugin_1st`` and ``plugin_myplugin_2nd``
               (and the divs will be ``tab_plugin_myplugin_1st`` and ``tab_plugin_myplugin_2nd``).

           * - div
             - Id for the div containing the component. If not provided, defaults to ``<type>_plugin_<plugin identifier>`` plus
               the ``suffix`` if provided or required.
           * - replaces
             - Id of the component this one replaces, might be either one of the core components or a component
               provided by another plugin. A list of the core component identifiers can be found
               :ref:`in the configuration documentation <sec-configuration-config_yaml-appearance>`. The identifiers of
               other plugin components always follow the format described above.
           * - custom_bindings
             - A boolean value indicating whether the default view model should be bound to the component (``false``)
               or if a custom binding will be used by the plugin (``true``, default).
           * - data_bind
             - Additional knockout data bindings to apply to the component, can be used to add further behaviour to
               the container based on internal state if necessary.
           * - classes
             - Additional classes to apply to the component, as a list of individual classes
               (e.g. ``classes=["myclass", "myotherclass"]``) which will be joined into the correct format by the template engine.
           * - styles
             - Additional CSS styles to apply to the component, as a list of individual declarations
               (e.g. ``styles=["color: red", "display: block"]``) which will be joined into the correct format by the template
               engine.

        Further keys to be included in the dictionary depend on the type:

        ``sidebar`` type

           .. list-table::
              :widths: 5 95

              * - icon
                - Icon to use for the sidebar header, should be the full name of a Font Awesome icon including the ``fas``/``far``/``fab`` prefix, eg. ``fas fa-plus``.
              * - template_header
                - Additional template to include in the head section of the sidebar item. For an example of this, see the additional
                  options included in the "Files" section.
              * - classes_wrapper
                - Like ``classes`` but only applied to the whole wrapper around the sidebar box.
              * - classes_content
                - Like ``classes`` but only applied to the content pane itself.
              * - styles_wrapper
                - Like ``styles`` but only applied to the whole wrapper around the sidebar box.
              * - styles_content
                - Like ``styles`` but only applied to the content pane itself

        ``tab`` type and ``settings`` type

           .. list-table::
              :widths: 5 95

              * - classes_content
                - Like ``classes`` but only applied to the content pane itself.
              * - styles_content
                - Like ``styles`` but only applied to the content pane itself.
              * - classes_link
                - Like ``classes`` but only applied to the link in the navigation.
              * - styles_link
                - Like ``styles`` but only applied to the link in the navigation.

        ``webcam`` type

           .. list-table::
              :widths: 5 95

              * - classes_content
                - Like ``classes`` but only applied to the content pane itself.
              * - styles_content
                - Like ``styles`` but only applied to the content pane itself.

        ``wizard`` type

           .. list-table::
              :widths: 5 95

              * - mandatory
                - Whether the wizard step is mandatory (True) or not (False). Optional,
                  defaults to False. If set to True, OctoPrint will sort visually mark
                  the step as mandatory in the UI (bold in the navigation and a little
                  alert) and also sort it into the first half.

        .. note::

           As already outlined above, each template type has a default template name (i.e. the default navbar template
           of a plugin is called ``<plugin identifier>_navbar.jinja2``), which may be overridden using the template configuration.
           If a plugin needs to include more than one template of a given type, it needs to provide an entry for each of
           those, since the implicit default template will only be included automatically if no other templates of that
           type are defined.

           Example: If you have a plugin that injects two tab components, one defined in the template file
           ``myplugin_tab.jinja2`` (the default template) and one in the template ``myplugin_othertab.jinja2``, you
           might be tempted to just return the following configuration since one your templates is named by the default
           template name:

           .. code-block:: python

              return [
                  dict(type="tab", template="myplugin_othertab.jinja2")
              ]

           This will only include the tab defined in ``myplugin_othertab.jinja2`` though, ``myplugin_tab.jinja2`` will
           not be included automatically since the presence of a definition for the ``tab`` type overrides the automatic
           injection of the default template. You'll have to include it explicitly:

           .. code-block:: python

              return [
                  dict(type="tab", template="myplugin_tab.jinja2"),
                  dict(type="tab", template="myplugin_othertab.jinja2")
              ]

        :return list: a list containing the configuration options for the plugin's injected templates
        """
        return []

    def get_template_vars(self):
        """
        Defines additional template variables to include into the template renderer. Variable names will be prefixed
        with ``plugin_<plugin identifier>_``.

        :return dict: a dictionary containing any additional template variables to include in the renderer
        """
        return {}

    def get_template_folder(self):
        """
        Defines the folder where the plugin stores its templates. Override this if your plugin stores its templates at
        some other place than the ``templates`` sub folder in the plugin base directory.

        :return string: the absolute path to the folder where the plugin stores its jinja2 templates
        """
        import os

        return os.path.join(self._basefolder, "templates")


class UiPlugin(OctoPrintPlugin, SortablePlugin):
    """
    The ``UiPlugin`` mixin allows plugins to completely replace the UI served
    by OctoPrint when requesting the main page hosted at `/`.

    OctoPrint will query whether your mixin implementation will handle a
    provided request by calling :meth:`~octoprint.plugin.UiPlugin.will_handle_ui` with the Flask
    `Request <https://flask.palletsprojects.com/api/#flask.Request>`_ object as
    parameter. If you plugin returns `True` here, OctoPrint will next call
    :meth:`~octoprint.plugin.UiPlugin.on_ui_render` with a few parameters like
    - again - the Flask Request object and the render keyword arguments as
    used by the default OctoPrint web interface. For more information see below.

    There are two methods used in order to allow for caching of the actual
    response sent to the client. Whatever a plugin implementation returns
    from the call to its :meth:`~octoprint.plugin.UiPlugin.on_ui_render` method
    will be cached server side. The cache will be emptied in case of explicit
    no-cache headers sent by the client, or if the ``_refresh`` query parameter
    on the request exists and is set to ``true``. To prevent caching of the
    response altogether, a plugin may set no-cache headers on the returned
    response as well.

    ``UiPlugin`` is a :class:`~octoprint.plugin.core.SortablePlugin` with a sorting context
    for :meth:`~octoprint.plugin.UiPlugin.will_handle_ui`. The first plugin to return ``True``
    for :meth:`~octoprint.plugin.UiPlugin.will_handle_ui` will be the one whose ui will be used,
    no further calls to :meth:`~octoprint.plugin.UiPlugin.on_ui_render` will be performed.

    If implementations want to serve custom templates in the :meth:`~octoprint.plugin.UiPlugin.on_ui_render`
    method it is recommended to also implement the :class:`~octoprint.plugin.TemplatePlugin`
    mixin.

    **Example**

    What follows is a very simple example that renders a different (non functional and
    only exemplary) UI if the requesting client has a UserAgent string hinting
    at it being a mobile device:

    .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/dummy_mobile_ui/__init__.py
       :tab-width: 4
       :caption: `dummy_mobile_ui/__init__.py <https://github.com/OctoPrint/Plugin-Examples/blob/master/dummy_mobile_ui/__init__.py>`_

    .. onlineinclude:: https://raw.githubusercontent.com/OctoPrint/Plugin-Examples/master/dummy_mobile_ui/templates/dummy_mobile_ui_index.jinja2
       :tab-width: 4
       :caption: `dummy_mobile_ui/templates/dummy_mobile_ui_index.jinja2 <https://github.com/OctoPrint/Plugin-Examples/blob/master/dummy_mobile_ui/templates/dummy_mobile_ui_index.jinja2>`_

    Try installing the above plugin ``dummy_mobile_ui`` (also available in the
    `plugin examples repository <https://github.com/OctoPrint/Plugin-Examples/blob/master/dummy_mobile_ui>`_)
    into your OctoPrint instance. If you access it from a regular desktop browser,
    you should still see the default UI. However if you access it from a mobile
    device (make sure to not have that request the desktop version of pages!)
    you should see the very simple dummy page defined above.

    **Preemptive and Runtime Caching**

    OctoPrint will also cache your custom UI for you in its server side UI cache, making sure
    it only gets re-rendered if the request demands that (by having no-cache headers set) or if
    the cache gets invalidated otherwise.

    In order to be able to do that, the ``UiPlugin`` offers overriding some cache specific
    methods used for figuring out the source files whose modification time to use for cache invalidation
    as well as override possibilities for ETag and LastModified calculation. Additionally there are
    methods to allow persisting call parameters to allow for preemptively caching your UI during
    server startup (basically eager caching instead of lazily waiting for the first request).

    See below for details on this.

    .. versionadded:: 1.3.0
    """

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def will_handle_ui(self, request):
        """
        Called by OctoPrint to determine if the mixin implementation will be
        able to handle the ``request`` provided as a parameter.

        Return ``True`` here to signal that your implementation will handle
        the request and that the result of its :meth:`~octoprint.plugin.UiPlugin.on_ui_render` method
        is what should be served to the user.

        The execution order of calls to this method can be influenced via the sorting context
        ``UiPlugin.will_handle_ui``.

        Arguments:
            request (flask.Request): A Flask `Request <https://flask.palletsprojects.com/api/#flask.Request>`_
                object.

        Returns:
            bool: ``True`` if the implementation will serve the request,
                ``False`` otherwise.
        """
        return False

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def on_ui_render(self, now, request, render_kwargs):
        """
        Called by OctoPrint to retrieve the response to send to the client
        for the ``request`` to ``/``. Only called if :meth:`~octoprint.plugin.UiPlugin.will_handle_ui`
        returned ``True``.

        ``render_kwargs`` will be a dictionary (whose contents are cached) which
        will contain the following key and value pairs (note that not all
        key value pairs contained in the dictionary are listed here, only
        those you should depend on as a plugin developer at the current time):

        .. list-table::
           :widths: 5 95

           * - debug
             - ``True`` if debug mode is enabled, ``False`` otherwise.
           * - firstRun
             - ``True`` if the server is being run for the first time (not
               configured yet), ``False`` otherwise.
           * - version
             - OctoPrint's version information. This is a ``dict`` with the
               following keys:

               .. list-table::
                  :widths: 5 95

                  * - number
                    - The version number (e.g. ``x.y.z``)
                  * - branch
                    - The GIT branch from which the OctoPrint instance was built
                      (e.g. ``master``)
                  * - display
                    - The full human readable version string, including the
                      branch information (e.g. ``x.y.z (master branch)``

           * - uiApiKey
             - The UI API key to use for unauthorized API requests. This is
               freshly generated on every server restart.
           * - templates
             - Template data to render in the UI. Will be a ``dict`` containing entries
               for all known template types.

               The sub structure for each key will be as follows:

               .. list-table::
                  :widths: 5 95

                  * - order
                    - A list of template names in the order they should appear
                      in the final rendered page
                  * - entries
                    - The template entry definitions to render. Depending on the
                      template type those are either 2-tuples of a name and a ``dict``
                      or directly ``dicts`` with information regarding the
                      template to render.

                      For the possible contents of the data ``dicts`` see the
                      :class:`~octoprint.plugin.TemplatePlugin` mixin.

           * - pluginNames
             - A list of names of :class:`~octoprint.plugin.TemplatePlugin`
               implementation that were enabled when creating the ``templates``
               value.
           * - locales
             - The locales for which there are translations available.
           * - supportedExtensions
             - The file extensions supported for uploads.

        On top of that all additional template variables as provided by :meth:`~octoprint.plugin.TemplatePlugin.get_template_vars`
        will be contained in the dictionary as well.

        Arguments:
            now (datetime.datetime): The datetime instance representing "now"
                for this request, in case your plugin implementation needs this
                information.
            request (flask.Request): A Flask `Request <https://flask.palletsprojects.com/api/#flask.Request>`_ object.
            render_kwargs (dict): The (cached) render keyword arguments that
                would usually be provided to the core UI render function.

        Returns:
            flask.Response: Should return a Flask `Response <https://flask.palletsprojects.com/api/#flask.Response>`_
                object that can be served to the requesting client directly. May be
                created with ``flask.make_response`` combined with something like
                ``flask.render_template``.
        """

        return None

    # noinspection PyMethodMayBeStatic
    def get_ui_additional_key_data_for_cache(self):
        """
        Allows to return additional data to use in the cache key.

        Returns:
            list, tuple: A list or tuple of strings to use in the cache key. Will be joined by OctoPrint
                using ``:`` as separator and appended to the existing ``ui:<identifier>:<base url>:<locale>``
                cache key. Ignored if ``None`` is returned.

        .. versionadded:: 1.3.0
        """
        return None

    # noinspection PyMethodMayBeStatic
    def get_ui_additional_tracked_files(self):
        """
        Allows to return additional files to track for validating existing caches. By default OctoPrint
        will track all declared templates, assets and translation files in the system. Additional
        files can be added by a plugin through this callback.

        Returns:
            list: A list of paths to additional files whose modification to track for (in)validating
                the cache. Ignored if ``None`` is returned.

        .. versionadded:: 1.3.0
        """
        return None

    # noinspection PyMethodMayBeStatic
    def get_ui_custom_tracked_files(self):
        """
        Allows to define a complete separate set of files to track for (in)validating the cache. If this
        method returns something, the templates, assets and translation files won't be tracked, only the
        files specified in the returned list.

        Returns:
            list: A list of paths representing the only files whose modification to track for (in)validating
                the cache. Ignored if ``None`` is returned.

        .. versionadded:: 1.3.0
        """
        return None

    # noinspection PyMethodMayBeStatic
    def get_ui_custom_etag(self):
        """
        Allows to use a custom way to calculate the ETag, instead of the default method (hashing
        OctoPrint's version, tracked file paths and ``LastModified`` value).

        Returns:
            str: An alternatively calculated ETag value. Ignored if ``None`` is returned (default).

        .. versionadded:: 1.3.0
        """
        return None

    # noinspection PyMethodMayBeStatic
    def get_ui_additional_etag(self, default_additional):
        """
        Allows to provide a list of additional fields to use for ETag generation.

        By default the same list will be returned that is also used in the stock UI (and injected
        via the parameter ``default_additional``).

        Arguments:
            default_additional (list): The list of default fields added to the ETag of the default UI

        Returns:
            (list): A list of additional fields for the ETag generation, or None

        .. versionadded:: 1.3.0
        """
        return default_additional

    # noinspection PyMethodMayBeStatic
    def get_ui_custom_lastmodified(self):
        """
        Allows to calculate the LastModified differently than using the most recent modification
        date of all tracked files.

        Returns:
            int: An alternatively calculated LastModified value. Ignored if ``None`` is returned (default).

        .. versionadded:: 1.3.0
        """
        return None

    # noinspection PyMethodMayBeStatic
    def get_ui_preemptive_caching_enabled(self):
        """
        Allows to control whether the view provided by the plugin should be preemptively
        cached on server startup (default) or not.

        Have this return False if you do not want your plugin's UI to ever be preemptively cached.

        Returns:
            bool: Whether to enable preemptive caching (True, default) or not (False)
        """
        return True

    # noinspection PyMethodMayBeStatic
    def get_ui_data_for_preemptive_caching(self):
        """
        Allows defining additional data to be persisted in the preemptive cache configuration, on
        top of the request path, base URL and used locale.

        Returns:
            dict: Additional data to persist in the preemptive cache configuration.

        .. versionadded:: 1.3.0
        """
        return None

    # noinspection PyMethodMayBeStatic
    def get_ui_additional_request_data_for_preemptive_caching(self):
        """
        Allows defining additional request data to persist in the preemptive cache configuration and
        to use for the fake request used for populating the preemptive cache.

        Keys and values are used as keyword arguments for creating the
        `Werkzeug EnvironBuilder <http://werkzeug.pocoo.org/docs/0.11/test/#werkzeug.test.EnvironBuilder>`_
        used for creating the fake request.

        Returns:
            dict: Additional request data to persist in the preemptive cache configuration and to
                use for request environment construction.

        .. versionadded:: 1.3.0
        """
        return None

    # noinspection PyMethodMayBeStatic
    def get_ui_preemptive_caching_additional_unless(self):
        """
        Allows defining additional reasons for temporarily not adding a preemptive cache record for
        your plugin's UI.

        OctoPrint will call this method when processing a UI request, to determine whether to record the
        access or not. If you return ``True`` here, no record will be created.

        Returns:
            bool: Whether to suppress a record (True) or not (False, default)

        .. versionadded:: 1.3.0
        """
        return False

    # noinspection PyMethodMayBeStatic
    def get_ui_custom_template_filter(self, default_template_filter):
        """
        Allows to specify a custom template filter to use for filtering the template contained in the
        ``render_kwargs`` provided to the templating sub system.

        Only relevant for UiPlugins that actually utilize the stock templates of OctoPrint.

        By default simply returns the provided ``default_template_filter``.

        Arguments:
            default_template_filter (callable): The default template filter used by the default UI

        Returns:
            (callable) A filter function accepting the ``template_type`` and ``template_key`` of a template
            and returning ``True`` to keep it and ``False`` to filter it out. If ``None`` is returned, no
            filtering will take place.

        .. versionadded:: 1.3.0
        """
        return default_template_filter

    # noinspection PyMethodMayBeStatic
    def get_ui_permissions(self):
        """
        Determines a list of permissions that need to be on the current user session. If
        these requirements are not met, OctoPrint will instead redirect to a login
        screen.

        Plugins may override this with their own set of permissions. Returning an empty
        list will instruct OctoPrint to never show a login dialog when this UiPlugin's
        view renders, in which case it will fall to your plugin to implement its own
        login logic.

        Returns:
            (list) A list of permissions which to check the current user session against.
            May be empty to indicate that no permission checks should be made by OctoPrint.

        .. versionadded: 1.5.0
        """
        from octoprint.access.permissions import Permissions

        return [Permissions.STATUS, Permissions.SETTINGS_READ]


class WizardPlugin(OctoPrintPlugin, ReloadNeedingPlugin):
    """
    The ``WizardPlugin`` mixin allows plugins to report to OctoPrint whether
    the ``wizard`` templates they define via the :class:`~octoprint.plugin.TemplatePlugin`
    should be displayed to the user, what details to provide to their respective
    wizard frontend components and what to do when the wizard is finished
    by the user.

    OctoPrint will only display such wizard dialogs to the user which belong
    to plugins that

      * report ``True`` in their :func:`is_wizard_required` method and
      * have not yet been shown to the user in the version currently being reported
        by the :meth:`~octoprint.plugin.WizardPlugin.get_wizard_version` method

    Example: If a plugin with the identifier ``myplugin`` has a specific
    setting ``some_key`` it needs to have filled by the user in order to be
    able to work at all, it would probably test for that setting's value in
    the :meth:`~octoprint.plugin.WizardPlugin.is_wizard_required` method and
    return ``True`` if the value is unset:

    .. code-block:: python

       class MyPlugin(octoprint.plugin.SettingsPlugin,
                      octoprint.plugin.TemplatePlugin,
                      octoprint.plugin.WizardPlugin):

           def get_default_settings(self):
               return dict(some_key=None)

           def is_wizard_required(self):
               return self._settings.get(["some_key"]) is None

    OctoPrint will then display the wizard dialog provided by the plugin through
    the :class:`TemplatePlugin` mixin. Once the user finishes the wizard on the
    frontend, OctoPrint will store that it already showed the wizard of ``myplugin``
    in the version reported by :meth:`~octoprint.plugin.WizardPlugin.get_wizard_version`
    - here ``None`` since that is the default value returned by that function
    and the plugin did not override it.

    If the plugin in a later version needs another setting from the user in order
    to function, it will also need to change the reported version in order to
    have OctoPrint reshow the dialog. E.g.

    .. code-block:: python

       class MyPlugin(octoprint.plugin.SettingsPlugin,
                      octoprint.plugin.TemplatePlugin,
                      octoprint.plugin.WizardPlugin):

           def get_default_settings(self):
               return dict(some_key=None, some_other_key=None)

           def is_wizard_required(self):
               some_key_unset = self._settings.get(["some_key"]) is None
               some_other_key_unset = self._settings.get(["some_other_key"]) is None

               return some_key_unset or some_other_key_unset

           def get_wizard_version(self):
               return 1

    ``WizardPlugin`` is a :class:`~octoprint.plugin.core.ReloadNeedingPlugin`.
    """

    # noinspection PyMethodMayBeStatic
    def is_wizard_required(self):
        """
        Allows the plugin to report whether it needs to display a wizard to the
        user or not.

        Defaults to ``False``.

        OctoPrint will only include those wizards from plugins which are reporting
        their wizards as being required through this method returning ``True``.
        Still, if OctoPrint already displayed that wizard in the same version
        to the user once it won't be displayed again regardless whether this
        method returns ``True`` or not.
        """
        return False

    # noinspection PyMethodMayBeStatic
    def get_wizard_version(self):
        """
        The version of this plugin's wizard. OctoPrint will only display a wizard
        of the same plugin and wizard version once to the user. After they
        finish the wizard, OctoPrint will remember that it already showed this
        wizard in this particular version and not reshow it.

        If a plugin needs to show its wizard to the user again (e.g. because
        of changes in the required settings), increasing this value is the
        way to notify OctoPrint of these changes.

        Returns:
            int or None: an int signifying the current wizard version, should be incremented by plugins whenever there
                         are changes to the plugin that might necessitate reshowing the wizard if it is required. ``None``
                         will also be accepted and lead to the wizard always be ignored unless it has never been finished
                         so far
        """
        return None

    # noinspection PyMethodMayBeStatic
    def get_wizard_details(self):
        """
        Called by OctoPrint when the wizard wrapper dialog is shown. Allows the plugin to return data
        that will then be made available to the view models via the view model callback ``onWizardDetails``.

        Use this if your plugin's view model that handles your wizard dialog needs additional
        data to perform its task.

        Returns:
            dict: a dictionary containing additional data to provide to the frontend. Whatever the plugin
                  returns here will be made available on the wizard API under the plugin's identifier
        """
        return {}

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def on_wizard_finish(self, handled):
        """
        Called by OctoPrint whenever the user finishes a wizard session.

        The ``handled`` parameter will indicate whether that plugin's wizard was
        included in the wizard dialog presented to the user (so the plugin providing
        it was reporting that the wizard was required and the wizard plus version was not
        ignored/had already been seen).

        Use this to do any clean up tasks necessary after wizard completion.

        Arguments:
            handled (bool): True if the plugin's wizard was previously reported as
                            required, not ignored and thus presented to the user,
                            False otherwise
        """
        pass

    # noinspection PyProtectedMember
    @classmethod
    def is_wizard_ignored(cls, seen_wizards, implementation):
        """
        Determines whether the provided implementation is ignored based on the
        provided information about already seen wizards and their versions or not.

        A wizard is ignored if

          * the current and seen versions are identical
          * the current version is None and the seen version is not
          * the seen version is not None and the current version is less or equal than the seen one

        .. code-block:: none

               |  current  |
               | N | 1 | 2 |   N = None
           ----+---+---+---+   X = ignored
           s N | X |   |   |
           e --+---+---+---+
           e 1 | X | X |   |
           n --+---+---+---+
             2 | X | X | X |
           ----+---+---+---+

        Arguments:
            seen_wizards (dict): A dictionary with information about already seen
                wizards and their versions. Mappings from the identifiers of
                the plugin providing the wizard to the reported wizard
                version (int or None) that was already seen by the user.
            implementation (object): The plugin implementation to check.

        Returns:
            bool: False if the provided ``implementation`` is either not a :class:`WizardPlugin`
                  or has not yet been seen (in this version), True otherwise
        """

        if not isinstance(implementation, cls):
            return False

        name = implementation._identifier
        if name not in seen_wizards:
            return False

        seen = seen_wizards[name]
        wizard_version = implementation.get_wizard_version()

        current = None
        if wizard_version is not None:
            try:
                current = int(wizard_version)
            except ValueError as e:
                import logging

                logging.getLogger(__name__).log(
                    "WizardPlugin {} returned invalid value {} for wizard version: {}".format(
                        name, wizard_version, str(e)
                    )
                )

        return (
            (current == seen)
            or (current is None and seen is not None)
            or (seen is not None and current <= seen)
        )


class SimpleApiPlugin(OctoPrintPlugin):
    """
    Utilizing the ``SimpleApiPlugin`` mixin plugins may implement a simple API based around one GET resource and one
    resource accepting JSON commands POSTed to it. This is the easy alternative for plugin's which don't need the
    full power of a `Flask Blueprint <https://flask.palletsprojects.com/blueprints/>`_ that the :class:`BlueprintPlugin`
    mixin offers.

    Use this mixin if all you need to do is return some kind of dynamic data to your plugin from the backend
    and/or want to react to simple commands which boil down to a type of command and a few flat parameters
    supplied with it.

    The simple API constructed by OctoPrint for you will be made available under ``/api/plugin/<plugin identifier>/``.
    OctoPrint will do some preliminary request validation for your defined commands, making sure the request body is in
    the correct format (content type must be JSON) and contains all obligatory parameters for your command.

    Let's take a look at a small example for such a simple API and how you would go about calling it.

    Take this example of a plugin registered under plugin identifier ``mysimpleapiplugin``:

    .. code-block:: python

       import octoprint.plugin

       import flask

       class MySimpleApiPlugin(octoprint.plugin.SimpleApiPlugin):
           def get_api_commands(self):
               return dict(
                   command1=[],
                   command2=["some_parameter"]
               )

           def on_api_command(self, command, data):
               import flask
               if command == "command1":
                   parameter = "unset"
                   if "parameter" in data:
                       parameter = "set"
                   self._logger.info("command1 called, parameter is {parameter}".format(**locals()))
               elif command == "command2":
                   self._logger.info("command2 called, some_parameter is {some_parameter}".format(**data))

           def on_api_get(self, request):
               return flask.jsonify(foo="bar")

       __plugin_implementation__ = MySimpleApiPlugin()

    Our plugin defines two commands, ``command1`` with no mandatory parameters and ``command2`` with one
    mandatory parameter ``some_parameter``.

    ``command1`` can also accept an optional parameter ``parameter``, and will log whether
    that parameter was set or unset. ``command2`` will log the content of the mandatory ``some_parameter`` parameter.

    A valid POST request for ``command2`` sent to ``/api/plugin/mysimpleapiplugin`` would look like this:

    .. sourcecode:: http

       POST /api/plugin/mysimpleapiplugin HTTP/1.1
       Host: example.com
       Content-Type: application/json
       X-Api-Key: abcdef...

       {
         "command": "command2",
         "some_parameter": "some_value",
         "some_optional_parameter": 2342
       }

    which would produce a response like this:

    .. sourcecode:: http

       HTTP/1.1 204 No Content

    and print something like this line to ``octoprint.log``::

       2015-02-12 17:40:21,140 - octoprint.plugins.mysimpleapiplugin - INFO - command2 called, some_parameter is some_value

    A GET request on our plugin's simple API resource will only return a JSON document like this:

    .. sourcecode:: http

       HTTP/1.1 200 Ok
       Content-Type: application/json

       {
         "foo": "bar"
       }
    """

    # noinspection PyMethodMayBeStatic
    def get_api_commands(self):
        """
        Return a dictionary here with the keys representing the accepted commands and the values being lists of
        mandatory parameter names.
        """
        return None

    # noinspection PyMethodMayBeStatic
    def is_api_adminonly(self):
        """
        Return True if the API is only available to users having the admin role.
        """
        return False

    # noinspection PyMethodMayBeStatic
    def on_api_command(self, command, data):
        """
        Called by OctoPrint upon a POST request to ``/api/plugin/<plugin identifier>``. ``command`` will contain one of
        the commands as specified via :func:`get_api_commands`, ``data`` will contain the full request body parsed
        from JSON into a Python dictionary. Note that this will also contain the ``command`` attribute itself. For the
        example given above, for the ``command2`` request the ``data`` received by the plugin would be equal to
        ``dict(command="command2", some_parameter="some_value")``.

        If your plugin returns nothing here, OctoPrint will return an empty response with return code ``204 No content``
        for you. You may also return regular responses as you would return from any Flask view here though, e.g.
        ``return flask.jsonify(result="some json result")`` or ``flask.abort(404)``.

        :param string command: the command with which the resource was called
        :param dict data:      the full request body of the POST request parsed from JSON into a Python dictionary
        :return: ``None`` in which case OctoPrint will generate a ``204 No content`` response with empty body, or optionally
                 a proper Flask response.
        """
        return None

    # noinspection PyMethodMayBeStatic
    def on_api_get(self, request):
        """
        Called by OctoPrint upon a GET request to ``/api/plugin/<plugin identifier>``. ``request`` will contain the
        received `Flask request object <https://flask.palletsprojects.com/api/#flask.Request>`_ which you may evaluate
        for additional arguments supplied with the request.

        If your plugin returns nothing here, OctoPrint will return an empty response with return code ``204 No content``
        for you. You may also return regular responses as you would return from any Flask view here though, e.g.
        ``return flask.jsonify(result="some json result")`` or ``flask.abort(404)``.

        :param request: the Flask request object
        :return: ``None`` in which case OctoPrint will generate a ``204 No content`` response with empty body, or optionally
                 a proper Flask response.
        """
        return None


class BlueprintPlugin(OctoPrintPlugin, RestartNeedingPlugin):
    """
    The ``BlueprintPlugin`` mixin allows plugins to define their own full fledged endpoints for whatever purpose,
    be it a more sophisticated API than what is possible via the :class:`SimpleApiPlugin` or a custom web frontend.

    The mechanism at work here is `Flask's <https://flask.palletsprojects.com/>`_ own `Blueprint mechanism <https://flask.palletsprojects.com/blueprints/>`_.

    The mixin automatically creates a blueprint for you that will be registered under ``/plugin/<plugin identifier>/``.
    All you need to do is decorate all of your view functions with the :func:`route` decorator,
    which behaves exactly the same like Flask's regular ``route`` decorators. Example:

    .. code-block:: python

       import octoprint.plugin
       import flask

       class MyBlueprintPlugin(octoprint.plugin.BlueprintPlugin):
           @octoprint.plugin.BlueprintPlugin.route("/echo", methods=["GET"])
           def myEcho(self):
               if not "text" in flask.request.values:
                   abort(400, description="Expected a text to echo back.")
               return flask.request.values["text"]

       __plugin_implementation__ = MyBlueprintPlugin()

    Your blueprint will be published by OctoPrint under the base URL ``/plugin/<plugin identifier>/``, so the above
    example of a plugin with the identifier "myblueprintplugin" would be reachable under
    ``/plugin/myblueprintplugin/echo``.

    Just like with regular blueprints you'll be able to create URLs via ``url_for``, just use the prefix
    ``plugin.<plugin identifier>.<method_name>``, e.g.:

    .. code-block:: python

       flask.url_for("plugin.myblueprintplugin.myEcho") # will return "/plugin/myblueprintplugin/echo"

    .. warning::

       As of OctoPrint 1.8.3, endpoints provided through a ``BlueprintPlugin`` do **not** automatically fall under
       OctoPrint's :ref:`CSRF protection <sec-api-general-csrf>`, for reasons of backwards compatibility. There will be a short grace period before this changes. You
       can and should however already opt into CSRF protection for your endpoints by implementing ``is_blueprint_csrf_protected``
       and returning ``True`` from it. You can exempt certain endpoints from CSRF protection by decorating them with
       ``@octoprint.plugin.BlueprintPlugin.csrf_exempt``.

       .. code-block:: python

          class MyPlugin(octoprint.plugin.BlueprintPlugin):
              @octoprint.plugin.BlueprintPlugin.route("/hello_world", methods=["GET"])
              def hello_world(self):
                  # This is a GET request and thus not subject to CSRF protection
                  return "Hello world!"

              @octoprint.plugin.BlueprintPlugin.route("/hello_you", methods=["POST"])
              def hello_you(self):
                  # This is a POST request and thus subject to CSRF protection. It is not exempt.
                  return "Hello you!"

              @octoprint.plugin.BlueprintPlugin.route("/hello_me", methods=["POST"])
              @octoprint.plugin.BlueprintPlugin.csrf_exempt()
              def hello_me(self):
                  # This is a POST request and thus subject to CSRF protection, but this one is exempt.
                  return "Hello me!"

              def is_blueprint_csrf_protected(self):
                  return True

    ``BlueprintPlugin`` implements :class:`~octoprint.plugins.core.RestartNeedingPlugin`.

    .. versionchanged:: 1.8.3
    """

    @staticmethod
    def route(rule, **options):
        """
        A decorator to mark view methods in your BlueprintPlugin subclass. Works just the same as Flask's
        own ``route`` decorator available on blueprints.

        See `the documentation for flask.Blueprint.route <https://flask.palletsprojects.com/api/#flask.Blueprint.route>`_
        and `the documentation for flask.Flask.route <https://flask.palletsprojects.com/api/#flask.Flask.route>`_ for more
        information.
        """

        from collections import defaultdict

        def decorator(f):
            # We attach the decorator parameters directly to the function object, because that's the only place
            # we can access right now.
            # This neat little trick was adapted from the Flask-Classy project: https://pythonhosted.org/Flask-Classy/
            if not hasattr(f, "_blueprint_rules") or f._blueprint_rules is None:
                f._blueprint_rules = defaultdict(list)
            f._blueprint_rules[f.__name__].append((rule, options))
            return f

        return decorator

    @staticmethod
    def errorhandler(code_or_exception):
        """
        A decorator to mark errorhandlings methods in your BlueprintPlugin subclass. Works just the same as Flask's
        own ``errorhandler`` decorator available on blueprints.

        See `the documentation for flask.Blueprint.errorhandler <https://flask.palletsprojects.com/api/#flask.Blueprint.errorhandler>`_
        and `the documentation for flask.Flask.errorhandler <https://flask.palletsprojects.com/api/#flask.Flask.errorhandler>`_ for more
        information.

        .. versionadded:: 1.3.0
        """
        from collections import defaultdict

        def decorator(f):
            if (
                not hasattr(f, "_blueprint_error_handler")
                or f._blueprint_error_handler is None
            ):
                f._blueprint_error_handler = defaultdict(list)
            f._blueprint_error_handler[f.__name__].append(code_or_exception)
            return f

        return decorator

    @staticmethod
    def csrf_exempt():
        """
        A decorator to mark a view method in your BlueprintPlugin as exempt from :ref:`CSRF protection <sec-api-general-csrf>`. This makes sense
        if you offer an authenticated API for a certain workflow (see e.g. the bundled appkeys plugin) but in most
        cases should not be needed.

        .. versionadded:: 1.8.3
        """

        def decorator(f):
            if (
                not hasattr(f, "_blueprint_csrf_exempt")
                or f._blueprint_csrf_exempt is None
            ):
                f._blueprint_csrf_exempt = set()
            f._blueprint_csrf_exempt.add(f.__name__)
            return f

        return decorator

    # noinspection PyProtectedMember
    def get_blueprint(self):
        """
        Creates and returns the blueprint for your plugin. Override this if you want to define and handle your blueprint yourself.

        This method will only be called once during server initialization.

        :return: the blueprint ready to be registered with Flask
        """

        if hasattr(self, "_blueprint"):
            # if we already constructed the blueprint and hence have it cached,
            # return that instance - we don't want to instance it multiple times
            return self._blueprint

        import flask

        from octoprint.server.util.csrf import add_exempt_view

        kwargs = self.get_blueprint_kwargs()
        blueprint = flask.Blueprint(self._identifier, self._identifier, **kwargs)

        # we now iterate over all members of ourselves and look if we find an attribute
        # that has data originating from one of our decorators - we ignore anything
        # starting with a _ to only handle public stuff
        for member in [x for x in dir(self) if not x.startswith("_")]:
            f = getattr(self, member)

            if hasattr(f, "_blueprint_rules") and member in f._blueprint_rules:
                # this attribute was annotated with our @route decorator
                for blueprint_rule in f._blueprint_rules[member]:
                    rule, options = blueprint_rule
                    endpoint = options.pop("endpoint", f.__name__)
                    blueprint.add_url_rule(rule, endpoint, view_func=f, **options)

                    if (
                        hasattr(f, "_blueprint_csrf_exempt")
                        and member in f._blueprint_csrf_exempt
                    ):
                        add_exempt_view(f"plugin.{self._identifier}.{endpoint}")

            if (
                hasattr(f, "_blueprint_error_handler")
                and member in f._blueprint_error_handler
            ):
                # this attribute was annotated with our @error_handler decorator
                for code_or_exception in f._blueprint_error_handler[member]:
                    blueprint.errorhandler(code_or_exception)(f)

        # cache and return the blueprint object
        self._blueprint = blueprint
        return blueprint

    def get_blueprint_kwargs(self):
        """
        Override this if you want your blueprint constructed with additional options such as ``static_folder``,
        ``template_folder``, etc.

        Defaults to the blueprint's ``static_folder`` and ``template_folder`` to be set to the plugin's basefolder
        plus ``/static`` or respectively ``/templates``, or -- if the plugin also implements :class:`AssetPlugin` and/or
        :class:`TemplatePlugin` -- the paths provided by ``get_asset_folder`` and ``get_template_folder`` respectively.
        """
        import os

        if isinstance(self, AssetPlugin):
            static_folder = self.get_asset_folder()
        else:
            static_folder = os.path.join(self._basefolder, "static")

        if isinstance(self, TemplatePlugin):
            template_folder = self.get_template_folder()
        else:
            template_folder = os.path.join(self._basefolder, "templates")

        return {"static_folder": static_folder, "template_folder": template_folder}

    # noinspection PyMethodMayBeStatic
    def is_blueprint_protected(self):
        """
        Whether a login session by a registered user is needed to access the blueprint's endpoints. Requiring
        a session is the default. Note that this only restricts access to the blueprint's dynamic methods, static files
        are always accessible.

        If you want your blueprint's endpoints to have specific permissions, return ``False`` for this and do your
        permissions checks explicitly.
        """
        return True

    # noinspection PyMethodMayBeStatic
    def is_blueprint_csrf_protected(self):
        """
        Whether a blueprint's endpoints are :ref:`CSRF protected <sec-api-general-csrf>`. For now, this defaults to ``False`` to leave it up to
        plugins to decide which endpoints *should* be protected. Long term, this will default to ``True`` and hence
        enforce protection unless a plugin opts out by returning False here.

        If you do not override this method in your mixin implementation, a warning will be logged to the console
        to alert you of the requirement to make a decision here and to not rely on the default implementation, due to the
        forthcoming change in implemented default behaviour.

        .. versionadded:: 1.8.3
        """
        self._logger.warning(
            "The Blueprint of this plugin is relying on the default implementation of "
            "is_blueprint_csrf_protected (newly added in OctoPrint 1.8.3), which in a future version will "
            "be switched from False to True for security reasons. Plugin authors should ensure they explicitly "
            "declare the CSRF protection status in their BlueprintPlugin mixin implementation. "
            "Recommendation is to enable CSRF protection and exempt views that must not use it with the "
            "octoprint.plugin.BlueprintPlugin.csrf_exempt decorator."
        )
        return False

    # noinspection PyMethodMayBeStatic
    def get_blueprint_api_prefixes(self):
        """
        Return all prefixes of your endpoint that are an API that should be containing JSON only.

        Anything that matches this will generate JSON error messages in case of flask.abort
        calls, instead of the default HTML ones.

        Defaults to all endpoints under the blueprint. Limit this further as needed. E.g.,
        if you only want your endpoints /foo, /foo/1 and /bar to be declared as API,
        return ``["/foo", "/bar"]``. A match will be determined via startswith.
        """
        return [""]


class SettingsPlugin(OctoPrintPlugin):
    """
    Including the ``SettingsPlugin`` mixin allows plugins to store and retrieve their own settings within OctoPrint's
    configuration.

    Plugins including the mixin will get injected an additional property ``self._settings`` which is an instance of
    :class:`PluginSettingsManager` already properly initialized for use by the plugin. In order for the manager to
    know about the available settings structure and default values upon initialization, implementing plugins will need
    to provide a dictionary with the plugin's default settings through overriding the method :func:`get_settings_defaults`.
    The defined structure will then be available to access through the settings manager available as ``self._settings``.

    .. note::

       Use the settings only to store configuration data or information that is relevant to the UI. Anything in the settings
       is part of the hash that is used to determine whether a client's copy of the UI is still up to date or not. If you
       store unrelated and possibly often changing information in the settings, you will force the client to reload the
       UI without visible changes, which will lead to a bad user experience.

       You may store additional data in your plugin's data folder instead, which is not part of the hash and whose path
       can be retrieved through :func:`~
       octoprint.plugin.types.OctoPrintPlugin.get_plugin_data_folder`, e.g.:

       .. code-block:: python

          data_folder = self.get_plugin_data_folder()
          with open(os.path.join(data_folder, "some_file.txt"), "w") as f:
            f.write("some data")

    If your plugin needs to react to the change of specific configuration values on the fly, e.g. to adjust the log level
    of a logger when the user changes a corresponding flag via the settings dialog, you can override the
    :func:`on_settings_save` method and wrap the call to the implementation from the parent class with retrieval of the
    old and the new value and react accordingly.

    Example:

    .. code-block:: python

       import octoprint.plugin

       class MySettingsPlugin(octoprint.plugin.SettingsPlugin, octoprint.plugin.StartupPlugin):
           def get_settings_defaults(self):
               return dict(
                   some_setting="foo",
                   some_value=23,
                   sub=dict(
                       some_flag=True
                   )
               )

           def on_settings_save(self, data):
               old_flag = self._settings.get_boolean(["sub", "some_flag"])

               octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

               new_flag = self._settings.get_boolean(["sub", "some_flag"])
               if old_flag != new_flag:
                   self._logger.info("sub.some_flag changed from {old_flag} to {new_flag}".format(**locals()))

           def on_after_startup(self):
               some_setting = self._settings.get(["some_setting"])
               some_value = self._settings.get_int(["some_value"])
               some_flag = self._settings.get_boolean(["sub", "some_flag"])
               self._logger.info("some_setting = {some_setting}, some_value = {some_value}, sub.some_flag = {some_flag}".format(**locals())

       __plugin_implementation__ = MySettingsPlugin()

    Of course, you are always free to completely override both :func:`on_settings_load` and :func:`on_settings_save` if the
    default implementations do not fit your requirements.


    .. warning::

       Make sure to protect sensitive information stored by your plugin that only logged in administrators (or users)
       should have access to via :meth:`~octoprint.plugin.SettingsPlugin.get_settings_restricted_paths`. OctoPrint will
       return its settings on the REST API even to anonymous clients, but will filter out fields it knows are restricted,
       therefore you **must** make sure that you specify sensitive information accordingly to limit access as required!
    """

    config_version_key = "_config_version"
    """Key of the field in the settings that holds the configuration format version."""

    # noinspection PyMissingConstructor
    def __init__(self):
        self._settings = None
        """
        The :class:`~octoprint.plugin.PluginSettings` instance to use for accessing the plugin's settings. Injected by
        the plugin core system upon initialization of the implementation.
        """

    def on_settings_load(self):
        """
        Loads the settings for the plugin, called by the Settings API view in order to retrieve all settings from
        all plugins. Override this if you want to inject additional settings properties that are not stored within
        OctoPrint's configuration.

        .. note::

           The default implementation will return your plugin's settings as is, so just in the structure and in the types
           that are currently stored in OctoPrint's configuration.

           If you need more granular control here, e.g. over the used data types, you'll need to override this method
           and iterate yourself over all your settings, using the proper retriever methods on the settings manager
           to retrieve the data in the correct format.

           The default implementation will also replace any paths that have been restricted by your plugin through
           :func:`~octoprint.plugin.SettingsPlugin.get_settings_restricted_paths` with either the provided
           default value (if one was provided), an empty dictionary (as fallback for restricted dictionaries), an
           empty list (as fallback for restricted lists) or ``None`` values where necessary.
           Make sure to do your own restriction if you decide to fully overload this method.

        :return: the current settings of the plugin, as a dictionary
        """
        import copy

        from flask_login import current_user

        from octoprint.access.permissions import OctoPrintPermission, Permissions

        data = copy.deepcopy(self._settings.get_all_data(merged=True))
        if self.config_version_key in data:
            del data[self.config_version_key]

        restricted_paths = self.get_settings_restricted_paths()

        # noinspection PyShadowingNames
        def restrict_path_unless(data, path, condition):
            if not path:
                return

            if condition():
                return

            node = data

            if len(path) > 1:
                for entry in path[:-1]:
                    if entry not in node:
                        return
                    node = node[entry]

            key = path[-1]
            default_value_available = False
            default_value = None
            if isinstance(key, (list, tuple)):
                # key, default_value tuple
                key, default_value = key
                default_value_available = True

            if key in node:
                if default_value_available:
                    if callable(default_value):
                        default_value = default_value()
                    node[key] = default_value
                else:
                    if isinstance(node[key], dict):
                        node[key] = {}
                    elif isinstance(node[key], (list, tuple)):
                        node[key] = []
                    else:
                        node[key] = None

        conditions = {
            "user": lambda: current_user is not None and not current_user.is_anonymous,
            "admin": lambda: current_user is not None
            and current_user.has_permission(Permissions.SETTINGS),
            "never": lambda: False,
        }

        for level, paths in restricted_paths.items():
            if isinstance(level, OctoPrintPermission):
                condition = lambda: (
                    current_user is not None and current_user.has_permission(level)
                )
            else:
                condition = conditions.get(level, lambda: False)

            for path in paths:
                restrict_path_unless(data, path, condition)

        return data

    def on_settings_save(self, data):
        """
        Saves the settings for the plugin, called by the Settings API view in order to persist all settings
        from all plugins. Override this if you need to directly react to settings changes or want to extract
        additional settings properties that are not stored within OctoPrint's configuration.

        .. note::

           The default implementation will persist your plugin's settings as is, so just in the structure and in the
           types that were received by the Settings API view. Values identical to the default settings values
           will *not* be persisted.

           If you need more granular control here, e.g. over the used data types, you'll need to override this method
           and iterate yourself over all your settings, retrieving them (if set) from the supplied received ``data``
           and using the proper setter methods on the settings manager to persist the data in the correct format.

        Arguments:
            data (dict): The settings dictionary to be saved for the plugin

        Returns:
            dict: The settings that differed from the defaults and were actually saved.
        """
        import octoprint.util

        # get the current data
        current = self._settings.get_all_data()
        if current is None:
            current = {}

        # merge our new data on top of it
        new_current = octoprint.util.dict_merge(current, data)
        if self.config_version_key in new_current:
            del new_current[self.config_version_key]

        # determine diff dict that contains minimal set of changes against the
        # default settings - we only want to persist that, not everything
        diff = octoprint.util.dict_minimal_mergediff(
            self.get_settings_defaults(), new_current
        )

        version = self.get_settings_version()

        to_persist = dict(diff)
        if version:
            to_persist[self.config_version_key] = version

        if to_persist:
            self._settings.set([], to_persist)
        else:
            self._settings.clean_all_data()

        return diff

    # noinspection PyMethodMayBeStatic
    def get_settings_defaults(self):
        """
        Retrieves the plugin's default settings with which the plugin's settings manager will be initialized.

        Override this in your plugin's implementation and return a dictionary defining your settings data structure
        with included default values.
        """
        return {}

    # noinspection PyMethodMayBeStatic
    def get_settings_restricted_paths(self):
        """
        Retrieves the list of paths in the plugin's settings which be restricted on the REST API.

        Override this in your plugin's implementation to restrict whether a path should only be returned to users with
        certain permissions, or never on the REST API.

        Return a ``dict`` with one of the following keys, mapping to a list of paths (as tuples or lists of
        the path elements) for which to restrict access via the REST API accordingly.

           * An :py:class:`~octoprint.access.permissions.OctoPrintPermission` instance: Paths will only be available on the REST API for users with the permission
           * ``admin``: Paths will only be available on the REST API for users with admin rights (any user with the SETTINGS permission)
           * ``user``: Paths will only be available on the REST API when accessed as a logged in user
           * ``never``: Paths will never be returned on the API

        Example:

        .. code-block:: python

           def get_settings_defaults(self):
               return dict(some=dict(admin_only=dict(path="path", foo="foo"),
                                     user_only=dict(path="path", bar="bar")),
                           another=dict(admin_only=dict(path="path"),
                                        field="field"),
                           path=dict(to=dict(never=dict(return="return"))),
                           the=dict(webcam=dict(data="webcam")))

           def get_settings_restricted_paths(self):
               from octoprint.access.permissions import Permissions
               return {'admin':[["some", "admin_only", "path"], ["another", "admin_only", "path"],],
                       'user':[["some", "user_only", "path"],],
                       'never':[["path", "to", "never", "return"],],
                       Permissions.WEBCAM:[["the", "webcam", "data"],]}

           # this will make the plugin return settings on the REST API like this for an anonymous user
           #
           #     dict(some=dict(admin_only=dict(path=None, foo="foo"),
           #                    user_only=dict(path=None, bar="bar")),
           #          another=dict(admin_only=dict(path=None),
           #                       field="field"),
           #          path=dict(to=dict(never=dict(return=None))),
           #          the=dict(webcam=dict(data=None)))
           #
           # like this for a logged in user without the webcam permission
           #
           #     dict(some=dict(admin_only=dict(path=None, foo="foo"),
           #                    user_only=dict(path="path", bar="bar")),
           #          another=dict(admin_only=dict(path=None),
           #                       field="field"),
           #          path=dict(to=dict(never=dict(return=None))),
           #          the=dict(webcam=dict(data=None)))
           #
           # like this for a logged in user with the webcam permission
           #
           #     dict(some=dict(admin_only=dict(path=None, foo="foo"),
           #                    user_only=dict(path="path", bar="bar")),
           #          another=dict(admin_only=dict(path=None),
           #                       field="field"),
           #          path=dict(to=dict(never=dict(return=None))),
           #          the=dict(webcam=dict(data="webcam")))
           #
           # and like this for an admin user
           #
           #     dict(some=dict(admin_only=dict(path="path", foo="foo"),
           #                    user_only=dict(path="path", bar="bar")),
           #          another=dict(admin_only=dict(path="path"),
           #                       field="field"),
           #          path=dict(to=dict(never=dict(return=None))),
           #          the=dict(webcam=dict(data="webcam")))

        .. versionadded:: 1.2.17
        """
        return {}

    # noinspection PyMethodMayBeStatic
    def get_settings_preprocessors(self):
        """
        Retrieves the plugin's preprocessors to use for preprocessing returned or set values prior to returning/setting
        them.

        The preprocessors should be provided as a dictionary mapping the path of the values to preprocess
        (hierarchically) to a transform function which will get the value to transform as only input and should return
        the transformed value.

        Example:

        .. code-block:: python

           def get_settings_defaults(self):
               return dict(some_key="Some_Value", some_other_key="Some_Value")

           def get_settings_preprocessors(self):
               return dict(some_key=lambda x: x.upper()),        # getter preprocessors
                      dict(some_other_key=lambda x: x.lower())   # setter preprocessors

           def some_method(self):
               # getting the value for "some_key" should turn it to upper case
               assert self._settings.get(["some_key"]) == "SOME_VALUE"

               # the value for "some_other_key" should be left alone
               assert self._settings.get(["some_other_key"] = "Some_Value"

               # setting a value for "some_other_key" should cause the value to first be turned to lower case
               self._settings.set(["some_other_key"], "SOME_OTHER_VALUE")
               assert self._settings.get(["some_other_key"]) == "some_other_value"

        Returns:
            (dict, dict): A tuple consisting of two dictionaries, the first being the plugin's preprocessors for
            getters, the second the preprocessors for setters
        """
        return {}, {}

    # noinspection PyMethodMayBeStatic
    def get_settings_version(self):
        """
        Retrieves the settings format version of the plugin.

        Use this to have OctoPrint trigger your migration function if it detects an outdated settings version in
        config.yaml.

        Returns:
            int or None: an int signifying the current settings format, should be incremented by plugins whenever there
            are backwards incompatible changes. Returning None here disables the version tracking for the
            plugin's configuration.
        """
        return None

    # noinspection PyMethodMayBeStatic
    def on_settings_migrate(self, target, current):
        """
        Called by OctoPrint if it detects that the installed version of the plugin necessitates a higher settings version
        than the one currently stored in _config.yaml. Will also be called if the settings data stored in config.yaml
        doesn't have version information, in which case the ``current`` parameter will be None.

        Your plugin's implementation should take care of migrating any data by utilizing self._settings. OctoPrint
        will take care of saving any changes to disk by calling `self._settings.save()` after returning from this method.

        This method will be called before your plugin's :func:`on_settings_initialized` method, with all injections already
        having taken place. You can therefore depend on the configuration having been migrated by the time
        :func:`on_settings_initialized` is called.

        Arguments:
            target (int): The settings format version the plugin requires, this should always be the same value as
                          returned by :func:`get_settings_version`.
            current (int or None): The settings format version as currently stored in config.yaml. May be None if
                          no version information can be found.
        """
        pass

    def on_settings_cleanup(self):
        """
        Called after migration and initialization but before call to :func:`on_settings_initialized`.

        Plugins may overwrite this method to perform additional clean up tasks.

        The default implementation just minimizes the data persisted on disk to only contain
        the differences to the defaults (in case the current data was persisted with an older
        version of OctoPrint that still duplicated default data).

        .. versionadded:: 1.3.0
        """
        import octoprint.util
        from octoprint.settings import NoSuchSettingsPath

        try:
            # let's fetch the current persisted config (so only the data on disk,
            # without the defaults)
            config = self._settings.get_all_data(
                merged=False, incl_defaults=False, error_on_path=True
            )
        except NoSuchSettingsPath:
            # no config persisted, nothing to do => get out of here
            return

        if config is None:
            # config is set to None, that doesn't make sense, kill it and leave
            self._settings.clean_all_data()
            return

        if self.config_version_key in config and config[self.config_version_key] is None:
            # delete None entries for config version - it's the default, no need
            del config[self.config_version_key]

        # calculate a minimal diff between the settings and the current config -
        # anything already in the settings will be removed from the persisted
        # config, no need to duplicate it
        defaults = self.get_settings_defaults()
        diff = octoprint.util.dict_minimal_mergediff(defaults, config)

        if not diff:
            # no diff to defaults, no need to have anything persisted
            self._settings.clean_all_data()
        else:
            # diff => persist only that
            self._settings.set([], diff)

    def on_settings_initialized(self):
        """
        Called after the settings have been initialized and - if necessary - also been migrated through a call to
        func:`on_settings_migrate`.

        This method will always be called after the `initialize` method.
        """
        pass


class EventHandlerPlugin(OctoPrintPlugin):
    """
    The ``EventHandlerPlugin`` mixin allows OctoPrint plugins to react to any of :ref:`OctoPrint's events <sec-events>`.
    OctoPrint will call the :func:`on_event` method for any event fired on its internal event bus, supplying the
    event type and the associated payload. Please note that until your plugin returns from that method, further event
    processing within OctoPrint will block - the event queue itself is run asynchronously from the rest of OctoPrint,
    but the processing of the events within the queue itself happens consecutively.

    This mixin is especially interesting for plugins which want to react on things like print jobs finishing, timelapse
    videos rendering etc.
    """

    # noinspection PyMethodMayBeStatic
    def on_event(self, event, payload):
        """
        Called by OctoPrint upon processing of a fired event on the platform.

        .. warning::

           Do not perform long-running or even blocking operations in your implementation or you **will** block and break the server.

        Arguments:
            event (str): The type of event that got fired, see :ref:`the list of events <sec-events-available_events>`
                for possible values
            payload (dict): The payload as provided with the event
        """
        pass


class SlicerPlugin(OctoPrintPlugin):
    """
    Via the ``SlicerPlugin`` mixin plugins can add support for slicing engines to be used by OctoPrint.

    """

    # noinspection PyMethodMayBeStatic
    def is_slicer_configured(self):
        """
        Unless the return value of this method is ``True``, OctoPrint will not register the slicer within the slicing
        sub system upon startup. Plugins may use this to do some start up checks to verify that e.g. the path to
        a slicing binary as set and the binary is executable, or credentials of a cloud slicing platform are properly
        entered etc.
        """
        return False

    # noinspection PyMethodMayBeStatic
    def get_slicer_properties(self):
        """
        Plugins should override this method to return a ``dict`` containing a bunch of meta data about the implemented slicer.

        The expected keys in the returned ``dict`` have the following meaning:

        type
            The type identifier to use for the slicer. This should be a short unique lower case string which will be
            used to store slicer profiles under or refer to the slicer programmatically or from the API.
        name
            The human readable name of the slicer. This will be displayed to the user during slicer selection.
        same_device
            True if the slicer runs on the same device as OctoPrint, False otherwise. Slicers running on the same
            device will not be allowed to slice on systems with less than two CPU cores (or an unknown number) while a
            print is running due to performance reasons. Slice requests against slicers running on the same device and
            less than two cores will result in an error.
        progress_report
            ``True`` if the slicer can report back slicing progress to OctoPrint ``False`` otherwise.
        source_file_types
            A list of file types this slicer supports as valid origin file types. These are file types as found in the
            paths within the extension tree. Plugins may add additional file types through the :ref:`sec-plugins-hook-filemanager-extensiontree` hook.
            The system will test source files contains in incoming slicing requests via :meth:`octoprint.filemanager.valid_file_type` against the
            targeted slicer's ``source_file_types``.
        destination_extension
            The possible extensions of slicing result files.

        Returns:
            dict: A dict describing the slicer as outlined above.
        """
        return {
            "type": None,
            "name": None,
            "same_device": True,
            "progress_report": False,
            "source_file_types": ["model"],
            "destination_extensions": ["gco", "gcode", "g"],
        }

    # noinspection PyMethodMayBeStatic
    def get_slicer_extension_tree(self):
        """
        Fetch additional entries to put into the extension tree for accepted files

        By default, a subtree for ``model`` files with ``stl`` extension is returned. Slicers who want to support
        additional/other file types will want to override this.

        For the extension tree format, take a look at the docs of the :ref:`octoprint.filemanager.extension_tree hook <sec-plugins-hook-filemanager-extensiontree>`.

        Returns: (dict) a dictionary containing a valid extension subtree.

        .. versionadded:: 1.3.11
        """
        from octoprint.filemanager import ContentTypeMapping

        return {"model": {"stl": ContentTypeMapping(["stl"], "application/sla")}}

    def get_slicer_profiles(self, profile_path):
        """
        Fetch all :class:`~octoprint.slicing.SlicingProfile` stored for this slicer.

        For compatibility reasons with existing slicing plugins this method defaults to returning profiles parsed from
        .profile files in the plugin's ``profile_path``, utilizing the :func:`SlicingPlugin.get_slicer_profile` method
        of the plugin implementation.

        Arguments:
            profile_path (str): The base folder where OctoPrint stores this slicer plugin's profiles

        .. versionadded:: 1.3.7
        """

        from os import scandir

        import octoprint.util

        profiles = {}
        for entry in scandir(profile_path):
            if not entry.name.endswith(".profile") or octoprint.util.is_hidden_path(
                entry.name
            ):
                # we are only interested in profiles and no hidden files
                continue

            profile_name = entry.name[: -len(".profile")]
            profiles[profile_name] = self.get_slicer_profile(entry.path)
        return profiles

    # noinspection PyMethodMayBeStatic
    def get_slicer_profiles_lastmodified(self, profile_path):
        """
        .. versionadded:: 1.3.0
        """
        import os

        lms = [os.stat(profile_path).st_mtime]
        lms += [
            os.stat(entry.path).st_mtime
            for entry in os.scandir(profile_path)
            if entry.name.endswith(".profile")
        ]
        return max(lms)

    # noinspection PyMethodMayBeStatic
    def get_slicer_default_profile(self):
        """
        Should return a :class:`~octoprint.slicing.SlicingProfile` containing the default slicing profile to use with
        this slicer if no other profile has been selected.

        Returns:
            SlicingProfile: The :class:`~octoprint.slicing.SlicingProfile` containing the default slicing profile for
                this slicer.
        """
        return None

    # noinspection PyMethodMayBeStatic
    def get_slicer_profile(self, path):
        """
        Should return a :class:`~octoprint.slicing.SlicingProfile` parsed from the slicing profile stored at the
        indicated ``path``.

        Arguments:
            path (str): The absolute path from which to read the slicing profile.

        Returns:
            SlicingProfile: The specified slicing profile.
        """
        return None

    # noinspection PyMethodMayBeStatic
    def save_slicer_profile(self, path, profile, allow_overwrite=True, overrides=None):
        """
        Should save the provided :class:`~octoprint.slicing.SlicingProfile` to the indicated ``path``, after applying
        any supplied ``overrides``. If a profile is already saved under the indicated path and ``allow_overwrite`` is
        set to False (defaults to True), an :class:`IOError` should be raised.

        Arguments:
            path (str): The absolute path to which to save the profile.
            profile (SlicingProfile): The profile to save.
            allow_overwrite (boolean): Whether to allow to overwrite an existing profile at the indicated path (True,
                default) or not (False). If a profile already exists on the path and this is False an
                :class:`IOError` should be raised.
            overrides (dict): Profile overrides to apply to the ``profile`` before saving it
        """
        pass

    # noinspection PyMethodMayBeStatic
    def do_slice(
        self,
        model_path,
        printer_profile,
        machinecode_path=None,
        profile_path=None,
        position=None,
        on_progress=None,
        on_progress_args=None,
        on_progress_kwargs=None,
    ):
        """
        Called by OctoPrint to slice ``model_path`` for the indicated ``printer_profile``. If the ``machinecode_path`` is ``None``,
        slicer implementations should generate it from the provided ``model_path``.

        If provided, the ``profile_path`` is guaranteed by OctoPrint to be a serialized slicing profile created through the slicing
        plugin's own :func:`save_slicer_profile` method.

        If provided, ``position`` will be a ``dict`` containing and ``x`` and a ``y`` key, indicating the position
        the center of the model on the print bed should have in the final sliced machine code. If not provided, slicer
        implementations should place the model in the center of the print bed.

        ``on_progress`` will be a callback which expects an additional keyword argument ``_progress`` with the current
        slicing progress which - if progress reporting is supported - the slicing plugin should call like the following:

        .. code-block:: python

           if on_progress is not None:
               if on_progress_args is None:
                   on_progress_args = ()
               if on_progress_kwargs is None:
                   on_progress_kwargs = dict()

               on_progress_kwargs["_progress"] = your_plugins_slicing_progress
               on_progress(*on_progress_args, **on_progress_kwargs)

        Please note that both ``on_progress_args`` and ``on_progress_kwargs`` as supplied by OctoPrint might be ``None``,
        so always make sure to initialize those values to sane defaults like depicted above before invoking the callback.

        In order to support external cancellation of an ongoing slicing job via :func:`cancel_slicing`, implementations
        should make sure to track the started jobs via the ``machinecode_path``, if provided.

        The method should return a 2-tuple consisting of a boolean ``flag`` indicating whether the slicing job was
        finished successfully (True) or not (False) and a ``result`` depending on the success of the slicing job.

        For jobs that finished successfully, ``result`` should be a :class:`dict` containing additional information
        about the slicing job under the following keys:

        analysis
            Analysis result of the generated machine code as returned by the slicer itself. This should match the
            data structure described for the analysis queue of the matching machine code format, e.g.
            :class:`~octoprint.filemanager.analysis.GcodeAnalysisQueue` for GCODE files.

        For jobs that did not finish successfully (but not due to being cancelled!), ``result`` should be a :class:`str`
        containing a human readable reason for the error.

        If the job gets cancelled, a :class:`~octoprint.slicing.SlicingCancelled` exception should be raised.

        Returns:
            tuple: A 2-tuple (boolean, object) as outlined above.

        Raises:
            SlicingCancelled: The slicing job was cancelled (via :meth:`cancel_slicing`).
        """
        pass

    # noinspection PyMethodMayBeStatic
    def cancel_slicing(self, machinecode_path):
        """
        Cancels the slicing to the indicated file.

        Arguments:
            machinecode_path (str): The absolute path to the machine code file to which to stop slicing to.
        """
        pass


class ProgressPlugin(OctoPrintPlugin):
    """
    Via the ``ProgressPlugin`` mixing plugins can let themselves be called upon progress in print jobs or slicing jobs,
    limited to minimally 1% steps.
    """

    # noinspection PyMethodMayBeStatic
    def on_print_progress(self, storage, path, progress):
        """
        Called by OctoPrint on minimally 1% increments during a running print job.

        :param string storage:  Location of the file
        :param string path:     Path of the file
        :param int progress:    Current progress as a value between 0 and 100
        """
        pass

    # noinspection PyMethodMayBeStatic
    def on_slicing_progress(
        self,
        slicer,
        source_location,
        source_path,
        destination_location,
        destination_path,
        progress,
    ):
        """
        Called by OctoPrint on minimally 1% increments during a running slicing job.

        :param string slicer:               Key of the slicer reporting the progress
        :param string source_location:      Location of the source file
        :param string source_path:          Path of the source file
        :param string destination_location: Location the destination file
        :param string destination_path:     Path of the destination file
        :param int progress:                Current progress as a value between 0 and 100
        """
        pass


class WebcamProviderPlugin(OctoPrintPlugin):
    """
    The ``WebcamProviderPlugin`` can be used to provide one or more webcams visible on the frontend and used for snapshots/timelapses.

    For an example of how to utilize this, see the bundled ``classicwebcam`` plugin, or the ``testpicture`` plugin available `here <https://github.com/OctoPrint/OctoPrint-Testpicture>`_.
    """

    def get_webcam_configurations(self):
        """
        Used to retrieve a list of available webcams

        Returns:
            A list of :class:`~octoprint.schema.webcam.Webcam`: The available webcams, can be empty if none available.
        """

        return []

    def take_webcam_snapshot(self, webcamName):
        """
        Used to take a JPEG snapshot of the webcam. This method may raise an exception, you can expect failures to be handled.

         :param string webcamName: The name of the webcam to take a snapshot of as given by the configurations

        Returns:
            An iterator over bytes of the JPEG image
        """
        raise NotImplementedError()
