$(function () {
    function LoggingViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];

        self.availableLoggers = ko.observableArray();
        self.availableLoggersName = ko.observable();
        self.availableLoggersLevel = ko.observable();
        self.configuredLoggers = ko.observableArray();
        self.configuredLoggersChanged = false;
        self.serialLogEnabled = ko.observable();
        self.pluginTimingsLogEnabled = ko.observable();
        self.freeSpace = ko.observable(undefined);
        self.totalSpace = ko.observable(undefined);

        self.markedForDeletion = ko.observableArray([]);

        self.availableLoggersSorted = ko.computed(function () {
            return _.sortBy(self.availableLoggers());
        });

        // initialize list helper
        self.listHelper = new ItemListHelper(
            "logFiles",
            {
                name: function (a, b) {
                    // sorts ascending
                    if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase())
                        return -1;
                    if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase())
                        return 1;
                    return 0;
                },
                modification: function (a, b) {
                    // sorts descending
                    if (a["date"] > b["date"]) return -1;
                    if (a["date"] < b["date"]) return 1;
                    return 0;
                },
                size: function (a, b) {
                    // sorts descending
                    if (a["size"] > b["size"]) return -1;
                    if (a["size"] < b["size"]) return 1;
                    return 0;
                }
            },
            {},
            "name",
            [],
            [],
            CONFIG_LOGFILESPERPAGE
        );

        self.requestData = function () {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_LOGGING_MANAGE
                )
            ) {
                return;
            }
            OctoPrint.plugins.logging.get().done(self.fromResponse);
        };

        self.fromResponse = function (response) {
            self.fromLogsResponse(response.logs);
            self.fromSetupResponse(response.setup);
            self.fromSerialLogResponse(response.serial_log);
            self.fromPluginTimingsLogResponse(response.plugintimings_log);
        };

        self.fromLogsResponse = function (response) {
            if (!response) return;

            var files = response.files;
            if (files === undefined) return;

            self.listHelper.updateItems(files);

            self.freeSpace(response.free);
            self.totalSpace(response.total);
        };

        self.fromSetupResponse = function (response) {
            if (!response) return;

            // levels
            var levels = [];
            var configuredLoggers = [];
            _.each(response.levels, function (level, logger) {
                var item = {component: logger, level: ko.observable(level)};
                item.level.subscribe(function () {
                    self.configuredLoggersHasChanged();
                });
                levels.push(item);
                configuredLoggers.push(logger);
            });
            var sortedLevels = _.sortBy(levels, function (o) {
                return o.component;
            });
            self.configuredLoggers(sortedLevels);

            // loggers
            var availableLoggers = _.difference(response.loggers, configuredLoggers);
            self.availableLoggers(availableLoggers);
            self.configuredLoggersChanged = false;
        };

        self.fromSerialLogResponse = function (response) {
            if (!response) return;

            self.serialLogEnabled(response.enabled);
        };

        self.fromPluginTimingsLogResponse = function (response) {
            if (!response) return;

            self.pluginTimingsLogEnabled(response.enabled);
        };

        self.serialLogPopoverContent = function () {
            return self.popoverContent("serial.log");
        };

        self.pluginTimingsLogPopoverContent = function () {
            return self.popoverContent("plugintimings.log");
        };

        self.popoverContent = function (logfile) {
            var free = self.freeSpace();
            var total = self.totalSpace();

            var content =
                "<p>" +
                _.sprintf(
                    gettext(
                        "You currently have <code>%(logfile)s</code> enabled. Please remember to turn it off " +
                            "again once your are done debugging whatever issue prompted you to turn it on."
                    ),
                    {logfile: logfile}
                ) +
                "</p><p>" +
                gettext(
                    "It can negatively impact print performance and also take up a lot of storage space " +
                        "depending on how long you keep it enabled and thus should only be used for " +
                        "debugging."
                ) +
                "</p>";

            if (free !== undefined && total !== undefined) {
                content +=
                    "<p class='muted'><small><strong>" +
                    gettext("Log storage:") +
                    "</strong> " +
                    formatSize(free) +
                    " / " +
                    formatSize(total) +
                    "</small></p>";
            }

            return content;
        };

        self.configuredLoggersHasChanged = function () {
            self.configuredLoggersChanged = true;
        };

        self.addLogger = function () {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_LOGGING_MANAGE
                )
            ) {
                return;
            }

            var component = self.availableLoggersName();
            if (!component) {
                return;
            }
            var level = self.availableLoggersLevel();

            self.configuredLoggers.push({
                component: component,
                level: ko.observable(level)
            });
            self.availableLoggers.remove(component);

            self.configuredLoggersHasChanged();
        };

        self.removeLogger = function (logger) {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_LOGGING_MANAGE
                )
            ) {
                return;
            }

            self.configuredLoggers.remove(logger);
            self.availableLoggers.push(logger.component);

            self.configuredLoggersHasChanged();
        };

        self.removeFile = function (filename) {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_LOGGING_MANAGE
                )
            ) {
                return;
            }
            var perform = function () {
                OctoPrint.plugins.logging.deleteLog(filename).done(self.requestData);
            };

            showConfirmationDialog(
                _.sprintf(gettext('You are about to delete log file "%(name)s".'), {
                    name: _.escape(filename)
                }),
                perform
            );
        };

        self.markFilesOnPage = function () {
            self.markedForDeletion(
                _.uniq(
                    self
                        .markedForDeletion()
                        .concat(_.map(self.listHelper.paginatedItems(), "name"))
                )
            );
        };

        self.markAllFiles = function () {
            self.markedForDeletion(_.map(self.listHelper.allItems, "name"));
        };

        self.clearMarkedFiles = function () {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_LOGGING_MANAGE
                )
            ) {
                return;
            }
            self.markedForDeletion.removeAll();
        };

        self.removeMarkedFiles = function () {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_LOGGING_MANAGE
                )
            ) {
                return;
            }
            var perform = function () {
                self._bulkRemove(self.markedForDeletion(), "files").done(function () {
                    self.markedForDeletion.removeAll();
                });
            };

            showConfirmationDialog(
                _.sprintf(gettext("You are about to delete %(count)d log files."), {
                    count: self.markedForDeletion().length
                }),
                perform
            );
        };

        self.enableBulkDownload = ko.pureComputed(function () {
            return self.markedForDeletion().length && !self.bulkDownloadUrlTooLong();
        });

        self.bulkDownloadUrlTooLong = ko.pureComputed(function () {
            return BASEURL.length + self.bulkDownloadUrl().length >= 2000;
        });

        self.bulkDownloadButtonUrl = ko.pureComputed(function () {
            var files = self.markedForDeletion();
            if (!files.length || self.bulkDownloadUrlTooLong()) {
                return "javascript:void(0)";
            }
            return self.bulkDownloadUrl();
        });

        self.bulkDownloadUrl = function () {
            var files = self.markedForDeletion();
            return OctoPrint.plugins.logging.bulkDownloadUrl(files);
        };

        self.onServerReconnect =
            self.onUserLoggedIn =
            self.onEventSettingsUpdated =
            self.onSettingsShown =
                function () {
                    if (
                        !self.loginState.hasPermission(
                            self.access.permissions.PLUGIN_LOGGING_MANAGE
                        )
                    ) {
                        return;
                    }
                    self.requestData();
                };

        self.onSettingsBeforeSave = function () {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_LOGGING_MANAGE
                )
            ) {
                return;
            }
            if (self.configuredLoggersChanged) {
                console.log("ConfiguredLoggers has changed. Saving!");
                var levels = {};
                _.each(self.configuredLoggers(), function (data) {
                    levels[data.component] = data.level();
                });
                OctoPrint.plugins.logging.updateLevels(levels);
            } else {
                console.log("ConfiguredLoggers has not changed. Not saving.");
            }
        };

        self._bulkRemove = function (files) {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_LOGGING_MANAGE
                )
            ) {
                return;
            }
            var title = gettext("Deleting log files");
            var message = _.sprintf(gettext("Deleting %(count)d log files..."), {
                count: files.length
            });
            var handler = function (filename) {
                return OctoPrint.plugins.logging
                    .deleteLog(filename)
                    .done(function () {
                        deferred.notify(
                            _.sprintf(gettext("Deleted %(filename)s..."), {
                                filename: _.escape(filename)
                            }),
                            true
                        );
                    })
                    .fail(function (jqXHR) {
                        var short = _.sprintf(
                            gettext("Deletion of %(filename)s failed, continuing..."),
                            {filename: _.escape(filename)}
                        );
                        var long = _.sprintf(
                            gettext("Deletion of %(filename)s failed: %(error)s"),
                            {
                                filename: _.escape(filename),
                                error: _.escape(jqXHR.responseText)
                            }
                        );
                        deferred.notify(short, long, false);
                    });
            };

            var deferred = $.Deferred();

            var promise = deferred.promise();

            var options = {
                title: title,
                message: message,
                max: files.length,
                output: true
            };
            showProgressModal(options, promise);

            var requests = [];
            _.each(files, function (filename) {
                var request = handler(filename);
                requests.push(request);
            });
            $.when.apply($, _.map(requests, wrapPromiseWithAlways)).done(function () {
                deferred.resolve();
                self.requestData();
            });

            return promise;
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: LoggingViewModel,
        additionalNames: ["logsViewModel"],
        dependencies: ["loginStateViewModel", "accessViewModel"],
        elements: [
            "#settings_plugin_logging",
            "#navbar_plugin_logging_seriallog",
            "#navbar_plugin_logging_plugintimingslog"
        ]
    });
});
