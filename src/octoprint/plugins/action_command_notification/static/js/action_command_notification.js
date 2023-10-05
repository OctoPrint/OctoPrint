$(function () {
    function ActionCommandNotificationViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];
        self.settings = parameters[2];

        self.notifications = ko.observableArray([]);
        self.sortDesc = ko.observable(false);
        self.sortDesc.subscribe(function () {
            self._toLocalStorage();
        });

        self.regexValid = function () {
            try {
                new RegExp(
                    self.settings.settings.plugins.action_command_notification.filter()
                );
                return true;
            } catch (e) {
                return false;
            }
        };

        self.toDateTimeString = function (timestamp) {
            return formatDate(timestamp);
        };

        self.requestData = function () {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_ACTION_COMMAND_NOTIFICATION_SHOW
                )
            )
                return;

            OctoPrint.plugins.action_command_notification.get().done(self.fromResponse);
        };

        self.fromResponse = function (response) {
            var notifications = response.notifications;
            if (self.sortDesc()) {
                notifications.reverse();
            }
            self.notifications(notifications);
        };

        self.clear = function () {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_ACTION_COMMAND_NOTIFICATION_CLEAR
                )
            )
                return;

            OctoPrint.plugins.action_command_notification.clear();
        };

        self.toggleSorting = function () {
            self.sortDesc(!self.sortDesc());
            self.requestData();
        };

        self.onStartup =
            self.onUserLoggedIn =
            self.onUserLoggedOut =
                function () {
                    self.requestData();
                };

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_ACTION_COMMAND_NOTIFICATION_SHOW
                )
            )
                return;
            if (plugin !== "action_command_notification") {
                return;
            }

            self.requestData();

            if (
                data.message &&
                self.settings.settings.plugins.action_command_notification.enable_popups()
            ) {
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

        var optionsLocalStorageKey = "plugin.action_command_notification.options";
        self._toLocalStorage = function () {
            saveToLocalStorage(optionsLocalStorageKey, {sortDesc: self.sortDesc()});
        };

        self._fromLocalStorage = function () {
            var data = loadFromLocalStorage(optionsLocalStorageKey);
            if (data["sortDesc"] !== undefined) {
                self.sortDesc(!!data["sortDesc"]);
            }
        };

        self._fromLocalStorage();
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ActionCommandNotificationViewModel,
        dependencies: ["loginStateViewModel", "accessViewModel", "settingsViewModel"],
        elements: [
            "#sidebar_plugin_action_command_notification_wrapper",
            "#settings_plugin_action_command_notification"
        ]
    });
});
