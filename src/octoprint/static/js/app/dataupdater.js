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
            self.loginStateViewModel.requestData();
            self.gcodeFilesViewModel.requestData();

            if ($('#tabs li[class="active"] a').attr("href") == "#control") {
                $("#webcam_image").attr("src", CONFIG_WEBCAM_STREAM + "?" + new Date().getTime());
            }
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
            var data = e.data[prop];

            switch (prop) {
                case "history": {
                    self.connectionViewModel.fromHistoryData(data);
                    self.printerStateViewModel.fromHistoryData(data);
                    self.temperatureViewModel.fromHistoryData(data);
                    self.controlViewModel.fromHistoryData(data);
                    self.terminalViewModel.fromHistoryData(data);
                    self.timelapseViewModel.fromHistoryData(data);
                    self.gcodeViewModel.fromHistoryData(data);
                    self.gcodeFilesViewModel.fromCurrentData(data);
                    break;
                }
                case "current": {
                    self.connectionViewModel.fromCurrentData(data);
                    self.printerStateViewModel.fromCurrentData(data);
                    self.temperatureViewModel.fromCurrentData(data);
                    self.controlViewModel.fromCurrentData(data);
                    self.terminalViewModel.fromCurrentData(data);
                    self.timelapseViewModel.fromCurrentData(data);
                    self.gcodeViewModel.fromCurrentData(data);
                    self.gcodeFilesViewModel.fromCurrentData(data);
                    break;
                }
                case "updateTrigger": {
                    var type = data["type"];
                    var payload = data["payload"];
                    if (type == "gcodeFiles") {
                        gcodeFilesViewModel.requestData();
                    } else if (type == "timelapseFiles") {
                        timelapseViewModel.requestData();
                    } else if (type == "slicingStarted") {
                        $("#gcode_upload_progress .bar").css("width", "100%");
                        $("#gcode_upload_progress").addClass("progress-striped").addClass("active");
                        $("#gcode_upload_progress .bar").text("Slicing ...");
                    } else if (type == "slicingDone") {
                        $("#gcode_upload_progress .bar").css("width", "0%");
                        $("#gcode_upload_progress").removeClass("progress-striped").removeClass("active");
                        $("#gcode_upload_progress .bar").text("");
                        $.pnotify({title: "Slicing done", text: "Sliced " + payload.stl + " to " + payload.gcode + ", took " + payload.time + " seconds"});
                        gcodeFilesViewModel.requestData(payload.gcode);
                    } else if (type == "slicingFailed") {
                        $("#gcode_upload_progress .bar").css("width", "0%");
                        $("#gcode_upload_progress").removeClass("progress-striped").removeClass("active");
                        $("#gcode_upload_progress .bar").text("");
                        $.pnotify({title: "Slicing failed", text: "Could not slice " + payload.stl + " to " + payload.gcode + ": " + payload.reason, type: "error"});
                    }
                    break;
                }
                case "feedbackCommandOutput": {
                    self.controlViewModel.fromFeedbackCommandData(data);
                    break;
                }
                case "timelapse": {
                    self.printerStateViewModel.fromTimelapseData(data);
                    break;
                }
            }
        }
    }

    self.connect();
}
