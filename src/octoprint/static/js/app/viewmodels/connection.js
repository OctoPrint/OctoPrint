function ConnectionViewModel(loginStateViewModel, settingsViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;
    self.settings = settingsViewModel;

    self.portOptions = ko.observableArray(undefined);
    self.baudrateOptions = ko.observableArray(undefined);
    self.selectedPort = ko.observable(undefined);
    self.selectedBaudrate = ko.observable(undefined);
    self.saveSettings = ko.observable(undefined);

    self.isErrorOrClosed = ko.observable(undefined);
    self.isOperational = ko.observable(undefined);
    self.isPrinting = ko.observable(undefined);
    self.isPaused = ko.observable(undefined);
    self.isError = ko.observable(undefined);
    self.isReady = ko.observable(undefined);
    self.isLoading = ko.observable(undefined);

    self.buttonText = ko.computed(function() {
        if (self.isErrorOrClosed())
            return "Connect";
        else
            return "Disconnect";
    })

    self.previousIsOperational = undefined;

    self.requestData = function() {
        $.ajax({
            url: AJAX_BASEURL + "control/connection/options",
            method: "GET",
            dataType: "json",
            success: function(response) {
                self.fromResponse(response);
            }
        })
    }

    self.fromResponse = function(response) {
        self.portOptions(response.ports);
        self.baudrateOptions(response.baudrates);

        if (!self.selectedPort() && response.ports && response.ports.indexOf(response.portPreference) >= 0)
            self.selectedPort(response.portPreference);
        if (!self.selectedBaudrate() && response.baudrates && response.baudrates.indexOf(response.baudratePreference) >= 0)
            self.selectedBaudrate(response.baudratePreference);

        self.saveSettings(false);
    }

    self.fromHistoryData = function(data) {
        self._processStateData(data.state);
    }

    self.fromCurrentData = function(data) {
        self._processStateData(data.state);
    }

    self._processStateData = function(data) {
        self.previousIsOperational = self.isOperational();

        self.isErrorOrClosed(data.flags.closedOrError);
        self.isOperational(data.flags.operational);
        self.isPaused(data.flags.paused);
        self.isPrinting(data.flags.printing);
        self.isError(data.flags.error);
        self.isReady(data.flags.ready);
        self.isLoading(data.flags.loading);

        var connectionTab = $("#connection");
        if (self.previousIsOperational != self.isOperational()) {
            if (self.isOperational() && connectionTab.hasClass("in")) {
                // connection just got established, close connection tab for now
                connectionTab.collapse("hide");
            } else if (!connectionTab.hasClass("in")) {
                // connection just dropped, make sure connection tab is open
                connectionTab.collapse("show");
            }
        }
    }

    self.connect = function() {
        if (self.isErrorOrClosed()) {
            var data = {
                "command": "connect",
                "port": self.selectedPort(),
                "baudrate": self.selectedBaudrate()
            };

            if (self.saveSettings())
                data["save"] = true;

            $.ajax({
                url: AJAX_BASEURL + "control/connection",
                type: "POST",
                dataType: "json",
                data: data
            })

            self.settings.serial_port(self.selectedPort())
            self.settings.serial_baudrate(self.selectedBaudrate())
            self.settings.saveData();
        } else {
            self.requestData();
            $.ajax({
                url: AJAX_BASEURL + "control/connection",
                type: "POST",
                dataType: "json",
                data: {"command": "disconnect"}
            })
        }
    }
}
