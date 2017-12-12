$(function() {
    function PrinterStateViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];

        self.stateString = ko.observable(undefined);
        self.isErrorOrClosed = ko.observable(undefined);
        self.isOperational = ko.observable(undefined);
        self.isPrinting = ko.observable(undefined);
        self.isPaused = ko.observable(undefined);
        self.isError = ko.observable(undefined);
        self.isReady = ko.observable(undefined);
        self.isLoading = ko.observable(undefined);
        self.isSdReady = ko.observable(undefined);

        self.enablePrint = ko.pureComputed(function() {
            return self.isOperational() && self.isReady() && !self.isPrinting() && self.loginState.isUser() && self.filename() != undefined;
        });
        self.enablePause = ko.pureComputed(function() {
            return self.isOperational() && (self.isPrinting() || self.isPaused()) && self.loginState.isUser();
        });
        self.enableCancel = ko.pureComputed(function() {
            return self.isOperational() && (self.isPrinting() || self.isPaused()) && self.loginState.isUser();
        });

        self.filename = ko.observable(undefined);
        self.filepath = ko.observable(undefined);
        self.filedisplay = ko.observable(undefined);
        self.progress = ko.observable(undefined);
        self.filesize = ko.observable(undefined);
        self.filepos = ko.observable(undefined);
        self.printTime = ko.observable(undefined);
        self.printTimeLeft = ko.observable(undefined);
        self.printTimeLeftOrigin = ko.observable(undefined);
        self.sd = ko.observable(undefined);
        self.timelapse = ko.observable(undefined);

        self.busyFiles = ko.observableArray([]);

        self.filament = ko.observableArray([]);
        self.estimatedPrintTime = ko.observable(undefined);
        self.lastPrintTime = ko.observable(undefined);

        self.currentHeight = ko.observable(undefined);

        self.TITLE_PRINT_BUTTON_PAUSED = gettext("Restarts the print job from the beginning");
        self.TITLE_PRINT_BUTTON_UNPAUSED = gettext("Starts the print job");
        self.TITLE_PAUSE_BUTTON_PAUSED = gettext("Resumes the print job");
        self.TITLE_PAUSE_BUTTON_UNPAUSED = gettext("Pauses the print job");

        self.titlePrintButton = ko.observable(self.TITLE_PRINT_BUTTON_UNPAUSED);
        self.titlePauseButton = ko.observable(self.TITLE_PAUSE_BUTTON_UNPAUSED);

        self.estimatedPrintTimeString = ko.pureComputed(function() {
            if (self.lastPrintTime())
                return formatFuzzyPrintTime(self.lastPrintTime());
            if (self.estimatedPrintTime())
                return formatFuzzyPrintTime(self.estimatedPrintTime());
            return "-";
        });
        self.byteString = ko.pureComputed(function() {
            if (!self.filesize())
                return "-";
            var filepos = self.filepos() ? formatSize(self.filepos()) : "-";
            return filepos + " / " + formatSize(self.filesize());
        });
        self.heightString = ko.pureComputed(function() {
            if (!self.currentHeight())
                return "-";
            return _.sprintf("%.02fmm", self.currentHeight());
        });
        self.printTimeString = ko.pureComputed(function() {
            if (!self.printTime())
                return "-";
            return formatDuration(self.printTime());
        });
        self.printTimeLeftString = ko.pureComputed(function() {
            if (self.printTimeLeft() == undefined) {
                if (!self.printTime() || !(self.isPrinting() || self.isPaused())) {
                    return "-";
                } else {
                    return gettext("Still stabilizing...");
                }
            } else {
                return formatFuzzyPrintTime(self.printTimeLeft());
            }
        });
        self.printTimeLeftOriginString = ko.pureComputed(function() {
            var value = self.printTimeLeftOrigin();
            switch (value) {
                case "linear": {
                    return gettext("Based on a linear approximation (very low accuracy, especially at the beginning of the print)");
                }
                case "analysis": {
                    return gettext("Based on the estimate from analysis of file (medium accuracy)");
                }
                case "mixed-analysis": {
                    return gettext("Based on a mix of estimate from analysis and calculation (medium accuracy)");
                }
                case "average": {
                    return gettext("Based on the average total of past prints of this model with the same printer profile (usually good accuracy)");
                }
                case "mixed-average": {
                    return gettext("Based on a mix of average total from past prints and calculation (usually good accuracy)");
                }
                case "estimate": {
                    return gettext("Based on the calculated estimate (best accuracy)");
                }
                default: {
                    return "";
                }
            }
        });
        self.printTimeLeftOriginClass = ko.pureComputed(function() {
            var value = self.printTimeLeftOrigin();
            switch (value) {
                default:
                case "linear": {
                    return "text-error";
                }
                case "analysis":
                case "mixed-analysis": {
                    return "text-warning";
                }
                case "average":
                case "mixed-average":
                case "estimate": {
                    return "text-success";
                }
            }
        });
        self.progressString = ko.pureComputed(function() {
            if (!self.progress())
                return 0;
            return self.progress();
        });
        self.progressBarString = ko.pureComputed(function() {
            if (!self.progress()) {
                return "";
            }
            return _.sprintf("%d%%", self.progress());
        });
        self.pauseString = ko.pureComputed(function() {
            if (self.isPaused())
                return gettext("Continue");
            else
                return gettext("Pause");
        });

        self.timelapseString = ko.pureComputed(function() {
            var timelapse = self.timelapse();

            if (!timelapse || !timelapse.hasOwnProperty("type"))
                return "-";

            var type = timelapse["type"];
            if (type == "zchange") {
                return gettext("On Z Change");
            } else if (type == "timed") {
                return gettext("Timed") + " (" + timelapse["options"]["interval"] + " " + gettext("sec") + ")";
            } else {
                return "-";
            }
        });

        self.fromCurrentData = function(data) {
            self._fromData(data);
        };

        self.fromHistoryData = function(data) {
            self._fromData(data);
        };

        self.fromTimelapseData = function(data) {
            self.timelapse(data);
        };

        self._fromData = function(data) {
            self._processStateData(data.state);
            self._processJobData(data.job);
            self._processProgressData(data.progress);
            self._processZData(data.currentZ);
            self._processBusyFiles(data.busyFiles);
        };

        self._processStateData = function(data) {
            var prevPaused = self.isPaused();

            self.stateString(gettext(data.text));
            self.isErrorOrClosed(data.flags.closedOrError);
            self.isOperational(data.flags.operational);
            self.isPaused(data.flags.paused);
            self.isPrinting(data.flags.printing);
            self.isError(data.flags.error);
            self.isReady(data.flags.ready);
            self.isSdReady(data.flags.sdReady);

            if (self.isPaused() != prevPaused) {
                if (self.isPaused()) {
                    self.titlePrintButton(self.TITLE_PRINT_BUTTON_PAUSED);
                    self.titlePauseButton(self.TITLE_PAUSE_BUTTON_PAUSED);
                } else {
                    self.titlePrintButton(self.TITLE_PRINT_BUTTON_UNPAUSED);
                    self.titlePauseButton(self.TITLE_PAUSE_BUTTON_UNPAUSED);
                }
            }
        };

        self._processJobData = function(data) {
            if (data.file) {
                self.filename(data.file.name);
                self.filepath(data.file.path);
                self.filesize(data.file.size);
                self.filedisplay(data.file.display);
                self.sd(data.file.origin == "sdcard");
            } else {
                self.filename(undefined);
                self.filepath(undefined);
                self.filesize(undefined);
                self.filedisplay(undefined);
                self.sd(undefined);
            }

            self.estimatedPrintTime(data.estimatedPrintTime);
            self.lastPrintTime(data.lastPrintTime);

            var result = [];
            if (data.filament && typeof(data.filament) == "object" && _.keys(data.filament).length > 0) {
                var keys = _.keys(data.filament);
                keys.sort();
                _.each(keys, function(key) {
                    if (!_.startsWith(key, "tool") || !data.filament[key] || !data.filament[key].hasOwnProperty("length") || data.filament[key].length <= 0) return;

                    result.push({
                        name: ko.observable(gettext("Tool") + " " + key.substr("tool".length)),
                        data: ko.observable(data.filament[key])
                    });
                });
            }
            self.filament(result);
        };

        self._processProgressData = function(data) {
            if (data.completion) {
                self.progress(data.completion);
            } else {
                self.progress(undefined);
            }
            self.filepos(data.filepos);
            self.printTime(data.printTime);
            self.printTimeLeft(data.printTimeLeft);
            self.printTimeLeftOrigin(data.printTimeLeftOrigin);
        };

        self._processZData = function(data) {
            self.currentHeight(data);
        };

        self._processBusyFiles = function(data) {
            var busyFiles = [];
            _.each(data, function(entry) {
                if (entry.hasOwnProperty("path") && entry.hasOwnProperty("origin")) {
                    busyFiles.push(entry.origin + ":" + entry.path);
                }
            });
            self.busyFiles(busyFiles);
        };

        self.print = function() {
            if (self.isPaused()) {
                showConfirmationDialog({
                    message: gettext("This will restart the print job from the beginning."),
                    onproceed: function() {
                        OctoPrint.job.restart();
                    }
                });
            } else {
                OctoPrint.job.start();
            }
        };

        self.onlyPause = function() {
            OctoPrint.job.pause();
        };

        self.onlyResume = function() {
            OctoPrint.job.resume();
        };

        self.pause = function(action) {
            OctoPrint.job.togglePause();
        };

        self.cancel = function() {
            if (!self.settings.feature_printCancelConfirmation()) {
                OctoPrint.job.cancel();
            } else {
                showConfirmationDialog({
                    message: gettext("This will cancel your print."),
                    cancel: gettext("No"),
                    proceed: gettext("Yes"),
                    onproceed: function() {
                        OctoPrint.job.cancel();
                    }
                });
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: PrinterStateViewModel,
        dependencies: ["loginStateViewModel", "settingsViewModel"],
        elements: ["#state_wrapper", "#drop_overlay"]
    });
});
