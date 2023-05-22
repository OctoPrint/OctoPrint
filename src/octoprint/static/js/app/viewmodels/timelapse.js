$(function () {
    function TimelapseViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];
        self.settings = parameters[2];

        self.renderProgressBar = undefined;
        self.timelapsePopup = undefined;

        self.defaultFps = 25;
        self.defaultPostRoll = 0;
        self.defaultInterval = 10;
        self.defaultRetractionZHop = 0;
        self.defaultMinDelay = 5.0;

        self.timelapseType = ko.observable(undefined);
        self.timelapseTimedInterval = ko.observable(self.defaultInterval);
        self.timelapsePostRoll = ko.observable(self.defaultPostRoll);
        self.timelapseFps = ko.observable(self.defaultFps);
        self.timelapseRetractionZHop = ko.observable(self.defaultRetractionZHop);
        self.timelapseMinDelay = ko.observable(self.defaultMinDelay);
        self.snapshotWebcam = ko.pureComputed(function () {
            var snapshotWebcamName = self.settings.webcam_snapshotWebcam();
            return self.settings.webcam_webcams().find(function (w) {
                return snapshotWebcamName == w.name;
            });
        });
        self.canSnapshot = ko.pureComputed(function () {
            if (!self.snapshotWebcam()) {
                return false;
            } else {
                return self.snapshotWebcam().canSnapshot;
            }
        });
        self.snapshotDisplay = ko.pureComputed(function () {
            if (!self.snapshotWebcam()) {
                return "";
            } else {
                return self.snapshotWebcam().snapshotDisplay;
            }
        });

        self.renderProgress = ko.observable();
        self.renderTarget = ko.observable();
        self.renderAnimation = ko.observable(false);
        self.renderProgressString = ko.pureComputed(function () {
            if (!self.renderTarget()) {
                return 0;
            }

            if (self.renderAnimation()) {
                return 100;
            }

            if (!self.renderProgress()) {
                return 0;
            }

            return self.renderProgress();
        });
        self.renderProgressBarString = ko.pureComputed(function () {
            if (!self.renderTarget()) {
                return "";
            }

            if (self.renderAnimation()) {
                return _.sprintf(gettext("Rendering %(target)s..."), {
                    target: self.renderTarget()
                });
            }

            var progress = self.renderProgress();
            if (!progress) {
                progress = 0;
            }
            return _.sprintf(gettext("Rendering %(target)s... (%(progress)d%%)"), {
                target: self.renderTarget(),
                progress: progress
            });
        });

        self.serverConfig = ko.observable();

        self.persist = ko.observable(false);
        self.isDirty = ko.observable(false);

        self.isErrorOrClosed = ko.observable(undefined);
        self.isOperational = ko.observable(undefined);
        self.isPrinting = ko.observable(undefined);
        self.isPaused = ko.observable(undefined);
        self.isError = ko.observable(undefined);
        self.isReady = ko.observable(undefined);
        self.isLoading = ko.observable(undefined);

        self.markedForFileDeletion = ko.observableArray([]);
        self.markedForUnrenderedDeletion = ko.observableArray([]);

        self.isTemporary = ko.pureComputed(function () {
            return self.isDirty() && !self.persist();
        });

        self.isBusy = ko.pureComputed(function () {
            return self.isPrinting() || self.isPaused();
        });

        self.timelapseTypeSelected = ko.pureComputed(function () {
            return "off" !== self.timelapseType();
        });
        self.intervalInputEnabled = ko.pureComputed(function () {
            return "timed" === self.timelapseType();
        });
        self.saveButtonEnabled = ko.pureComputed(function () {
            return (
                self.loginState.hasPermission(self.access.permissions.TIMELAPSE_ADMIN) &&
                self.isDirty() &&
                !self.isPrinting()
            );
        });
        self.resetButtonEnabled = ko.pureComputed(function () {
            return self.saveButtonEnabled() && self.serverConfig() !== undefined;
        });

        self.timelapseType.subscribe(function () {
            self.isDirty(true);
        });
        self.timelapseTimedInterval.subscribe(function () {
            self.isDirty(true);
        });
        self.timelapsePostRoll.subscribe(function () {
            self.isDirty(true);
        });
        self.timelapseFps.subscribe(function () {
            self.isDirty(true);
        });
        self.timelapseRetractionZHop.subscribe(function (newValue) {
            self.isDirty(true);
        });
        self.timelapseMinDelay.subscribe(function () {
            self.isDirty(true);
        });
        self.persist.subscribe(function () {
            self.isDirty(true);
        });

        // initialize list helper
        self.listHelper = new ItemListHelper(
            "timelapseFiles",
            {
                name: function (a, b) {
                    // sorts ascending
                    if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase())
                        return -1;
                    if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase())
                        return 1;
                    return 0;
                },
                date: function (a, b) {
                    // sorts descending
                    if (a["date"] > b["date"]) return -1;
                    if (a["date"] < b["date"]) return 1;
                    return 0;
                },
                size: function (a, b) {
                    // sorts descending
                    if (a["bytes"] > b["bytes"]) return -1;
                    if (a["bytes"] < b["bytes"]) return 1;
                    return 0;
                }
            },
            {},
            "name",
            [],
            [],
            CONFIG_TIMELAPSEFILESPERPAGE
        );

        // initialize list helper for unrendered timelapses
        self.unrenderedListHelper = new ItemListHelper(
            "unrenderedTimelapseFiles",
            {
                name: function (a, b) {
                    // sorts ascending
                    if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase())
                        return -1;
                    if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase())
                        return 1;
                    return 0;
                },
                creation: function (a, b) {
                    // sorts descending
                    if (a["date"] > b["date"]) return -1;
                    if (a["date"] < b["date"]) return 1;
                    return 0;
                },
                size: function (a, b) {
                    // sorts descending
                    if (a["bytes"] > b["bytes"]) return -1;
                    if (a["bytes"] < b["bytes"]) return 1;
                    return 0;
                }
            },
            {},
            "name",
            [],
            [],
            CONFIG_TIMELAPSEFILESPERPAGE
        );

        self.requestData = function () {
            if (!self.loginState.hasPermission(self.access.permissions.TIMELAPSE_LIST))
                return;

            OctoPrint.timelapse.get(true).done(self.fromResponse);
        };

        self.fromResponse = function (response) {
            var config = response.config;
            if (config === undefined) return;

            // timelapses & unrendered
            self.listHelper.updateItems(response.files);
            self.listHelper.resetPage();
            if (response.unrendered) {
                self.unrenderedListHelper.updateItems(response.unrendered);
                self.unrenderedListHelper.resetPage();
            }

            // timelapse config
            self.fromConfig(response.config);
            self.serverConfig(response.config);
        };

        self.fromConfig = function (config) {
            self.timelapseType(config.type);

            if (
                config.type === "timed" &&
                config.interval !== undefined &&
                config.interval > 0
            ) {
                self.timelapseTimedInterval(config.interval);
            } else {
                self.timelapseTimedInterval(self.defaultInterval);
            }

            if (
                config.type === "zchange" &&
                config.retractionZHop !== undefined &&
                config.retractionZHop > 0
            ) {
                self.timelapseRetractionZHop(config.retractionZHop);
            } else {
                self.timelapseRetractionZHop(self.defaultRetractionZHop);
            }

            if (
                config.type === "zchange" &&
                config.minDelay !== undefined &&
                config.minDelay >= 0
            ) {
                self.timelapseMinDelay(config.minDelay);
            } else {
                self.timelapseMinDelay(self.defaultMinDelay);
            }

            if (config.postRoll !== undefined && config.postRoll >= 0) {
                self.timelapsePostRoll(config.postRoll);
            } else {
                self.timelapsePostRoll(self.defaultPostRoll);
            }

            if (config.fps !== undefined && config.fps > 0) {
                self.timelapseFps(config.fps);
            } else {
                self.timelapseFps(self.defaultFps);
            }

            self.persist(false);
            self.isDirty(false);
        };

        self.fromCurrentData = function (data) {
            self._processStateData(data.state);
        };

        self.fromHistoryData = function (data) {
            self._processStateData(data.state);
        };

        self._processStateData = function (data) {
            self.isErrorOrClosed(data.flags.closedOrError);
            self.isOperational(data.flags.operational);
            self.isPaused(data.flags.paused);
            self.isPrinting(data.flags.printing);
            self.isError(data.flags.error);
            self.isReady(data.flags.ready);
            self.isLoading(data.flags.loading);
        };

        self.markFilesOnPage = function () {
            self.markedForFileDeletion(
                _.uniq(
                    self
                        .markedForFileDeletion()
                        .concat(_.map(self.listHelper.paginatedItems(), "name"))
                )
            );
        };

        self.markAllFiles = function () {
            self.markedForFileDeletion(_.map(self.listHelper.allItems, "name"));
        };

        self.clearMarkedFiles = function () {
            self.markedForFileDeletion.removeAll();
        };

        self.isTimelapseViewable = function (data) {
            var url = data.url;
            return (
                self.loginState.hasPermission(
                    self.access.permissions.TIMELAPSE_DOWNLOAD
                ) && url.indexOf(".mp4") >= 0
            );
        };
        self.showTimelapsePreview = function (data) {
            if (!self.isTimelapseViewable(data)) return;

            var url = data.url;
            var previewModal = $("#timelapsePreviewModal");
            previewModal.children("div.modal-body").children("video").attr("src", url);
            previewModal.off("hidden.bs.modal").on("hidden.bs.modal", function () {
                $(this).attr("src", "");
            });
            previewModal.modal("show");
        };

        self.removeFile = function (filename) {
            if (!self.loginState.hasPermission(self.access.permissions.TIMELAPSE_DELETE))
                return;

            var perform = function () {
                OctoPrint.timelapse
                    .delete(filename)
                    .done(function () {
                        self.markedForFileDeletion.remove(filename);
                        self.requestData();
                    })
                    .fail(function (jqXHR) {
                        var html =
                            "<p>" +
                            _.sprintf(
                                gettext(
                                    "Failed to remove timelapse %(name)s.</p><p>Please consult octoprint.log for details.</p>"
                                ),
                                {name: _.escape(filename)}
                            );
                        html += pnotifyAdditionalInfo(
                            '<pre style="overflow: auto">' +
                                _.escape(jqXHR.responseText) +
                                "</pre>"
                        );
                        new PNotify({
                            title: gettext("Could not remove timelapse"),
                            text: html,
                            type: "error",
                            hide: false
                        });
                    });
            };

            showConfirmationDialog(
                _.sprintf(gettext('You are about to delete timelapse file "%(name)s".'), {
                    name: _.escape(filename)
                }),
                perform
            );
        };

        self.removeMarkedFiles = function () {
            if (!self.loginState.hasPermission(self.access.permissions.TIMELAPSE_DELETE))
                return;

            var perform = function () {
                self._bulkRemove(self.markedForFileDeletion(), "files").done(function () {
                    self.markedForFileDeletion.removeAll();
                });
            };

            showConfirmationDialog(
                _.sprintf(gettext("You are about to delete %(count)d timelapse files."), {
                    count: self.markedForFileDeletion().length
                }),
                perform
            );
        };

        self.enableBulkDownload = ko.pureComputed(function () {
            return (
                self.markedForFileDeletion().length &&
                !self.isBusy() &&
                !self.bulkDownloadUrlTooLong()
            );
        });

        self.bulkDownloadUrlTooLong = ko.pureComputed(function () {
            return BASEURL.length + self.bulkDownloadUrl().length >= 2000;
        });

        self.bulkDownloadButtonUrl = ko.pureComputed(function () {
            var files = self.markedForFileDeletion();
            if (!files.length || self.bulkDownloadUrlTooLong()) {
                return "javascript:void(0)";
            }
            return self.bulkDownloadUrl();
        });

        self.bulkDownloadUrl = function () {
            var files = self.markedForFileDeletion();
            return OctoPrint.timelapse.bulkDownloadUrl(files);
        };

        self.markUnrenderedOnPage = function () {
            self.markedForUnrenderedDeletion(
                _.uniq(
                    self
                        .markedForUnrenderedDeletion()
                        .concat(_.map(self.unrenderedListHelper.paginatedItems(), "name"))
                )
            );
        };

        self.markAllUnrendered = function () {
            self.markedForUnrenderedDeletion(
                _.map(self.unrenderedListHelper.allItems, "name")
            );
        };

        self.clearMarkedUnrendered = function () {
            self.markedForUnrenderedDeletion.removeAll();
        };

        self.removeUnrendered = function (name) {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.TIMELAPSE_MANAGE_UNRENDERED
                )
            )
                return;

            var perform = function () {
                OctoPrint.timelapse.deleteUnrendered(name).done(function () {
                    self.markedForUnrenderedDeletion.remove(name);
                    self.requestData();
                });
            };

            showConfirmationDialog(
                _.sprintf(
                    gettext('You are about to delete unrendered timelapse "%(name)s".'),
                    {name: _.escape(name)}
                ),
                perform
            );
        };

        self.removeMarkedUnrendered = function () {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.TIMELAPSE_MANAGE_UNRENDERED
                )
            )
                return;

            var perform = function () {
                self._bulkRemove(self.markedForUnrenderedDeletion(), "unrendered").done(
                    function () {
                        self.markedForUnrenderedDeletion.removeAll();
                    }
                );
            };

            showConfirmationDialog(
                _.sprintf(
                    gettext("You are about to delete %(count)d unrendered timelapses."),
                    {count: self.markedForUnrenderedDeletion().length}
                ),
                perform
            );
        };

        self._bulkRemove = function (files, type) {
            var title, message, handler;

            if (type === "files") {
                title = gettext("Deleting timelapse files");
                message = _.sprintf(gettext("Deleting %(count)d timelapse files..."), {
                    count: files.length
                });
                handler = function (filename) {
                    return OctoPrint.timelapse
                        .delete(filename)
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
            } else if (type === "unrendered") {
                title = gettext("Deleting unrendered timelapses");
                message = _.sprintf(
                    gettext("Deleting %(count)d unrendered timelapses..."),
                    {count: files.length}
                );
                handler = function (filename) {
                    return OctoPrint.timelapse
                        .deleteUnrendered(filename)
                        .done(function () {
                            deferred.notify(
                                _.sprintf(gettext("Deleted %(filename)s..."), {
                                    filename: _.escape(filename)
                                }),
                                true
                            );
                        })
                        .fail(function () {
                            deferred.notify(
                                _.sprintf(
                                    gettext(
                                        "Deletion of %(filename)s failed, continuing..."
                                    ),
                                    {filename: _.escape(filename)}
                                ),
                                false
                            );
                        });
                };
            } else {
                return;
            }

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

        self.renderUnrendered = function (name) {
            if (!self.loginState.hasPermission(self.access.permissions.TIMELAPSE_ADMIN))
                return;

            OctoPrint.timelapse.renderUnrendered(name).done(self.requestData);
        };

        self.save = function () {
            if (!self.loginState.hasPermission(self.access.permissions.TIMELAPSE_ADMIN))
                return;

            var payload = {
                type: self.timelapseType(),
                postRoll: self.timelapsePostRoll(),
                fps: self.timelapseFps(),
                save: self.persist()
            };

            if (self.timelapseType() === "timed") {
                payload["interval"] = self.timelapseTimedInterval();
            }

            if (self.timelapseType() === "zchange") {
                payload["retractionZHop"] = self.timelapseRetractionZHop();
                payload["minDelay"] = self.timelapseMinDelay();
            }

            OctoPrint.timelapse.saveConfig(payload).done(self.fromResponse);
        };

        self.reset = function () {
            if (self.serverConfig() === undefined) return;
            self.fromConfig(self.serverConfig());
        };

        self.displayTimelapsePopup = function (options) {
            if (self.timelapsePopup !== undefined) {
                self.timelapsePopup.remove();
            }

            _.extend(options, {
                callbacks: {
                    before_close: function (notice) {
                        if (self.timelapsePopup === notice) {
                            self.timelapsePopup = undefined;
                        }
                    }
                }
            });

            self.timelapsePopup = new PNotify(options);
        };

        self.onDataUpdaterReconnect = function () {
            self.requestData();
        };

        self.onEventPostRollStart = function (payload) {
            var title = gettext("Capturing timelapse postroll");

            var text;
            if (!payload.postroll_duration) {
                text = _.sprintf(
                    gettext(
                        "Now capturing timelapse post roll, this will take only a moment..."
                    )
                );
            } else {
                var format = {
                    time: moment().add(payload.postroll_duration, "s").format("LT")
                };

                if (payload.postroll_duration > 60) {
                    format.duration = _.sprintf(gettext("%(minutes)d min"), {
                        minutes: payload.postroll_duration / 60
                    });
                    text = _.sprintf(
                        gettext(
                            "Now capturing timelapse post roll, this will take approximately %(duration)s (so until %(time)s)..."
                        ),
                        format
                    );
                } else {
                    format.duration = _.sprintf(gettext("%(seconds)d sec"), {
                        seconds: payload.postroll_duration
                    });
                    text = _.sprintf(
                        gettext(
                            "Now capturing timelapse post roll, this will take approximately %(duration)s..."
                        ),
                        format
                    );
                }
            }

            self.displayTimelapsePopup({
                title: title,
                text: text,
                hide: false
            });
        };

        // 3 consecutive capture fails trigger error popup
        self._warnAboutCaptureFailThreshold = 3;
        self._warnAboutCaptureFailCounter = 0;
        self._warnedAboutCaptureFail = false;
        self.onEventPrintStarted = function (payload) {
            self._warnAboutCaptureFailCounter = 0;
            self._warnedAboutCaptureFail = false;
        };
        self.onEventCaptureDone = function (payload) {
            self._warnAboutCaptureFailCounter = 0;
            self._warnedAboutCaptureFail = false;
        };
        self.onEventCaptureFailed = function (payload) {
            self._warnAboutCaptureFailCounter++;
            if (
                self._warnedAboutCaptureFail ||
                self._warnAboutCaptureFailCounter <= self._warnAboutCaptureFailThreshold
            ) {
                return;
            }
            self._warnedAboutCaptureFail = true;

            var html =
                "<p>" +
                gettext(
                    "Failed repeatedly to capture timelapse frame from webcam - is the snapshot webcam configured correctly and the camera on?"
                );

            var additional = "";
            if (payload.snapshotDisplay) {
                additional +=
                    'Snapshot info: <pre style="overflow: auto">' +
                    payload.snapshotDisplay +
                    "</pre>";
            }
            if (payload.webcamDisplay) {
                additional +=
                    'Webcam: <pre style="overflow: auto">' +
                    payload.webcamDisplay +
                    "</pre>";
            }
            if (payload.error) {
                additional +=
                    'Error: <pre style="overflow: auto">' + payload.error + "</pre>";
            }
            if (additional) {
                html += pnotifyAdditionalInfo(additional);
            }

            new PNotify({
                title: gettext("Could not capture snapshots"),
                text: html,
                type: "error",
                hide: false
            });
        };

        self.onEventMovieRendering = function (payload) {
            self.displayTimelapsePopup({
                title: gettext("Rendering timelapse"),
                text: _.sprintf(
                    gettext(
                        "Now rendering timelapse %(movie_prefix)s. Due to performance reasons it is not recommended to start a print job while a movie is still rendering."
                    ),
                    {movie_prefix: _.escape(payload.movie_prefix)}
                ),
                hide: false
            });

            self.renderProgress(0);
            self.renderTarget(payload.movie_prefix);
            self.renderAnimation(true);
        };

        self.onRenderProgress = function (percentage) {
            self.renderProgress(percentage);
            self.renderAnimation(false);
        };

        self.onEventMovieFailed = function (payload) {
            var title, html;

            if (payload.reason === "no_frames") {
                title = gettext("Cannot render timelapse");
                html =
                    "<p>" +
                    _.sprintf(
                        gettext(
                            "Rendering of timelapse %(movie_prefix)s is not possible since no frames were captured. Is the snapshot webcam configured correctly?"
                        ),
                        {movie_prefix: _.escape(payload.movie_prefix)}
                    ) +
                    "</p>";
            } else if ((payload.reason = "returncode")) {
                title = gettext("Rendering timelapse failed");
                html =
                    "<p>" +
                    _.sprintf(
                        gettext(
                            "Rendering of timelapse %(movie_prefix)s failed with return code %(returncode)s"
                        ),
                        {
                            movie_prefix: _.escape(payload.movie_prefix),
                            returncode: _.escape(payload.returncode)
                        }
                    ) +
                    "</p>";
                html += pnotifyAdditionalInfo(
                    '<pre style="overflow: auto">' + payload.error + "</pre>"
                );
            } else {
                title = gettext("Rendering timelapse failed");
                html =
                    "<p>" +
                    _.sprintf(
                        gettext(
                            "Rendering of timelapse %(movie_prefix)s failed due to an unknown error, please consult the log file"
                        ),
                        {movie_prefix: _.escape(payload.movie_prefix)}
                    ) +
                    "</p>";
            }

            self.displayTimelapsePopup({
                title: title,
                text: html,
                type: "error",
                hide: false
            });

            self.renderProgress(0);
            self.renderTarget(undefined);
            self.renderAnimation(false);
        };

        self.onEventMovieDone = function (payload) {
            self.displayTimelapsePopup({
                title: gettext("Timelapse ready"),
                text: _.sprintf(
                    gettext("New timelapse %(movie_prefix)s is done rendering."),
                    {movie_prefix: _.escape(payload.movie_prefix)}
                ),
                type: "success",
                callbacks: {
                    before_close: function (notice) {
                        if (self.timelapsePopup === notice) {
                            self.timelapsePopup = undefined;
                        }
                    }
                }
            });
            self.requestData();

            self.renderProgress(0);
            self.renderTarget(undefined);
            self.renderAnimation(false);
        };

        self.onUserPermissionsChanged =
            self.onUserLoggedIn =
            self.onUserLoggedOut =
                function () {
                    self.requestData();

                    self.renderProgressBar = $("#render_progress");
                };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: TimelapseViewModel,
        dependencies: ["loginStateViewModel", "accessViewModel", "settingsViewModel"],
        elements: ["#timelapse", "#timelapse_link", "#timelapsePreviewModal"]
    });
});
