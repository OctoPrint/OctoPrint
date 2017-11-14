$(function() {
    function LoggingViewModel(parameters) {
        var self = this;
        var logsURL = "plugin/logging/logs"

        self.loginState = parameters[0];
        self.available_loggers = ko.observableArray();
        self.logging_config = ko.observableArray();

        // initialize list helper
        self.listHelper = new ItemListHelper(
            "logFiles",
            {
                "name": function(a, b) {
                    // sorts ascending
                    if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase()) return -1;
                    if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase()) return 1;
                    return 0;
                },
                "modification": function(a, b) {
                    // sorts descending
                    if (a["date"] > b["date"]) return -1;
                    if (a["date"] < b["date"]) return 1;
                    return 0;
                },
                "size": function(a, b) {
                    // sorts descending
                    if (a["size"] > b["size"]) return -1;
                    if (a["size"] < b["size"]) return 1;
                    return 0;
                }
            },
            {
            },
            "name",
            [],
            [],
            CONFIG_LOGFILESPERPAGE
        );

        self.requestData = function() {
            OctoPrint.get(logsURL)
                .done(self.fromResponse);
        };

        self.fromResponse = function(response) {
            var files = response.files;
            if (files === undefined)
                return;

            self.listHelper.updateItems(files);
        };

        self.removeFile = function(filename) {
            OctoPrint.delete(logsURL + "/" + filename)
                .done(self.requestData);
        };

        self.onSettingsShown = function() {
            self.requestData();
        };

/*
        self.onBeforeBinding = function () {
            self.global_settings.settings.plugins.gcodesystemcommands.command_definitions.subscribe(function() {
                settings = self.global_settings.settings.plugins.gcodesystemcommands;
                self.command_definitions(settings.command_definitions.slice(0));            
            });
        };

        self.onSettingsBeforeSave = function () {
            self.global_settings.settings.plugins.gcodesystemcommands.command_definitions(self.command_definitions.slice(0));
        };
*/
    }


    OCTOPRINT_VIEWMODELS.push([
        LoggingViewModel,
        ["loginStateViewModel"],
        "#logs"
    ]);
});
