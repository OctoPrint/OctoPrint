function DataUpdater(allViewModels) {
    var self = this;

    self.allViewModels = allViewModels;

    self._pluginHash = undefined;
    self._configHash = undefined;

    self._throttleFactor = 1;
    self._baseProcessingLimit = 500.0;
    self._lastProcessingTimes = [];
    self._lastProcessingTimesSize = 20;

    self._timelapse_popup = undefined;

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

    self.connect = function() {
        OctoPrint.socket.connect({debug: !!SOCKJS_DEBUG});
    };

    self.reconnect = function() {
        OctoPrint.socket.reconnect();
    };

    self._onReconnectAttempt = function(trial) {
        if (trial <= 0) {
            // Only consider it a real disconnect if the trial number has exceeded our threshold.
            return;
        }

        var handled = false;
        callViewModelsIf(
            self.allViewModels,
            "onServerDisconnect",
            function() { return !handled; },
            function(method) { var result = method(); handled = (result !== undefined && !result) || handled; }
        );

        if (handled) {
            return true;
        }

        showOfflineOverlay(
            gettext("Server is offline"),
            gettext("The server appears to be offline, at least I'm not getting any response from it. I'll try to reconnect automatically <strong>over the next couple of minutes</strong>, however you are welcome to try a manual reconnect anytime using the button below."),
            self.reconnect
        );
    };

    self._onReconnectFailed = function() {
        var handled = false;
        callViewModelsIf(
            self.allViewModels,
            "onServerDisconnect",
            function() { return !handled; },
            function(method) { var result = method(); handled = (result !== undefined && !result) || handled; }
        );

        if (handled) {
            return;
        }

        $("#offline_overlay_title").text(gettext("Server is offline"));
        $("#offline_overlay_message").html(gettext("The server appears to be offline, at least I'm not getting any response from it. I <strong>could not reconnect automatically</strong>, but you may try a manual reconnect using the button below."));
    };

    self._onConnected = function(event) {
        var data = event.data;

        // update version information
        var oldVersion = VERSION;
        VERSION = data["version"];
        DISPLAY_VERSION = data["display_version"];
        BRANCH = data["branch"];
        $("span.version").text(DISPLAY_VERSION);

        // update plugin hash
        var oldPluginHash = self._pluginHash;
        self._pluginHash = data["plugin_hash"];

        // update config hash
        var oldConfigHash = self._configHash;
        self._configHash = data["config_hash"];

        // if the offline overlay is still showing, now's a good time to
        // hide it, plus reload the camera feed if it's currently displayed
        if ($("#offline_overlay").is(":visible")) {
            hideOfflineOverlay();
            callViewModels(self.allViewModels, "onServerReconnect");
            callViewModels(self.allViewModels, "onDataUpdaterReconnect");

            if ($('#tabs li[class="active"] a').attr("href") == "#control") {
                $("#webcam_image").attr("src", CONFIG_WEBCAM_STREAM + "?" + new Date().getTime());
            }
        } else {
            callViewModels(self.allViewModels, "onServerConnect");
        }

        // if the version, the plugin hash or the config hash changed, we
        // want the user to reload the UI since it might be stale now
        var versionChanged = oldVersion != VERSION;
        var pluginsChanged = oldPluginHash != undefined && oldPluginHash != self._pluginHash;
        var configChanged = oldConfigHash != undefined && oldConfigHash != self._configHash;
        if (versionChanged || pluginsChanged || configChanged) {
            showReloadOverlay();
        }
    };

    self._onHistoryData = function(event) {
        callViewModels(self.allViewModels, "fromHistoryData", [event.data]);
    };

    self._onCurrentData = function(event) {
        callViewModels(self.allViewModels, "fromCurrentData", [event.data]);
    };

    self._onSlicingProgress = function(event) {
        $("#gcode_upload_progress").find(".bar").text(_.sprintf(gettext("Slicing ... (%(percentage)d%%)"), {percentage: Math.round(event.data["progress"])}));

        var data = event.data;
        callViewModels(self.allViewModels, "onSlicingProgress", [
            data["slicer"],
            data["model_path"],
            data["machinecode_path"],
            data["progress"]
        ]);
    };

    self._onEvent = function(event) {
        var gcodeUploadProgress = $("#gcode_upload_progress");
        var gcodeUploadProgressBar = $(".bar", gcodeUploadProgress);

        var type = event.data["type"];
        var payload = event.data["payload"];
        var html = "";
        var format = {};

        log.debug("Got event " + type + " with payload: " + JSON.stringify(payload));

        if (type == "SettingsUpdated") {
            if (payload && payload.hasOwnProperty("config_hash")) {
                self._configHash = payload.config_hash;
            }
        } else if (type == "MovieRendering") {
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
    };

    self._onTimelapse = function(event) {
        callViewModels(self.allViewModels, "fromTimelapseData", [event.data]);
    };

    self._onPluginMessage = function(event) {
        callViewModels(self.allViewModels, "onDataUpdaterPluginMessage", [event.data.plugin, event.data.data]);
    };

    self._onIncreaseRate = function(measurement, minimum) {
        log.debug("We are fast (" + measurement + " < " + minimum + "), increasing refresh rate");
        OctoPrint.socket.increaseRate();
    };

    self._onDecreaseRate = function(measurement, maximum) {
        log.debug("We are slow (" + measurement + " > " + maximum + "), reducing refresh rate");
        OctoPrint.socket.decreaseRate();
    };

    OctoPrint.socket.onReconnectAttempt = self._onReconnectAttempt;
    OctoPrint.socket.onReconnectFailed = self._onReconnectFailed;
    OctoPrint.socket.onRateTooHigh = self._onDecreaseRate;
    OctoPrint.socket.onRateTooLow = self._onIncreaseRate;
    OctoPrint.socket
        .onMessage("connected", self._onConnected)
        .onMessage("history", self._onHistoryData)
        .onMessage("current", self._onCurrentData)
        .onMessage("slicingProgress", self._onSlicingProgress)
        .onMessage("event", self._onEvent)
        .onMessage("timelapse", self._onTimelapse)
        .onMessage("plugin", self._onPluginMessage);

    self.connect();
}
