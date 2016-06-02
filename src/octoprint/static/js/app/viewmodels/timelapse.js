$(function() {
    function TimelapseViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];

        self.timelapsePopup = undefined;

        self.defaultFps = 25;
        self.defaultPostRoll = 0;
        self.defaultInterval = 10;

        self.timelapseType = ko.observable(undefined);
        self.timelapseTimedInterval = ko.observable(self.defaultInterval);
        self.timelapsePostRoll = ko.observable(self.defaultPostRoll);
        self.timelapseFps = ko.observable(self.defaultFps);

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

        self.isOperational.subscribe(function(newValue) {
            self.requestData();
        });

        self.timelapseType.subscribe(function(newValue) {
            self.isDirty(true);
        });
        self.timelapseTimedInterval.subscribe(function(newValue) {
            self.isDirty(true);
        });
        self.timelapsePostRoll.subscribe(function(newValue) {
            self.isDirty(true);
        });
        self.timelapseFps.subscribe(function(newValue) {
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
            $.ajax({
                url: API_BASEURL + "timelapse?unrendered=true",
                type: "GET",
                dataType: "json",
                success: self.fromResponse
            });
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
            $.ajax({
                url: API_BASEURL + "timelapse/" + filename,
                type: "DELETE",
                dataType: "json",
                success: self.requestData
            });
        };

        self.removeUnrendered = function(name) {
            $.ajax({
                url: API_BASEURL + "timelapse/unrendered/" + name,
                type: "DELETE",
                dataType: "json",
                success: self.requestData
            });
        };

        self.renderUnrendered = function(name) {
            $.ajax({
                url: API_BASEURL + "timelapse/unrendered/" + name,
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({command: "render"})
            });
        };

        self.save = function(data, event) {
            var payload = {
                "type": self.timelapseType(),
                "postRoll": self.timelapsePostRoll(),
                "fps": self.timelapseFps(),
                "save": self.persist()
            };

            if (self.timelapseType() == "timed") {
                payload["interval"] = self.timelapseTimedInterval();
            }

            $.ajax({
                url: API_BASEURL + "timelapse",
                type: "POST",
                dataType: "json",
                data: payload,
                success: self.fromResponse
            });
        };

        self.displayTimelapsePopup = function(options) {
            if (self.timelapsePopup !== undefined) {
                self.timelapsePopup.remove();
            }

            _.extend(options, {
                callbacks: {
                    before_close: function(notice) {
                        if (self.timelapsePopup == notice) {
                            self.timelapsePopup = undefined;
                        }
                    }
                }
            });

            self.timelapsePopup = new PNotify(options);
        };

        self.onDataUpdaterReconnect = function() {
            self.requestData();
        };

        self.onEventPostRollStart = function(payload) {
            var title = gettext("Capturing timelapse postroll");

            var text;
            if (!payload.postroll_duration) {
                text = _.sprintf(gettext("Now capturing timelapse post roll, this will take only a moment..."), format);
            } else {
                var format = {
                    time: moment().add(payload.postroll_duration, "s").format("LT")
                };

                if (payload.postroll_duration > 60) {
                    format.duration = _.sprintf(gettext("%(minutes)d min"), {minutes: payload.postroll_duration / 60});
                    text = _.sprintf(gettext("Now capturing timelapse post roll, this will take approximately %(duration)s (so until %(time)s)..."), format);
                } else {
                    format.duration = _.sprintf(gettext("%(seconds)d sec"), {seconds: payload.postroll_duration});
                    text = _.sprintf(gettext("Now capturing timelapse post roll, this will take approximately %(duration)s..."), format);
                }
            }

            self.displayTimelapsePopup({
                title: title,
                text: text,
                hide: false
            });
        };

        self.onEventMovieRendering = function(payload) {
            self.displayTimelapsePopup({
                title: gettext("Rendering timelapse"),
                text: _.sprintf(gettext("Now rendering timelapse %(movie_prefix)s. Due to performance reasons it is not recommended to start a print job while a movie is still rendering."), payload),
                hide: false
            });
        };

        self.onEventMovieFailed = function(payload) {
            var html = "<p>" + _.sprintf(gettext("Rendering of timelapse %(movie_prefix)s failed with return code %(returncode)s"), payload) + "</p>";
            html += pnotifyAdditionalInfo('<pre style="overflow: auto">' + payload.error + '</pre>');

            self.displayTimelapsePopup({
                title: gettext("Rendering failed"),
                text: html,
                type: "error",
                hide: false
            });
        };

        self.onEventMovieDone = function(payload) {
            self.displayTimelapsePopup({
                title: gettext("Timelapse ready"),
                text: _.sprintf(gettext("New timelapse %(movie_prefix)s is done rendering."), payload),
                type: "success",
                callbacks: {
                    before_close: function(notice) {
                        if (self.timelapsePopup == notice) {
                            self.timelapsePopup = undefined;
                        }
                    }
                }
            });
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
