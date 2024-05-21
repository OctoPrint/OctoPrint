$(function () {
    function PrinterStateViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];
        self.access = parameters[2];

        self.allViewModels = undefined;

        self.stateString = ko.observable(undefined);
        self.errorString = ko.observable(undefined);
        self.hasErrorString = ko.pureComputed(function () {
            return !!self.errorString();
        });

        self.resendCount = ko.observable(0);
        self.resendTotalTransmitted = ko.observable(0);
        self.resendRatio = ko.observable(0);
        self.resendRatioCritical = ko.pureComputed(function () {
            return (
                self.resendRatio() >= self.settings.serial_resendRatioThreshold() &&
                self.resendTotalTransmitted() >= self.settings.serial_resendRatioStart()
            );
        });
        self.resendRatioNotification = undefined;

        self.isErrorOrClosed = ko.observable(undefined);
        self.isOperational = ko.observable(undefined);
        self.isPrinting = ko.observable(undefined);
        self.isCancelling = ko.observable(undefined);
        self.isPausing = ko.observable(undefined);
        self.isPaused = ko.observable(undefined);
        self.isError = ko.observable(undefined);
        self.isReady = ko.observable(undefined);
        self.isLoading = ko.observable(undefined);
        self.isSdReady = ko.observable(undefined);

        self.isBusy = ko.pureComputed(function () {
            return (
                self.isPrinting() ||
                self.isCancelling() ||
                self.isPausing() ||
                self.isPaused()
            );
        });

        self.enablePrint = ko.pureComputed(function () {
            return (
                self.isOperational() &&
                (self.isReady() || self.isPaused()) &&
                !self.isPrinting() &&
                !self.isCancelling() &&
                !self.isPausing() &&
                self.loginState.hasPermission(self.access.permissions.PRINT) &&
                self.filename()
            );
        });
        self.enablePause = ko.pureComputed(function () {
            return (
                self.isOperational() &&
                (self.isPrinting() || self.isPaused()) &&
                !self.isCancelling() &&
                !self.isPausing() &&
                self.loginState.hasPermission(self.access.permissions.PRINT)
            );
        });
        self.enableCancel = ko.pureComputed(function () {
            return (
                self.isOperational() &&
                (self.isPrinting() || self.isPaused()) &&
                !self.isCancelling() &&
                !self.isPausing() &&
                self.loginState.hasPermission(self.access.permissions.PRINT)
            );
        });

        self.filename = ko.observable(undefined);
        self.filepath = ko.observable(undefined);
        self.filedisplay = ko.observable(undefined);
        self.filesize = ko.observable(undefined);
        self.filepos = ko.observable(undefined);
        self.filedate = ko.observable(undefined);
        self.progress = ko.observable(undefined);
        self.printTime = ko.observable(undefined);
        self.printTimeLeft = ko.observable(undefined);
        self.printTimeLeftOrigin = ko.observable(undefined);
        self.sd = ko.observable(undefined);
        self.timelapse = ko.observable(undefined);
        self.user = ko.observable(undefined);

        self.busyFiles = ko.observableArray([]);

        self.filament = ko.observableArray([]);
        self.estimatedPrintTime = ko.observable(undefined);
        self.lastPrintTime = ko.observable(undefined);

        self.currentHeight = ko.observable(undefined);

        self.errorInfoAvailable = ko.observable(false);
        self.errorInfo = {};

        self.TITLE_PRINT_BUTTON_PAUSED = gettext(
            "Restarts the print job from the beginning"
        );
        self.TITLE_PRINT_BUTTON_UNPAUSED = gettext("Starts the print job");
        self.TITLE_PAUSE_BUTTON_PAUSED = gettext("Resumes the print job");
        self.TITLE_PAUSE_BUTTON_UNPAUSED = gettext("Pauses the print job");

        self.titlePrintButton = ko.observable(self.TITLE_PRINT_BUTTON_UNPAUSED);
        self.titlePauseButton = ko.observable(self.TITLE_PAUSE_BUTTON_UNPAUSED);

        var estimatedPrintTimeStringHlpr = function (fmt) {
            if (self.lastPrintTime()) return fmt(self.lastPrintTime());
            if (self.estimatedPrintTime()) return fmt(self.estimatedPrintTime());
            return "-";
        };
        self.estimatedPrintTimeString = ko.pureComputed(function () {
            return estimatedPrintTimeStringHlpr(
                self.settings.appearance_fuzzyTimes()
                    ? formatFuzzyPrintTime
                    : formatDuration
            );
        });
        self.estimatedPrintTimeExactString = ko.pureComputed(function () {
            return estimatedPrintTimeStringHlpr(formatDuration);
        });
        self.byteString = ko.pureComputed(function () {
            if (!self.filesize()) return "-";
            var filepos = self.filepos() ? formatSize(self.filepos()) : "-";
            return filepos + " / " + formatSize(self.filesize());
        });
        self.heightString = ko.pureComputed(function () {
            if (!self.currentHeight()) return "-";
            return _.sprintf("%.02fmm", self.currentHeight());
        });
        self.printTimeString = ko.pureComputed(function () {
            if (!self.printTime()) return "-";
            return formatDuration(self.printTime());
        });
        var printTimeLeftStringHlpr = function (fmt) {
            if (self.printTimeLeft() === undefined) {
                if (!self.printTime() || !(self.isPrinting() || self.isPaused())) {
                    return "-";
                } else {
                    return gettext("Still stabilizing...");
                }
            } else {
                return fmt(self.printTimeLeft());
            }
        };
        self.printTimeLeftString = ko.pureComputed(function () {
            return printTimeLeftStringHlpr(
                self.settings.appearance_fuzzyTimes()
                    ? formatFuzzyPrintTime
                    : formatDuration
            );
        });
        self.printTimeLeftExactString = ko.pureComputed(function () {
            return printTimeLeftStringHlpr(formatDuration);
        });
        self.printTimeLeftOriginString = ko.pureComputed(function () {
            var value = self.printTimeLeftOrigin();
            switch (value) {
                case "linear": {
                    return gettext(
                        "Based on a linear approximation (very low accuracy, especially at the beginning of the print)"
                    );
                }
                case "analysis": {
                    return gettext(
                        "Based on the estimate from analysis of file (medium accuracy)"
                    );
                }
                case "mixed-analysis": {
                    return gettext(
                        "Based on a mix of estimate from analysis and calculation (medium accuracy)"
                    );
                }
                case "average": {
                    return gettext(
                        "Based on the average total of past prints of this model with the same printer profile (usually good accuracy)"
                    );
                }
                case "mixed-average": {
                    return gettext(
                        "Based on a mix of average total from past prints and calculation (usually good accuracy)"
                    );
                }
                case "estimate": {
                    return gettext("Based on the calculated estimate (best accuracy)");
                }
                default: {
                    return "";
                }
            }
        });
        self.printTimeLeftOriginClass = ko.pureComputed(function () {
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
        self.progressString = ko.pureComputed(function () {
            if (!self.progress()) return 0;
            return self.progress();
        });
        self.progressBarString = ko.pureComputed(function () {
            if (!self.progress()) {
                return "";
            }
            return _.sprintf("%d%%", self.progress());
        });
        self.pauseString = ko.pureComputed(function () {
            if (self.isPaused()) return gettext("Continue");
            else return gettext("Pause");
        });

        self.timelapseString = ko.pureComputed(function () {
            var timelapse = self.timelapse();

            if (!timelapse || !timelapse.hasOwnProperty("type")) return "-";

            var type = timelapse["type"];
            if (type === "zchange") {
                return gettext("On Z Change");
            } else if (type === "timed") {
                return (
                    gettext("Timed") +
                    " (" +
                    timelapse["options"]["interval"] +
                    " " +
                    gettext("sec") +
                    ")"
                );
            } else {
                return "-";
            }
        });

        self.userString = ko.pureComputed(function () {
            var user = self.user();
            if (user === "_api") {
                user = "API client";
            }

            var file = self.filename();
            return user ? user : file ? "-" : "";
        });

        self.dateString = ko.pureComputed(function () {
            var date = self.filedate();
            if (!date) {
                return gettext("unknown");
            }

            return formatDate(date, {seconds: true});
        });

        self.fromCurrentData = function (data) {
            self._fromData(data);
        };

        self.fromHistoryData = function (data) {
            self._fromData(data);
        };

        self.fromTimelapseData = function (data) {
            self.timelapse(data);
        };

        self._fromData = function (data) {
            self._processStateData(data.state);
            self._processJobData(data.job);
            self._processProgressData(data.progress);
            self._processZData(data.currentZ);
            self._processBusyFiles(data.busyFiles);
            self._processResends(data.resends);

            self._checkResendRatioCriticality();
        };

        self._processStateData = function (data) {
            var prevPaused = self.isPaused();

            self.stateString(gettext(data.text));
            self.errorString(data.error);
            self.isErrorOrClosed(data.flags.closedOrError);
            self.isOperational(data.flags.operational);
            self.isPaused(data.flags.paused);
            self.isPrinting(data.flags.printing);
            self.isCancelling(data.flags.cancelling);
            self.isPausing(data.flags.pausing);
            self.isError(data.flags.error);
            self.isReady(data.flags.ready);
            self.isSdReady(data.flags.sdReady);

            if (self.isPaused() !== prevPaused) {
                if (self.isPaused()) {
                    self.titlePrintButton(self.TITLE_PRINT_BUTTON_PAUSED);
                    self.titlePauseButton(self.TITLE_PAUSE_BUTTON_PAUSED);
                } else {
                    self.titlePrintButton(self.TITLE_PRINT_BUTTON_UNPAUSED);
                    self.titlePauseButton(self.TITLE_PAUSE_BUTTON_UNPAUSED);
                }
            }
        };

        self._processJobData = function (data) {
            if (data.file) {
                self.filename(data.file.name);
                self.filepath(data.file.path);
                self.filesize(data.file.size);
                self.filedisplay(data.file.display);
                self.filedate(data.file.date);
                self.sd(data.file.origin === "sdcard");
            } else {
                self.filename(undefined);
                self.filepath(undefined);
                self.filesize(undefined);
                self.filedisplay(undefined);
                self.filedate(undefined);
                self.sd(undefined);
            }

            self.estimatedPrintTime(data.estimatedPrintTime);
            self.lastPrintTime(data.lastPrintTime);

            var result = [];
            if (
                data.filament &&
                typeof data.filament === "object" &&
                _.keys(data.filament).length > 0
            ) {
                var keys = _.keys(data.filament);
                keys.sort();
                _.each(keys, function (key) {
                    if (
                        !_.startsWith(key, "tool") ||
                        !data.filament[key] ||
                        !data.filament[key].hasOwnProperty("length") ||
                        data.filament[key].length <= 0
                    )
                        return;

                    result.push({
                        name: ko.observable(
                            gettext("Tool") + " " + key.substr("tool".length)
                        ),
                        data: ko.observable(data.filament[key])
                    });
                });
            }
            self.filament(result);

            self.user(data.user);
        };

        self._processProgressData = function (data) {
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

        self._processZData = function (data) {
            self.currentHeight(data);
        };

        self._processBusyFiles = function (data) {
            var busyFiles = [];
            _.each(data, function (entry) {
                if (entry.hasOwnProperty("path") && entry.hasOwnProperty("origin")) {
                    busyFiles.push(entry.origin + ":" + entry.path);
                }
            });
            self.busyFiles(busyFiles);
        };

        self._processResends = function (data) {
            self.resendCount(data.count);
            self.resendTotalTransmitted(data.transmitted);
            self.resendRatio(data.ratio);
        };

        self._checkResendRatioCriticality = function () {
            if (self.resendRatioCritical()) {
                if (self.resendRatioNotification === undefined) {
                    var message = gettext(
                        "<p>%(ratio)d%% of transmitted lines have triggered resend " +
                            "requests. The communication with the printer is unreliable " +
                            "and this will cause print artefacts and failures.</p><p>Please " +
                            "see <a href='%(url)s' target='_blank'>this FAQ entry</a> " +
                            "on tips on how to solve this.</p>"
                    );
                    message = _.sprintf(message, {
                        ratio: self.resendRatio(),
                        url: "https://faq.octoprint.org/communication-errors"
                    });
                    self.resendRatioNotification = new PNotify({
                        title: gettext("Critical resend ratio!"),
                        text: message,
                        type: "error",
                        hide: false
                    });
                }
            } else if (self.resendRatioNotification !== undefined) {
                self.resendRatioNotification.remove();
                self.resendRatioNotification = undefined;
            }
        };

        self.print = function () {
            if (self.isPaused()) {
                showConfirmationDialog({
                    message: gettext(
                        "This will restart the print job from the beginning."
                    ),
                    onproceed: function () {
                        OctoPrint.job.restart();
                    }
                });
            } else {
                var proceed = function (p) {
                    var prevented = false;
                    var callback = function () {
                        OctoPrint.job.start();
                    };

                    callViewModels(
                        self.allViewModels,
                        "onBeforePrintStart",
                        function (method) {
                            prevented = prevented || method(callback) === false;
                        }
                    );

                    if (!prevented) {
                        callback();
                    }
                };

                if (!self.settings.feature_printStartConfirmation()) {
                    proceed();
                } else {
                    showConfirmationDialog({
                        message: gettext(
                            "This will start a new print job. Please check that the print bed is clear."
                        ),
                        question: gettext("Do you want to start the print job now?"),
                        cancel: gettext("No"),
                        proceed: gettext("Yes"),
                        onproceed: proceed,
                        nofade: true
                    });
                }
            }
        };

        self.onlyPause = function () {
            OctoPrint.job.pause();
        };

        self.onlyResume = function () {
            OctoPrint.job.resume();
        };

        self.pause = function (action) {
            OctoPrint.job.togglePause();
        };

        self.cancel = function () {
            if (!self.settings.feature_printCancelConfirmation()) {
                OctoPrint.job.cancel();
            } else {
                showConfirmationDialog({
                    message: gettext("This will cancel your print."),
                    cancel: gettext("No, continue the print"),
                    proceed: gettext("Yes, cancel the print"),
                    onproceed: function () {
                        OctoPrint.job.cancel();
                    },
                    nofade: true
                });
            }
        };

        self.showFirmwareErrorModal = (data) => {
            if (!data) {
                data = self.errorInfo;
            }
            if (!data) return;

            const modal = $("#firmwareErrorModal");
            if (!modal.length) return;

            $("#firmwareErrorModalError", modal).text(data.error);

            switch (data.consequence) {
                case "emergency": {
                    $("#firmwareErrorModalM112", modal).show();
                    $("#firmwareErrorModalDisconnect", modal).hide();
                    $("#firmwareErrorModalCancel", modal).hide();
                    break;
                }
                case "disconnect": {
                    $("#firmwareErrorModalM112", modal).hide();
                    $("#firmwareErrorModalDisconnect", modal).show();
                    $("#firmwareErrorModalCancel", modal).hide();
                    break;
                }
                case "cancel": {
                    $("#firmwareErrorModalM112", modal).hide();
                    $("#firmwareErrorModalDisconnect", modal).hide();
                    $("#firmwareErrorModalCancel", modal).show();
                    break;
                }
                default: {
                    $("#firmwareErrorModalM112", modal).hide();
                    $("#firmwareErrorModalDisconnect", modal).hide();
                    $("#firmwareErrorModalCancel", modal).hide();
                    break;
                }
            }

            if (data.faq) {
                $("#firmwareErrorModalFaq a", modal).attr(
                    "href",
                    "https://faq.octoprint.org/" + data.faq
                );
                $("#firmwareErrorModalFaq", modal).show();
            } else {
                $("#firmwareErrorModalFaq", modal).hide();
            }

            const logs = $("#firmwareErrorModalLogs", modal);
            const logOutput = $("#firmwareErrorModalLogsOutput", logs);
            if (data.logs) {
                logOutput.empty();
                _.each(data.logs, (line) => {
                    logOutput.append(
                        '<span class="line">' + _.escape(line) + "\n" + "</span>"
                    );
                });
                logs.show();
            } else {
                logs.hide();
            }

            modal.modal("show");

            logOutput.scrollTop(logOutput.prop("scrollHeight"));
        };

        self.requestErrorInfo = () => {
            OctoPrint.printer.getErrorInfo().then((data) => {
                if (data && data.error && data.error !== "") {
                    self.errorInfoAvailable(true);
                    self.errorInfo = data;
                } else {
                    self.errorInfoAvailable(false);
                    self.errorInfo = {};
                }
            });
        };

        self.onEventError = (payload) => {
            if (payload.reason === "firmware") {
                self.errorInfo = payload;
                self.errorInfoAvailable(true);
                self.showFirmwareErrorModal();
            }
        };

        self.onEventConnecting =
            self.onEventPrintCancelling =
            self.onEventPrintStarted =
                () => {
                    self.requestErrorInfo();
                };

        self.onUserPermissionsChanged =
            self.onUserLoggedIn =
            self.onUserLoggedOut =
                () => {
                    self.requestErrorInfo();
                };

        self.onAllBound = (allViewModels) => {
            self.allViewModels = allViewModels;
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: PrinterStateViewModel,
        dependencies: ["loginStateViewModel", "settingsViewModel", "accessViewModel"],
        elements: ["#state_wrapper", "#drop_overlay"]
    });
});
