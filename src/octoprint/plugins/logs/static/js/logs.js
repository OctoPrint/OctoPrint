$(function() {
    function LogsViewModel(parameters) {
        var self = this;
        var logsURL = "plugin/logs/logs"

        self.loginState = parameters[0];
        self.available_loggers = ko.observableArray();
        self.configured_loggers = ko.observableArray();

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

            OctoPrint.simpleApiCommand("logs", "getLoggingConfig")
                .done(self.fromGetLoggingConfigResponse);

            OctoPrint.simpleApiCommand("logs", "getAvailableLoggers")
                .done(self.fromGetAvailableLoggers);
        };

        self.fromResponse = function(response) {
            var files = response.files;
            if (files === undefined)
                return;

            self.listHelper.updateItems(files);
        };

        self.fromGetLoggingConfigResponse = function(data) {
            $.each(data.result.loggers, function(id, options) {
                if (options.level !== undefined) {
                    self.configured_loggers.push({id: id, level: options.level});
                }
            });
            //console.log(self.configured_loggers());
        };

        self.fromGetAvailableLoggers = function(data) {
            console.log(data.result);
            $.each(data.result, function(id, name) {
                self.available_loggers.push({name: name.name});
            });
            console.log(self.available_loggers());
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
        LogsViewModel,
        ["loginStateViewModel"],
        "#settings_plugin_logs"
    ]);
});
