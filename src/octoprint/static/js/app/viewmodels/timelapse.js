$(function() {
    function TimelapseViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];

        self.defaultFps = 25;
        self.defaultPostRoll = 0;
        self.defaultInterval = 10;
        self.defaultRetractionZHop = 0;

        self.timelapseType = ko.observable(undefined);
        self.timelapseTimedInterval = ko.observable(self.defaultInterval);
        self.timelapsePostRoll = ko.observable(self.defaultPostRoll);
        self.timelapseFps = ko.observable(self.defaultFps);
        self.timelapseRetractionZHop = ko.observable(self.defaultRetractionZHop);

        self.persist = ko.observable(false);
        self.isDirty = ko.observable(false);

        self.isErrorOrClosed = ko.observable(undefined);
        self.isOperational = ko.observable(undefined);
        self.isPrinting = ko.observable(undefined);
        self.isPaused = ko.observable(undefined);
        self.isError = ko.observable(undefined);
        self.isReady = ko.observable(undefined);
        self.isLoading = ko.observable(undefined);

        self.isBusy = ko.pureComputed(function() {
            return self.isPrinting() || self.isPaused();
        });

        self.timelapseTypeSelected = ko.pureComputed(function() {
            return ("off" != self.timelapseType());
        });
        self.intervalInputEnabled = ko.pureComputed(function() {
            return ("timed" == self.timelapseType());
        });
        self.saveButtonEnabled = ko.pureComputed(function() {
            return self.isDirty() && self.isOperational() && !self.isPrinting() && self.loginState.isUser();
        });

        self.isOperational.subscribe(function() {
            self.requestData();
        });

        self.timelapseType.subscribe(function() {
            self.isDirty(true);
        });
        self.timelapseTimedInterval.subscribe(function() {
            self.isDirty(true);
        });
        self.timelapsePostRoll.subscribe(function() {
            self.isDirty(true);
        });
        self.timelapseFps.subscribe(function() {
            self.isDirty(true);
        });
        self.timelapseRetractionZHop.subscribe(function(newValue) {
            self.isDirty(true);
        });

        // initialize list helper
        self.listHelper = new ItemListHelper(
            "timelapseFiles",
            {
                "name": function(a, b) {
                    // sorts ascending
                    if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase()) return -1;
                    if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase()) return 1;
                    return 0;
                },
                "creation": function(a, b) {
                    // sorts descending
                    if (a["date"] > b["date"]) return -1;
                    if (a["date"] < b["date"]) return 1;
                    return 0;
                },
                "size": function(a, b) {
                    // sorts descending
                    if (a["bytes"] > b["bytes"]) return -1;
                    if (a["bytes"] < b["bytes"]) return 1;
                    return 0;
                }
            },
            {
            },
            "name",
            [],
            [],
            CONFIG_TIMELAPSEFILESPERPAGE
        );

        // initialize list helper for unrendered timelapses
        self.unrenderedListHelper = new ItemListHelper(
            "unrenderedTimelapseFiles",
            {
                "name": function(a, b) {
                    // sorts ascending
                    if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase()) return -1;
                    if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase()) return 1;
                    return 0;
                },
                "creation": function(a, b) {
                    // sorts descending
                    if (a["date"] > b["date"]) return -1;
                    if (a["date"] < b["date"]) return 1;
                    return 0;
                },
                "size": function(a, b) {
                    // sorts descending
                    if (a["bytes"] > b["bytes"]) return -1;
                    if (a["bytes"] < b["bytes"]) return 1;
                    return 0;
                }
            },
            {
            },
            "name",
            [],
            [],
            CONFIG_TIMELAPSEFILESPERPAGE
        );

        self.requestData = function() {
            OctoPrint.timelapse.get({ data: { unrendered: true} })
                .done(self.fromResponse);
        };

        self.fromResponse = function(response) {
            var config = response.config;
            if (config === undefined) return;

            self.timelapseType(config.type);
            self.listHelper.updateItems(response.files);
            if (response.unrendered) {
                self.unrenderedListHelper.updateItems(response.unrendered);
            }

            if (config.type == "timed") {
                if (config.interval != undefined && config.interval > 0) {
                    self.timelapseTimedInterval(config.interval);
                }
            } else {
                self.timelapseTimedInterval(self.defaultInterval);
            }

            if (config.type == "zchange") {
                if (config.retractionZHop != undefined && config.retractionZHop > 0) {
                    self.timelapseRetractionZHop(config.retractionZHop);
                }
            } else {
                self.timelapseRetractionZHop(self.defaultRetractionZHop);
            }

            if (config.postRoll != undefined && config.postRoll >= 0) {
                self.timelapsePostRoll(config.postRoll);
            } else {
                self.timelapsePostRoll(self.defaultPostRoll);
            }

            if (config.fps != undefined && config.fps > 0) {
                self.timelapseFps(config.fps);
            } else {
                self.timelapseFps(self.defaultFps);
            }

            self.persist(false);
            self.isDirty(false);
        };

        self.fromCurrentData = function(data) {
            self._processStateData(data.state);
        };

        self.fromHistoryData = function(data) {
            self._processStateData(data.state);
        };

        self._processStateData = function(data) {
            self.isErrorOrClosed(data.flags.closedOrError);
            self.isOperational(data.flags.operational);
            self.isPaused(data.flags.paused);
            self.isPrinting(data.flags.printing);
            self.isError(data.flags.error);
            self.isReady(data.flags.ready);
            self.isLoading(data.flags.loading);
        };

        self.removeFile = function(filename) {
            OctoPrint.timelapse.delete(filename)
                .done(self.requestData);
        };

        self.removeUnrendered = function(name) {
            OctoPrint.timelapse.deleteUnrendered(name)
                .done(self.requestData);
        };

        self.renderUnrendered = function(name) {
            OctoPrint.timelapse.renderUnrendered(name)
                .done(self.requestData);
        };

        self.save = function() {
            var payload = {
                "type": self.timelapseType(),
                "postRoll": self.timelapsePostRoll(),
                "fps": self.timelapseFps(),
                "save": self.persist()
            };

            if (self.timelapseType() == "timed") {
                payload["interval"] = self.timelapseTimedInterval();
            }

            if (self.timelapseType() == "zchange") {
                payload["retractionZHop"] = self.timelapseRetractionZHop();
            }

            OctoPrint.timelapse.saveConfig(payload)
                .done(self.fromResponse);
        };

        self.onDataUpdaterReconnect = function() {
            self.requestData();
        };

        self.onEventMovieDone = function() {
            self.requestData();
        };

        self.onStartup = function() {
            self.requestData();
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        TimelapseViewModel,
        ["loginStateViewModel"],
        "#timelapse"
    ]);
});
