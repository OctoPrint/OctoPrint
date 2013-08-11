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

    self._socket = io.connect();
    self._socket.on("connect", function() {
        if ($("#offline_overlay").is(":visible")) {
            $("#offline_overlay").hide();
            self.timelapseViewModel.requestData();
            $("#webcam_image").attr("src", CONFIG_WEBCAM_STREAM + "?" + new Date().getTime());
            self.loginStateViewModel.requestData();
            self.gcodeFilesViewModel.requestData();
        }
    });
    self._socket.on("disconnect", function() {
        $("#offline_overlay_message").html(
            "The server appears to be offline, at least I'm not getting any response from it. I'll try to reconnect " +
                "automatically <strong>over the next couple of minutes</strong>, however you are welcome to try a manual reconnect " +
                "anytime using the button below."
        );
        if (!$("#offline_overlay").is(":visible"))
            $("#offline_overlay").show();
    });
    self._socket.on("reconnect_failed", function() {
        $("#offline_overlay_message").html(
            "The server appears to be offline, at least I'm not getting any response from it. I <strong>could not reconnect automatically</strong>, " +
                "but you may try a manual reconnect using the button below."
        );
    });
    self._socket.on("history", function(data) {
        self.connectionViewModel.fromHistoryData(data);
        self.printerStateViewModel.fromHistoryData(data);
        self.temperatureViewModel.fromHistoryData(data);
        self.controlViewModel.fromHistoryData(data);
        self.terminalViewModel.fromHistoryData(data);
        self.timelapseViewModel.fromHistoryData(data);
        self.gcodeViewModel.fromHistoryData(data);
        self.gcodeFilesViewModel.fromCurrentData(data);
    });
    self._socket.on("current", function(data) {
        self.connectionViewModel.fromCurrentData(data);
        self.printerStateViewModel.fromCurrentData(data);
        self.temperatureViewModel.fromCurrentData(data);
        self.controlViewModel.fromCurrentData(data);
        self.terminalViewModel.fromCurrentData(data);
        self.timelapseViewModel.fromCurrentData(data);
        self.gcodeViewModel.fromCurrentData(data);
        self.gcodeFilesViewModel.fromCurrentData(data);
    });
    self._socket.on("updateTrigger", function(type) {
        if (type == "gcodeFiles") {
            gcodeFilesViewModel.requestData();
        } else if (type == "timelapseFiles") {
            timelapseViewModel.requestData();
        }
    });
    self._socket.on("feedbackCommandOutput", function(data) {
        self.controlViewModel.fromFeedbackCommandData(data);
    });

    self.reconnect = function() {
        self._socket.socket.connect();
    }
}
