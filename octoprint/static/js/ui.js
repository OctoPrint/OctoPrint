//~~ View models

function ConnectionViewModel() {
    var self = this;

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
            url: AJAX_BASEURL + "control/connectionOptions",
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
                "port": self.selectedPort(),
                "baudrate": self.selectedBaudrate()
            };

            if (self.saveSettings())
                data["save"] = true;

            $.ajax({
                url: AJAX_BASEURL + "control/connect",
                type: "POST",
                dataType: "json",
                data: data
            })
        } else {
            self.requestData();
            $.ajax({
                url: AJAX_BASEURL + "control/disconnect",
                type: "POST",
                dataType: "json"
            })
        }
    }
}

function PrinterStateViewModel() {
    var self = this;

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
    self.currentLine = ko.observable(undefined);
    self.totalLines = ko.observable(undefined);
    self.currentHeight = ko.observable(undefined);

    self.lineString = ko.computed(function() {
        if (!self.totalLines())
            return "-";
        var currentLine = self.currentLine() ? self.currentLine() : "-";
        return currentLine + " / " + self.totalLines();
    });
    self.progress = ko.computed(function() {
        if (!self.currentLine() || !self.totalLines())
            return 0;
        return Math.round(self.currentLine() * 100 / self.totalLines());
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

    self._processProgressData = function(data) {
        self.currentLine(data.progress);
        self.printTime(data.printTime);
        self.printTimeLeft(data.printTimeLeft);
    }

    self._processZData = function(data) {
        self.currentHeight(data);
    }

    self.print = function() {
        var printAction = function() {
            $.ajax({
                url: AJAX_BASEURL + "control/print",
                type: "POST",
                dataType: "json"
            });
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
        $("#job_pause").button("toggle");
        $.ajax({
            url: AJAX_BASEURL + "control/pause",
            type: "POST",
            dataType: "json"
        });
    }

    self.cancel = function() {
        $.ajax({
            url: AJAX_BASEURL + "control/cancel",
            type: "POST",
            dataType: "json"
        });
    }
}

function TemperatureViewModel(settingsViewModel) {
    var self = this;

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

function ControlViewModel() {
    var self = this;

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

function SpeedViewModel() {
    var self = this;

    self.outerWall = ko.observable(undefined);
    self.innerWall = ko.observable(undefined);
    self.fill = ko.observable(undefined);
    self.support = ko.observable(undefined);

    self.isErrorOrClosed = ko.observable(undefined);
    self.isOperational = ko.observable(undefined);
    self.isPrinting = ko.observable(undefined);
    self.isPaused = ko.observable(undefined);
    self.isError = ko.observable(undefined);
    self.isReady = ko.observable(undefined);
    self.isLoading = ko.observable(undefined);

    self._fromCurrentData = function(data) {
        self._processStateData(data.state);
    }

    self._fromHistoryData = function(data) {
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
            url: AJAX_BASEURL + "control/speed",
            type: "GET",
            dataType: "json",
            success: self._fromResponse
        });
    }

    self._fromResponse = function(response) {
        if (response.feedrate) {
            self.outerWall(response.feedrate.outerWall);
            self.innerWall(response.feedrate.innerWall);
            self.fill(response.feedrate.fill);
            self.support(response.feedrate.support);
        } else {
            self.outerWall(undefined);
            self.innerWall(undefined);
            self.fill(undefined);
            self.support(undefined);
        }
    }
}

function TerminalViewModel() {
    var self = this;

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

function GcodeFilesViewModel() {
    var self = this;

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
            "printed": function(file) {
                return !(file["prints"] && file["prints"]["success"] && file["prints"]["success"] > 0);
            }
        },
        "name",
        [],
        CONFIG_GCODEFILESPERPAGE
    );

    self.isLoadActionPossible = ko.computed(function() {
        return !self.isPrinting() && !self.isPaused() && !self.isLoading();
    });

    self.isLoadAndPrintActionPossible = ko.computed(function() {
        return self.isOperational() && self.isLoadActionPossible();
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
        $.ajax({
            url: AJAX_BASEURL + "gcodefiles/load",
            type: "POST",
            dataType: "json",
            data: {filename: filename, print: printAfterLoad}
        })
    }

    self.removeFile = function(filename) {
        $.ajax({
            url: AJAX_BASEURL + "gcodefiles/delete",
            type: "POST",
            dataType: "json",
            data: {filename: filename},
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

function TimelapseViewModel() {
    var self = this;

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
            url: AJAX_BASEURL + "timelapse/config",
            type: "POST",
            dataType: "json",
            data: data,
            success: self.fromResponse
        })
    }
}

function GcodeViewModel() {
    var self = this;

    self.loadedFilename = undefined;
    self.status = 'idle';
    self.enabled = false;

    self.initialize = function(){
        self.enabled = true;
        GCODE.ui.initHandlers();
    }

    self.loadFile = function(filename){
        if (self.status == 'idle') {
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
        } else if (data.job.filename) {
            self.loadFile(data.job.filename);
        }
    }

}

function SettingsViewModel() {
    var self = this;

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
        })
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
                "waitForStart": self.feature_waitForStart()
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

function NavigationViewModel(appearanceViewModel, settingsViewModel) {
    var self = this;

    self.appearance = appearanceViewModel;
    self.systemActions = settingsViewModel.system_actions;

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

function DataUpdater(connectionViewModel, printerStateViewModel, temperatureViewModel, controlViewModel, speedViewModel, terminalViewModel, gcodeFilesViewModel, timelapseViewModel, gcodeViewModel) {
    var self = this;

    self.connectionViewModel = connectionViewModel;
    self.printerStateViewModel = printerStateViewModel;
    self.temperatureViewModel = temperatureViewModel;
    self.controlViewModel = controlViewModel;
    self.terminalViewModel = terminalViewModel;
    self.speedViewModel = speedViewModel;
    self.gcodeFilesViewModel = gcodeFilesViewModel;
    self.timelapseViewModel = timelapseViewModel;
    self.gcodeViewModel = gcodeViewModel;

    self._socket = io.connect();
    self._socket.on("connect", function() {
        if ($("#offline_overlay").is(":visible")) {
            $("#offline_overlay").hide();
            self.timelapseViewModel.requestData();
            $("#webcam_image").attr("src", CONFIG_WEBCAM_STREAM + "?" + new Date().getTime());
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

function ItemListHelper(listType, supportedSorting, supportedFilters, defaultSorting, defaultFilters, filesPerPage) {
    var self = this;

    self.listType = listType;
    self.supportedSorting = supportedSorting;
    self.supportedFilters = supportedFilters;
    self.defaultSorting = defaultSorting;
    self.defaultFilters = defaultFilters;

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

        var filters = self.currentFilters();
        filters.push(filter);
        self.currentFilters(filters);
        self._saveCurrentFiltersToLocalStorage();

        self._updateItems();
    }

    self.removeFilter = function(filter) {
        if (filter != "printed")
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
        var connectionViewModel = new ConnectionViewModel();
        var printerStateViewModel = new PrinterStateViewModel();
        var settingsViewModel = new SettingsViewModel();
        var appearanceViewModel = new AppearanceViewModel(settingsViewModel);
        var temperatureViewModel = new TemperatureViewModel(settingsViewModel);
        var controlViewModel = new ControlViewModel();
        var speedViewModel = new SpeedViewModel();
        var terminalViewModel = new TerminalViewModel();
        var gcodeFilesViewModel = new GcodeFilesViewModel();
        var timelapseViewModel = new TimelapseViewModel();
        var gcodeViewModel = new GcodeViewModel();
        var navigationViewModel = new NavigationViewModel(appearanceViewModel, settingsViewModel);

        var dataUpdater = new DataUpdater(
            connectionViewModel, 
            printerStateViewModel, 
            temperatureViewModel, 
            controlViewModel,
            speedViewModel, 
            terminalViewModel,
            gcodeFilesViewModel,
            timelapseViewModel,
            gcodeViewModel
        );
        
        //work around a stupid iOS6 bug where ajax requests get cached and only work once, as described at http://stackoverflow.com/questions/12506897/is-safari-on-ios-6-caching-ajax-results
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

        //~~ Print job control

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
        });

        //~~ Speed controls

        function speedCommand(structure) {
            var speedSetting = $("#speed_" + structure).val();
            if (speedSetting) {
                $.ajax({
                    url: AJAX_BASEURL + "control/speed",
                    type: "POST",
                    dataType: "json",
                    data: structure + "=" + speedSetting,
                    success: function(response) {
                        $("#speed_" + structure).val("")
                        speedViewModel.fromResponse(response);
                    }
                })
            }
        }
        $("#speed_outerWall_set").click(function() {speedCommand("outerWall")});
        $("#speed_innerWall_set").click(function() {speedCommand("innerWall")});
        $("#speed_support_set").click(function() {speedCommand("support")});
        $("#speed_fill_set").click(function() {speedCommand("fill")});

        //~~ Terminal

        $("#terminal-send").click(function () {
            var command = $("#terminal-command").val();
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

        $("#gcode_upload").fileupload({
            dataType: "json",
            done: function (e, data) {
                gcodeFilesViewModel.fromResponse(data.result);
                $("#gcode_upload_progress .bar").css("width", "0%");
                $("#gcode_upload_progress").removeClass("progress-striped").removeClass("active");
                $("#gcode_upload_progress .bar").text("");
            },
            progressall: function (e, data) {
                var progress = parseInt(data.loaded / data.total * 100, 10);
                $("#gcode_upload_progress .bar").css("width", progress + "%");
                $("#gcode_upload_progress .bar").text("Uploading ...");
                if (progress >= 100) {
                    $("#gcode_upload_progress").addClass("progress-striped").addClass("active");
                    $("#gcode_upload_progress .bar").text("Saving ...");
                }
            }
        });

        //~~ Offline overlay
        $("#offline_overlay_reconnect").click(function() {dataUpdater.reconnect()});

        //~~ Alert

        /*
        function displayAlert(text, timeout, type) {
            var placeholder = $("#alert_placeholder");

            var alertType = "";
            if (type == "success" || type == "error" || type == "info") {
                alertType = " alert-" + type;
            }

            placeholder.append($("<div id='activeAlert' class='alert " + alertType + " fade in' data-alert='alert'><p>" + text + "</p></div>"));
            placeholder.fadeIn();
            $("#activeAlert").delay(timeout).fadeOut("slow", function() {$(this).remove(); $("#alert_placeholder").hide();});
        }
        */

        //~~ Login/logout

        $("#login_button").click(function() {
            var username = $("#login_user").val();
            var password = $("#login_pass").val();
            var remember = $("#login_remember").is(":checked");

            $.ajax({
                url: AJAX_BASEURL + "login",
                type: "POST",
                data: {"user": username, "pass": password, "remember": remember},
                success: function(response) {
                    $.pnotify({title: "Login successful", text: "You are now logged in", type: "success"});
                    $("#login_dropdown_text").text("\"" + response.name + "\"");
                    $("#login_dropdown_loggedout").removeClass("dropdown-menu").addClass("hide");
                    $("#login_dropdown_loggedin").removeClass("hide").addClass("dropdown-menu");
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    $.pnotify({title: "Login failed", text: "User unknown or wrong password", type: "error"});
                }
            })
        });
        $("#logout_button").click(function(){
            $.ajax({
                url: AJAX_BASEURL + "logout",
                type: "POST",
                success: function(response) {
                    $.pnotify({title: "Logout successful", text: "You are now logged out", type: "success"});
                    $("#login_dropdown_text").text("Login");
                    $("#login_dropdown_loggedin").removeClass("dropdown-menu").addClass("hide");
                    $("#login_dropdown_loggedout").removeClass("hide").addClass("dropdown-menu");
                }
            })
        })

        $.ajax({
            url: AJAX_BASEURL + "login",
            type: "POST",
            data: {"passive": true},
            success: function(response) {
                if (response["name"]) {
                    $("#login_dropdown_text").text("\"" + response.name + "\"");
                    $("#login_dropdown_loggedout").removeClass("dropdown-menu").addClass("hide");
                    $("#login_dropdown_loggedin").removeClass("hide").addClass("dropdown-menu");
                }
            }
        })

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

        ko.applyBindings(connectionViewModel, document.getElementById("connection"));
        ko.applyBindings(printerStateViewModel, document.getElementById("state"));
        ko.applyBindings(gcodeFilesViewModel, document.getElementById("files"));
        ko.applyBindings(gcodeFilesViewModel, document.getElementById("files-heading"));
        ko.applyBindings(temperatureViewModel, document.getElementById("temp"));
        ko.applyBindings(controlViewModel, document.getElementById("control"));
        ko.applyBindings(terminalViewModel, document.getElementById("term"));
        ko.applyBindings(speedViewModel, document.getElementById("speed"));
        ko.applyBindings(gcodeViewModel, document.getElementById("gcode"));
        ko.applyBindings(settingsViewModel, document.getElementById("settings_dialog"));
        ko.applyBindings(navigationViewModel, document.getElementById("navbar"));
        ko.applyBindings(appearanceViewModel, document.getElementsByTagName("head")[0]);

        var timelapseElement = document.getElementById("timelapse");
        if (timelapseElement) {
            ko.applyBindings(timelapseViewModel, document.getElementById("timelapse"));
        }
        var gCodeVisualizerElement = document.getElementById("gcode");
        if(gCodeVisualizerElement){
            gcodeViewModel.initialize();
        }
        //~~ startup commands

        connectionViewModel.requestData();
        controlViewModel.requestData();
        gcodeFilesViewModel.requestData();
        timelapseViewModel.requestData();
        settingsViewModel.requestData();

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

        // Fix input element click problem
        $('.dropdown input, .dropdown label').click(function(e) {
            e.stopPropagation();
        });

    }
);

