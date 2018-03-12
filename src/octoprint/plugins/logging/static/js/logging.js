(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {

    var OctoPrintLoggingClient = function(base) {
        this.base = base;

        this.baseUrl = this.base.getBlueprintUrl("logging");
        this.logsUrl = this.baseUrl + "logs";
        this.setupUrl = this.baseUrl + "setup";
    };

    OctoPrintLoggingClient.prototype.get = function(opts) {
        return this.base.get(this.baseUrl, opts);
    };

    OctoPrintLoggingClient.prototype.listLogs = function(opts) {
        return this.base.get(this.logsUrl, opts);
    };

    OctoPrintLoggingClient.prototype.deleteLog = function(file, opts) {
        var fileUrl = this.logsUrl + "/" + file;
        return this.base.delete(fileUrl, opts);
    };

    OctoPrintLoggingClient.prototype.downloadLog = function(file, opts) {
        var fileUrl = this.logsUrl + "/" + file;
        return this.base.download(fileUrl, opts);
    };

    OctoPrintLoggingClient.prototype.updateLevels = function(config, opts) {
        return this.base.putJson(this.setupUrl + "/levels", config, opts);
    };

    //~~ wrapper for backwards compatibility

    var DeprecatedOctoPrintLogsClient = function(base) {
        this.base = base;
        this.wrapped = this.base.plugins.logging;
    };

    DeprecatedOctoPrintLogsClient.prototype.list = function(opts) {
        log.warn("OctoPrintClient.logs.list has been deprecated as of OctoPrint 1.3.7, use OctoPrintClient.plugins.logging.listLogs instead");
        return this.wrapped.listLogs(opts);
    };

    DeprecatedOctoPrintLogsClient.prototype.delete = function(file, opts) {
        log.warn("OctoPrintClient.logs.delete has been deprecated as of OctoPrint 1.3.7, use OctoPrintClient.plugins.logging.deleteLog instead");
        return this.wrapped.deleteLog(file, opts);
    };

    DeprecatedOctoPrintLogsClient.prototype.download = function(file, opts) {
        log.warn("OctoPrintClient.logs.download has been deprecated as of OctoPrint 1.3.7, use OctoPrintClient.plugins.logging.downloadLog instead");
        return this.wrapped.downloadLog(file, opts);
    };

    // register plugin component
    OctoPrintClient.registerPluginComponent("logging", OctoPrintLoggingClient);

    // also register deprecated client under old endpoint
    OctoPrintClient.registerComponent("logs", DeprecatedOctoPrintLogsClient);

    return OctoPrintLoggingClient;
});

$(function() {
    function LoggingViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.availableLoggers = ko.observableArray();
        self.availableLoggersName = ko.observable();
        self.availableLoggersLevel = ko.observable();
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
            OctoPrint.plugins.logging.get()
                .done(self.fromResponse);
        };

        self.fromResponse = function(response) {
            self.fromLogsResponse(response.logs);
            self.fromSetupResponse(response.setup);
        };

        self.fromLogsResponse = function(response) {
            if (!response) return;

            var files = response.files;
            if (files === undefined)
                return;

            self.listHelper.updateItems(files);
        };

        self.fromSetupResponse = function(response) {
            if (!response) return;

            // levels
            var levels = [];
            var configuredLoggers = [];
            _.each(response.levels, function(level, logger) {
                var item = {component: logger, level: ko.observable(level)};
                item.level.subscribe(function() {
                    self.configuredLoggersHasChanged();
                });
                levels.push(item);
                configuredLoggers.push(logger);
            });
            self.configuredLoggers(levels);

            // loggers
            var availableLoggers = _.without(response.loggers, configuredLoggers);
            self.availableLoggers(availableLoggers);
        };

        self.configuredLoggersHasChanged = function () {
            self.configuredLoggersChanged = true;
        };

        self.addLogger = function() {
            var component = self.availableLoggersName();
            var level = self.availableLoggersLevel();

            self.configuredLoggers.push({component: component, level: ko.observable(level)});
            self.availableLoggers.remove(component);

            self.configuredLoggersHasChanged();
        };

        self.removeLogger = function(logger) {
            self.configuredLoggers.remove(logger);
            self.availableLoggers.push(logger.component);

            self.configuredLoggersHasChanged();
        };

        self.removeFile = function(filename) {
            OctoPrint.plugins.logging.deleteLog(filename)
                .done(self.requestData);
        };

        self.onSettingsShown = function() {
            self.requestData();
        };

        self.onSettingsBeforeSave = function () {
            if ( self.configuredLoggersChanged ) {
                console.log("ConfiguredLoggers has changed. Saving!");
                var levels = {};
                _.each(self.configuredLoggers(), function(data) {
                    levels[data.component] = data.level();
                });
                OctoPrint.plugins.logging.updateLevels(levels);
            } else {
                console.log("ConfiguredLoggers has not changed. Not saving.");
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: LoggingViewModel,
        additionalNames: ["logsViewModel"],
        dependencies: ["loginStateViewModel"],
        elements: ["#settings_plugin_logging"]
    });
});
