$(function () {
    function NavigationViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.appearance = parameters[1];
        self.settings = parameters[2];
        self.usersettings = parameters[3];
        self.system = parameters[4];
        self.access = parameters[5];

        self.offline = ko.observable(!ONLINE);
        self.offlinePopoverContent = function () {
            return (
                "<p>" +
                gettext(
                    "OctoPrint cannot reach the internet. If this is not " +
                        "intentional, please check OctoPrint's network settings and " +
                        "the connectivity check configuration. Updates, plugin repository " +
                        "and anything else requiring access to the public internet will not " +
                        "work."
                ) +
                "</p>"
            );
        };

        self.appearanceClasses = ko.pureComputed(function () {
            var classes = self.appearance.color();
            if (self.appearance.colorTransparent()) {
                classes += " transparent";
            }
            return classes;
        });

        self.onServerReconnect =
            self.onServerConnect =
            self.onEventConnectivityChanged =
                function () {
                    self.offline(!ONLINE);
                };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: NavigationViewModel,
        dependencies: [
            "loginStateViewModel",
            "appearanceViewModel",
            "settingsViewModel",
            "userSettingsViewModel",
            "systemViewModel",
            "accessViewModel"
        ],
        elements: ["#navbar"]
    });
});
