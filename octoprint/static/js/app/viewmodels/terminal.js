function TerminalViewModel(loginStateViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;

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
    self.filterM105 = ko.observable(false);
    self.filterM27 = ko.observable(false);

    self.filters = ko.observableArray();

    self.regexM105 = /(Send: M105)|(Recv: ok T:)/;
    self.regexM27 = /(Send: M27)|(Recv: SD printing byte)/;

    self.filterM105.subscribe(function(newValue) {
        self.updateOutput();
    });

    self.filterM27.subscribe(function(newValue) {
        self.updateOutput();
    });

    self.filters.subscribe(function(newValue) {
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

    self.updateOutput = function() {
        if (!self.log)
            return;

        var output = "";
        for (var i = 0; i < self.log.length; i++) {
            var filters = self.filters();
            var filtered = false;
            for (var j = 0; j < filters.length; j++) {
                var filter = filters[j];
                if (self.log[i].match(filter.regex)) {
                    filtered = true;
                    break;
                }
            }
            if (filtered) continue;

            if (self.filterM105() && self.log[i].match(self.regexM105)) continue;
            if (self.filterM27() && self.log[i].match(self.regexM27)) continue;

            output += self.log[i] + "\n";
        }

        var container = $("#terminal-output");
        container.text(output);

        if (self.autoscrollEnabled()) {
            container.scrollTop(container[0].scrollHeight - container.height())
        }
    }

    self.sendCommand = function() {
        /*
         var re = /^([gm][0-9]+)(\s.*)?/;
         var commandMatch = command.match(re);
         if (commandMatch != null) {
         command = commandMatch[1].toUpperCase() + ((commandMatch[2] !== undefined) ? commandMatch[2] : "");
         }
         */

        var command = self.command();
        if (command) {
            $.ajax({
                url: AJAX_BASEURL + "control/command",
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
