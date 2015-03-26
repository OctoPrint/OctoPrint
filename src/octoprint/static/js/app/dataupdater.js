function DataUpdater(allViewModels) {
    var self = this;

    self.allViewModels = allViewModels;

    self._socket = undefined;
    self._autoReconnecting = false;
    self._autoReconnectTrial = 0;
    self._autoReconnectTimeouts = [0, 1, 1, 2, 3, 5, 8, 13, 20, 40, 100];
    self._autoReconnectDialogIndex = 1;

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
        delete self._socket;
        self.connect();
    };

    self._onconnect = function() {
        self._autoReconnecting = false;
        self._autoReconnectTrial = 0;
    };

    self._onclose = function() {
        if (self._autoReconnectTrial >= self._autoReconnectDialogIndex) {
            // Only consider it a real disconnect if the trial number has exceeded our threshold.

            var handled = false;
            _.each(self.allViewModels, function(viewModel) {
                if (handled == true) {
                    return;
                }

                if (viewModel.hasOwnProperty("onServerDisconnect")) {
                    if (!viewModel.onServerDisconnect()) {
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
                if (!viewModel.onServerDisconnect()) {
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
                    $("span.version").text(DISPLAY_VERSION);

                    if ($("#offline_overlay").is(":visible")) {
                        hideOfflineOverlay();
                        _.each(self.allViewModels, function(viewModel) {
                            if (viewModel.hasOwnProperty("onDataUpdaterReconnect")) {
                                viewModel.onDataUpdaterReconnect();
                            }
                        });

                        if ($('#tabs li[class="active"] a').attr("href") == "#control") {
                            $("#webcam_image").attr("src", CONFIG_WEBCAM_STREAM + "?" + new Date().getTime());
                        }
                    }

                    if (oldVersion != VERSION) {
                        // version change detected, force reloading UI - use randomized delay to reduce server load in
                        // the case of multiple clients
                        var delay = 5 + Math.floor(Math.random() * 5) + 1;
                        setTimeout(function() {location.reload(true);}, delay * 1000);

                        // TODO notify about that, or show confirmation
                    }

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

                    log.debug("Got event " + type + " with payload: " + JSON.stringify(payload));

                    if (type == "MovieRendering") {
                        new PNotify({title: gettext("Rendering timelapse"), text: _.sprintf(gettext("Now rendering timelapse %(movie_basename)s"), payload)});
                    } else if (type == "MovieDone") {
                        new PNotify({title: gettext("Timelapse ready"), text: _.sprintf(gettext("New timelapse %(movie_basename)s is done rendering."), payload)});
                    } else if (type == "MovieFailed") {
                        html = "<p>" + _.sprintf(gettext("Rendering of timelapse %(movie_basename)s failed with return code %(returncode)s"), payload) + "</p>";
                        html += pnotifyAdditionalInfo('<pre style="overflow: auto">' + payload.error + '</pre>');
                        new PNotify({title: gettext("Rendering failed"), text: html, type: "error", hide: false});
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
                        gcodeFilesViewModel.requestData(payload.remote, "sdcard");
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
        }
    };

    self.connect();
}
