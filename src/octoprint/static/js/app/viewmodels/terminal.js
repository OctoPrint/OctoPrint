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

    self.cmdHistory = [];
    self.cmdHistoryIdx = -1;

    self.activeFilters = ko.observableArray([]);
    self.activeFilters.subscribe(function(e) {
        self.updateFilterRegex();
        self.updateOutput();
    });

    self.fromCurrentData = function(data) {
        self._processStateData(data.state);
        self._processCurrentLogData(data.logs);
    };

    self.fromHistoryData = function(data) {
        self._processStateData(data.state);
        self._processHistoryLogData(data.logs);
    };

    self._processCurrentLogData = function(data) {
        if (!self.log)
            self.log = [];
        self.log = self.log.concat(data);
        self.log = self.log.slice(-300);
        self.updateOutput();
    };

    self._processHistoryLogData = function(data) {
        self.log = data;
        self.updateOutput();
    };

    self._processStateData = function(data) {
        self.isErrorOrClosed(data.flags.closedOrError);
        self.isOperational(data.flags.operational);
        self.isPaused(data.flags.paused);
        self.isPrinting(data.flags.printing);
        self.isError(data.flags.error);
        self.isReady(data.flags.ready);
        self.isLoading(data.flags.loading);
    };

    self.updateFilterRegex = function() {
        var filterRegexStr = self.activeFilters().join("|").trim();
        if (filterRegexStr == "") {
            self.filterRegex = undefined;
        } else {
            self.filterRegex = new RegExp(filterRegexStr);
        }
        console.log("Terminal filter regex: " + filterRegexStr);
    };

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
    };

    self.sendCommand = function() {
        var command = self.command();
        if (!command) {
            return;
        }

        var re = /^([gmt][0-9]+)(\s.*)?/;
        var commandMatch = command.match(re);
        if (commandMatch != null) {
            command = commandMatch[1].toUpperCase() + ((commandMatch[2] !== undefined) ? commandMatch[2] : "");
        }

        if (command) {
            $.ajax({
                url: API_BASEURL + "printer/command",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({"command": command})
            });

            self.cmdHistory.push(command);
            self.cmdHistory.slice(-300); // just to set a sane limit to how many manually entered commands will be saved...
            self.cmdHistoryIdx = self.cmdHistory.length;
            self.command("");
        }
    };

    self.handleKeyDown = function(event) {
        var keyCode = event.keyCode;

        if (keyCode == 38 || keyCode == 40) {
            if (keyCode == 38 && self.cmdHistory.length > 0 && self.cmdHistoryIdx > 0) {
                self.cmdHistoryIdx--;
            } else if (keyCode == 40 && self.cmdHistoryIdx < self.cmdHistory.length - 1) {
                self.cmdHistoryIdx++;
            }

            if (self.cmdHistoryIdx >= 0 && self.cmdHistoryIdx < self.cmdHistory.length) {
                self.command(self.cmdHistory[self.cmdHistoryIdx]);
            }

            // prevent the cursor from being moved to the beginning of the input field (this is actually the reason
            // why we do the arrow key handling in the keydown event handler, keyup would be too late already to
            // prevent this from happening, causing a jumpy cursor)
            return false;
        }

        // do not prevent default action
        return true;
    };

    self.handleKeyUp = function(event) {
        if (event.keyCode == 13) {
            self.sendCommand();
        }

        // do not prevent default action
        return true;
    };

}
