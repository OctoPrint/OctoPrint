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
        self.temperature_cutoff = self.settingsViewModel.temperature_cutoff;

        self.heaterOptions = ko.observable({});

        self._printerProfileInitialized = false;
        self._currentTemperatureDataBacklog = [];
        self._historyTemperatureDataBacklog = [];

        self._printerProfileUpdated = function() {
            var graphColors = ["red", "orange", "green", "brown", "purple"];
            var heaterOptions = {};
            var tools = self.tools();
            var color;

            // tools
            var currentProfileData = self.settingsViewModel.printerProfiles.currentProfileData();
            var numExtruders = (currentProfileData ? currentProfileData.extruder.count() : 0);
            var sharedNozzle = (currentProfileData ? currentProfileData.extruder.sharedNozzle() : false);
            if (numExtruders && numExtruders > 1 && !sharedNozzle) {
                // multiple extruders
                for (var extruder = 0; extruder < numExtruders; extruder++) {
                    color = graphColors.shift();
                    if (!color) color = "black";
                    heaterOptions["tool" + extruder] = {name: "T" + extruder, color: color};

                    if (tools.length <= extruder || !tools[extruder]) {
                        tools[extruder] = self._createToolEntry();
                    }
                    tools[extruder]["name"](gettext("Tool") + " " + extruder);
                    tools[extruder]["key"]("tool" + extruder);
                }
            } else if (numExtruders == 1 || sharedNozzle) {
                // only one extruder, no need to add numbers
                color = graphColors[0];
                heaterOptions["tool0"] = {name: "T", color: color};

                if (tools.length < 1 || !tools[0]) {
                    tools[0] = self._createToolEntry();
                }
                tools[0]["name"](gettext("Hotend"));
                tools[0]["key"]("tool0");
            }

            // print bed
            if (currentProfileData && currentProfileData.heatedBed()) {
                self.hasBed(true);
                heaterOptions["bed"] = {name: gettext("Bed"), color: "blue"};
            } else {
                self.hasBed(false);
            }

            // write back
            self.heaterOptions(heaterOptions);
            self.tools(tools);

            if (!self._printerProfileInitialized) {
                self._triggerBacklog();
            }
            self.updatePlot(false);
        };
        self.settingsViewModel.printerProfiles.currentProfileData.subscribe(function() {
            self._printerProfileUpdated();
            self.settingsViewModel.printerProfiles.currentProfileData().extruder.count.subscribe(self._printerProfileUpdated);
            self.settingsViewModel.printerProfiles.currentProfileData().heatedBed.subscribe(self._printerProfileUpdated);
        });

        self.temperatures = [];

        self.plot = undefined;
        self.plotHoverPos = undefined;
        self.plotLegendTimeout = undefined;

        self.fromCurrentData = function(data) {
            self._processStateData(data.state);
            if (!self._printerProfileInitialized) {
                self._currentTemperatureDataBacklog.push(data);
            } else {
                self._processTemperatureUpdateData(data.serverTime, data.temps);
            }
            self._processOffsetData(data.offsets);
        };

        self.fromHistoryData = function(data) {
            self._processStateData(data.state);
            if (!self._printerProfileInitialized) {
                self._historyTemperatureDataBacklog.push(data);
            } else {
                self._processTemperatureHistoryData(data.serverTime, data.temps);
            }
            self._processOffsetData(data.offsets);
        };

        self._triggerBacklog = function() {
            _.each(self._historyTemperatureDataBacklog, function(data) {
                self._processTemperatureHistoryData(data.serverTime, data.temps);
            });
            _.each(self._currentTemperatureDataBacklog, function(data) {
                self._processTemperatureUpdateData(data.serverTime, data.temps);
            });
            self._historyTemperatureDataBacklog = [];
            self._currentTemperatureDataBacklog = [];
            self._printerProfileInitialized = true;
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

        self._processTemperatureUpdateData = function(serverTime, data) {
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
                self.bedTemp["actual"](lastData.bed.actual);
                self.bedTemp["target"](lastData.bed.target);
            }

            if (!CONFIG_TEMPERATURE_GRAPH) return;

            self.temperatures = self._processTemperatureData(serverTime, data, self.temperatures);
            self.updatePlot(false);
        };

        self._processTemperatureHistoryData = function(serverTime, data) {
            self.temperatures = self._processTemperatureData(serverTime, data);
            self.updatePlot(false);
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

        self._processTemperatureData = function(serverTime, data, result) {
            var types = _.keys(self.heaterOptions());
            var clientTime = Date.now();

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
                var timeDiff = (serverTime - d.time) * 1000;
                var time = clientTime - timeDiff;
                _.each(types, function(type) {
                    if (!d[type]) return;
                    result[type].actual.push([time, d[type].actual]);
                    result[type].target.push([time, d[type].target]);
                })
            });

            var temperature_cutoff = self.temperature_cutoff();
            if (temperature_cutoff != undefined) {
                var filterOld = function(item) {
                    return item[0] >= clientTime - temperature_cutoff * 60 * 1000;
                };

                _.each(_.keys(self.heaterOptions()), function(d) {
                    result[d].actual = _.filter(result[d].actual, filterOld);
                    result[d].target = _.filter(result[d].target, filterOld);
                });
            }

            return result;
        };

        self.updatePlot = function(force) {
            force = force == undefined ? true : force;

            var graph = $("#temperature-graph");
            if (graph.length) {
                var data = [];
                var heaterOptions = self.heaterOptions();
                if (!heaterOptions) return;

                var maxTemps = [310/1.1];

                var showFahrenheit = self._shallShowFahrenheit();

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

                    var actualTemp = actuals && actuals.length ? formatTemperature(actuals[actuals.length - 1][1], showFahrenheit) : "-";
                    var targetTemp = targets && targets.length ? formatTemperature(targets[targets.length - 1][1], showFahrenheit) : "-";

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

                    maxTemps.push(self.getMaxTemp(actuals, targets));
                });

                if (!self.plot || force) {
                    // we don't have a plot yet, we need to set stuff up
                    var options = {
                        yaxis: {
                            min: 0,
                            max: Math.max(Math.max.apply(null, maxTemps) * 1.1, 310),
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

                    if (!OctoPrint.coreui.browser.mobile) {
                        options["crosshair"] = { mode: "x" };
                        options["grid"] = { hoverable: true, autoHighlight: false };
                    }

                    self.plot = $.plot(graph, data, options);

                } else {
                    // graph already active, let's just update the data
                    self.plot.setData(data);
                    self.plot.getAxes().yaxis.max = Math.max(Math.max.apply(null, maxTemps) * 1.1, 310);
                    self.updateLegend(self._replaceLegendLabel);
                    self.plot.draw();
                }
            }
        };

        self.updateLegend = function(replaceLegendLabel) {
            self.plotLegendTimeout = undefined;

            var resetLegend = function() {
                _.each(dataset, function(series, index) {
                    var value = series.data && series.data.length ? series.data[series.data.length - 1][1] : undefined;
                    replaceLegendLabel(index, series, value);
                });
            };

            var pos = self.plotHoverPos;
            if (pos && !OctoPrint.coreui.browser.mobile) {
                // we got a hover position, let's see what we need to do with that

                var i;
                var axes = self.plot.getAxes();
                var dataset = self.plot.getData();

                if (pos.x < axes.xaxis.min || pos.x > axes.xaxis.max ||
                    pos.y < axes.yaxis.min || pos.y > axes.yaxis.max) {
                    // position outside of the graph, show latest temperature in legend
                    resetLegend();
                } else {
                    // position inside the graph, determine temperature at point and display that in the legend
                    _.each(dataset, function(series, index) {
                        for (i = 0; i < series.data.length; i++) {
                            if (series.data[i][0] > pos.x) {
                                break;
                            }
                        }

                        var y;
                        var p1 = series.data[i - 1];
                        var p2 = series.data[i];

                        if (p1 === undefined && p2 === undefined) {
                            y = undefined;
                        } else if (p1 === undefined) {
                            y = p2[1];
                        } else if (p2 === undefined) {
                            y = p1[1];
                        } else {
                            y = p1[1] + (p2[1] - p1[1]) * (pos.x - p1[0]) / (p2[0] - p1[0]);
                        }

                        replaceLegendLabel(index, series, y, true);
                    });
                }
            } else {
                resetLegend();
            }

            // update the grid
            self.plot.setupGrid();
        };

        self.getMaxTemp = function(actuals, targets) {
            var pair;
            var maxTemp = 0;
            actuals.forEach(function(pair) {
                if (pair[1] > maxTemp){
                    maxTemp = pair[1];
                }
            });
            targets.forEach(function(pair) {
                if (pair[1] > maxTemp){
                    maxTemp = pair[1];
                }
            });
            return maxTemp;
        };

        self.setTarget = function(item) {
            var value = item.newTarget();
            if (!value) return;

            var onSuccess = function() {
                item.newTarget("");
            };

            if (item.key() == "bed") {
                self._setBedTemperature(value)
                    .done(onSuccess);
            } else {
                self._setToolTemperature(item.key(), value)
                    .done(onSuccess);
            }
        };

        self.setTargetFromProfile = function(item, profile) {
            if (!profile) return;

            var onSuccess = function() {
                item.newTarget("");
            };

            if (item.key() == "bed") {
                self._setBedTemperature(profile.bed)
                    .done(onSuccess);
            } else {
                self._setToolTemperature(item.key(), profile.extruder)
                    .done(onSuccess);
            }
        };

        self.setTargetToZero = function(item) {
            var onSuccess = function() {
                item.newTarget("");
            };

            if (item.key() == "bed") {
                self._setBedTemperature(0)
                    .done(onSuccess);
            } else {
                self._setToolTemperature(item.key(), 0)
                    .done(onSuccess);
            }
        };

        self.setOffset = function(item) {
            var value = item.newOffset();
            if (!value) return;

            var onSuccess = function() {
                item.newOffset("");
            };

            if (item.key() == "bed") {
                self._setBedOffset(value)
                    .done(onSuccess);
            } else {
                self._setToolOffset(item.key(), value)
                    .done(onSuccess);
            }
        };

        self._setToolTemperature = function(tool, temperature) {
            var data = {};
            data[tool] = parseInt(temperature);
            return OctoPrint.printer.setToolTargetTemperatures(data);
        };

        self._setToolOffset = function(tool, offset) {
            var data = {};
            data[tool] = parseInt(offset);
            return OctoPrint.printer.setToolTemperatureOffsets(data);
        };

        self._setBedTemperature = function(temperature) {
            return OctoPrint.printer.setBedTargetTemperature(parseInt(temperature));
        };

        self._setBedOffset = function(offset) {
            return OctoPrint.printer.setBedTemperatureOffset(parseInt(offset));
        };

        self._replaceLegendLabel = function(index, series, value, emph) {
            var showFahrenheit = self._shallShowFahrenheit();

            var temp = formatTemperature(value, showFahrenheit);
            if (emph) {
                temp = "<em>" + temp + "</em>";
            }
            series.label = series.label.replace(/:.*/, ": " + temp);
        };

        self._shallShowFahrenheit = function() {
            return (self.settingsViewModel.settings !== undefined )
                   ? self.settingsViewModel.settings.appearance.showFahrenheitAlso()
                   : false;
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
            self.updatePlot(false);
        };

        self.onStartup = function() {
            var graph = $("#temperature-graph");
            if (graph.length && !OctoPrint.coreui.browser.mobile) {
                graph.bind("plothover",  function (event, pos, item) {
                    self.plotHoverPos = pos;
                    if (!self.plotLegendTimeout) {
                        self.plotLegendTimeout = window.setTimeout(function() {
                            self.updateLegend(self._replaceLegendLabel)
                        }, 50);
                    }
                });
            }
        };

        self.onStartupComplete = function() {
            self._printerProfileUpdated();
        };

    }

    OCTOPRINT_VIEWMODELS.push([
        TemperatureViewModel,
        ["loginStateViewModel", "settingsViewModel"],
        "#temp"
    ]);
});
