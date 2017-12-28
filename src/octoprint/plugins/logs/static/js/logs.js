$(function() {
    function LogsViewModel(parameters) {
        var self = this;
        var logsURL = "plugin/logs/logs"

        self.loginState = parameters[0];
        self.availableLoggers = ko.observableArray();
        self.configuredLoggers = ko.observableArray();

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
            self.configuredLoggers([]);

            $.each(data.result.loggers, function(component, options) {
                if (options.level !== undefined) {
                    self.configuredLoggers.push({component: component, level: options.level});
                }
            });

            self.configuredLoggers.sort();
        };

        self.fromGetAvailableLoggers = function(data) {
            self.availableLoggers([]);
            
            $.each(data.result, function(key, component) {
                if (component.toLowerCase().indexOf("octoprint") >= 0) {
                    self.availableLoggers.push(component);
                }
            });

            self.availableLoggers.sort();
        };

        self.addLogger = function() {
            component = $("#availableLoggers").val();
            level = $("#availableLoggers_level").val();
            
            self.configuredLoggers.push({component: component, level: level});
            self.availableLoggers.remove(component);

            self.configuredLoggers.sort();
        };

        self.removeLogger = function(logger) {
            self.configuredLoggers.remove(logger);
            self.availableLoggers.push(logger.component);

            self.availableLoggers.sort();
        };

        self.removeFile = function(filename) {
            OctoPrint.delete(logsURL + "/" + filename)
                .done(self.requestData);
        };

        self.onSettingsShown = function() {
            self.requestData();
        };

        self.onSettingsBeforeSave = function () {
            //console.log(self.configuredLoggers());
            //console.log(JSON.stringify(self.configuredLoggers()));
            OctoPrint.simpleApiCommand("logs", "setLoggingConfig", {'config': self.configuredLoggers()});
                //.done(self.fromGetLoggingConfigResponse);           
        };
    }


    OCTOPRINT_VIEWMODELS.push([
        LogsViewModel,
        ["loginStateViewModel"],
        "#settings_plugin_logs"
    ]);
});
