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

    self.fromStateResponse = function(response) {
        self.previousIsOperational = self.isOperational();

        self.isErrorOrClosed(response.closedOrError);
        self.isOperational(response.operational);
        self.isPaused(response.paused);
        self.isPrinting(response.printing);
        self.isError(response.error);
        self.isReady(response.ready);
        self.isLoading(response.loading);

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
var connectionViewModel = new ConnectionViewModel();

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

    self.fromResponse = function(response) {
        self.stateString(response.state);
        self.isErrorOrClosed(response.closedOrError);
        self.isOperational(response.operational);
        self.isPaused(response.paused);
        self.isPrinting(response.printing);
        self.isError(response.error);
        self.isReady(response.ready);
        self.isLoading(response.loading);

        if (response.job) {
            self.filename(response.job.filename);
            self.filament(response.job.filament);
            self.estimatedPrintTime(response.job.estimatedPrintTime);
            self.printTime(response.job.printTime);
            self.printTimeLeft(response.job.printTimeLeft);
            self.currentLine(response.job.line ? response.job.line : 0);
            self.totalLines(response.job.totalLines ? response.job.totalLines : 0);
            self.currentHeight(response.job.currentZ);
        } else {
            if (response.loading && response.gcode) {
                self.filename("Loading... (" + Math.round(response.gcode.progress * 100) + "%)");
            } else {
                self.filename(undefined);
            }
            self.filament(undefined);
            self.estimatedPrintTime(undefined);
            self.printTime(undefined);
            self.printTimeLeft(undefined);
            self.currentLine(undefined);
            self.totalLines(undefined);
            self.currentHeight(undefined);
        }
    }
}
var printerStateViewModel = new PrinterStateViewModel();

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

    self.fromResponse = function(response) {
        self.temp(response.temp);
        self.bedTemp(response.bedTemp);
        self.targetTemp(response.targetTemp);
        self.bedTargetTemp(response.bedTargetTemp);
        self.temperatures = (response.temperatures);

        self.isErrorOrClosed(response.closedOrError);
        self.isOperational(response.operational);
        self.isPaused(response.paused);
        self.isPrinting(response.printing);
        self.isError(response.error);
        self.isReady(response.ready);
        self.isLoading(response.loading);

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
var temperatureViewModel = new TemperatureViewModel();

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

    self.fromResponse = function(response) {
        self.isErrorOrClosed(response.closedOrError);
        self.isOperational(response.operational);
        self.isPaused(response.paused);
        self.isPrinting(response.printing);
        self.isError(response.error);
        self.isReady(response.ready);
        self.isLoading(response.loading);

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
var speedViewModel = new SpeedViewModel();

function TerminalViewModel() {
    var self = this;

    self.log = undefined;

    self.fromResponse = function(response) {
        self.log = response.log;

        self.updateOutput();
    }

    self.updateOutput = function() {
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

    self.sendCommand = function(command) {

    }
}
var terminalViewModel = new TerminalViewModel();

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
var gcodeFilesViewModel = new GcodeFilesViewModel();

function WebcamViewModel() {
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

    self.requestData = function() {
        $.ajax({
            url: AJAX_BASEURL + "timelapse",
            type: "GET",
            dataType: "json",
            success: self.fromResponse
        })
    }

    self.fromResponse = function(response) {
        self.timelapseType(response.type)

        if (response.type == "timed" && response.config && response.config.interval) {
            self.timelapseTimedInterval(response.config.interval)
        } else {
            self.timelapseTimedInterval(undefined)
        }
    }

    self.fromStateResponse = function(response) {
        self.isErrorOrClosed(response.closedOrError);
        self.isOperational(response.operational);
        self.isPaused(response.paused);
        self.isPrinting(response.printing);
        self.isError(response.error);
        self.isReady(response.ready);
        self.isLoading(response.loading);
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
var webcamViewModel = new WebcamViewModel();

function DataUpdater(connectionViewModel, printerStateViewModel, temperatureViewModel, speedViewModel, terminalViewModel, webcamViewModel) {
    var self = this;

    self.updateInterval = 500;
    self.updateIntervalOnError = 10000;
    self.includeTemperatures = true;
    self.includeLogs = true;

    self.connectionViewModel = connectionViewModel;
    self.printerStateViewModel = printerStateViewModel;
    self.temperatureViewModel = temperatureViewModel;
    self.terminalViewModel = terminalViewModel;
    self.speedViewModel = speedViewModel;
    self.webcamViewModel = webcamViewModel;

    self.requestData = function() {
        var parameters = {};

        if (self.includeTemperatures)
            parameters.temperatures = true;
        if (self.includeLogs)
            parameters.log = true;

        $.ajax({
            url: AJAX_BASEURL + "state",
            type: "GET",
            dataType: "json",
            data: parameters,
            success: function(response) {
                if ($("#offline_overlay").is(":visible"))
                    $("#offline_overlay").hide();

                self.printerStateViewModel.fromResponse(response);
                self.connectionViewModel.fromStateResponse(response);
                self.speedViewModel.fromResponse(response);
                self.webcamViewModel.fromStateResponse(response);

                if (response.temperatures)
                    self.temperatureViewModel.fromResponse(response);

                if (response.log)
                    self.terminalViewModel.fromResponse(response);

                setTimeout(self.requestData, self.updateInterval);
            },
            error: function(jqXHR, textState, errorThrows) {
                // if the updated fails to communicate with the backend, we interpret this as a missing backend
                if (!$("#offline_overlay").is(":visible"))
                    $("#offline_overlay").show();
                setTimeout(self.requestData, self.updateIntervalOnError);
            }
        });
    }
}
var dataUpdater = new DataUpdater(connectionViewModel, printerStateViewModel, temperatureViewModel, speedViewModel, terminalViewModel, webcamViewModel);

$(function() {

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
        $("#offline_overlay_reconnect").click(function() {dataUpdater.requestData()});

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

        dataUpdater.requestData();
        connectionViewModel.requestData();
        gcodeFilesViewModel.requestData();
        webcamViewModel.requestData();

    }
);

