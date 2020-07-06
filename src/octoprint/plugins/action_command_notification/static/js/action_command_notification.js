$(function() {
    function ActionCommandNotificationViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];
        self.settings = parameters[2];

        self.notifications = ko.observableArray([]);

        self.toDateTimeString = function(timestamp) {
            return formatDate(timestamp);
        };

        self.requestData = function() {
            if (!self.loginState.hasPermission(self.access.permissions.PLUGIN_ACTION_COMMAND_NOTIFICATION_SHOW)) return;

            OctoPrint.plugins.action_command_notification.get()
                .done(self.fromResponse)
        };

        self.fromResponse = function(response) {
            self.notifications(response.notifications);
        };

        self.clear = function() {
            if (!self.loginState.hasPermission(self.access.permissions.PLUGIN_ACTION_COMMAND_NOTIFICATION_CLEAR)) return;

            OctoPrint.plugins.action_command_notification.clear();
        };

        self.onStartup = self.onUserLoggedIn = self.onUserLoggedOut = function() {
            self.requestData();
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (!self.loginState.hasPermission(self.access.permissions.PLUGIN_ACTION_COMMAND_NOTIFICATION_SHOW)) return;
            if (plugin !== "action_command_notification") {
                return;
            }

            self.requestData();

            if (data.message && self.settings.settings.plugins.action_command_notification.enable_popups()) {
                new PNotify({
                    title: gettext("Printer Notification"),
                    text: data.message,
                    hide: false,
                    icon: "fa fa-bell-o",
                    buttons: {
                        sticker: false,
                        closer: true
                    }
                });
            }
        };

    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ActionCommandNotificationViewModel,
        dependencies: ["loginStateViewModel", "accessViewModel", "settingsViewModel"],
        elements: ["#sidebar_plugin_action_command_notification_wrapper"]
    });
});
