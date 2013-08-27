function DataUpdater(loginStateViewModel, connectionViewModel, printerStateViewModel, temperatureViewModel, controlViewModel, terminalViewModel, gcodeFilesViewModel, timelapseViewModel, gcodeViewModel) {
    var self = this;

    self.loginStateViewModel = loginStateViewModel;
    self.connectionViewModel = connectionViewModel;
    self.printerStateViewModel = printerStateViewModel;
    self.temperatureViewModel = temperatureViewModel;
    self.controlViewModel = controlViewModel;
    self.terminalViewModel = terminalViewModel;
    self.gcodeFilesViewModel = gcodeFilesViewModel;
    self.timelapseViewModel = timelapseViewModel;
    self.gcodeViewModel = gcodeViewModel;

    self._socket = undefined;
    self._autoReconnecting = false;
    self._autoReconnectTrial = 0;
    self._autoReconnectTimeouts = [1, 1, 2, 3, 5, 8, 13, 20, 40, 100];

    self.connect = function() {
        var options = {};
        if (SOCKJS_DEBUG) {
            options["debug"] = true;
        }

        self._socket = new SockJS(SOCKJS_URI, undefined, options);
        self._socket.onopen = self._onconnect;
        self._socket.onclose = self._onclose;
        self._socket.onmessage = self._onmessage;
    }

    self.reconnect = function() {
        delete self._socket;
        self.connect();
    }

    self._onconnect = function() {
        self._autoReconnecting = false;
        self._autoReconnectTrial = 0;

        if ($("#offline_overlay").is(":visible")) {
            $("#offline_overlay").hide();
            self.timelapseViewModel.requestData();
            $("#webcam_image").attr("src", CONFIG_WEBCAM_STREAM + "?" + new Date().getTime());
            self.loginStateViewModel.requestData();
            self.gcodeFilesViewModel.requestData();
        }
    }

    self._onclose = function() {
        $("#offline_overlay_message").html(
            "The server appears to be offline, at least I'm not getting any response from it. I'll try to reconnect " +
                "automatically <strong>over the next couple of minutes</strong>, however you are welcome to try a manual reconnect " +
                "anytime using the button below."
        );
        if (!$("#offline_overlay").is(":visible"))
            $("#offline_overlay").show();

        if (self._autoReconnectTrial < self._autoReconnectTimeouts.length) {
            var timeout = self._autoReconnectTimeouts[self._autoReconnectTrial];
            console.log("Reconnect trial #" + self._autoReconnectTrial + ", waiting " + timeout + "s");
            setTimeout(self.reconnect, timeout * 1000);
            self._autoReconnectTrial++;
        } else {
            self._onreconnectfailed();
        }
    }

    self._onreconnectfailed = function() {
        $("#offline_overlay_message").html(
            "The server appears to be offline, at least I'm not getting any response from it. I <strong>could not reconnect automatically</strong>, " +
                "but you may try a manual reconnect using the button below."
        );
    }

    self._onmessage = function(e) {
        for (var prop in e.data) {
            var payload = e.data[prop];

            switch (prop) {
                case "history": {
                    self.connectionViewModel.fromHistoryData(payload);
                    self.printerStateViewModel.fromHistoryData(payload);
                    self.temperatureViewModel.fromHistoryData(payload);
                    self.controlViewModel.fromHistoryData(payload);
                    self.terminalViewModel.fromHistoryData(payload);
                    self.timelapseViewModel.fromHistoryData(payload);
                    self.gcodeViewModel.fromHistoryData(payload);
                    self.gcodeFilesViewModel.fromCurrentData(payload);
                    break;
                }
                case "current": {
                    self.connectionViewModel.fromCurrentData(payload);
                    self.printerStateViewModel.fromCurrentData(payload);
                    self.temperatureViewModel.fromCurrentData(payload);
                    self.controlViewModel.fromCurrentData(payload);
                    self.terminalViewModel.fromCurrentData(payload);
                    self.timelapseViewModel.fromCurrentData(payload);
                    self.gcodeViewModel.fromCurrentData(payload);
                    self.gcodeFilesViewModel.fromCurrentData(payload);
                    break;
                }
                case "updateTrigger": {
                    if (payload == "gcodeFiles") {
                        gcodeFilesViewModel.requestData();
                    } else if (payload == "timelapseFiles") {
                        timelapseViewModel.requestData();
                    }
                    break;
                }
                case "feedbackCommandOutput": {
                    self.controlViewModel.fromFeedbackCommandData(payload);
                    break
                }
            }
        }
    }

    self.connect();
}
