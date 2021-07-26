/*
 * View model for OctoPrint-EventCoordinator
 *
 * Author: jneilliii
 * License: AGPLv3
 */
$(function () {
    function eventManagerViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];
        self.selectedCommand = ko.observable();

        self.eventDetails = function (data) {
            if (data === false) {
                return {
                    event: ko.observable(""),
                    command: ko.observable(""),
                    type: ko.observable(""),
                    enabled: ko.observable(true),
                    debug: ko.observable(false)
                };
            } else {
                if (!data.hasOwnProperty("enabled")) {
                    data["enabled"] = ko.observable(true);
                }
                if (!data.hasOwnProperty("debug")) {
                    data["debug"] = ko.observable(false);
                }
                return data;
            }
        };

        self.addEvent = function () {
            self.selectedCommand(self.eventDetails(false));
            self.settingsViewModel.settings.plugins.eventmanager.subscriptions.push(
                self.selectedCommand()
            );
            $("#EventManagerEditor").modal("show");
        };

        self.editEvent = function (data) {
            self.selectedCommand(self.eventDetails(data));
            $("#EventManagerEditor").modal("show");
        };

        self.removeEvent = function (data) {
            self.settingsViewModel.settings.plugins.eventmanager.subscriptions.remove(
                data
            );
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: eventManagerViewModel,
        dependencies: ["settingsViewModel"],
        elements: ["#settings_plugin_eventmanager"]
    });
});
