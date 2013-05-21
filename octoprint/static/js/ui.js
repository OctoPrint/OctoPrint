//~~ View models

function LoginStateViewModel() {
    var self = this;

    self.loggedIn = ko.observable(false);
    self.username = ko.observable(undefined);
    self.isAdmin = ko.observable(false);
    self.isUser = ko.observable(false);

    self.currentUser = ko.observable(undefined);

    self.userMenuText = ko.computed(function() {
        if (self.loggedIn()) {
            return "\"" + self.username() + "\"";
        } else {
            return "Login";
        }
    })

    self.subscribers = [];
    self.subscribe = function(callback) {
        self.subscribers.push(callback);
    }

    self.requestData = function() {
        $.ajax({
            url: AJAX_BASEURL + "login",
            type: "POST",
            data: {"passive": true},
            success: self.fromResponse
        })
    }

    self.fromResponse = function(response) {
        if (response && response.name) {
            self.loggedIn(true);
            self.username(response.name);
            self.isUser(response.user);
            self.isAdmin(response.admin);

            self.currentUser(response);

            _.each(self.subscribers, function(callback) { callback("login", response); });
        } else {
            self.loggedIn(false);
            self.username(undefined);
            self.isUser(false);
            self.isAdmin(false);

            self.currentUser(undefined);

            _.each(self.subscribers, function(callback) { callback("logout", {}); });
        }
    }

    self.login = function() {
        var username = $("#login_user").val();
        var password = $("#login_pass").val();
        var remember = $("#login_remember").is(":checked");

        $("#login_user").val("");
        $("#login_pass").val("");
        $("#login_remember").prop("checked", false);

        $.ajax({
            url: AJAX_BASEURL + "login",
            type: "POST",
            data: {"user": username, "pass": password, "remember": remember},
            success: function(response) {
                $.pnotify({title: "Login successful", text: "You are now logged in as \"" + response.name + "\"", type: "success"});
                self.fromResponse(response);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                $.pnotify({title: "Login failed", text: "User unknown or wrong password", type: "error"});
            }
        })
    }

    self.logout = function() {
        $.ajax({
            url: AJAX_BASEURL + "logout",
            type: "POST",
            success: function(response) {
                $.pnotify({title: "Logout successful", text: "You are now logged out", type: "success"});
                self.fromResponse(response);
            }
        })
    }
}

function ConnectionViewModel(loginStateViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;

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

function PrinterStateViewModel(loginStateViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;

    self.stateString = ko.observable(undefined);
    self.isErrorOrClosed = ko.observable(undefined);
    self.isOperational = ko.observable(undefined);
    self.isPrinting = ko.observable(undefined);
    self.isPaused = ko.observable(undefined);
    self.isError = ko.observable(undefined);
    self.isReady = ko.observable(undefined);
    self.isLoading = ko.observable(undefined);

    self.filename = ko.observable(undefined);
    self.filament = ko.observable(undefined);
    self.estimatedPrintTime = ko.observable(undefined);
    self.printTime = ko.observable(undefined);
    self.printTimeLeft = ko.observable(undefined);
    self.progress = ko.observable(undefined);
    self.currentLine = ko.observable(undefined);
    self.totalLines = ko.observable(undefined);
    self.currentHeight = ko.observable(undefined);

    self.lineString = ko.computed(function() {
        if (!self.totalLines())
            return "-";
        var currentLine = self.currentLine() ? self.currentLine() : "-";
        return currentLine + " / " + self.totalLines();
    });
    self.progressString = ko.computed(function() {
        if (!self.progress())
            return 0;
        return self.progress();
    });
    self.pauseString = ko.computed(function() {
        if (self.isPaused())
            return "Continue";
        else
            return "Pause";
    });

    self.fromCurrentData = function(data) {
        self._fromData(data);
    }

    self.fromHistoryData = function(data) {
        self._fromData(data);
    }

    self._fromData = function(data) {
        self._processStateData(data.state)
        self._processJobData(data.job);
        self._processGcodeData(data.gcode);
        self._processSdUploadData(data.sdUpload);
        self._processProgressData(data.progress);
        self._processZData(data.currentZ);
    }

    self._processStateData = function(data) {
        self.stateString(data.stateString);
        self.isErrorOrClosed(data.flags.closedOrError);
        self.isOperational(data.flags.operational);
        self.isPaused(data.flags.paused);
        self.isPrinting(data.flags.printing);
        self.isError(data.flags.error);
        self.isReady(data.flags.ready);
        self.isLoading(data.flags.loading);
    }

    self._processJobData = function(data) {
        self.filename(data.filename);
        self.totalLines(data.lines);
        self.estimatedPrintTime(data.estimatedPrintTime);
        self.filament(data.filament);
    }

    self._processGcodeData = function(data) {
        if (self.isLoading()) {
            var progress = Math.round(data.progress * 100);
            if (data.mode == "loading") {
                self.filename("Loading... (" + progress + "%)");
            } else if (data.mode == "parsing") {
                self.filename("Parsing... (" + progress + "%)");
            }
        }
    }

    self._processSdUploadData = function(data) {
        if (self.isLoading()) {
            var progress = Math.round(data.progress * 100);
            self.filename("Streaming... (" + progress + "%)");
        }
    }

    self._processProgressData = function(data) {
        if (data.progress) {
            self.progress(Math.round(data.progress * 100));
        } else {
            self.progress(undefined);
        }
        self.currentLine(data.currentLine);
        self.printTime(data.printTime);
        self.printTimeLeft(data.printTimeLeft);
    }

    self._processZData = function(data) {
        self.currentHeight(data);
    }

    self.print = function() {
        var printAction = function() {
            self._jobCommand("start");
        }

        if (self.isPaused()) {
            $("#confirmation_dialog .confirmation_dialog_message").text("This will restart the print job from the beginning.");
            $("#confirmation_dialog .confirmation_dialog_acknowledge").click(function(e) {e.preventDefault(); $("#confirmation_dialog").modal("hide"); printAction(); });
            $("#confirmation_dialog").modal("show");
        } else {
            printAction();
        }

    }

    self.pause = function() {
        self._jobCommand("pause");
    }

    self.cancel = function() {
        self._jobCommand("cancel");
    }

    self._jobCommand = function(command) {
        $.ajax({
            url: AJAX_BASEURL + "control/job",
            type: "POST",
            dataType: "json",
            data: {command: command}
        });
    }
}

function TemperatureViewModel(loginStateViewModel, settingsViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;

    self.temp = ko.observable(undefined);
    self.bedTemp = ko.observable(undefined);
    self.targetTemp = ko.observable(undefined);
    self.bedTargetTemp = ko.observable(undefined);

    self.isErrorOrClosed = ko.observable(undefined);
    self.isOperational = ko.observable(undefined);
    self.isPrinting = ko.observable(undefined);
    self.isPaused = ko.observable(undefined);
    self.isError = ko.observable(undefined);
    self.isReady = ko.observable(undefined);
    self.isLoading = ko.observable(undefined);

    self.temperature_profiles = settingsViewModel.temperature_profiles;

    self.setTempFromProfile = function(profile) {
        if (!profile)
            return;
        self.setTemp(profile.extruder);
    }

    self.setTemp = function(temp) {
        $.ajax({
            url: AJAX_BASEURL + "control/temperature",
            type: "POST",
            dataType: "json",
            data: { temp: temp },
            success: function() {$("#temp_newTemp").val("")}
        })
    };

    self.setBedTempFromProfile = function(profile) {
        if (!profile)
            return;
        self.setBedTemp(profile.bed);
    }

    self.setBedTemp = function(bedTemp) {
        $.ajax({
            url: AJAX_BASEURL + "control/temperature",
            type: "POST",
            dataType: "json",
            data: { bedTemp: bedTemp },
            success: function() {$("#temp_newBedTemp").val("")}
        })
    };

    self.tempString = ko.computed(function() {
        if (!self.temp())
            return "-";
        return self.temp() + " &deg;C";
    });
    self.bedTempString = ko.computed(function() {
        if (!self.bedTemp())
            return "-";
        return self.bedTemp() + " &deg;C";
    });
    self.targetTempString = ko.computed(function() {
        if (!self.targetTemp())
            return "-";
        return self.targetTemp() + " &deg;C";
    });
    self.bedTargetTempString = ko.computed(function() {
        if (!self.bedTargetTemp())
            return "-";
        return self.bedTargetTemp() + " &deg;C";
    });

    self.temperatures = [];
    self.plotOptions = {
        yaxis: {
            min: 0,
            max: 310,
            ticks: 10
        },
        xaxis: {
            mode: "time",
            minTickSize: [2, "minute"],
            tickFormatter: function(val, axis) {
                if (val == undefined || val == 0)
                    return ""; // we don't want to display the minutes since the epoch if not connected yet ;)

                // current time in milliseconds in UTC
                var timestampUtc = Date.now();

                // calculate difference in milliseconds
                var diff = timestampUtc - val;

                // convert to minutes
                var diffInMins = Math.round(diff / (60 * 1000));
                if (diffInMins == 0)
                    return "just now";
                else
                    return "- " + diffInMins + " min";
            }
        },
        legend: {
            noColumns: 4
        }
    }

    self.fromCurrentData = function(data) {
        self._processStateData(data.state);
        self._processTemperatureUpdateData(data.temperatures);
    }

    self.fromHistoryData = function(data) {
        self._processStateData(data.state);
        self._processTemperatureHistoryData(data.temperatureHistory);
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

    self._processTemperatureUpdateData = function(data) {
        if (data.length == 0)
            return;

        self.temp(data[data.length - 1].temp);
        self.bedTemp(data[data.length - 1].bedTemp);
        self.targetTemp(data[data.length - 1].targetTemp);
        self.bedTargetTemp(data[data.length - 1].targetBedTemp);

        if (!self.temperatures)
            self.temperatures = [];
        if (!self.temperatures.actual)
            self.temperatures.actual = [];
        if (!self.temperatures.target)
            self.temperatures.target = [];
        if (!self.temperatures.actualBed)
            self.temperatures.actualBed = [];
        if (!self.temperatures.targetBed)
            self.temperatures.targetBed = [];

        for (var i = 0; i < data.length; i++) {
            self.temperatures.actual.push([data[i].currentTime, data[i].temp])
            self.temperatures.target.push([data[i].currentTime, data[i].targetTemp])
            self.temperatures.actualBed.push([data[i].currentTime, data[i].bedTemp])
            self.temperatures.targetBed.push([data[i].currentTime, data[i].targetBedTemp])
        }
        self.temperatures.actual = self.temperatures.actual.slice(-300);
        self.temperatures.target = self.temperatures.target.slice(-300);
        self.temperatures.actualBed = self.temperatures.actualBed.slice(-300);
        self.temperatures.targetBed = self.temperatures.targetBed.slice(-300);

        self.updatePlot();
    }

    self._processTemperatureHistoryData = function(data) {
        self.temperatures = data;
        self.updatePlot();
    }

    self.updatePlot = function() {
        var data = [
            {label: "Actual", color: "#FF4040", data: self.temperatures.actual},
            {label: "Target", color: "#FFA0A0", data: self.temperatures.target},
            {label: "Bed Actual", color: "#4040FF", data: self.temperatures.actualBed},
            {label: "Bed Target", color: "#A0A0FF", data: self.temperatures.targetBed}
        ]
        $.plot($("#temperature-graph"), data, self.plotOptions);
    }
}

function ControlViewModel(loginStateViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;

    self.isErrorOrClosed = ko.observable(undefined);
    self.isOperational = ko.observable(undefined);
    self.isPrinting = ko.observable(undefined);
    self.isPaused = ko.observable(undefined);
    self.isError = ko.observable(undefined);
    self.isReady = ko.observable(undefined);
    self.isLoading = ko.observable(undefined);

    self.extrusionAmount = ko.observable(undefined);
    self.controls = ko.observableArray([]);

    self.fromCurrentData = function(data) {
        self._processStateData(data.state);
    }

    self.fromHistoryData = function(data) {
        self._processStateData(data.state);
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

    self.requestData = function() {
        $.ajax({
            url: AJAX_BASEURL + "control/custom",
            method: "GET",
            dataType: "json",
            success: function(response) {
                self._fromResponse(response);
            }
        });
    }

    self._fromResponse = function(response) {
        self.controls(self._enhanceControls(response.controls));
    }

    self._enhanceControls = function(controls) {
        for (var i = 0; i < controls.length; i++) {
            controls[i] = self._enhanceControl(controls[i]);
        }
        return controls;
    }

    self._enhanceControl = function(control) {
        if (control.type == "parametric_command" || control.type == "parametric_commands") {
            for (var i = 0; i < control.input.length; i++) {
                control.input[i].value = control.input[i].default;
            }
        } else if (control.type == "section") {
            control.children = self._enhanceControls(control.children);
        }
        return control;
    }

    self.sendJogCommand = function(axis, multiplier, distance) {
        if (typeof distance === "undefined")
            distance = $('#jog_distance button.active').data('distance');
        $.ajax({
            url: AJAX_BASEURL + "control/jog",
            type: "POST",
            dataType: "json",
            data: axis + "=" + ( distance * multiplier )
        })
    }

    self.sendHomeCommand = function(axis) {
        $.ajax({
            url: AJAX_BASEURL + "control/jog",
            type: "POST",
            dataType: "json",
            data: "home" + axis
        })
    }

    self.sendExtrudeCommand = function() {
        self._sendECommand(1);
    }

    self.sendRetractCommand = function() {
        self._sendECommand(-1);
    }

    self._sendECommand = function(dir) {
        var length = self.extrusionAmount();
        if (!length)
            length = 5;
        $.ajax({
            url: AJAX_BASEURL + "control/jog",
            type: "POST",
            dataType: "json",
            data: "extrude=" + (dir * length)
        })
    }

    self.sendCustomCommand = function(command) {
        if (!command)
            return;

        var data = undefined;
        if (command.type == "command" || command.type == "parametric_command") {
            // single command
            data = {"command" : command.command};
        } else if (command.type == "commands" || command.type == "parametric_commands") {
            // multi command
            data = {"commands": command.commands};
        }

        if (command.type == "parametric_command" || command.type == "parametric_commands") {
            // parametric command(s)
            data["parameters"] = {};
            for (var i = 0; i < command.input.length; i++) {
                data["parameters"][command.input[i].parameter] = command.input[i].value;
            }
        }

        if (!data)
            return;

        $.ajax({
            url: AJAX_BASEURL + "control/command",
            type: "POST",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify(data)
        })
    }

    self.displayMode = function(customControl) {
        switch (customControl.type) {
            case "section":
                return "customControls_sectionTemplate";
            case "command":
            case "commands":
                return "customControls_commandTemplate";
            case "parametric_command":
            case "parametric_commands":
                return "customControls_parametricCommandTemplate";
            default:
                return "customControls_emptyTemplate";
        }
    }

}

function TerminalViewModel(loginStateViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;

    self.log = [];

    self.isErrorOrClosed = ko.observable(undefined);
    self.isOperational = ko.observable(undefined);
    self.isPrinting = ko.observable(undefined);
    self.isPaused = ko.observable(undefined);
    self.isError = ko.observable(undefined);
    self.isReady = ko.observable(undefined);
    self.isLoading = ko.observable(undefined);

    self.autoscrollEnabled = ko.observable(true);

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
            output += self.log[i] + "\n";
        }

        var container = $("#terminal-output");
        container.text(output);

        if (self.autoscrollEnabled()) {
            container.scrollTop(container[0].scrollHeight - container.height())
        }
    }
}

function GcodeFilesViewModel(loginStateViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;

    self.isErrorOrClosed = ko.observable(undefined);
    self.isOperational = ko.observable(undefined);
    self.isPrinting = ko.observable(undefined);
    self.isPaused = ko.observable(undefined);
    self.isError = ko.observable(undefined);
    self.isReady = ko.observable(undefined);
    self.isLoading = ko.observable(undefined);

    // initialize list helper
    self.listHelper = new ItemListHelper(
        "gcodeFiles",
        {
            "name": function(a, b) {
                // sorts ascending
                if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase()) return -1;
                if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase()) return 1;
                return 0;
            },
            "upload": function(a, b) {
                // sorts descending
                if (b["date"] === undefined || a["date"] > b["date"]) return -1;
                if (a["date"] < b["date"]) return 1;
                return 0;
            },
            "size": function(a, b) {
                // sorts descending
                if (b["bytes"] === undefined || a["bytes"] > b["bytes"]) return -1;
                if (a["bytes"] < b["bytes"]) return 1;
                return 0;
            }
        },
        {
            "printed": function(file) {
                return !(file["prints"] && file["prints"]["success"] && file["prints"]["success"] > 0);
            },
            "sd": function(file) {
                return file["origin"] && file["origin"] == "sd";
            },
            "local": function(file) {
                return !(file["origin"] && file["origin"] == "sd");
            }
        },
        "name",
        [],
        [["sd", "local"]],
        CONFIG_GCODEFILESPERPAGE
    );

    self.isLoadActionPossible = ko.computed(function() {
        return self.loginState.isUser() && !self.isPrinting() && !self.isPaused() && !self.isLoading();
    });

    self.isLoadAndPrintActionPossible = ko.computed(function() {
        return self.loginState.isUser() && self.isOperational() && self.isLoadActionPossible();
    });

    self.fromCurrentData = function(data) {
        self._processStateData(data.state);
    }

    self.fromHistoryData = function(data) {
        self._processStateData(data.state);
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

    self.requestData = function() {
        $.ajax({
            url: AJAX_BASEURL + "gcodefiles",
            method: "GET",
            dataType: "json",
            success: function(response) {
                self.fromResponse(response);
            }
        });
    }

    self.fromResponse = function(response) {
        self.listHelper.updateItems(response.files);

        if (response.filename) {
            // got a file to scroll to
            self.listHelper.switchToItem(function(item) {return item.name == response.filename});
        }
    }

    self.loadFile = function(filename, printAfterLoad) {
        var file = self.listHelper.getItem(function(item) {return item.name == filename});
        if (!file) return;

        $.ajax({
            url: AJAX_BASEURL + "gcodefiles/load",
            type: "POST",
            dataType: "json",
            data: {filename: filename, print: printAfterLoad, target: file.origin}
        })
    }

    self.removeFile = function(filename) {
        var file = self.listHelper.getItem(function(item) {return item.name == filename});
        if (!file) return;

        $.ajax({
            url: AJAX_BASEURL + "gcodefiles/delete",
            type: "POST",
            dataType: "json",
            data: {filename: filename, target: file.origin},
            success: self.fromResponse
        })
    }

    self.getPopoverContent = function(data) {
        var output = "<p><strong>Uploaded:</strong> " + data["date"] + "</p>";
        if (data["gcodeAnalysis"]) {
            output += "<p>";
            output += "<strong>Filament:</strong> " + data["gcodeAnalysis"]["filament"] + "<br>";
            output += "<strong>Estimated Print Time:</strong> " + data["gcodeAnalysis"]["estimatedPrintTime"];
            output += "</p>";
        }
        if (data["prints"] && data["prints"]["last"]) {
            output += "<p>";
            output += "<strong>Last Print:</strong> <span class=\"" + (data["prints"]["last"]["success"] ? "text-success" : "text-error") + "\">" + data["prints"]["last"]["date"] + "</span>";
            output += "</p>";
        }
        return output;
    }

    self.getSuccessClass = function(data) {
        if (!data["prints"] || !data["prints"]["last"]) {
            return "";
        }
        return data["prints"]["last"]["success"] ? "text-success" : "text-error";
    }

}

function TimelapseViewModel(loginStateViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;

    self.timelapseType = ko.observable(undefined);
    self.timelapseTimedInterval = ko.observable(undefined);

    self.isErrorOrClosed = ko.observable(undefined);
    self.isOperational = ko.observable(undefined);
    self.isPrinting = ko.observable(undefined);
    self.isPaused = ko.observable(undefined);
    self.isError = ko.observable(undefined);
    self.isReady = ko.observable(undefined);
    self.isLoading = ko.observable(undefined);

    self.intervalInputEnabled = ko.computed(function() {
        return ("timed" == self.timelapseType());
    })

    self.isOperational.subscribe(function(newValue) {
        self.requestData();
    })

    // initialize list helper
    self.listHelper = new ItemListHelper(
        "timelapseFiles",
        {
            "name": function(a, b) {
                // sorts ascending
                if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase()) return -1;
                if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase()) return 1;
                return 0;
            },
            "creation": function(a, b) {
                // sorts descending
                if (a["date"] > b["date"]) return -1;
                if (a["date"] < b["date"]) return 1;
                return 0;
            },
            "size": function(a, b) {
                // sorts descending
                if (a["bytes"] > b["bytes"]) return -1;
                if (a["bytes"] < b["bytes"]) return 1;
                return 0;
            }
        },
        {
        },
        "name",
        [],
        [],
        CONFIG_TIMELAPSEFILESPERPAGE
    )

    self.requestData = function() {
        $.ajax({
            url: AJAX_BASEURL + "timelapse",
            type: "GET",
            dataType: "json",
            success: self.fromResponse
        });
    }

    self.fromResponse = function(response) {
        self.timelapseType(response.type);
        self.listHelper.updateItems(response.files);

        if (response.type == "timed" && response.config && response.config.interval) {
            self.timelapseTimedInterval(response.config.interval)
        } else {
            self.timelapseTimedInterval(undefined)
        }
    }

    self.fromCurrentData = function(data) {
        self._processStateData(data.state);
    }

    self.fromHistoryData = function(data) {
        self._processStateData(data.state);
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

    self.removeFile = function() {
        var filename = this.name;
        $.ajax({
            url: AJAX_BASEURL + "timelapse/" + filename,
            type: "DELETE",
            dataType: "json",
            success: self.requestData
        })
    }

    self.save = function() {
        var data = {
            "type": self.timelapseType()
        }

        if (self.timelapseType() == "timed") {
            data["interval"] = self.timelapseTimedInterval();
        }

        $.ajax({
            url: AJAX_BASEURL + "timelapse",
            type: "POST",
            dataType: "json",
            data: data,
            success: self.fromResponse
        })
    }
}

function GcodeViewModel(loginStateViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;

    self.loadedFilename = undefined;
    self.status = 'idle';
    self.enabled = false;

    self.errorCount = 0;

    self.initialize = function(){
        self.enabled = true;
        GCODE.ui.initHandlers();
    }

    self.loadFile = function(filename){
        if (self.status == 'idle' && self.errorCount < 3) {
            self.status = 'request';
            $.ajax({
                url: AJAX_BASEURL + "gcodefiles/" + filename,
                type: "GET",
                success: function(response, rstatus) {
                    if(rstatus === 'success'){
                        self.showGCodeViewer(response, rstatus);
                        self.loadedFilename=filename;
                        self.status = 'idle';
                    }
                },
                error: function() {
                    self.status = 'idle';
                    self.errorCount++;
                }
            })
        }
    }

    self.showGCodeViewer = function(response, rstatus) {
        var par = {};
        par.target = {};
        par.target.result = response;
        GCODE.gCodeReader.loadFile(par);
    }

    self.fromHistoryData = function(data) {
        self._processData(data);
    }

    self.fromCurrentData = function(data) {
        self._processData(data);
    }

    self._processData = function(data) {
        if(!self.enabled)return;

        if(self.loadedFilename == data.job.filename) {
            var cmdIndex = GCODE.gCodeReader.getLinesCmdIndex(data.progress.progress);
            if(cmdIndex){
                GCODE.renderer.render(cmdIndex.layer, 0, cmdIndex.cmd);
                GCODE.ui.updateLayerInfo(cmdIndex.layer);
            }
            self.errorCount = 0
        } else if (data.job.filename) {
            self.loadFile(data.job.filename);
        }
    }

}

function UsersViewModel(loginStateViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;

    // initialize list helper
    self.listHelper = new ItemListHelper(
        "users",
        {
            "name": function(a, b) {
                // sorts ascending
                if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase()) return -1;
                if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase()) return 1;
                return 0;
            }
        },
        {},
        "name",
        [],
        CONFIG_USERSPERPAGE
    );

    self.emptyUser = {name: "", admin: false, active: false};

    self.currentUser = ko.observable(self.emptyUser);

    self.editorUsername = ko.observable(undefined);
    self.editorPassword = ko.observable(undefined);
    self.editorRepeatedPassword = ko.observable(undefined);
    self.editorAdmin = ko.observable(undefined);
    self.editorActive = ko.observable(undefined);

    self.currentUser.subscribe(function(newValue) {
        if (newValue === undefined) {
            self.editorUsername(undefined);
            self.editorAdmin(undefined);
            self.editorActive(undefined);
        } else {
            self.editorUsername(newValue.name);
            self.editorAdmin(newValue.admin);
            self.editorActive(newValue.active);
        }
        self.editorPassword(undefined);
        self.editorRepeatedPassword(undefined);
    });

    self.editorPasswordMismatch = ko.computed(function() {
        return self.editorPassword() != self.editorRepeatedPassword();
    });

    self.requestData = function() {
        if (!CONFIG_ACCESS_CONTROL) return;

        $.ajax({
            url: AJAX_BASEURL + "users",
            type: "GET",
            dataType: "json",
            success: self.fromResponse
        });
    }

    self.fromResponse = function(response) {
        self.listHelper.updateItems(response.users);
    }

    self.showAddUserDialog = function() {
        if (!CONFIG_ACCESS_CONTROL) return;

        self.currentUser(undefined);
        self.editorActive(true);
        $("#settings-usersDialogAddUser").modal("show");
    }

    self.confirmAddUser = function() {
        if (!CONFIG_ACCESS_CONTROL) return;

        var user = {name: self.editorUsername(), password: self.editorPassword(), admin: self.editorAdmin(), active: self.editorActive()};
        self.addUser(user, function() {
            // close dialog
            self.currentUser(undefined);
            $("#settings-usersDialogAddUser").modal("hide");
        });
    }

    self.showEditUserDialog = function(user) {
        if (!CONFIG_ACCESS_CONTROL) return;

        self.currentUser(user);
        $("#settings-usersDialogEditUser").modal("show");
    }

    self.confirmEditUser = function() {
        if (!CONFIG_ACCESS_CONTROL) return;

        var user = self.currentUser();
        user.active = self.editorActive();
        user.admin = self.editorAdmin();

        // make AJAX call
        self.updateUser(user, function() {
            // close dialog
            self.currentUser(undefined);
            $("#settings-usersDialogEditUser").modal("hide");
        });
    }

    self.showChangePasswordDialog = function(user) {
        if (!CONFIG_ACCESS_CONTROL) return;

        self.currentUser(user);
        $("#settings-usersDialogChangePassword").modal("show");
    }

    self.confirmChangePassword = function() {
        if (!CONFIG_ACCESS_CONTROL) return;

        self.updatePassword(self.currentUser().name, self.editorPassword(), function() {
            // close dialog
            self.currentUser(undefined);
            $("#settings-usersDialogChangePassword").modal("hide");
        });
    }

    //~~ AJAX calls

    self.addUser = function(user, callback) {
        if (!CONFIG_ACCESS_CONTROL) return;
        if (user === undefined) return;

        $.ajax({
            url: AJAX_BASEURL + "users",
            type: "POST",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify(user),
            success: function(response) {
                self.fromResponse(response);
                callback();
            }
        });
    }

    self.removeUser = function(user, callback) {
        if (!CONFIG_ACCESS_CONTROL) return;
        if (user === undefined) return;

        if (user.name == loginStateViewModel.username()) {
            // we do not allow to delete ourselves
            $.pnotify({title: "Not possible", text: "You may not delete your own account.", type: "error"});
            return;
        }

        $.ajax({
            url: AJAX_BASEURL + "users/" + user.name,
            type: "DELETE",
            success: function(response) {
                self.fromResponse(response);
                callback();
            }
        });
    }

    self.updateUser = function(user, callback) {
        if (!CONFIG_ACCESS_CONTROL) return;
        if (user === undefined) return;

        $.ajax({
            url: AJAX_BASEURL + "users/" + user.name,
            type: "PUT",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify(user),
            success: function(response) {
                self.fromResponse(response);
                callback();
            }
        });
    }

    self.updatePassword = function(username, password, callback) {
        if (!CONFIG_ACCESS_CONTROL) return;

        $.ajax({
            url: AJAX_BASEURL + "users/" + username + "/password",
            type: "PUT",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify({password: password}),
            success: callback
        });
    }
}

function SettingsViewModel(loginStateViewModel, usersViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;
    self.users = usersViewModel;

    self.appearance_name = ko.observable(undefined);
    self.appearance_color = ko.observable(undefined);

    /* I did attempt to allow arbitrary gradients but cross browser support via knockout or jquery was going to be horrible */
    self.appearance_available_colors = ko.observable(["default", "red", "orange", "yellow", "green", "blue", "violet"]);

    self.printer_movementSpeedX = ko.observable(undefined);
    self.printer_movementSpeedY = ko.observable(undefined);
    self.printer_movementSpeedZ = ko.observable(undefined);
    self.printer_movementSpeedE = ko.observable(undefined);

    self.webcam_streamUrl = ko.observable(undefined);
    self.webcam_snapshotUrl = ko.observable(undefined);
    self.webcam_ffmpegPath = ko.observable(undefined);
    self.webcam_bitrate = ko.observable(undefined);
    self.webcam_watermark = ko.observable(undefined);

    self.feature_gcodeViewer = ko.observable(undefined);
    self.feature_waitForStart = ko.observable(undefined);
    self.feature_sdSupport = ko.observable(undefined);

    self.folder_uploads = ko.observable(undefined);
    self.folder_timelapse = ko.observable(undefined);
    self.folder_timelapseTmp = ko.observable(undefined);
    self.folder_logs = ko.observable(undefined);

    self.temperature_profiles = ko.observableArray(undefined);

    self.system_actions = ko.observableArray([]);

    self.addTemperatureProfile = function() {
            self.temperature_profiles.push({name: "New", extruder:0, bed:0});
        };

    self.removeTemperatureProfile = function(profile) {
            self.temperature_profiles.remove(profile);
        };

    self.requestData = function() {
        $.ajax({
            url: AJAX_BASEURL + "settings",
            type: "GET",
            dataType: "json",
            success: self.fromResponse
        });
    }

    self.fromResponse = function(response) {
        self.appearance_name(response.appearance.name);
        self.appearance_color(response.appearance.color);

        self.printer_movementSpeedX(response.printer.movementSpeedX);
        self.printer_movementSpeedY(response.printer.movementSpeedY);
        self.printer_movementSpeedZ(response.printer.movementSpeedZ);
        self.printer_movementSpeedE(response.printer.movementSpeedE);

        self.webcam_streamUrl(response.webcam.streamUrl);
        self.webcam_snapshotUrl(response.webcam.snapshotUrl);
        self.webcam_ffmpegPath(response.webcam.ffmpegPath);
        self.webcam_bitrate(response.webcam.bitrate);
        self.webcam_watermark(response.webcam.watermark);

        self.feature_gcodeViewer(response.feature.gcodeViewer);
        self.feature_waitForStart(response.feature.waitForStart);
        self.feature_sdSupport(response.feature.sdSupport);

        self.folder_uploads(response.folder.uploads);
        self.folder_timelapse(response.folder.timelapse);
        self.folder_timelapseTmp(response.folder.timelapseTmp);
        self.folder_logs(response.folder.logs);

        self.temperature_profiles(response.temperature.profiles);

        self.system_actions(response.system.actions);
    }

    self.saveData = function() {
        var data = {
            "appearance" : {
                "name": self.appearance_name(),
                "color": self.appearance_color()
             },
            "printer": {
                "movementSpeedX": self.printer_movementSpeedX(),
                "movementSpeedY": self.printer_movementSpeedY(),
                "movementSpeedZ": self.printer_movementSpeedZ(),
                "movementSpeedE": self.printer_movementSpeedE()
            },
            "webcam": {
                "streamUrl": self.webcam_streamUrl(),
                "snapshotUrl": self.webcam_snapshotUrl(),
                "ffmpegPath": self.webcam_ffmpegPath(),
                "bitrate": self.webcam_bitrate(),
                "watermark": self.webcam_watermark()
            },
            "feature": {
                "gcodeViewer": self.feature_gcodeViewer(),
                "waitForStart": self.feature_waitForStart(),
                "sdSupport": self.feature_sdSupport()
            },
            "folder": {
                "uploads": self.folder_uploads(),
                "timelapse": self.folder_timelapse(),
                "timelapseTmp": self.folder_timelapseTmp(),
                "logs": self.folder_logs()
            },
            "temperature": {
                "profiles": self.temperature_profiles()
            },
            "system": {
                "actions": self.system_actions()
            }
        }

        $.ajax({
            url: AJAX_BASEURL + "settings",
            type: "POST",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify(data),
            success: function(response) {
                self.fromResponse(response);
                $("#settings_dialog").modal("hide");
            }
        })
    }

}

function NavigationViewModel(loginStateViewModel, appearanceViewModel, settingsViewModel, usersViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;
    self.appearance = appearanceViewModel;
    self.systemActions = settingsViewModel.system_actions;
    self.users = usersViewModel;

    self.triggerAction = function(action) {
        var callback = function() {
            $.ajax({
                url: AJAX_BASEURL + "system",
                type: "POST",
                dataType: "json",
                data: "action=" + action.action,
                success: function() {
                    $.pnotify({title: "Success", text: "The command \""+ action.name +"\" executed successfully", type: "success"});
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    $.pnotify({title: "Error", text: "<p>The command \"" + action.name + "\" could not be executed.</p><p>Reason: <pre>" + jqXHR.responseText + "</pre></p>", type: "error"});
                }
            })
        }
        if (action.confirm) {
            $("#confirmation_dialog .confirmation_dialog_message").text(action.confirm);
            $("#confirmation_dialog .confirmation_dialog_acknowledge").click(function(e) {e.preventDefault(); $("#confirmation_dialog").modal("hide"); callback(); });
            $("#confirmation_dialog").modal("show");
        } else {
            callback();
        }
    }
}

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
    })
    self._socket.on("disconnect", function() {
        $("#offline_overlay_message").html(
            "The server appears to be offline, at least I'm not getting any response from it. I'll try to reconnect " +
            "automatically <strong>over the next couple of minutes</strong>, however you are welcome to try a manual reconnect " +
            "anytime using the button below."
        );
        if (!$("#offline_overlay").is(":visible"))
            $("#offline_overlay").show();
    })
    self._socket.on("reconnect_failed", function() {
        $("#offline_overlay_message").html(
            "The server appears to be offline, at least I'm not getting any response from it. I <strong>could not reconnect automatically</strong>, " +
            "but you may try a manual reconnect using the button below."
        );
    })
    self._socket.on("history", function(data) {
        self.connectionViewModel.fromHistoryData(data);
        self.printerStateViewModel.fromHistoryData(data);
        self.temperatureViewModel.fromHistoryData(data);
        self.controlViewModel.fromHistoryData(data);
        self.terminalViewModel.fromHistoryData(data);
        self.timelapseViewModel.fromHistoryData(data);
        self.gcodeViewModel.fromHistoryData(data);
        self.gcodeFilesViewModel.fromCurrentData(data);
    })
    self._socket.on("current", function(data) {
        self.connectionViewModel.fromCurrentData(data);
        self.printerStateViewModel.fromCurrentData(data);
        self.temperatureViewModel.fromCurrentData(data);
        self.controlViewModel.fromCurrentData(data);
        self.terminalViewModel.fromCurrentData(data);
        self.timelapseViewModel.fromCurrentData(data);
        self.gcodeViewModel.fromCurrentData(data);
        self.gcodeFilesViewModel.fromCurrentData(data);
    })
    self._socket.on("updateTrigger", function(type) {
        if (type == "gcodeFiles") {
            gcodeFilesViewModel.requestData();
        }
    })

    self.reconnect = function() {
        self._socket.socket.connect();
    }
}

function ItemListHelper(listType, supportedSorting, supportedFilters, defaultSorting, defaultFilters, exclusiveFilters, filesPerPage) {
    var self = this;

    self.listType = listType;
    self.supportedSorting = supportedSorting;
    self.supportedFilters = supportedFilters;
    self.defaultSorting = defaultSorting;
    self.defaultFilters = defaultFilters;
    self.exclusiveFilters = exclusiveFilters;

    self.allItems = [];
    self.items = ko.observableArray([]);
    self.pageSize = ko.observable(filesPerPage);
    self.currentPage = ko.observable(0);
    self.currentSorting = ko.observable(self.defaultSorting);
    self.currentFilters = ko.observableArray(self.defaultFilters);

    //~~ item handling

    self.updateItems = function(items) {
        self.allItems = items;
        self._updateItems();
    }

    //~~ pagination

    self.paginatedItems = ko.dependentObservable(function() {
        if (self.items() == undefined) {
            return [];
        } else {
            var from = Math.max(self.currentPage() * self.pageSize(), 0);
            var to = Math.min(from + self.pageSize(), self.items().length);
            return self.items().slice(from, to);
        }
    })
    self.lastPage = ko.dependentObservable(function() {
        return Math.ceil(self.items().length / self.pageSize()) - 1;
    })
    self.pages = ko.dependentObservable(function() {
        var pages = [];
        if (self.lastPage() < 7) {
            for (var i = 0; i < self.lastPage() + 1; i++) {
                pages.push({ number: i, text: i+1 });
            }
        } else {
            pages.push({ number: 0, text: 1 });
            if (self.currentPage() < 5) {
                for (var i = 1; i < 5; i++) {
                    pages.push({ number: i, text: i+1 });
                }
                pages.push({ number: -1, text: "…"});
            } else if (self.currentPage() > self.lastPage() - 5) {
                pages.push({ number: -1, text: "…"});
                for (var i = self.lastPage() - 4; i < self.lastPage(); i++) {
                    pages.push({ number: i, text: i+1 });
                }
            } else {
                pages.push({ number: -1, text: "…"});
                for (var i = self.currentPage() - 1; i <= self.currentPage() + 1; i++) {
                    pages.push({ number: i, text: i+1 });
                }
                pages.push({ number: -1, text: "…"});
            }
            pages.push({ number: self.lastPage(), text: self.lastPage() + 1})
        }
        return pages;
    })

    self.switchToItem = function(matcher) {
        var pos = -1;
        var itemList = self.items();
        for (var i = 0; i < itemList.length; i++) {
            if (matcher(itemList[i])) {
                pos = i;
                break;
            }
        }

        if (pos > -1) {
            var page = Math.floor(pos / self.pageSize());
            self.changePage(page);
        }
    }

    self.changePage = function(newPage) {
        if (newPage < 0 || newPage > self.lastPage())
            return;
        self.currentPage(newPage);
    }
    self.prevPage = function() {
        if (self.currentPage() > 0) {
            self.currentPage(self.currentPage() - 1);
        }
    }
    self.nextPage = function() {
        if (self.currentPage() < self.lastPage()) {
            self.currentPage(self.currentPage() + 1);
        }
    }

    self.getItem = function(matcher) {
        var itemList = self.items();
        for (var i = 0; i < itemList.length; i++) {
            if (matcher(itemList[i])) {
                return itemList[i];
            }
        }

        return undefined;
    }

    //~~ sorting

    self.changeSorting = function(sorting) {
        if (!_.contains(_.keys(self.supportedSorting), sorting))
            return;

        self.currentSorting(sorting);
        self._saveCurrentSortingToLocalStorage();

        self.changePage(0);
        self._updateItems();
    }

    //~~ filtering

    self.toggleFilter = function(filter) {
        if (!_.contains(_.keys(self.supportedFilters), filter))
            return;

        if (_.contains(self.currentFilters(), filter)) {
            self.removeFilter(filter);
        } else {
            self.addFilter(filter);
        }
    }

    self.addFilter = function(filter) {
        if (!_.contains(_.keys(self.supportedFilters), filter))
            return;

        for (var i = 0; i < self.exclusiveFilters.length; i++) {
            if (_.contains(self.exclusiveFilters[i], filter)) {
                for (var j = 0; j < self.exclusiveFilters[i].length; j++) {
                    if (self.exclusiveFilters[i][j] == filter)
                        continue;
                    self.removeFilter(self.exclusiveFilters[i][j]);
                }
            }
        }

        var filters = self.currentFilters();
        filters.push(filter);
        self.currentFilters(filters);
        self._saveCurrentFiltersToLocalStorage();

        self._updateItems();
    }

    self.removeFilter = function(filter) {
        if (!_.contains(_.keys(self.supportedFilters), filter))
            return;

        var filters = self.currentFilters();
        filters.pop(filter);
        self.currentFilters(filters);
        self._saveCurrentFiltersToLocalStorage();

        self._updateItems();
    }

    //~~ update for sorted and filtered view

    self._updateItems = function() {
        // determine comparator
        var comparator = undefined;
        var currentSorting = self.currentSorting();
        if (typeof currentSorting !== undefined && typeof self.supportedSorting[currentSorting] !== undefined) {
            comparator = self.supportedSorting[currentSorting];
        }

        // work on all items
        var result = self.allItems;

        // filter if necessary
        var filters = self.currentFilters();
        _.each(filters, function(filter) {
            if (typeof filter !== undefined && typeof supportedFilters[filter] !== undefined)
                result = _.filter(result, supportedFilters[filter]);
        });

        // sort if necessary
        if (typeof comparator !== undefined)
            result.sort(comparator);

        // set result list
        self.items(result);
    }

    //~~ local storage

    self._saveCurrentSortingToLocalStorage = function() {
        self._initializeLocalStorage();

        var currentSorting = self.currentSorting();
        if (currentSorting !== undefined)
            localStorage[self.listType + "." + "currentSorting"] = currentSorting;
        else
            localStorage[self.listType + "." + "currentSorting"] = undefined;
    }

    self._loadCurrentSortingFromLocalStorage = function() {
        self._initializeLocalStorage();

        if (_.contains(_.keys(supportedSorting), localStorage[self.listType + "." + "currentSorting"]))
            self.currentSorting(localStorage[self.listType + "." + "currentSorting"]);
        else
            self.currentSorting(defaultSorting);
    }

    self._saveCurrentFiltersToLocalStorage = function() {
        self._initializeLocalStorage();

        var filters = _.intersection(_.keys(self.supportedFilters), self.currentFilters());
        localStorage[self.listType + "." + "currentFilters"] = JSON.stringify(filters);
    }

    self._loadCurrentFiltersFromLocalStorage = function() {
        self._initializeLocalStorage();

        self.currentFilters(_.intersection(_.keys(self.supportedFilters), JSON.parse(localStorage[self.listType + "." + "currentFilters"])));
    }

    self._initializeLocalStorage = function() {
        if (localStorage[self.listType + "." + "currentSorting"] !== undefined && localStorage[self.listType + "." + "currentFilters"] !== undefined && JSON.parse(localStorage[self.listType + "." + "currentFilters"]) instanceof Array)
            return;

        localStorage[self.listType + "." + "currentSorting"] = self.defaultSorting;
        localStorage[self.listType + "." + "currentFilters"] = JSON.stringify(self.defaultFilters);
    }

    self._loadCurrentFiltersFromLocalStorage();
    self._loadCurrentSortingFromLocalStorage();
}

function AppearanceViewModel(settingsViewModel) {
    var self = this;

    self.name = settingsViewModel.appearance_name;
    self.color = settingsViewModel.appearance_color;

    self.brand = ko.computed(function() {
        if (self.name())
            return "OctoPrint: " + self.name();
        else
            return "OctoPrint";
    })

    self.title = ko.computed(function() {
        if (self.name())
            return self.name() + " [OctoPrint]";
        else
            return "OctoPrint";
    })
}

$(function() {

        //~~ View models
        var loginStateViewModel = new LoginStateViewModel(loginStateViewModel);
        var usersViewModel = new UsersViewModel(loginStateViewModel);
        var connectionViewModel = new ConnectionViewModel(loginStateViewModel);
        var printerStateViewModel = new PrinterStateViewModel(loginStateViewModel);
        var settingsViewModel = new SettingsViewModel(loginStateViewModel, usersViewModel);
        var appearanceViewModel = new AppearanceViewModel(settingsViewModel);
        var temperatureViewModel = new TemperatureViewModel(loginStateViewModel, settingsViewModel);
        var controlViewModel = new ControlViewModel(loginStateViewModel);
        var terminalViewModel = new TerminalViewModel(loginStateViewModel);
        var gcodeFilesViewModel = new GcodeFilesViewModel(loginStateViewModel);
        var timelapseViewModel = new TimelapseViewModel(loginStateViewModel);
        var gcodeViewModel = new GcodeViewModel(loginStateViewModel);
        var navigationViewModel = new NavigationViewModel(loginStateViewModel, appearanceViewModel, settingsViewModel, usersViewModel);

        var dataUpdater = new DataUpdater(
            loginStateViewModel,
            connectionViewModel, 
            printerStateViewModel, 
            temperatureViewModel, 
            controlViewModel,
            terminalViewModel,
            gcodeFilesViewModel,
            timelapseViewModel,
            gcodeViewModel
        );
        
        // work around a stupid iOS6 bug where ajax requests get cached and only work once, as described at
        // http://stackoverflow.com/questions/12506897/is-safari-on-ios-6-caching-ajax-results
        $.ajaxSetup({
            type: 'POST',
            headers: { "cache-control": "no-cache" }
        });

        //~~ Show settings - to ensure centered
        $('#navbar_show_settings').click(function() {
            $('#settings_dialog').modal()
                 .css({
                     width: 'auto',
                     'margin-left': function() { return -($(this).width() /2); }
                  });
            return false;
        })

        //~~ Temperature control (should really move to knockout click binding)

        $("#temp_newTemp_set").click(function() {
            var newTemp = $("#temp_newTemp").val();
            $.ajax({
                url: AJAX_BASEURL + "control/temperature",
                type: "POST",
                dataType: "json",
                data: { temp: newTemp },
                success: function() {$("#temp_newTemp").val("")}
            })
        })
        $("#temp_newBedTemp_set").click(function() {
            var newBedTemp = $("#temp_newBedTemp").val();
            $.ajax({
                url: AJAX_BASEURL + "control/temperature",
                type: "POST",
                dataType: "json",
                data: { bedTemp: newBedTemp },
                success: function() {$("#temp_newBedTemp").val("")}
            })
        })
        $('#tabs a[data-toggle="tab"]').on('shown', function (e) {
            temperatureViewModel.updatePlot();
            terminalViewModel.updateOutput();
        });

        //~~ Terminal

        $("#terminal-send").click(function () {
            var command = $("#terminal-command").val();

            /*
            var re = /^([gm][0-9]+)(\s.*)?/;
            var commandMatch = command.match(re);
            if (commandMatch != null) {
                command = commandMatch[1].toUpperCase() + ((commandMatch[2] !== undefined) ? commandMatch[2] : "");
            }
            */

            if (command) {
                $.ajax({
                    url: AJAX_BASEURL + "control/command",
                    type: "POST",
                    dataType: "json",
                    contentType: "application/json; charset=UTF-8",
                    data: JSON.stringify({"command": command})
                })
                $("#terminal-command").val('')
            }

        })

        $("#terminal-command").keyup(function (event) {
            if (event.keyCode == 13) {
                $("#terminal-send").click()
            }
        })

        //~~ Gcode upload

        function gcode_upload_done(e, data) {
            gcodeFilesViewModel.fromResponse(data.result);
            $("#gcode_upload_progress .bar").css("width", "0%");
            $("#gcode_upload_progress").removeClass("progress-striped").removeClass("active");
            $("#gcode_upload_progress .bar").text("");
        }

        function gcode_upload_progress(e, data) {
            var progress = parseInt(data.loaded / data.total * 100, 10);
            $("#gcode_upload_progress .bar").css("width", progress + "%");
            $("#gcode_upload_progress .bar").text("Uploading ...");
            if (progress >= 100) {
                $("#gcode_upload_progress").addClass("progress-striped").addClass("active");
                $("#gcode_upload_progress .bar").text("Saving ...");
            }
        }

        var localTarget;
        if (CONFIG_SD_SUPPORT) {
            localTarget = $("#drop_locally");
        } else {
            localTarget = $("#drop");
        }

        $("#gcode_upload").fileupload({
            dataType: "json",
            dropZone: localTarget,
            formData: {target: "local"},
            done: gcode_upload_done,
            progressall: gcode_upload_progress
        });

        if (CONFIG_SD_SUPPORT) {
            $("#gcode_upload_sd").fileupload({
                dataType: "json",
                dropZone: $("#drop_sd"),
                formData: {target: "sd"},
                done: gcode_upload_done,
                progressall: gcode_upload_progress
            });
        }

        $(document).bind("dragover", function (e) {
            var dropOverlay = $("#drop_overlay");
            var dropZone = $("#drop");
            var dropZoneLocal = $("#drop_locally");
            var dropZoneSd = $("#drop_sd");
            var dropZoneBackground = $("#drop_background");
            var dropZoneLocalBackground = $("#drop_locally_background");
            var dropZoneSdBackground = $("#drop_sd_background");
            var timeout = window.dropZoneTimeout;

            if (!timeout) {
                dropOverlay.addClass('in');
            } else {
                clearTimeout(timeout);
            }

            var foundLocal = false;
            var foundSd = false;
            var found = false
            var node = e.target;
            do {
                if (dropZoneLocal && node === dropZoneLocal[0]) {
                    foundLocal = true;
                    break;
                } else if (dropZoneSd && node === dropZoneSd[0]) {
                    foundSd = true;
                    break;
                } else if (dropZone && node === dropZone[0]) {
                    found = true;
                    break;
                }
                node = node.parentNode;
            } while (node != null);

            if (foundLocal) {
                dropZoneLocalBackground.addClass("hover");
                dropZoneSdBackground.removeClass("hover");
            } else if (foundSd) {
                dropZoneSdBackground.addClass("hover");
                dropZoneLocalBackground.removeClass("hover");
            } else if (found) {
                dropZoneBackground.addClass("hover");
            } else {
                if (dropZoneLocalBackground) dropZoneLocalBackground.removeClass("hover");
                if (dropZoneSdBackground) dropZoneSdBackground.removeClass("hover");
                if (dropZoneBackground) dropZoneBackground.removeClass("hover");
            }

            window.dropZoneTimeout = setTimeout(function () {
                window.dropZoneTimeout = null;
                dropOverlay.removeClass("in");
                if (dropZoneLocal) dropZoneLocalBackground.removeClass("hover");
                if (dropZoneSd) dropZoneSdBackground.removeClass("hover");
                if (dropZone) dropZoneBackground.removeClass("hover");
            }, 100);
        });

        //~~ Offline overlay
        $("#offline_overlay_reconnect").click(function() {dataUpdater.reconnect()});

        //~~ knockout.js bindings

        ko.bindingHandlers.popover = {
            init: function(element, valueAccessor, allBindingsAccessor, viewModel, bindingContext) {
                var val = ko.utils.unwrapObservable(valueAccessor());

                var options = {
                    title: val.title,
                    animation: val.animation,
                    placement: val.placement,
                    trigger: val.trigger,
                    delay: val.delay,
                    content: val.content,
                    html: val.html
                };
                $(element).popover(options);
            }
        }

        ko.applyBindings(connectionViewModel, document.getElementById("connection_accordion"));
        ko.applyBindings(printerStateViewModel, document.getElementById("state_accordion"));
        ko.applyBindings(gcodeFilesViewModel, document.getElementById("files_accordion"));
        ko.applyBindings(temperatureViewModel, document.getElementById("temp"));
        ko.applyBindings(controlViewModel, document.getElementById("control"));
        ko.applyBindings(terminalViewModel, document.getElementById("term"));
        ko.applyBindings(gcodeViewModel, document.getElementById("gcode"));
        ko.applyBindings(settingsViewModel, document.getElementById("settings_dialog"));
        ko.applyBindings(navigationViewModel, document.getElementById("navbar"));
        ko.applyBindings(appearanceViewModel, document.getElementsByTagName("head")[0]);

        var timelapseElement = document.getElementById("timelapse");
        if (timelapseElement) {
            ko.applyBindings(timelapseViewModel, timelapseElement);
        }
        var gCodeVisualizerElement = document.getElementById("gcode");
        if (gCodeVisualizerElement) {
            gcodeViewModel.initialize();
        }

        //~~ startup commands

        loginStateViewModel.requestData();
        connectionViewModel.requestData();
        controlViewModel.requestData();
        gcodeFilesViewModel.requestData();
        timelapseViewModel.requestData();

        loginStateViewModel.subscribe(function(change, data) {
            if ("login" == change) {
                $("#gcode_upload").fileupload("enable");

                settingsViewModel.requestData();
                if (data.admin) {
                    usersViewModel.requestData();
                }
            } else {
                $("#gcode_upload").fileupload("disable");
            }
        });

        //~~ UI stuff

        $(".accordion-toggle[href='#files']").click(function() {
            if ($("#files").hasClass("in")) {
                $("#files").removeClass("overflow_visible");
            } else {
                setTimeout(function() {
                    $("#files").addClass("overflow_visible");
                }, 1000);
            }
        })

        $.pnotify.defaults.history = false;

        $.fn.modal.defaults.maxHeight = function(){
            // subtract the height of the modal header and footer
            return $(window).height() - 165;
        }

        // Fix input element click problem on login dialog
        $(".dropdown input, .dropdown label").click(function(e) {
            e.stopPropagation();
        });

        $(document).bind("drop dragover", function (e) {
            e.preventDefault();
        });
    }
);

