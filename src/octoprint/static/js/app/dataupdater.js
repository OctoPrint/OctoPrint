function DataUpdater(allViewModels) {
    var self = this;

    self.allViewModels = allViewModels;

    self._pluginHash = undefined;
    self._configHash = undefined;

    self._connectedDeferred = undefined;

    self._throttleFactor = 1;
    self._baseProcessingLimit = 500.0;
    self._lastProcessingTimes = [];
    self._lastProcessingTimesSize = 20;

    self._safeModePopup = undefined;

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
        if (self._connectedDeferred) {
            self._connectedDeferred.reject();
        }
        self._connectedDeferred = $.Deferred();
        OctoPrint.socket.connect({debug: !!SOCKJS_DEBUG});
        return self._connectedDeferred.promise();
    };

    self.reconnect = function() {
        if (self._connectedDeferred) {
            self._connectedDeferred.reject();
        }
        self._connectedDeferred = $.Deferred();
        OctoPrint.socket.reconnect();
        return self._connectedDeferred.promise();
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

        // process safe mode
        if (self._safeModePopup) self._safeModePopup.remove();
        if (data["safe_mode"]) {
            // safe mode is active, let's inform the user
            log.info("Safe mode is active. Third party plugins are disabled and cannot be enabled.");

            self._safeModePopup = new PNotify({
                title: gettext("Safe mode is active"),
                text: gettext("The server is currently running in safe mode. Third party plugins are disabled and cannot be enabled."),
                hide: false
            });
        }

        // if the offline overlay is still showing, now's a good time to
        // hide it, plus reload the camera feed if it's currently displayed
        if ($("#offline_overlay").is(":visible")) {
            hideOfflineOverlay();
            callViewModels(self.allViewModels, "onServerReconnect");
            callViewModels(self.allViewModels, "onDataUpdaterReconnect");
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

        log.info("Connected to the server");

        // if we have a connected promise, resolve it now
        if (self._connectedDeferred) {
            self._connectedDeferred.resolve();
            self._connectedDeferred = undefined;
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

        log.debug("Got event " + type + " with payload: " + JSON.stringify(payload));

        if (type == "PrintCancelled") {
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
}
