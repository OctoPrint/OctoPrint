function TerminalViewModel(loginStateViewModel, settingsViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;
    self.settings = settingsViewModel;

    self.log = [];

    self.command = ko.observable(undefined);

    self.isErrorOrClosed = ko.observable(undefined);
    self.isOperational = ko.observable(undefined);
    self.isPrinting = ko.observable(undefined);
    self.isPaused = ko.observable(undefined);
    self.isError = ko.observable(undefined);
    self.isReady = ko.observable(undefined);
    self.isLoading = ko.observable(undefined);

    self.autoscrollEnabled = ko.observable(true);

    self.filters = self.settings.terminalFilters;
    self.filterRegex = undefined;

    self.activeFilters = ko.observableArray([]);
    self.activeFilters.subscribe(function(e) {
        self.updateFilterRegex();
        self.updateOutput();
    });

    self.fromCurrentData = function(data) {
        self._processStateData(data.state);
        self._processCurrentLogData(data.logs);
    }

    self.fromHistoryData = function(data) {
        self._processStateData(data.state);
        self._processHistoryLogData(data.logHistory);
    }

    self._processCurrentLogData = function(data) {
        if (!self.log)
            self.log = []
        self.log = self.log.concat(data)
        self.log = self.log.slice(-300)
        self.updateOutput();
    }

    self._processHistoryLogData = function(data) {
        self.log = data;
        self.updateOutput();
    }

    self._processStateData = function(data) {
        self.isErrorOrClosed(data.flags.closedOrError);
        self.isOperational(data.flags.operational);
        self.isPaused(data.flags.paused);
        self.isPrinting(data.flags.printing);
        self.isError(data.flags.error);
        self.isReady(data.flags.ready);
        self.isLoading(data.flags.loading);
    }

    self.updateFilterRegex = function() {
        var filterRegexStr = self.activeFilters().join("|").trim();
        if (filterRegexStr == "") {
            self.filterRegex = undefined;
        } else {
            self.filterRegex = new RegExp(filterRegexStr);
        }
        console.log("Terminal filter regex: " + filterRegexStr);
    }

    self.updateOutput = function() {
        if (!self.log)
            return;

        var output = "";
        for (var i = 0; i < self.log.length; i++) {
            if (self.filterRegex !== undefined && self.log[i].match(self.filterRegex)) continue;
            output += self.log[i] + "\n";
        }

        var container = $("#terminal-output");
        container.text(output);

        if (self.autoscrollEnabled()) {
            container.scrollTop(container[0].scrollHeight - container.height())
        }
    }

    self.sendCommand = function() {
        var command = self.command();

        var re = /^([gm][0-9]+)(\s.*)?/;
        var commandMatch = command.match(re);
        if (commandMatch != null) {
            command = commandMatch[1].toUpperCase() + ((commandMatch[2] !== undefined) ? commandMatch[2] : "");
        }

        if (command) {
            $.ajax({
                url: AJAX_BASEURL + "control/printer/command",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({"command": command})
            });
            self.command("");
        }
    }

    self.handleEnter = function(event) {
        if (event.keyCode == 13) {
            self.sendCommand();
        }
    }

}
