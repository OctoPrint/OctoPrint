$(function() {
    function TemperatureViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settingsViewModel = parameters[1];

        self._createToolEntry = function() {
            return {
                name: ko.observable(),
                key: ko.observable(),
                actual: ko.observable(0),
                target: ko.observable(0),
                offset: ko.observable(0),
                newTarget: ko.observable(),
                newOffset: ko.observable()
            }
        };

        self.tools = ko.observableArray([]);
        self.hasBed = ko.observable(true);
        self.bedTemp = self._createToolEntry();
        self.bedTemp["name"](gettext("Bed"));
        self.bedTemp["key"]("bed");

        self.isErrorOrClosed = ko.observable(undefined);
        self.isOperational = ko.observable(undefined);
        self.isPrinting = ko.observable(undefined);
        self.isPaused = ko.observable(undefined);
        self.isError = ko.observable(undefined);
        self.isReady = ko.observable(undefined);
        self.isLoading = ko.observable(undefined);

        self.temperature_profiles = self.settingsViewModel.temperature_profiles;

        self.heaterOptions = ko.observable({});

        self._numExtrudersUpdated = function() {
            var graphColors = ["red", "orange", "green", "brown", "purple"];
            var heaterOptions = {};
            var tools = self.tools();

            // tools
            var numExtruders = self.settingsViewModel.printerProfiles.currentProfileData().extruder.count();
            if (numExtruders && numExtruders > 1) {
                // multiple extruders
                for (var extruder = 0; extruder < numExtruders; extruder++) {
                    var color = graphColors.shift();
                    if (!color) color = "black";
                    heaterOptions["tool" + extruder] = {name: "T" + extruder, color: color};

                    if (tools.length <= extruder || !tools[extruder]) {
                        tools[extruder] = self._createToolEntry();
                    }
                    tools[extruder]["name"](gettext("Tool") + " " + extruder);
                    tools[extruder]["key"]("tool" + extruder);
                }
            } else {
                // only one extruder, no need to add numbers
                var color = graphColors[0];
                heaterOptions["tool0"] = {name: "T", color: color};

                if (tools.length < 1 || !tools[0]) {
                    tools[0] = self._createToolEntry();
                }
                tools[0]["name"](gettext("Hotend"));
                tools[0]["key"]("tool0");
            }

            // print bed
            heaterOptions["bed"] = {name: gettext("Bed"), color: "blue"};

            // write back
            self.heaterOptions(heaterOptions);
            self.tools(tools);
        };
        self.settingsViewModel.printerProfiles.currentProfileData.subscribe(function() {
            self._numExtrudersUpdated();
            self.settingsViewModel.printerProfiles.currentProfileData().extruder.count.subscribe(self._numExtrudersUpdated);
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
                        return gettext("just now");
                    else
                        return "- " + diffInMins + " " + gettext("min");
                }
            },
            legend: {
                position: "sw",
                noColumns: 2,
                backgroundOpacity: 0
            }
        };

        self.fromCurrentData = function(data) {
            self._processStateData(data.state);
            self._processTemperatureUpdateData(data.temps);
            self._processOffsetData(data.offsets);
        };

        self.fromHistoryData = function(data) {
            self._processStateData(data.state);
            self._processTemperatureHistoryData(data.temps);
            self._processOffsetData(data.offsets);
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

        self._processTemperatureUpdateData = function(data) {
            if (data.length == 0)
                return;

            var lastData = data[data.length - 1];

            var tools = self.tools();
            for (var i = 0; i < tools.length; i++) {
                if (lastData.hasOwnProperty("tool" + i)) {
                    tools[i]["actual"](lastData["tool" + i].actual);
                    tools[i]["target"](lastData["tool" + i].target);
                }
            }

            if (lastData.hasOwnProperty("bed")) {
                self.hasBed(true);
                self.bedTemp["actual"](lastData.bed.actual);
                self.bedTemp["target"](lastData.bed.target);
            } else {
                self.hasBed(false);
            }

            if (!CONFIG_TEMPERATURE_GRAPH) return;

            self.temperatures = self._processTemperatureData(data, self.temperatures);
            _.each(_.keys(self.heaterOptions()), function(d) {
                self.temperatures[d].actual = self.temperatures[d].actual.slice(-300);
                self.temperatures[d].target = self.temperatures[d].target.slice(-300);
            });

            self.updatePlot();
        };

        self._processTemperatureHistoryData = function(data) {
            self.temperatures = self._processTemperatureData(data);
            self.updatePlot();
        };

        self._processOffsetData = function(data) {
            var tools = self.tools();
            for (var i = 0; i < tools.length; i++) {
                if (data.hasOwnProperty("tool" + i)) {
                    tools[i]["offset"](data["tool" + i]);
                }
            }

            if (data.hasOwnProperty("bed")) {
                self.bedTemp["offset"](data["bed"]);
            }
        };

        self._processTemperatureData = function(data, result) {
            var types = _.keys(self.heaterOptions());

            // make sure result is properly initialized
            if (!result) {
                result = {};
            }

            _.each(types, function(type) {
                if (!result.hasOwnProperty(type)) {
                    result[type] = {actual: [], target: []};
                }
                if (!result[type].hasOwnProperty("actual")) result[type]["actual"] = [];
                if (!result[type].hasOwnProperty("target")) result[type]["target"] = [];
            });

            // convert data
            _.each(data, function(d) {
                var time = d.time * 1000;
                _.each(types, function(type) {
                    if (!d[type]) return;
                    result[type].actual.push([time, d[type].actual]);
                    result[type].target.push([time, d[type].target]);

                    self.hasBed(self.hasBed() || (type == "bed"));
                })
            });

            return result;
        };

        self.updatePlot = function() {
            var graph = $("#temperature-graph");
            if (graph.length) {
                var data = [];
                var heaterOptions = self.heaterOptions();
                if (!heaterOptions) return;

                _.each(_.keys(heaterOptions), function(type) {
                    if (type == "bed" && !self.hasBed()) {
                        return;
                    }

                    var actuals = [];
                    var targets = [];

                    if (self.temperatures[type]) {
                        actuals = self.temperatures[type].actual;
                        targets = self.temperatures[type].target;
                    }

                    var actualTemp = actuals && actuals.length ? formatTemperature(actuals[actuals.length - 1][1]) : "-";
                    var targetTemp = targets && targets.length ? formatTemperature(targets[targets.length - 1][1]) : "-";

                    data.push({
                        label: gettext("Actual") + " " + heaterOptions[type].name + ": " + actualTemp,
                        color: heaterOptions[type].color,
                        data: actuals
                    });
                    data.push({
                        label: gettext("Target") + " " + heaterOptions[type].name + ": " + targetTemp,
                        color: pusher.color(heaterOptions[type].color).tint(0.5).html(),
                        data: targets
                    });
                });

                $.plot(graph, data, self.plotOptions);
            }
        };

        self.setTarget = function(item) {
            var value = item.newTarget();
            if (!value) return;

            self._sendToolCommand("target",
                item.key(),
                item.newTarget(),
                function() {item.newTarget("");}
            );
        };

        self.setTargetFromProfile = function(item, profile) {
            if (!profile) return;

            var value = undefined;
            if (item.key() == "bed") {
                value = profile.bed;
            } else {
                value = profile.extruder;
            }

            self._sendToolCommand("target",
                item.key(),
                value,
                function() {item.newTarget("");}
            );
        };

        self.setTargetToZero = function(item) {
            self._sendToolCommand("target",
                item.key(),
                0,
                function() {item.newTarget("");}
            );
        };

        self.setOffset = function(item) {
            self._sendToolCommand("offset",
                item.key(),
                item.newOffset(),
                function() {item.newOffset("");}
            );
        };

        self._sendToolCommand = function(command, type, temp, successCb, errorCb) {
            var data = {
                command: command
            };

            var endpoint;
            if (type == "bed") {
                if ("target" == command) {
                    data["target"] = parseInt(temp);
                } else if ("offset" == command) {
                    data["offset"] = parseInt(temp);
                } else {
                    return;
                }

                endpoint = "bed";
            } else {
                var group;
                if ("target" == command) {
                    group = "targets";
                } else if ("offset" == command) {
                    group = "offsets";
                } else {
                    return;
                }
                data[group] = {};
                data[group][type] = parseInt(temp);

                endpoint = "tool";
            }

            $.ajax({
                url: API_BASEURL + "printer/" + endpoint,
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify(data),
                success: function() { if (successCb !== undefined) successCb(); },
                error: function() { if (errorCb !== undefined) errorCb(); }
            });

        };

        self.handleEnter = function(event, type, item) {
            if (event.keyCode == 13) {
                if (type == "target") {
                    self.setTarget(item);
                } else if (type == "offset") {
                    self.setOffset(item);
                }
            }
        };

        self.onAfterTabChange = function(current, previous) {
            if (current != "#temp") {
                return;
            }
            self.updatePlot();
        }

    }

    OCTOPRINT_VIEWMODELS.push([
        TemperatureViewModel,
        ["loginStateViewModel", "settingsViewModel"],
        "#temp"
    ]);
});