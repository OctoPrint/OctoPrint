function PrinterStateViewModel() {
    var self = this;

    self.stateString = ko.observable(undefined);
    self.isErrorOrClosed = ko.observable(undefined);
    self.isOperational = ko.observable(undefined);

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
    })
    self.progress = ko.computed(function() {
        if (!self.currentLine() || !self.totalLines())
            return 0;
        return Math.round(self.currentLine() * 100 / self.totalLines());
    });

    self.connect = function() {
        $.ajax({
            url: AJAX_BASEURL + "control/connect",
            type: 'POST',
            dataType: 'json'
        })
    }

    self.fromResponse = function(response) {
        self.stateString(response.state);
        self.isErrorOrClosed(response.closedOrError);
        self.isOperational(response.operational);

        if (response.job) {
            self.filament(response.job.filament);
            self.estimatedPrintTime(response.job.estimatedPrintTime);
            self.printTime(response.job.printTime);
            self.printTimeLeft(response.job.printTimeLeft);
            self.currentLine(response.job.line ? response.job.line : 0);
            self.totalLines(response.job.totalLines ? response.job.totalLines : 0);
            self.currentHeight(response.job.currentZ);
        } else {
            self.filament(undefined);
            self.estimatedPrintTime(undefined);
            self.printTime(undefined);
            self.printTimeLeft(undefined);
            self.currentLine(undefined);
            self.currentHeight(undefined);
        }
    }
}
var printerStateViewModel = new PrinterStateViewModel();

function TemperatureViewModel() {
    var self = this;

    self.temp = ko.observable(undefined);
    self.bedTemp = ko.observable(undefined);

    self.temperatures = [];
    self.plotOptions = {
        yaxis: {
            min: 0,
            max: 310,
            ticks: 10
        },
        xaxis: {
            mode: "time"
        },
        legend: {
            noColumns: 4
        }
    }

    self.fromResponse = function(response) {
        self.temp(response.currentTemp);
        self.bedTemp(response.currentBedTemp);
        self.temperatures = (response.temperatures);

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

function TerminalViewModel() {
    var self = this;

    self.log = undefined;

    self.fromResponse = function(response) {
        self.log = response.log;

        self.updateOutput();
    }

    self.updateOutput = function() {
        var output = '';
        for (var i = 0; i < self.log.length; i++) {
            output += self.log[i] + '<br>';
        }

        var container = $("#terminal-output");
        var autoscroll = (container.scrollTop() == container[0].scrollHeight - container.height);

        container.html(output);

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

function DataUpdater(printerStateViewModel, temperatureViewModel, terminalViewModel) {
    var self = this;

    self.updateInterval = 500;
    self.includeTemperatures = true;
    self.includeLogs = true;

    self.printerStateViewModel = printerStateViewModel;
    self.temperatureViewModel = temperatureViewModel;
    self.terminalViewModel = terminalViewModel;

    self.requestData = function() {
        var parameters = {};

        if (self.includeTemperatures)
            parameters.temperatures = true;
        if (self.includeLogs)
            parameters.log = true;

        $.ajax({
            url: AJAX_BASEURL + "state",
            type: 'GET',
            dataType: 'json',
            data: parameters,
            success: function(response) {
                self.printerStateViewModel.fromResponse(response);

                if (response.temperatures)
                    self.temperatureViewModel.fromResponse(response);

                if (response.log)
                    self.terminalViewModel.fromResponse(response);
            }
        });

        setTimeout(self.requestData, self.updateInterval);
    }
}
var dataUpdater = new DataUpdater(printerStateViewModel, temperatureViewModel, terminalViewModel);

$(function() {
        $("#printer_connect").click(printerStateViewModel.connect);
        $("#job_print").click(function() {
            $.ajax({
                url: AJAX_BASEURL + "control/print",
                type: 'POST',
                dataType: 'json',
                success: function(){}
            })
        })
        $("#job_pause").click(function() {
            $.ajax({
                url: AJAX_BASEURL + "control/pause",
                type: 'POST',
                dataType: 'json',
                success: function(){}
            })
        })
        $("#job_cancel").click(function() {
            $.ajax({
                url: AJAX_BASEURL + "control/cancel",
                type: 'POST',
                dataType: 'json',
                success: function(){}
            })
        })

        $("#terminal-send").click(function () {
            var command = $("#terminal-command").val();
            $.ajax({
                url: AJAX_BASEURL + "control/command",
                type: 'POST',
                dataType: 'json',
                data: 'command=' + command,
                success: function(response) {
                    // do nothing
                }
            })
        })

        $('#gcode_upload').fileupload({
            dataType: 'json',
            done: function (e, data) {
                gcodeFilesViewModel.fromResponse(data.result);
            },
            acceptFileTypes: /(\.|\/)gcode$/i,
            progressall: function (e, data) {
                var progress = parseInt(data.loaded / data.total * 100, 10);
                $('#gcode_upload_progress .bar').css(
                    'width',
                    progress + '%'
                );
            }
        });

        ko.applyBindings(printerStateViewModel, document.getElementById("state"));
        ko.applyBindings(temperatureViewModel, document.getElementById("temp"));
        ko.applyBindings(terminalViewModel, document.getElementById("term"));
        ko.applyBindings(gcodeFilesViewModel, document.getElementById("files"));

        dataUpdater.requestData();
        $.ajax({
            url: AJAX_BASEURL + "gcodefiles",
            method: 'GET',
            dataType: 'json',
            success: function(response) {
                self.gcodeFilesViewModel.fromResponse(response);
            }
        });
    }
);

