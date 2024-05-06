$(function () {
    function TemperatureViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settingsViewModel = parameters[1];
        self.access = parameters[2];
        self.printerState = parameters[3];

        self._createToolEntry = function () {
            var entry = {
                name: ko.observable(),
                key: ko.observable(),
                actual: ko.observable(0),
                target: ko.observable(0),
                offset: ko.observable(0),
                newTarget: ko.observable(),
                newOffset: ko.observable()
            };

            entry.newTargetValid = ko.pureComputed(function () {
                var value = entry.newTarget();

                try {
                    value = parseInt(value);
                } catch (exc) {
                    return false;
                }

                return value >= 0 && value <= 999;
            });

            entry.newOffsetValid = ko.pureComputed(function () {
                var value = entry.newOffset();

                try {
                    value = parseInt(value);
                } catch (exc) {
                    return false;
                }

                return -50 <= value <= 50;
            });

            entry.offset.subscribe(function (newValue) {
                if (
                    self.changingOffset.item !== undefined &&
                    self.changingOffset.item.key() === entry.key()
                ) {
                    // if our we currently have the offset dialog open for this entry and the offset changed
                    // meanwhile, update the displayed value in the dialog
                    self.changingOffset.offset(newValue);
                }
            });

            return entry;
        };

        self.changingOffset = {
            offset: ko.observable(0),
            newOffset: ko.observable(0),
            name: ko.observable(""),
            item: undefined,

            title: ko.pureComputed(function () {
                return _.sprintf(gettext("Changing Offset of %(name)s"), {
                    name: _.escape(self.changingOffset.name())
                });
            }),
            description: ko.pureComputed(function () {
                return _.sprintf(
                    gettext(
                        'Use the form below to specify a new offset to apply to all temperature commands sent from printed files for "%(name)s"'
                    ),
                    {name: _.escape(self.changingOffset.name())}
                );
            })
        };
        self.changeOffsetDialog = undefined;

        // TODO: find some nicer way to update plot AFTER graph becomes visible
        self.loginStateSubscription = undefined;

        self.tools = ko.observableArray([]);
        self.hasTools = ko.pureComputed(function () {
            return self.tools().length > 0;
        });
        self.hasBed = ko.observable(true);
        self.hasChamber = ko.observable(false);

        self.visible = ko.pureComputed(function () {
            return self.hasTools() || self.hasBed();
        });

        self.bedTemp = self._createToolEntry();
        self.bedTemp["name"](gettext("Bed"));
        self.bedTemp["key"]("bed");

        self.chamberTemp = self._createToolEntry();
        self.chamberTemp["name"](gettext("Chamber"));
        self.chamberTemp["key"]("chamber");

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

        self._graphUpdater = undefined;

        self._printerProfileUpdated = function () {
            var graphColors = ["red", "orange", "green", "brown", "purple"];
            var heaterOptions = {};
            var tools = [];
            var color;

            // make sure we only update if we have a printer profile loaded
            const currentProfileData =
                self.settingsViewModel.printerProfiles.currentProfileData();
            if (!currentProfileData) return;

            // tools
            var numExtruders = currentProfileData
                ? currentProfileData.extruder.count()
                : 0;
            var sharedNozzle = currentProfileData
                ? currentProfileData.extruder.sharedNozzle()
                : false;
            if (numExtruders && numExtruders > 1 && !sharedNozzle) {
                // multiple extruders
                for (var extruder = 0; extruder < numExtruders; extruder++) {
                    color = graphColors.shift();
                    if (!color) color = "black";
                    heaterOptions["tool" + extruder] = {
                        name: "T" + extruder,
                        color: color
                    };

                    if (tools.length <= extruder || !tools[extruder]) {
                        tools[extruder] = self._createToolEntry();
                    }
                    tools[extruder]["name"](gettext("Tool") + " " + extruder);
                    tools[extruder]["key"]("tool" + extruder);
                }
            } else if (numExtruders === 1 || sharedNozzle) {
                // only one extruder, no need to add numbers
                color = graphColors[0];
                heaterOptions["tool0"] = {name: "T", color: color};

                if (tools.length < 1 || !tools[0]) {
                    tools[0] = self._createToolEntry();
                }
                tools[0]["name"](gettext("Tool"));
                tools[0]["key"]("tool0");
            }

            // print bed
            if (currentProfileData && currentProfileData.heatedBed()) {
                self.hasBed(true);
                heaterOptions["bed"] = {name: gettext("Bed"), color: "blue"};
            } else {
                self.hasBed(false);
            }

            // heated chamber
            if (currentProfileData && currentProfileData.heatedChamber()) {
                self.hasChamber(true);
                heaterOptions["chamber"] = {name: gettext("Chamber"), color: "black"};
            } else {
                self.hasChamber(false);
            }

            // write back
            self.heaterOptions(heaterOptions);
            self.tools(tools);

            if (!self._printerProfileInitialized) {
                self._triggerBacklog();
            }
            self.updatePlot();
        };

        self.settingsViewModel.printerProfiles.currentProfileData.subscribe(function () {
            self._printerProfileUpdated();
            self.settingsViewModel.printerProfiles
                .currentProfileData()
                .extruder.count.subscribe(self._printerProfileUpdated);
            self.settingsViewModel.printerProfiles
                .currentProfileData()
                .extruder.sharedNozzle.subscribe(self._printerProfileUpdated);
            self.settingsViewModel.printerProfiles
                .currentProfileData()
                .heatedBed.subscribe(self._printerProfileUpdated);
            self.settingsViewModel.printerProfiles
                .currentProfileData()
                .heatedChamber.subscribe(self._printerProfileUpdated);
        });

        self.markings = [];

        self.showStateMarks = ko.observable(
            loadFromLocalStorage("temperatureGraph.showStateMarks", true)
        );
        self.showStateMarks.subscribe(function (newValue) {
            saveToLocalStorage("temperatureGraph.showStateMarks", newValue);
            self.updatePlot();
        });

        self.toggleStateMarks = function () {
            self.showStateMarks(!self.showStateMarks());
        };

        self.temperatures = [];

        self.plot = undefined;
        self.plotHoverPos = undefined;
        self.plotLegendTimeout = undefined;

        self.fromCurrentData = function (data) {
            self.markings = data.markings;
            self._processStateData(data.state);
            if (!self._printerProfileInitialized) {
                self._currentTemperatureDataBacklog.push(data);
            } else {
                self._processTemperatureUpdateData(data.serverTime, data.temps);
            }
            self._processOffsetData(data.offsets);
        };

        self.fromHistoryData = function (data) {
            self.markings = data.markings;
            self._processStateData(data.state);
            if (!self._printerProfileInitialized) {
                self._historyTemperatureDataBacklog.push(data);
            } else {
                self._processTemperatureHistoryData(data.serverTime, data.temps);
            }
            self._processOffsetData(data.offsets);
        };

        self._triggerBacklog = function () {
            _.each(self._historyTemperatureDataBacklog, function (data) {
                self._processTemperatureHistoryData(data.serverTime, data.temps);
            });
            _.each(self._currentTemperatureDataBacklog, function (data) {
                self._processTemperatureUpdateData(data.serverTime, data.temps);
            });
            self._historyTemperatureDataBacklog = [];
            self._currentTemperatureDataBacklog = [];
            self._printerProfileInitialized = true;
        };

        self._processStateData = function (data) {
            self.isErrorOrClosed(data.flags.closedOrError);
            self.isOperational(data.flags.operational);
            self.isPaused(data.flags.paused);
            self.isPrinting(data.flags.printing);
            self.isError(data.flags.error);
            self.isReady(data.flags.ready);
            self.isLoading(data.flags.loading);
        };

        self._processTemperatureUpdateData = function (serverTime, data) {
            if (data.length === 0) return;

            var lastData = data[data.length - 1];

            var tools = self.tools();
            for (var i = 0; i < tools.length; i++) {
                if (lastData.hasOwnProperty("tool" + i)) {
                    tools[i]["actual"](lastData["tool" + i].actual);
                    tools[i]["target"](lastData["tool" + i].target);
                } else {
                    tools[i]["actual"](0);
                    tools[i]["target"](0);
                }
            }

            if (lastData.hasOwnProperty("bed")) {
                self.bedTemp["actual"](lastData.bed.actual);
                self.bedTemp["target"](lastData.bed.target);
            } else {
                self.bedTemp["actual"](0);
                self.bedTemp["target"](0);
            }

            if (lastData.hasOwnProperty("chamber")) {
                self.chamberTemp["actual"](lastData.chamber.actual);
                self.chamberTemp["target"](lastData.chamber.target);
            } else {
                self.chamberTemp["actual"](0);
                self.chamberTemp["target"](0);
            }

            if (!CONFIG_TEMPERATURE_GRAPH) return;

            self.temperatures = self._processTemperatureData(
                serverTime,
                data,
                self.temperatures
            );
            self.updatePlot();
        };

        self._processTemperatureHistoryData = function (serverTime, data) {
            self.temperatures = self._processTemperatureData(serverTime, data);
            self.updatePlot();
        };

        self._processOffsetData = function (data) {
            var tools = self.tools();
            for (var i = 0; i < tools.length; i++) {
                if (data.hasOwnProperty("tool" + i)) {
                    tools[i]["offset"](data["tool" + i]);
                } else {
                    tools[i]["offset"](0);
                }
            }

            if (data.hasOwnProperty("bed")) {
                self.bedTemp["offset"](data["bed"]);
            } else {
                self.bedTemp["offset"](0);
            }

            if (data.hasOwnProperty("chamber")) {
                self.chamberTemp["offset"](data["chamber"]);
            } else {
                self.chamberTemp["offset"](0);
            }
        };

        self._processTemperatureData = function (serverTime, data, result) {
            var types = _.keys(self.heaterOptions());
            var clientTime = Date.now();

            // make sure result is properly initialized
            if (!result) {
                result = {};
            }

            _.each(types, function (type) {
                if (!result.hasOwnProperty(type)) {
                    result[type] = {actual: [], target: []};
                }
                if (!result[type].hasOwnProperty("actual")) result[type]["actual"] = [];
                if (!result[type].hasOwnProperty("target")) result[type]["target"] = [];
            });

            // convert data
            _.each(data, function (d) {
                var timeDiff = (serverTime - d.time) * 1000;
                var time = clientTime - timeDiff;
                _.each(types, function (type) {
                    if (!d[type]) return;
                    result[type].actual.push([time, d[type].actual]);
                    result[type].target.push([time, d[type].target]);
                });
            });

            var temperature_cutoff = self.temperature_cutoff();
            if (temperature_cutoff !== undefined) {
                const minTime = clientTime - temperature_cutoff * 60 * 1000;

                var filterOld = function (item) {
                    return item[0] >= minTime;
                };

                _.each(_.keys(self.heaterOptions()), function (d) {
                    const actualLen = result[d].actual.length;
                    result[d].actual = _.filter(result[d].actual, filterOld);
                    if (actualLen && result[d].actual.length <= actualLen) {
                        result[d].actual.unshift([minTime, undefined]);
                    }

                    const targetLen = result[d].target.length;
                    result[d].target = _.filter(result[d].target, filterOld);
                    if (targetLen && result[d].target.length <= targetLen) {
                        result[d].target.unshift([minTime, undefined]);
                    }
                });
            }

            return result;
        };

        self.profileText = function (heater, profile) {
            var text = gettext("Set %(name)s (%(value)s)");

            var format = function (temp) {
                if (temp === 0 || temp === undefined || temp === null) {
                    return gettext("Off");
                } else {
                    return "" + temp + "°C";
                }
            };

            var value;
            if (heater === "all") {
                value = gettext("Tool") + ": %(extruder)s";
                if (self.hasBed()) {
                    value += "/" + gettext("Bed") + ": %(bed)s";
                }
                if (self.hasChamber()) {
                    value += "/" + gettext("Chamber") + ": %(chamber)s";
                }
                value = _.sprintf(value, {
                    extruder: format(profile.extruder),
                    bed: format(profile.bed),
                    chamber: format(profile.chamber)
                });
            } else if (heater.key() === "bed") {
                value = format(profile.bed);
            } else if (heater.key() === "chamber") {
                value = format(profile.chamber);
            } else {
                value = format(profile.extruder);
            }

            return _.sprintf(text, {
                name: _.escape(profile.name),
                value: _.escape(value)
            });
        };

        self.updatePlot = function () {
            var graph = $("#temperature-graph");
            if (!graph.length) return; // no graph
            if (!self.plot) return; // plot not yet initialized

            var plotInfo = self._getPlotInfo();
            if (plotInfo === undefined) return;

            var newMax = Math.max(Math.max.apply(null, plotInfo.max) * 1.1, 310);
            if (newMax !== self.plot.getAxes().yaxis.max) {
                // re-init (because flot apparently has NO way to change the max value of an axes :/)
                self._initializePlot(true, plotInfo);
            } else {
                // update the data
                self.plot.setData(plotInfo.data);
                self.plot.setupGrid();
                self.updateLegend(self._replaceLegendLabel);
                self.plot.draw();
            }
        };

        self._drawMarkings = function () {
            var graph = $("#temperature-graph");
            if (!self.plot) {
                return [];
            }

            $(".temperature-mark-label").remove();

            if (!self.showStateMarks()) {
                return [];
            }

            var graphWidth = self.plot.width();
            var yAxisLabelWidth = 40;
            var markingsLabelMargin = 0;
            var lineWidth = 2;

            var marks = self.markings.map(function (mark) {
                var time = parseInt(mark.time * 1000);
                var o = self.plot.pointOffset({
                    x: time,
                    y: self.plot.getAxes().yaxis.max
                });

                var markLabel = mark.type;
                if (mark.label) {
                    markLabel = gettext(mark.label);
                }

                // we create the label even if we don't show it so that we can query its
                // background color (see #4761)
                var label = $("<div></div>");
                label.html(markLabel);
                label.addClass("temperature-mark-label");
                label.addClass("temperature-mark-type-" + mark.type);

                if (o.left > yAxisLabelWidth) {
                    graph.append(label);

                    // draw markings label on the left if doesn't fit on the right
                    if (
                        o.left >
                        graphWidth +
                            yAxisLabelWidth -
                            label.outerHeight() -
                            markingsLabelMargin
                    ) {
                        label.css(
                            "left",
                            o.left - label.outerHeight() - markingsLabelMargin + "px"
                        );
                        label.css("border-radius", "5px 0 0 0");
                    } else {
                        label.css("left", o.left + markingsLabelMargin + "px");
                        label.css("border-radius", "0 0 0 5px");
                    }

                    // set top position
                    label.css("top", o.top + label.outerWidth() + "px");
                }

                return {
                    color: label.css("background-color"),
                    lineWidth: lineWidth,
                    xaxis: {from: time, to: time}
                };
            });

            return marks;
        };

        // Dummy translation requests for dynamic strings supplied by the backend
        // noinspection BadExpressionStatementJS
        [
            // mark labels
            gettext("Start"),
            gettext("Done"),
            gettext("Cancel"),
            gettext("Pause"),
            gettext("Resume"),
            gettext("Connected"),
            gettext("Disconnected")
        ];

        self._initializePlot = function (force, plotInfo) {
            var graph = $("#temperature-graph");
            if (!graph.length) return; // no graph
            if (self.plot && !force) return; // already initialized

            plotInfo = plotInfo || self._getPlotInfo();
            if (plotInfo === undefined) return;

            // we don't have a plot yet, we need to set stuff up
            var options = {
                yaxis: {
                    min: 0,
                    max: Math.max(Math.max.apply(null, plotInfo.max) * 1.1, 310),
                    ticks: 10,
                    tickFormatter: (val, axis) => {
                        if (val === undefined || val === 0) return "";
                        return val + "°C";
                    }
                },
                xaxis: {
                    mode: "time",
                    ticks: (axis) => {
                        if (
                            axis.max === undefined ||
                            axis.min === undefined ||
                            axis.datamax === axis.datamin
                        )
                            return [];

                        let tickSize = 5 * 60 * 1000; // 5 minutes
                        while ((axis.max - axis.min) / tickSize > 10) {
                            tickSize += 5 * 60 * 1000; // 5 minutes
                        }

                        const ticks = [];
                        let val = axis.max;
                        while (val > axis.min) {
                            ticks.push(val);
                            val -= tickSize;
                        }
                        return ticks;
                    },
                    tickFormatter: (val, axis) => {
                        // current time in milliseconds in UTC
                        var timestampUtc = Date.now();

                        // calculate difference in milliseconds
                        var diff = timestampUtc - val;

                        // convert to minutes
                        var diffInMins = Math.round(diff / (60 * 1000));
                        if (diffInMins < 0) {
                            // we can't look into the future
                            return "";
                        } else if (diffInMins === 0) {
                            return gettext("now");
                        } else {
                            return "-" + diffInMins + gettext("min");
                        }
                    }
                },
                legend: {
                    position: "sw",
                    noColumns: 2,
                    backgroundOpacity: 0
                }
            };

            if (!OctoPrint.coreui.browser.mobile) {
                options["crosshair"] = {mode: "x"};
                options["grid"] = {
                    hoverable: true,
                    autoHighlight: false,
                    markings: self._drawMarkings
                };
            }

            self.plot = $.plot(graph, plotInfo.data, options);
        };

        self._getPlotInfo = function () {
            var data = [];
            var heaterOptions = self.heaterOptions();
            if (!heaterOptions) return undefined;

            var maxTemps = [310 / 1.1];
            var now = Date.now();

            var showFahrenheit = self._shallShowFahrenheit();

            _.each(_.keys(heaterOptions), function (type) {
                if (type === "bed" && !self.hasBed()) {
                    return;
                }

                var actuals = [];
                var targets = [];

                if (self.temperatures[type]) {
                    actuals = self.temperatures[type].actual;
                    targets = self.temperatures[type].target;
                }

                var actualTemp =
                    actuals && actuals.length
                        ? formatTemperature(
                              actuals[actuals.length - 1][1],
                              showFahrenheit
                          )
                        : "-";
                var targetTemp =
                    targets && targets.length
                        ? formatTemperature(
                              targets[targets.length - 1][1],
                              showFahrenheit,
                              1
                          )
                        : "-";

                data.push({
                    label:
                        gettext("Actual") +
                        " " +
                        heaterOptions[type].name +
                        ": " +
                        actualTemp,
                    color: heaterOptions[type].color,
                    data: actuals.length ? actuals : [[now, undefined]]
                });
                data.push({
                    label:
                        gettext("Target") +
                        " " +
                        heaterOptions[type].name +
                        ": " +
                        targetTemp,
                    color: pusher.color(heaterOptions[type].color).tint(0.5).html(),
                    data: targets.length ? targets : [[now, undefined]],
                    dashes: {show: true}
                });

                maxTemps.push(self.getMaxTemp(actuals, targets));
            });

            return {max: maxTemps, data: data};
        };

        self.updateLegend = function (replaceLegendLabel) {
            self.plotLegendTimeout = undefined;

            var resetLegend = function () {
                _.each(dataset, function (series, index) {
                    var value =
                        series.data && series.data.length
                            ? series.data[series.data.length - 1][1]
                            : undefined;
                    replaceLegendLabel(index, series, value);
                });
            };

            var pos = self.plotHoverPos;
            if (pos && !OctoPrint.coreui.browser.mobile) {
                // we got a hover position, let's see what we need to do with that

                var i;
                var axes = self.plot.getAxes();
                var dataset = self.plot.getData();

                if (
                    pos.x < axes.xaxis.min ||
                    pos.x > axes.xaxis.max ||
                    pos.y < axes.yaxis.min ||
                    pos.y > axes.yaxis.max
                ) {
                    // position outside of the graph, show latest temperature in legend
                    resetLegend();
                } else {
                    // position inside the graph, determine temperature at point and display that in the legend
                    _.each(dataset, function (series, index) {
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
                            y =
                                p1[1] +
                                ((p2[1] - p1[1]) * (pos.x - p1[0])) / (p2[0] - p1[0]);
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

        self.getMaxTemp = function (actuals, targets) {
            var maxTemp = 0;
            actuals.forEach(function (pair) {
                if (pair[1] > maxTemp) {
                    maxTemp = pair[1];
                }
            });
            targets.forEach(function (pair) {
                if (pair[1] > maxTemp) {
                    maxTemp = pair[1];
                }
            });
            return maxTemp;
        };

        self.incrementTarget = function (item) {
            var value = item.newTarget();
            if (
                value === undefined ||
                (typeof value === "string" && value.trim() === "")
            ) {
                value = item.target();
            }
            try {
                value = parseInt(value);
                if (value > 999) return;
                item.newTarget(value + 1);
                self.autosendTarget(item);
            } catch (ex) {
                // do nothing
            }
        };

        self.decrementTarget = function (item) {
            var value = item.newTarget();
            if (
                value === undefined ||
                (typeof value === "string" && value.trim() === "")
            ) {
                value = item.target();
            }
            try {
                value = parseInt(value);
                if (value <= 0) return;
                item.newTarget(value - 1);
                self.autosendTarget(item);
            } catch (ex) {
                // do nothing
            }
        };

        var _sendTimeout = {};

        self.autosendTarget = function (item) {
            if (!self.settingsViewModel.temperature_sendAutomatically()) return;
            var delay =
                self.settingsViewModel.temperature_sendAutomaticallyAfter() * 1000;

            var name = item.name();
            if (_sendTimeout[name]) {
                window.clearTimeout(_sendTimeout[name]);
            }
            _sendTimeout[name] = window.setTimeout(function () {
                self.setTarget(item);
                delete _sendTimeout[name];
            }, delay);
        };

        self.clearAutosendTarget = function (item) {
            var name = item.name();
            if (_sendTimeout[name]) {
                window.clearTimeout(_sendTimeout[name]);
                delete _sendTimeout[name];
            }
        };

        self.setTarget = function (item, form) {
            var value = item.newTarget();
            if (form !== undefined) {
                $(form).find("input").blur();
            }
            if (value === undefined || (typeof value === "string" && value.trim() === ""))
                return OctoPrintClient.createRejectedDeferred();

            self.clearAutosendTarget(item);
            return self.setTargetToValue(item, value);
        };

        // Wrapper of self.setTargetFromProfile() to apply all the temperature from a temperature profile
        self.setTargetsFromProfile = function (temperatureProfile) {
            if (temperatureProfile === undefined) {
                console.log("temperatureProfile is undefined!");
                return;
            }

            if (self.hasBed()) {
                self.setTargetFromProfile(self.bedTemp, temperatureProfile);
            }

            if (self.hasChamber()) {
                self.setTargetFromProfile(self.chamberTemp, temperatureProfile);
            }

            self.tools().forEach(function (element) {
                self.setTargetFromProfile(element, temperatureProfile);
            });
        };

        self.setTargetFromProfile = function (item, profile) {
            if (!profile) return OctoPrintClient.createRejectedDeferred();

            self.clearAutosendTarget(item);

            var target;
            if (item.key() === "bed") {
                target = profile.bed;
            } else if (item.key() === "chamber") {
                target = profile.chamber;
            } else {
                target = profile.extruder;
            }

            if (target === undefined) target = 0;
            return self.setTargetToValue(item, target);
        };

        // Wrapper of self.setTargetToZero() to set off all the temperatures
        self.setTargetsToZero = function () {
            if (self.hasBed()) {
                self.setTargetToZero(self.bedTemp);
            }

            if (self.hasChamber()) {
                self.setTargetToZero(self.chamberTemp);
            }

            self.tools().forEach(function (element) {
                self.setTargetToZero(element);
            });
        };

        self.setTargetToZero = function (item) {
            self.clearAutosendTarget(item);
            return self.setTargetToValue(item, 0);
        };

        self.setTargetToValue = function (item, value) {
            self.clearAutosendTarget(item);

            try {
                value = parseInt(value);
            } catch (ex) {
                return OctoPrintClient.createRejectedDeferred();
            }

            if (value < 0 || value > 999) return OctoPrintClient.createRejectedDeferred();

            var onSuccess = function () {
                item.target(value);
                item.newTarget("");
            };

            if (item.key() === "bed") {
                return self._setBedTemperature(value).done(onSuccess);
            } else if (item.key() === "chamber") {
                return self._setChamberTemperature(value).done(onSuccess);
            } else {
                return self._setToolTemperature(item.key(), value).done(onSuccess);
            }
        };

        self.changeOffset = function (item) {
            // copy values
            self.changingOffset.item = item;
            self.changingOffset.name(item.name());
            self.changingOffset.offset(item.offset());
            self.changingOffset.newOffset(item.offset());

            self.changeOffsetDialog.modal("show");
        };

        self.incrementChangeOffset = function () {
            var value = self.changingOffset.newOffset();
            if (value === undefined || (typeof value === "string" && value.trim() === ""))
                value = self.changingOffset.offset();
            try {
                value = parseInt(value);
                if (value >= 50) return;
                self.changingOffset.newOffset(value + 1);
            } catch (ex) {
                // do nothing
            }
        };

        self.decrementChangeOffset = function () {
            var value = self.changingOffset.newOffset();
            if (value === undefined || (typeof value === "string" && value.trim() === ""))
                value = self.changingOffset.offset();
            try {
                value = parseInt(value);
                if (value <= -50) return;
                self.changingOffset.newOffset(value - 1);
            } catch (ex) {
                // do nothing
            }
        };

        self.deleteChangeOffset = function () {
            self.changingOffset.newOffset(0);
        };

        self.confirmChangeOffset = function () {
            var item = self.changingOffset.item;
            item.newOffset(self.changingOffset.newOffset());

            self.setOffset(item).done(function () {
                self.changeOffsetDialog.modal("hide");

                // reset
                self.changingOffset.offset(0);
                self.changingOffset.newOffset(0);
                self.changingOffset.name("");
                self.changingOffset.item = undefined;
            });
        };

        self.setOffset = function (item) {
            var value = item.newOffset();
            if (value === undefined || (typeof value === "string" && value.trim() === ""))
                return OctoPrintClient.createRejectedDeferred();
            return self.setOffsetToValue(item, value);
        };

        self.setOffsetToZero = function (item) {
            return self.setOffsetToValue(item, 0);
        };

        self.setOffsetToValue = function (item, value) {
            try {
                value = parseInt(value);
            } catch (ex) {
                return OctoPrintClient.createRejectedDeferred();
            }

            if (value < -50 || value > 50)
                return OctoPrintClient.createRejectedDeferred();

            var onSuccess = function () {
                item.offset(value);
                item.newOffset("");
            };

            if (item.key() === "bed") {
                return self._setBedOffset(value).done(onSuccess);
            } else if (item.key() === "chamber") {
                return self._setChamberOffset(value).done(onSuccess);
            } else {
                return self._setToolOffset(item.key(), value).done(onSuccess);
            }
        };

        self._setToolTemperature = function (tool, temperature) {
            var data = {};
            data[tool] = parseInt(temperature);
            return OctoPrint.printer.setToolTargetTemperatures(data);
        };

        self._setToolOffset = function (tool, offset) {
            var data = {};
            data[tool] = parseInt(offset);
            return OctoPrint.printer.setToolTemperatureOffsets(data);
        };

        self._setBedTemperature = function (temperature) {
            return OctoPrint.printer.setBedTargetTemperature(parseInt(temperature));
        };

        self._setBedOffset = function (offset) {
            return OctoPrint.printer.setBedTemperatureOffset(parseInt(offset));
        };

        self._setChamberTemperature = function (temperature) {
            return OctoPrint.printer.setChamberTargetTemperature(parseInt(temperature));
        };

        self._setChamberOffset = function (offset) {
            return OctoPrint.printer.setChamberTemperatureOffset(parseInt(offset));
        };

        self._replaceLegendLabel = function (index, series, value, emph) {
            var showFahrenheit = self._shallShowFahrenheit();

            var temp;
            if (index % 2 === 0) {
                // actual series
                temp = formatTemperature(value, showFahrenheit);
            } else {
                // target series
                temp = formatTemperature(value, showFahrenheit, 1);
            }
            if (emph) {
                temp = "<em>" + temp + "</em>";
            }
            series.label = series.label.replace(/:.*/, ": " + temp);
        };

        self._shallShowFahrenheit = function () {
            return self.settingsViewModel.settings !== undefined
                ? self.settingsViewModel.settings.appearance.showFahrenheitAlso()
                : false;
        };

        self.handleEnter = function (event, type, item) {
            if (event.keyCode === 13) {
                if (type === "target") {
                    self.setTarget(item).done(function () {
                        event.target.blur();
                    });
                } else if (type === "offset") {
                    self.confirmChangeOffset();
                }
            }
        };

        self.handleFocus = function (event, type, item) {
            if (type === "target") {
                var value = item.newTarget();
                if (
                    value === undefined ||
                    (typeof value === "string" && value.trim() === "")
                ) {
                    item.newTarget(item.target());
                }
                window.setTimeout(function () {
                    event.target.select();
                }, 0);
            } else if (type === "offset") {
                window.setTimeout(function () {
                    event.target.select();
                }, 0);
            }
        };

        self.initOrUpdate = function () {
            if (OctoPrint.coreui.selectedTab !== "#temp" || !$("#temp").is(":visible")) {
                // do not try to initialize the graph when it's not visible or its sizing will be off
                return;
            }

            if (!self.plot) {
                self._initializePlot();
            } else {
                self.updatePlot();
            }
        };

        self.onAfterTabChange = function () {
            self.initOrUpdate();
        };

        self.onStartup = function () {
            var graph = $("#temperature-graph");
            if (graph.length && !OctoPrint.coreui.browser.mobile) {
                graph.bind("plothover", function (event, pos, item) {
                    self.plotHoverPos = pos;
                    if (!self.plotLegendTimeout) {
                        self.plotLegendTimeout = window.setTimeout(function () {
                            self.updateLegend(self._replaceLegendLabel);
                        }, 50);
                    }
                });
            }

            self.changeOffsetDialog = $("#change_offset_dialog");

            self._graphUpdater = setInterval(() => {
                if (self.printerState.isOperational()) return;

                const now = Date.now() / 1000;
                const entry = {};
                _.each(_.keys(self.heaterOptions()), (type) => {
                    entry[type] = {actual: undefined, target: undefined};
                });
                entry["time"] = now;

                self.temperatures = self._processTemperatureData(
                    now,
                    [entry],
                    self.temperatures
                );
                self.updatePlot();
            }, 1000);
        };

        self.onStartupComplete = function () {
            self.initOrUpdate();
            self._printerProfileUpdated();
        };

        self.onUserPermissionsChanged =
            self.onUserLoggedIn =
            self.onUserLoggedOut =
                function () {
                    self.initOrUpdate();
                };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: TemperatureViewModel,
        dependencies: [
            "loginStateViewModel",
            "settingsViewModel",
            "accessViewModel",
            "printerStateViewModel"
        ],
        elements: ["#temp", "#temp_link", "#change_offset_dialog"]
    });
});
