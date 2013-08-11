function TemperatureViewModel(loginStateViewModel, settingsViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;

    self.temp = ko.observable(undefined);
    self.bedTemp = ko.observable(undefined);
    self.targetTemp = ko.observable(undefined);
    self.bedTargetTemp = ko.observable(undefined);

    self.newTemp = ko.observable(undefined);
    self.newBedTemp = ko.observable(undefined);

    self.isErrorOrClosed = ko.observable(undefined);
    self.isOperational = ko.observable(undefined);
    self.isPrinting = ko.observable(undefined);
    self.isPaused = ko.observable(undefined);
    self.isError = ko.observable(undefined);
    self.isReady = ko.observable(undefined);
    self.isLoading = ko.observable(undefined);

    self.temperature_profiles = settingsViewModel.temperature_profiles;

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

    self.setTempFromProfile = function(profile) {
        if (!profile)
            return;
        self._updateTemperature(profile.extruder, "temp");
    }

    self.setTemp = function() {
        self._updateTemperature(self.newTemp(), "temp", function(){self.targetTemp(self.newTemp()); self.newTemp("");});
    };

    self.setBedTempFromProfile = function(profile) {
        self._updateTemperature(profile.bed, "bedTemp");
    }

    self.setBedTemp = function() {
        self._updateTemperature(self.newBedTemp(), "bedTemp", function() {self.bedTargetTemp(self.newBedTemp()); self.newBedTemp("");});
    };

    self._updateTemperature = function(temp, type, callback) {
        var data = {};
        data[type] = temp;

        $.ajax({
            url: AJAX_BASEURL + "control/temperature",
            type: "POST",
            dataType: "json",
            data: data,
            success: function() { if (callback !== undefined) callback(); }
        })
    }

    self.handleEnter = function(event, type) {
        if (event.keyCode == 13) {
            if (type == "temp") {
                self.setTemp();
            } else if (type == "bedTemp") {
                self.setBedTemp();
            }
        }
    }
}
