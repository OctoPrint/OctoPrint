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
            self.filename("Loading... (" + Math.round(data.progress * 100) + "%)");
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
}

function TemperatureViewModel() {
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

    self.tempString = ko.computed(function() {
        if (!self.temp())
            return "-";
        return self.temp() + " °C";
    });
    self.bedTempString = ko.computed(function() {
        if (!self.bedTemp())
            return "-";
        return self.bedTemp() + " °C";
    });
    self.targetTempString = ko.computed(function() {
        if (!self.targetTemp())
            return "-";
        return self.targetTemp() + " °C";
    });
    self.bedTargetTempString = ko.computed(function() {
        if (!self.bedTargetTemp())
            return "-";
        return self.bedTargetTemp() + " °C";
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
                var now = new Date();
                var diff = now.getTime() - val;
                var diffInMins = Math.round(diff / (60000));
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
        self.bedTargetTemp(data[data.length - 1].bedTargetTemp);

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
            self.temperatures.targetBed.push([data[i].currentTime, data[i].bedTargetTemp])
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

    /*
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
    */
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
        var autoscroll = (container.scrollTop() == container[0].scrollHeight - container.height);

        container.text(output);

        if (autoscroll) {
            container.scrollTop(container[0].scrollHeight - container.height())
        }
    }
}

function GcodeFilesViewModel() {
    var self = this;

    self.files = ko.observableArray([]);

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
        self.files(response.files);
    }

    self.loadFile = function() {
        var filename = this.name;
        $.ajax({
            url: AJAX_BASEURL + "gcodefiles/load",
            type: "POST",
            dataType: "json",
            data: {filename: filename}
        })
    }

    self.removeFile = function() {
        var filename = this.name;
        $.ajax({
            url: AJAX_BASEURL + "gcodefiles/delete",
            type: "POST",
            dataType: "json",
            data: {filename: filename},
            success: self.fromResponse
        })
    }
}

function WebcamViewModel() {
    var self = this;

    self.timelapseType = ko.observable(undefined);
    self.timelapseTimedInterval = ko.observable(undefined);
    self.files = ko.observableArray([]);

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

    self.requestData = function() {
        $.ajax({
            url: AJAX_BASEURL + "timelapse",
            type: "GET",
            dataType: "json",
            success: self.fromResponse
        });
    }

    self.fromResponse = function(response) {
        self.timelapseType(response.type)
        self.files(response.files)

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

function DataUpdater(connectionViewModel, printerStateViewModel, temperatureViewModel, speedViewModel, terminalViewModel, webcamViewModel) {
    var self = this;

    self.connectionViewModel = connectionViewModel;
    self.printerStateViewModel = printerStateViewModel;
    self.temperatureViewModel = temperatureViewModel;
    self.terminalViewModel = terminalViewModel;
    self.speedViewModel = speedViewModel;
    self.webcamViewModel = webcamViewModel;

    self._socket = io.connect();
    self._socket.on("connect", function() {
        if ($("#offline_overlay").is(":visible")) {
            $("#offline_overlay").hide();
            self.webcamViewModel.requestData();
        }
    })
    self._socket.on("disconnect", function() {
        // if the updated fails to communicate with the backend, we interpret this as a missing backend
        if (!$("#offline_overlay").is(":visible"))
            $("#offline_overlay").show();
    })
    self._socket.on("history", function(data) {
        self.connectionViewModel.fromHistoryData(data);
        self.printerStateViewModel.fromHistoryData(data);
        self.temperatureViewModel.fromHistoryData(data);
        self.terminalViewModel.fromHistoryData(data);
        self.webcamViewModel.fromHistoryData(data);
    })
    self._socket.on("current", function(data) {
        self.connectionViewModel.fromCurrentData(data);
        self.printerStateViewModel.fromCurrentData(data);
        self.temperatureViewModel.fromCurrentData(data);
        self.terminalViewModel.fromCurrentData(data);
        self.webcamViewModel.fromCurrentData(data);
    })

    self.reconnect = function() {
        self._socket.socket.connect();
    }
}

$(function() {

        //~~ View models
        var connectionViewModel = new ConnectionViewModel();
        var printerStateViewModel = new PrinterStateViewModel();
        var temperatureViewModel = new TemperatureViewModel();
        var speedViewModel = new SpeedViewModel();
        var terminalViewModel = new TerminalViewModel();
        var gcodeFilesViewModel = new GcodeFilesViewModel();
        var webcamViewModel = new WebcamViewModel();
        var dataUpdater = new DataUpdater(connectionViewModel, printerStateViewModel, temperatureViewModel, speedViewModel, terminalViewModel, webcamViewModel);

        //~~ Print job control

        $("#job_print").click(function() {
            $.ajax({
                url: AJAX_BASEURL + "control/print",
                type: "POST",
                dataType: "json",
                success: function(){}
            })
        })
        $("#job_pause").click(function() {
            $("#job_pause").button("toggle");
            $.ajax({
                url: AJAX_BASEURL + "control/pause",
                type: "POST",
                dataType: "json"
            })
        })
        $("#job_cancel").click(function() {
            $.ajax({
                url: AJAX_BASEURL + "control/cancel",
                type: "POST",
                dataType: "json"
            })
        })

        //~~ Temperature control

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

        //~~ Jog controls

        function jogCommand(axis, distance) {
            $.ajax({
                url: AJAX_BASEURL + "control/jog",
                type: "POST",
                dataType: "json",
                data: axis + "=" + distance
            })
        }
        function homeCommand(axis) {
            $.ajax({
                url: AJAX_BASEURL + "control/jog",
                type: "POST",
                dataType: "json",
                data: "home" + axis
            })
        }
        $("#jog_x_inc").click(function() {jogCommand("x", "10")});
        $("#jog_x_dec").click(function() {jogCommand("x", "-10")});
        $("#jog_y_inc").click(function() {jogCommand("y", "10")});
        $("#jog_y_dec").click(function() {jogCommand("y", "-10")});
        $("#jog_z_inc").click(function() {jogCommand("z", "10")});
        $("#jog_z_dec").click(function() {jogCommand("z", "-10")});
        $("#jog_xy_home").click(function() {homeCommand("XY")});
        $("#jog_z_home").click(function() {homeCommand("Z")});

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
                    data: "command=" + command
                })
            }
        })

        //~~ Gcode upload

        $("#gcode_upload").fileupload({
            dataType: "json",
            done: function (e, data) {
                gcodeFilesViewModel.fromResponse(data.result);
            },
            progressall: function (e, data) {
                var progress = parseInt(data.loaded / data.total * 100, 10);
                $("#gcode_upload_progress .bar").css("width", progress + "%");
            }
        });

        //~~ Offline overlay
        $("#offline_overlay_reconnect").click(function() {dataUpdater.reconnect()});

        //~~ knockout.js bindings

        ko.applyBindings(connectionViewModel, document.getElementById("connection"));
        ko.applyBindings(printerStateViewModel, document.getElementById("state"));
        ko.applyBindings(gcodeFilesViewModel, document.getElementById("files"));
        ko.applyBindings(temperatureViewModel, document.getElementById("temp"));
        ko.applyBindings(printerStateViewModel, document.getElementById("jog"));
        ko.applyBindings(terminalViewModel, document.getElementById("term"));
        ko.applyBindings(speedViewModel, document.getElementById("speed"));

        var webcamElement = document.getElementById("webcam");
        if (webcamElement) {
            ko.applyBindings(webcamViewModel, document.getElementById("webcam"));
        }

        //~~ startup commands

        connectionViewModel.requestData();
        gcodeFilesViewModel.requestData();
        webcamViewModel.requestData();

    }
);

