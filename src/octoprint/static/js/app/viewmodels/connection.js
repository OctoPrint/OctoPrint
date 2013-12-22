function ConnectionViewModel(loginStateViewModel, settingsViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;
    self.settings = settingsViewModel;

    self.portOptions = ko.observableArray(undefined);
    self.baudrateOptions = ko.observableArray(undefined);
    self.selectedPort = ko.observable(undefined);
    self.selectedBaudrate = ko.observable(undefined);
    self.saveSettings = ko.observable(undefined);
    self.autoconnect = ko.observable(undefined);

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
            url: API_BASEURL + "connection",
            method: "GET",
            dataType: "json",
            success: function(response) {
                self.fromResponse(response);
            }
        })
    }

    self.fromResponse = function(response) {
        var ports = response.options.ports;
        var baudrates = response.options.baudrates;
        var portPreference = response.options.portPreference;
        var baudratePreference = response.options.baudratePreference;

        self.portOptions(ports);
        self.baudrateOptions(baudrates);

        if (!self.selectedPort() && ports && ports.indexOf(portPreference) >= 0)
            self.selectedPort(portPreference);
        if (!self.selectedBaudrate() && baudrates && baudrates.indexOf(baudratePreference) >= 0)
            self.selectedBaudrate(baudratePreference);

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
                "baudrate": self.selectedBaudrate(),
                "autoconnect": self.settings.serial_autoconnect()
            };

            if (self.saveSettings())
                data["save"] = true;

            $.ajax({
                url: API_BASEURL + "connection",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify(data),
                success: function(response) {
                    self.settings.requestData()
                }
            });
        } else {
            self.requestData();
            $.ajax({
                url: API_BASEURL + "connection",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({"command": "disconnect"})
            })
        }
    }
}
