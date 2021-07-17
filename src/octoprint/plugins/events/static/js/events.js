/*
 * View model for OctoPrint-EventCoordinator
 *
 * Author: jneilliii
 * License: MIT
 */
$(function () {
    function EventcoordinatorViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];
        self.selected_command = ko.observable();

        self.event_details = function (data) {
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
            self.selected_command(self.event_details(false));
            self.settingsViewModel.settings.plugins.events.subscriptions.push(
                self.selected_command()
            );
            $("#EventCoordinatorEditor").modal("show");
        };

        self.editEvent = function (data) {
            self.selected_command(self.event_details(data));
            $("#EventCoordinatorEditor").modal("show");
        };

        self.removeEvent = function (data) {
            self.settingsViewModel.settings.plugins.events.subscriptions.remove(data);
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: EventcoordinatorViewModel,
        dependencies: ["settingsViewModel"],
        elements: ["#settings_plugin_events"]
    });
});
