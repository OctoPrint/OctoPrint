$(function() {
    function LogsViewModel(parameters) {
        var self = this;
        var logsURL = "plugin/logs/logs"

        self.loginState = parameters[0];
        self.availableLoggers = ko.observableArray();
        self.configuredLoggers = ko.observableArray();
        self.configuredLoggersChanged = false;

        self.availableLoggersSorted = ko.computed(function() {
            return _.sortBy(self.availableLoggers());
        });

        self.configuredLoggersSorted = ko.computed(function() {
            return _.sortBy(self.configuredLoggers(), function (o) {
                o.level();
                return o.component;
            });
        });

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
                .done(self.fromGetAvailableLoggersResponse);
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
                    self.configuredLoggers.push({component: component, level: ko.observable(options.level)});
                }
            });

            self.configuredLoggersChanged = false;
        };

        self.fromGetAvailableLoggersResponse = function(data) {
            self.availableLoggers([]);

            $.each(data.result, function(key, component) {
                if (component.toLowerCase().indexOf("octoprint") >= 0) {
                    self.availableLoggers.push(component);
                }
            });

            $.each(self.configuredLoggers(), function(key, logger) {
                self.availableLoggers.remove(logger.component);
            });
        };

        self.addLogger = function() {
            component = $("#availableLoggers").val();
            level = $("#availableLoggers_level").val();
            
            self.configuredLoggers.push({component: component, level: ko.observable(level)});
            self.availableLoggers.remove(component);
        };

        self.removeLogger = function(logger) {
            self.configuredLoggers.remove(logger);
            self.availableLoggers.push(logger.component);
        };

        self.removeFile = function(filename) {
            OctoPrint.delete(logsURL + "/" + filename)
                .done(self.requestData);
        };

        self.onSettingsShown = function() {
            self.requestData();
        };

        self.configuredLoggersSorted.subscribe(function () {
            self.configuredLoggersChanged = true;
        }, self);

        self.onSettingsBeforeSave = function () {
            if ( self.configuredLoggersChanged ) {
                console.log("ConfiguredLoggers has changed. Saving!");
                OctoPrint.simpleApiCommand("logs", "setLoggingConfig", {'config': ko.toJSON(self.configuredLoggers)});
            } else {
                console.log("ConfiguredLoggers has not changed. Not saving.");
            }
        };
    }


    OCTOPRINT_VIEWMODELS.push([
        LogsViewModel,
        ["loginStateViewModel"],
        "#settings_plugin_logs"
    ]);
});
