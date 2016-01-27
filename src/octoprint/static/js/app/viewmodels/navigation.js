$(function() {
    function NavigationViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.appearance = parameters[1];
        self.settings = parameters[2];
        self.usersettings = parameters[3];
        self.system = parameters[4];

        self.appearanceClasses = ko.pureComputed(function() {
            var classes = self.appearance.color();
            if (self.appearance.colorTransparent()) {
                classes += " transparent";
            }
            return classes;
        });

    }

    OCTOPRINT_VIEWMODELS.push([
        NavigationViewModel,
        ["loginStateViewModel", "appearanceViewModel", "settingsViewModel", "userSettingsViewModel", "systemViewModel"],
        "#navbar"
    ]);
});
