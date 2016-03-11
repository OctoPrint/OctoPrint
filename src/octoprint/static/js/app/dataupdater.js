function DataUpdater(allViewModels) {
    var self = this;

    self.allViewModels = allViewModels;

    self._socket = undefined;
    self._autoReconnecting = false;
    self._autoReconnectTrial = 0;
    self._autoReconnectTimeouts = [0, 1, 1, 2, 3, 5, 8, 13, 20, 40, 100];
    self._autoReconnectDialogIndex = 1;

    self._pluginHash = undefined;

    self._throttleFactor = 1;
    self._baseProcessingLimit = 500.0;
    self._lastProcessingTimes = [];
    self._lastProcessingTimesSize = 20;

    self._timelapse_popup = undefined;

    self.connect = function() {
        var options = {};
        if (SOCKJS_DEBUG) {
            options["debug"] = true;
        }

        self._socket = new SockJS(SOCKJS_URI, undefined, options);
        self._socket.onopen = self._onconnect;
        self._socket.onclose = self._onclose;
        self._socket.onmessage = self._onmessage;
    };

    self.reconnect = function() {
        self._socket.close();
        delete self._socket;
        self.connect();
    };

    self.increaseThrottle = function() {
        self.setThrottle(self._throttleFactor + 1);
    };

    self.decreaseThrottle = function() {
        if (self._throttleFactor <= 1) {
            return;
        }
        self.setThrottle(self._throttleFactor - 1);
    };

    self.setThrottle = function(throttle) {
        self._throttleFactor = throttle;

        self._send("throttle", self._throttleFactor);
        log.debug("DataUpdater: New SockJS throttle factor:", self._throttleFactor, " new processing limit:", self._baseProcessingLimit * self._throttleFactor);
    };

    self._send = function(message, data) {
        var payload = {};
        payload[message] = data;
        self._socket.send(JSON.stringify(payload));
    };

    self._onconnect = function() {
        self._autoReconnecting = false;
        self._autoReconnectTrial = 0;
    };

    self._onclose = function(e) {
        if (e.code == SOCKJS_CLOSE_NORMAL) {
            return;
        }
        if (self._autoReconnectTrial >= self._autoReconnectDialogIndex) {
            // Only consider it a real disconnect if the trial number has exceeded our threshold.

            var handled = false;
            _.each(self.allViewModels, function(viewModel) {
                if (handled == true) {
                    return;
                }

                if (viewModel.hasOwnProperty("onServerDisconnect")) {
                    var result = viewModel.onServerDisconnect();
                    if (result !== undefined && !result) {
                        handled = true;
                    }
                }
            });

            if (handled) {
                return;
            }

            showOfflineOverlay(
                gettext("Server is offline"),
                gettext("The server appears to be offline, at least I'm not getting any response from it. I'll try to reconnect automatically <strong>over the next couple of minutes</strong>, however you are welcome to try a manual reconnect anytime using the button below."),
                self.reconnect
            );
        }

        if (self._autoReconnectTrial < self._autoReconnectTimeouts.length) {
            var timeout = self._autoReconnectTimeouts[self._autoReconnectTrial];
            log.info("Reconnect trial #" + self._autoReconnectTrial + ", waiting " + timeout + "s");
            setTimeout(self.reconnect, timeout * 1000);
            self._autoReconnectTrial++;
        } else {
            self._onreconnectfailed();
        }
    };

    self._onreconnectfailed = function() {
        var handled = false;
        _.each(self.allViewModels, function(viewModel) {
            if (handled == true) {
                return;
            }

            if (viewModel.hasOwnProperty("onServerDisconnect")) {
                var result = viewModel.onServerDisconnect();
                if (result !== undefined && !result) {
                    handled = true;
                }
            }
        });

        if (handled) {
            return;
        }

        $("#offline_overlay_title").text(gettext("Server is offline"));
        $("#offline_overlay_message").html(gettext("The server appears to be offline, at least I'm not getting any response from it. I <strong>could not reconnect automatically</strong>, but you may try a manual reconnect using the button below."));
    };

    self._onmessage = function(e) {
        for (var prop in e.data) {
            if (!e.data.hasOwnProperty(prop)) {
                continue;
            }

            var data = e.data[prop];

            var gcodeUploadProgress = $("#gcode_upload_progress");
            var gcodeUploadProgressBar = $(".bar", gcodeUploadProgress);

            var start = new Date().getTime();
            switch (prop) {
                case "connected": {
                    // update the current UI API key and send it with any request
                    UI_API_KEY = data["apikey"];
                    $.ajaxSetup({
                        headers: {"X-Api-Key": UI_API_KEY}
                    });

                    var oldVersion = VERSION;
                    VERSION = data["version"];
                    DISPLAY_VERSION = data["display_version"];
                    BRANCH = data["branch"];
                    $("span.version").text(DISPLAY_VERSION);

                    var oldPluginHash = self._pluginHash;
                    self._pluginHash = data["plugin_hash"];

                    if ($("#offline_overlay").is(":visible")) {
                        hideOfflineOverlay();
                        _.each(self.allViewModels, function(viewModel) {
                            if (viewModel.hasOwnProperty("onServerReconnect")) {
                                viewModel.onServerReconnect();
                            } else if (viewModel.hasOwnProperty("onDataUpdaterReconnect")) {
                                viewModel.onDataUpdaterReconnect();
                            }
                        });

                        if ($('#tabs li[class="active"] a').attr("href") == "#control") {
                            $("#webcam_image").attr("src", CONFIG_WEBCAM_STREAM + "?" + new Date().getTime());
                        }
                    } else {
                        _.each(self.allViewModels, function(viewModel) {
                            if (viewModel.hasOwnProperty("onServerConnect")) {
                                viewModel.onServerConnect();
                            }
                        });
                    }

                    if (oldVersion != VERSION || (oldPluginHash != undefined && oldPluginHash != self._pluginHash)) {
                        showReloadOverlay();
                    }

                    self.setThrottle(1);

                    break;
                }
                case "history": {
                    _.each(self.allViewModels, function(viewModel) {
                        if (viewModel.hasOwnProperty("fromHistoryData")) {
                            viewModel.fromHistoryData(data);
                        }
                    });
                    break;
                }
                case "current": {
                    _.each(self.allViewModels, function(viewModel) {
                        if (viewModel.hasOwnProperty("fromCurrentData")) {
                            viewModel.fromCurrentData(data);
                        }
                    });
                    break;
                }
                case "slicingProgress": {
                    gcodeUploadProgressBar.text(_.sprintf(gettext("Slicing ... (%(percentage)d%%)"), {percentage: Math.round(data["progress"])}));

                    _.each(self.allViewModels, function(viewModel) {
                        if (viewModel.hasOwnProperty("onSlicingProgress")) {
                            viewModel.onSlicingProgress(data["slicer"], data["model_path"], data["machinecode_path"], data["progress"]);
                        }
                    });
                    break;
                }
                case "event": {
                    var type = data["type"];
                    var payload = data["payload"];
                    var html = "";
                    var format = {};

                    log.debug("Got event " + type + " with payload: " + JSON.stringify(payload));

                    if (type == "MovieRendering") {
                        if (self._timelapse_popup !== undefined) {
                            self._timelapse_popup.remove();
                        }
                        self._timelapse_popup = new PNotify({
                            title: gettext("Rendering timelapse"),
                            text: _.sprintf(gettext("Now rendering timelapse %(movie_basename)s. Due to performance reasons it is not recommended to start a print job while a movie is still rendering."), payload),
                            hide: false,
                            callbacks: {
                                before_close: function() {
                                    self._timelapse_popup = undefined;
                                }
                            }
                        });
                    } else if (type == "MovieDone") {
                        if (self._timelapse_popup !== undefined) {
                            self._timelapse_popup.remove();
                        }
                        self._timelapse_popup = new PNotify({
                            title: gettext("Timelapse ready"),
                            text: _.sprintf(gettext("New timelapse %(movie_basename)s is done rendering."), payload),
                            type: "success",
                            callbacks: {
                                before_close: function(notice) {
                                    if (self._timelapse_popup == notice) {
                                        self._timelapse_popup = undefined;
                                    }
                                }
                            }
                        });
                    } else if (type == "MovieFailed") {
                        html = "<p>" + _.sprintf(gettext("Rendering of timelapse %(movie_basename)s failed with return code %(returncode)s"), payload) + "</p>";
                        html += pnotifyAdditionalInfo('<pre style="overflow: auto">' + payload.error + '</pre>');

                        if (self._timelapse_popup !== undefined) {
                            self._timelapse_popup.remove();
                        }
                        self._timelapse_popup = new PNotify({
                            title: gettext("Rendering failed"),
                            text: html,
                            type: "error",
                            hide: false,
                            callbacks: {
                                before_close: function(notice) {
                                    if (self._timelapse_popup == notice) {
                                        self._timelapse_popup = undefined;
                                    }
                                }
                            }
                        });
                    } else if (type == "PostRollStart") {
                        var title = gettext("Capturing timelapse postroll");

                        var text;
                        if (!payload.postroll_duration) {
                            text = _.sprintf(gettext("Now capturing timelapse post roll, this will take only a moment..."), format);
                        } else {
                            format = {
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

                        if (self._timelapse_popup !== undefined) {
                            self._timelapse_popup.remove();
                        }
                        self._timelapse_popup = new PNotify({
                            title: title,
                            text: text,
                            hide: false,
                            callbacks: {
                                before_close: function(notice) {
                                    if (self._timelapse_popup == notice) {
                                        self._timelapse_popup = undefined;
                                    }
                                }
                            }
                        });
                    } else if (type == "SlicingStarted") {
                        gcodeUploadProgress.addClass("progress-striped").addClass("active");
                        gcodeUploadProgressBar.css("width", "100%");
                        if (payload.progressAvailable) {
                            gcodeUploadProgressBar.text(_.sprintf(gettext("Slicing ... (%(percentage)d%%)"), {percentage: 0}));
                        } else {
                            gcodeUploadProgressBar.text(gettext("Slicing ..."));
                        }
                    } else if (type == "SlicingDone") {
                        gcodeUploadProgress.removeClass("progress-striped").removeClass("active");
                        gcodeUploadProgressBar.css("width", "0%");
                        gcodeUploadProgressBar.text("");
                        new PNotify({title: gettext("Slicing done"), text: _.sprintf(gettext("Sliced %(stl)s to %(gcode)s, took %(time).2f seconds"), payload), type: "success"});
                    } else if (type == "SlicingCancelled") {
                        gcodeUploadProgress.removeClass("progress-striped").removeClass("active");
                        gcodeUploadProgressBar.css("width", "0%");
                        gcodeUploadProgressBar.text("");
                    } else if (type == "SlicingFailed") {
                        gcodeUploadProgress.removeClass("progress-striped").removeClass("active");
                        gcodeUploadProgressBar.css("width", "0%");
                        gcodeUploadProgressBar.text("");

                        html = _.sprintf(gettext("Could not slice %(stl)s to %(gcode)s: %(reason)s"), payload);
                        new PNotify({title: gettext("Slicing failed"), text: html, type: "error", hide: false});
                    } else if (type == "TransferStarted") {
                        gcodeUploadProgress.addClass("progress-striped").addClass("active");
                        gcodeUploadProgressBar.css("width", "100%");
                        gcodeUploadProgressBar.text(gettext("Streaming ..."));
                    } else if (type == "TransferDone") {
                        gcodeUploadProgress.removeClass("progress-striped").removeClass("active");
                        gcodeUploadProgressBar.css("width", "0%");
                        gcodeUploadProgressBar.text("");
                        new PNotify({
                            title: gettext("Streaming done"),
                            text: _.sprintf(gettext("Streamed %(local)s to %(remote)s on SD, took %(time).2f seconds"), payload),
                            type: "success"
                        });
                    } else if (type == "PrintCancelled") {
                        if (payload.firmwareError) {
                            new PNotify({
                                title: gettext("Unhandled communication error"),
                                text: _.sprintf(gettext("There was an unhandled error while talking to the printer. Due to that the ongoing print job was cancelled. Error: %(firmwareError)s"), payload),
                                type: "error",
                                hide: false
                            });
                        }
                    } else if (type == "Error") {
                        new PNotify({
                                title: gettext("Unhandled communication error"),
                                text: _.sprintf(gettext("The was an unhandled error while talking to the printer. Due to that OctoPrint disconnected. Error: %(error)s"), payload),
                                type: "error",
                                hide: false
                        });
                    }

                    var legacyEventHandlers = {
                        "UpdatedFiles": "onUpdatedFiles",
                        "MetadataStatisticsUpdated": "onMetadataStatisticsUpdated",
                        "MetadataAnalysisFinished": "onMetadataAnalysisFinished",
                        "SlicingDone": "onSlicingDone",
                        "SlicingCancelled": "onSlicingCancelled",
                        "SlicingFailed": "onSlicingFailed"
                    };
                    _.each(self.allViewModels, function(viewModel) {
                        if (viewModel.hasOwnProperty("onEvent" + type)) {
                            viewModel["onEvent" + type](payload);
                        } else if (legacyEventHandlers.hasOwnProperty(type) && viewModel.hasOwnProperty(legacyEventHandlers[type])) {
                            // there might still be code that uses the old callbacks, make sure those still get called
                            // but log a warning
                            log.warn("View model " + viewModel.name + " is using legacy event handler " + legacyEventHandlers[type] + ", new handler is called " + legacyEventHandlers[type]);
                            viewModel[legacyEventHandlers[type]](payload);
                        }
                    });

                    break;
                }
                case "timelapse": {
                    _.each(self.allViewModels, function(viewModel) {
                        if (viewModel.hasOwnProperty("fromTimelapseData")) {
                            viewModel.fromTimelapseData(data);
                        }
                    });
                    break;
                }
                case "plugin": {
                    _.each(self.allViewModels, function(viewModel) {
                        if (viewModel.hasOwnProperty("onDataUpdaterPluginMessage")) {
                            viewModel.onDataUpdaterPluginMessage(data.plugin, data.data);
                        }
                    })
                }
            }

            var end = new Date().getTime();
            var difference = end - start;

            while (self._lastProcessingTimes.length >= self._lastProcessingTimesSize) {
                self._lastProcessingTimes.shift();
            }
            self._lastProcessingTimes.push(difference);

            var processingLimit = self._throttleFactor * self._baseProcessingLimit;
            if (difference > processingLimit) {
                self.increaseThrottle();
                log.debug("We are slow (" + difference + " > " + processingLimit + "), reducing refresh rate");
            } else if (self._throttleFactor > 1) {
                var maxProcessingTime = Math.max.apply(null, self._lastProcessingTimes);
                var lowerProcessingLimit = (self._throttleFactor - 1) * self._baseProcessingLimit;
                if (maxProcessingTime < lowerProcessingLimit) {
                    self.decreaseThrottle();
                    log.debug("We are fast (" + maxProcessingTime + " < " + lowerProcessingLimit + "), increasing refresh rate");
                }
            }
        }
    };

    self.connect();
}
