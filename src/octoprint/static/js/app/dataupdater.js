function DataUpdater(allViewModels, connectCallback, disconnectCallback) {
    var self = this;

    self.allViewModels = allViewModels;
    self.connectCallback = connectCallback;
    self.disconnectCallback = disconnectCallback;

    self._pluginHash = undefined;
    self._configHash = undefined;

    self._connectedDeferred = undefined;

    self._initializedDeferred = undefined;

    self._throttleFactor = 1;
    self._baseProcessingLimit = 500.0;
    self._lastProcessingTimes = [];
    self._lastProcessingTimesSize = 20;

    self._safeModePopup = undefined;
    self._reloadPopup = undefined;

    self.increaseThrottle = function () {
        self.setThrottle(self._throttleFactor + 1);
    };

    self.decreaseThrottle = function () {
        if (self._throttleFactor <= 1) {
            return;
        }
        self.setThrottle(self._throttleFactor - 1);
    };

    self.setThrottle = function (throttle) {
        self._throttleFactor = throttle;

        self._send("throttle", self._throttleFactor);
        log.debug(
            "DataUpdater: New SockJS throttle factor:",
            self._throttleFactor,
            " new processing limit:",
            self._baseProcessingLimit * self._throttleFactor
        );
    };

    self._send = function (message, data) {
        var payload = {};
        payload[message] = data;
        self._socket.send(JSON.stringify(payload));
    };

    self.connect = function () {
        if (self._connectedDeferred) {
            self._connectedDeferred.reject("reconnect");
        }
        self._connectedDeferred = $.Deferred();
        OctoPrint.socket.connect({
            debug: !!SOCKJS_DEBUG,
            connectTimeout: SOCKJS_CONNECT_TIMEOUT
        });
        return self._connectedDeferred.promise();
    };

    self.reconnect = function () {
        if (self._connectedDeferred) {
            self._connectedDeferred.reject("reconnect");
        }
        self._connectedDeferred = $.Deferred();
        OctoPrint.socket.reconnect();
        return self._connectedDeferred.promise();
    };

    self.initialized = function () {
        if (self._initializedDeferred) {
            self._initializedDeferred.resolve();
            self._initializedDeferred = undefined;
        }
    };

    self._onReconnectAttempt = function (trial) {
        if (trial <= 0) {
            // Only consider it a real disconnect if the trial number has exceeded our threshold.
            return;
        }

        var handled = false;
        callViewModelsIf(
            self.allViewModels,
            "onServerDisconnect",
            function () {
                return !handled;
            },
            function (method) {
                var result = method();
                handled = (result !== undefined && !result) || handled;
            }
        );

        if (handled) {
            return true;
        }

        showOfflineOverlay(
            gettext("Server is offline"),
            gettext(
                "The server appears to be offline, at least I'm not getting any response from it. I'll try to reconnect automatically <strong>over the next couple of minutes</strong>, however you are welcome to try a manual reconnect anytime using the button below."
            ),
            self.reconnect
        );
    };

    self._onReconnectFailed = function () {
        var handled = false;
        callViewModelsIf(
            self.allViewModels,
            "onServerDisconnect",
            function () {
                return !handled;
            },
            function (method) {
                var result = method();
                handled = (result !== undefined && !result) || handled;
            }
        );

        if (handled) {
            return;
        }

        $("#offline_overlay_title").text(gettext("Server is offline"));
        $("#offline_overlay_message").html(
            gettext(
                "The server appears to be offline, at least I'm not getting any response from it. I <strong>could not reconnect automatically</strong>, but you may try a manual reconnect using the button below."
            )
        );
    };

    self._onDisconnected = function (code) {
        if (self._initializedDeferred) {
            self._initializedDeferred.reject();
        }
        self._initializedDeferred = undefined;

        if (self.disconnectCallback) {
            self.disconnectCallback();
        }
    };

    self._onConnectTimeout = function () {
        if (self._connectedDeferred) {
            self._connectedDeferred.reject("timeout");
        }
    };

    self._onConnectMessage = function (event) {
        if (self._initializedDeferred) {
            self._initializedDeferred.reject();
        }
        self._initializedDeferred = $.Deferred();

        if (self.connectCallback) {
            self.connectCallback();
        }

        var data = event.data;

        // update permissions
        PERMISSIONS = data["permissions"];

        // update version information
        var oldVersion = VERSION;
        VERSION = data["version"];
        DISPLAY_VERSION = data["display_version"];
        BRANCH = data["branch"];
        PYTHON_VERSION = data["python_version"];

        $("span.version").text(DISPLAY_VERSION);
        $("span.python_version").text(PYTHON_VERSION);

        // update connectivity state
        ONLINE = data["online"];

        // update plugin hash
        var oldPluginHash = self._pluginHash;
        self._pluginHash = data["plugin_hash"];

        // update config hash
        var oldConfigHash = self._configHash;
        self._configHash = data["config_hash"];

        log.info("Connected to the server");

        // if we have a connected promise, resolve it now
        if (self._connectedDeferred) {
            self._connectedDeferred.resolve();
            self._connectedDeferred = undefined;
        }

        self._ifInitialized(function () {
            // process safe mode
            if (self._safeModePopup) self._safeModePopup.remove();
            if (data["safe_mode"]) {
                // safe mode is active, let's inform the user
                log.info(
                    "❗ Safe mode is active. Third party plugins and language packs are disabled and cannot be enabled."
                );
                log.info("❗ Reason for safe mode: " + data["safe_mode"]);

                var reason = gettext("Unknown");
                switch (data["safe_mode"]) {
                    case "flag": {
                        reason = gettext("Command line flag");
                        break;
                    }
                    case "settings": {
                        reason = gettext("Setting in config.yaml");
                        break;
                    }
                    case "incomplete_startup": {
                        reason = gettext("Problem during last startup");
                        break;
                    }
                }

                self._safeModePopup = new PNotify({
                    title: gettext("Safe mode is active"),
                    text: _.sprintf(
                        gettext(
                            "<p>The server is currently running in safe mode. Third party plugins and language packs are disabled and cannot be enabled.</p><p>Reason: %(reason)s</p>"
                        ),
                        {reason: _.escape(reason)}
                    ),
                    hide: false
                });
            }

            // if the offline overlay is still showing, now's a good time to
            // hide it, plus reload the camera feed if it's currently displayed
            if ($("#offline_overlay").is(":visible")) {
                hideOfflineOverlay();
                log.info("Triggering reconnect on all view models");
                callViewModels(self.allViewModels, "onServerReconnect");
                callViewModels(self.allViewModels, "onDataUpdaterReconnect");
            } else {
                log.info("Triggering connect on all view models");
                callViewModels(self.allViewModels, "onServerConnect");
            }

            // if the version, the plugin hash or the config hash changed, we
            // want the user to reload the UI since it might be stale now
            const versionChanged = oldVersion !== VERSION;
            const pluginsChanged =
                oldPluginHash !== undefined && oldPluginHash !== self._pluginHash;
            const configChanged =
                oldConfigHash !== undefined && oldConfigHash !== self._configHash;

            if (versionChanged) {
                showReloadOverlay();
            } else if (pluginsChanged || configChanged) {
                if (self._reloadPopup) self._reloadPopup.remove();

                let text;
                if (pluginsChanged && configChanged) {
                    text = gettext(
                        "A client reconnect happened and the configuration of the server and the active UI relevant plugins have changed."
                    );
                } else if (pluginsChanged) {
                    text = gettext(
                        "A client reconnect happened and the active UI relevant plugins have changed."
                    );
                } else if (configChanged) {
                    text = gettext(
                        "A client reconnect happened and the configuration of the server has changed."
                    );
                }

                self._reloadPopup = new PNotify({
                    title: gettext("Page reload recommended"),
                    text:
                        "<p>" +
                        text +
                        "</p>" +
                        "<p>" +
                        gettext(
                            "Due to this a reload of the UI is recommended. " +
                                "Please reload the UI now by clicking " +
                                'the "Reload" button below. This will not interrupt ' +
                                "any print jobs you might have ongoing."
                        ) +
                        "</p>",
                    hide: false,
                    confirm: {
                        confirm: true,
                        buttons: [
                            {
                                text: gettext("Ignore"),
                                click: function () {
                                    self._reloadPopup.remove();
                                }
                            },
                            {
                                text: gettext("Reload"),
                                addClass: "btn-primary",
                                click: function () {
                                    self._reloadPopup.remove();
                                    location.reload(true);
                                }
                            }
                        ]
                    },
                    buttons: {
                        closer: false,
                        sticker: false
                    }
                });
            }

            log.info("Server (re)connect processed");
        });
    };

    self._onHistoryData = function (event) {
        self._ifInitialized(function () {
            callViewModels(self.allViewModels, "fromHistoryData", [event.data]);
        });
    };

    self._onCurrentData = function (event) {
        self._ifInitialized(function () {
            callViewModels(self.allViewModels, "fromCurrentData", [event.data]);
        });
    };

    self._onSlicingProgress = function (event) {
        self._ifInitialized(function () {
            $("#gcode_upload_progress")
                .find(".bar")
                .text(
                    _.sprintf(gettext("Slicing ... (%(percentage)d%%)"), {
                        percentage: Math.round(event.data["progress"])
                    })
                );

            var data = event.data;
            callViewModels(self.allViewModels, "onSlicingProgress", [
                data["slicer"],
                data["model_path"],
                data["machinecode_path"],
                data["progress"]
            ]);
        });
    };

    self._onRenderProgress = function (event) {
        self._ifInitialized(function () {
            var data = event.data;
            callViewModels(self.allViewModels, "onRenderProgress", [data["progress"]]);
        });
    };

    self._printerErrorCancelNotification = undefined;
    self._printerErrorDisconnectNotification = undefined;
    self._printerResetNotification = undefined;
    self._onEvent = function (event) {
        self._ifInitialized(function () {
            var type = event.data["type"];
            var payload = event.data["payload"];

            var title, text, severity;

            log.debug("Got event " + type + " with payload: " + JSON.stringify(payload));

            if (type === "PrintCancelling" && payload.firmwareError) {
                if (self._printerErrorCancelNotification !== undefined) {
                    self._printerErrorCancelNotification.remove();
                }
                self._printerErrorCancelNotification = new PNotify({
                    title: gettext("Error reported by printer"),
                    text: _.sprintf(
                        gettext(
                            "Your printer's firmware reported an error. Due to that the ongoing print job will be cancelled. Reported error: %(firmwareError)s"
                        ),
                        {firmwareError: _.escape(payload.firmwareError)}
                    ),
                    type: "error",
                    hide: false
                });
            } else if (type === "Error" && payload.error) {
                severity = "error";
                switch (payload.reason) {
                    case "firmware": {
                        title = gettext("Error reported by printer");
                        text = _.sprintf(
                            gettext(
                                "Your printer's firmware reported an error. Due to that OctoPrint will disconnect. Reported error: %(error)s"
                            ),
                            {error: _.escape(payload.error)}
                        );

                        break;
                    }
                    case "resend":
                    case "resend_loop":
                    case "timeout": {
                        title = gettext("Communication error");
                        text = _.sprintf(
                            gettext(
                                "There was a communication error while talking to your printer. Please consult the terminal output and octoprint.log for details. Error: %(error)s"
                            ),
                            {error: _.escape(payload.error)}
                        );
                        break;
                    }
                    case "connection": {
                        title = gettext("Error connecting to printer");
                        text = _.sprintf(
                            gettext(
                                "There was an error while trying to connect to your printer. Error: %(error)s"
                            ),
                            {error: _.escape(payload.error)}
                        );
                        break;
                    }
                    case "start_print": {
                        title = gettext("Error starting a print");
                        text = _.sprintf(
                            gettext(
                                "There was an error while trying to start a print job. Error: %(error)s"
                            ),
                            {error: _.escape(payload.error)}
                        );
                        break;
                    }
                    case "autodetect": {
                        title = gettext("Could not autodetect your printer");
                        text = _.sprintf(
                            gettext(
                                'No working connection parameters could be found. Are you sure your printer is physically connected and supported? Refer to <a href="%(url)s" target="_blank" rel="noopener noreferer">the FAQ</a> for help in debugging this.'
                            ),
                            {url: "https://faq.octoprint.org/connection-error"}
                        );
                        break;
                    }
                    default: {
                        title = gettext("Unknown error");
                        text = _.sprintf(
                            gettext(
                                "There was an unknown error while talking to your printer. Please consult the terminal output and octoprint.log for details. Error: %(error)s"
                            ),
                            {error: _.escape(payload.error)}
                        );
                        break;
                    }
                }

                if (title && text) {
                    if (self._printerErrorDisconnectNotification !== undefined) {
                        self._printerErrorDisconnectNotification.remove();
                    }
                    self._printerErrorDisconnectNotification = new PNotify({
                        title: title,
                        text: text,
                        type: severity,
                        hide: false
                    });
                }
            } else if (type === "PrinterReset") {
                if (payload.idle) {
                    text = gettext(
                        "It looks like your printer reset while a connection was active. If this was intentional you may safely ignore this message. Otherwise you should investigate why your printer reset itself, since this will interrupt prints and also file transfers to your printer's SD."
                    );
                    severity = "alert";
                } else {
                    text = gettext(
                        "It looks like your printer reset while a connection was active. Due to this the ongoing job was aborted. If this was intentional you may safely ignore this message. Otherwise you should investigate why your printer reset itself, since this will interrupt prints and also file transfers to your printer's SD."
                    );
                    severity = "error";
                }

                if (self._printerResetNotification !== undefined) {
                    self._printerResetNotification.remove();
                }
                self._printerResetNotification = new PNotify({
                    title: gettext("Printer reset detected"),
                    text: text,
                    type: severity,
                    hide: false
                });
            } else if (type === "ConnectivityChanged") {
                ONLINE = payload.new;
            } else if (type === "SettingsUpdated") {
                self._configHash = payload.config_hash;
            }

            var legacyEventHandlers = {
                UpdatedFiles: "onUpdatedFiles",
                MetadataStatisticsUpdated: "onMetadataStatisticsUpdated",
                MetadataAnalysisFinished: "onMetadataAnalysisFinished",
                SlicingDone: "onSlicingDone",
                SlicingCancelled: "onSlicingCancelled",
                SlicingFailed: "onSlicingFailed"
            };
            const camelCaseType = type
                .split("_")
                .map((item) => item.charAt(0).toUpperCase() + item.slice(1))
                .join("");
            _.each(self.allViewModels, function (viewModel) {
                if (viewModel.hasOwnProperty("onEvent" + camelCaseType)) {
                    viewModel["onEvent" + camelCaseType](payload);
                } else if (
                    type !== camelCaseType &&
                    viewModel.hasOwnProperty("onEvent" + type)
                ) {
                    viewModel["onEvent" + type](payload);
                } else if (
                    legacyEventHandlers.hasOwnProperty(type) &&
                    viewModel.hasOwnProperty(legacyEventHandlers[type])
                ) {
                    // there might still be code that uses the old callbacks, make sure those still get called
                    // but log a warning
                    log.warn(
                        "View model " +
                            viewModel.name +
                            " is using legacy event handler " +
                            legacyEventHandlers[type] +
                            ", new handler is called " +
                            legacyEventHandlers[type]
                    );
                    viewModel[legacyEventHandlers[type]](payload);
                }
            });
        });
    };

    self._onTimelapse = function (event) {
        self._ifInitialized(function () {
            callViewModels(self.allViewModels, "fromTimelapseData", [event.data]);
        });
    };

    self._onPluginMessage = function (event) {
        self._ifInitialized(function () {
            callViewModels(self.allViewModels, "onDataUpdaterPluginMessage", [
                event.data.plugin,
                event.data.data
            ]);
        });
    };

    self._onReauthMessage = function (event) {
        self._ifInitialized(function () {
            callViewModels(self.allViewModels, "onDataUpdaterReauthRequired", [
                event.data.reason
            ]);
        });
    };

    self._onIncreaseRate = function (measurement, minimum) {
        log.debug(
            "We are fast (" + measurement + " < " + minimum + "), increasing refresh rate"
        );
        OctoPrint.socket.increaseRate();
    };

    self._onDecreaseRate = function (measurement, maximum) {
        log.debug(
            "We are slow (" + measurement + " > " + maximum + "), reducing refresh rate"
        );
        OctoPrint.socket.decreaseRate();
    };

    self._ifInitialized = function (callback) {
        if (self._initializedDeferred) {
            self._initializedDeferred.done(callback);
        } else {
            callback();
        }
    };

    OctoPrint.socket.onDisconnected = self._onDisconnected;
    OctoPrint.socket.onReconnectAttempt = self._onReconnectAttempt;
    OctoPrint.socket.onReconnectFailed = self._onReconnectFailed;
    OctoPrint.socket.onConnectTimeout = self._onConnectTimeout;
    OctoPrint.socket.onRateTooHigh = self._onDecreaseRate;
    OctoPrint.socket.onRateTooLow = self._onIncreaseRate;
    OctoPrint.socket
        .onMessage("connected", self._onConnectMessage)
        .onMessage("history", self._onHistoryData)
        .onMessage("current", self._onCurrentData)
        .onMessage("slicingProgress", self._onSlicingProgress)
        .onMessage("renderProgress", self._onRenderProgress)
        .onMessage("event", self._onEvent)
        .onMessage("timelapse", self._onTimelapse)
        .onMessage("plugin", self._onPluginMessage)
        .onMessage("reauthRequired", self._onReauthMessage);
}
