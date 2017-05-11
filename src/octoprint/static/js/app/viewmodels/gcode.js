$(function() {
    function GcodeViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];

        self.ui_progress_percentage = ko.observable();
        self.ui_progress_type = ko.observable();
        self.ui_progress_text = ko.pureComputed(function() {
            var text = "";
            switch (self.ui_progress_type()) {
                case "loading": {
                    text = gettext("Loading...") + " (" + self.ui_progress_percentage().toFixed(0) + "%)";
                    break;
                }
                case "analyzing": {
                    text = gettext("Analyzing...") + " (" + self.ui_progress_percentage().toFixed(0) + "%)";
                    break;
                }
                case "done": {
                    text = gettext("Analyzed");
                    break;
                }
            }

            return text;
        });
        self.ui_modelInfo = ko.observable("");
        self.ui_layerInfo = ko.observable("");

        self.tabActive = false;
        self.enableReload = ko.observable(false);

        self.waitForApproval = ko.observable(false);
        self.selectedFile = {
            path: ko.observable(undefined),
            date: ko.observable(undefined),
            size: ko.observable(undefined)
        };

        self.needsLoad = false;

        self.renderer_centerModel = ko.observable(false);
        self.renderer_centerViewport = ko.observable(false);
        self.renderer_zoomOnModel = ko.observable(false);
        self.renderer_showMoves = ko.observable(true);
        self.renderer_showRetracts = ko.observable(true);
        self.renderer_extrusionWidthEnabled = ko.observable(false);
        self.renderer_extrusionWidth = ko.observable(2);
        self.renderer_showNext = ko.observable(false);
        self.renderer_showPrevious = ko.observable(false);
        self.renderer_syncProgress = ko.observable(true);

        self.reader_sortLayers = ko.observable(true);
        self.reader_hideEmptyLayers = ko.observable(true);

        self.layerSelectionEnabled = ko.observable(false);
        self.layerUpEnabled = ko.observable(false);
        self.layerDownEnabled = ko.observable(false);

        self.synchronizeOptions = function(additionalRendererOptions, additionalReaderOptions) {
            var renderer = {
                moveModel: self.renderer_centerModel(),
                centerViewport: self.renderer_centerViewport(),
                showMoves: self.renderer_showMoves(),
                showRetracts: self.renderer_showRetracts(),
                extrusionWidth: self.renderer_extrusionWidthEnabled() ? self.renderer_extrusionWidth() : 1,
                showNextLayer: self.renderer_showNext(),
                showPreviousLayer: self.renderer_showPrevious(),
                zoomInOnModel: self.renderer_zoomOnModel(),
                onInternalOptionChange: self._onInternalRendererOptionChange
            };
            if (additionalRendererOptions) {
                _.extend(renderer, additionalRendererOptions);
            }

            var reader = {
                sortLayers: self.reader_sortLayers(),
                purgeEmptyLayers: self.reader_hideEmptyLayers()
            };
            if (additionalReaderOptions) {
                _.extend(reader, additionalReaderOptions);
            }

            GCODE.ui.updateOptions({
                renderer: renderer,
                reader: reader
            });
        };

        // subscribe to update Gcode view on updates...
        self.renderer_centerModel.subscribe(self.synchronizeOptions);
        self.renderer_centerViewport.subscribe(self.synchronizeOptions);
        self.renderer_zoomOnModel.subscribe(self.synchronizeOptions);
        self.renderer_showMoves.subscribe(self.synchronizeOptions);
        self.renderer_showRetracts.subscribe(self.synchronizeOptions);
        self.renderer_extrusionWidthEnabled.subscribe(self.synchronizeOptions);
        self.renderer_extrusionWidth.subscribe(self.synchronizeOptions);
        self.renderer_showNext.subscribe(self.synchronizeOptions);
        self.renderer_showPrevious.subscribe(self.synchronizeOptions);
        self.reader_sortLayers.subscribe(self.synchronizeOptions);
        self.reader_hideEmptyLayers.subscribe(self.synchronizeOptions);

        // subscribe to relevant printer settings...
        self.settings.printerProfiles.currentProfileData.subscribe(function() {
            if (!self.enabled) return;

            var currentProfileData = self.settings.printerProfiles.currentProfileData();
            if (!currentProfileData) return;

            var toolOffsets = self._retrieveToolOffsets(currentProfileData);
            if (toolOffsets) {
                GCODE.ui.updateOptions({
                    reader: {
                        toolOffsets: toolOffsets
                    }
                });

            }

            var bedDimensions = self._retrieveBedDimensions(currentProfileData);
            if (toolOffsets) {
                GCODE.ui.updateOptions({
                    renderer: {
                        bed: bedDimensions
                    }
                });
            }

            var axesConfiguration = self._retrieveAxesConfiguration(currentProfileData);
            if (axesConfiguration) {
                GCODE.ui.updateOptions({
                    renderer: {
                        invertAxes: axesConfiguration
                    }
                });
            }
        });

        self.settings.feature_g90InfluencesExtruder.subscribe(function() {
            GCODE.ui.updateOptions({
                reader: {
                    g90InfluencesExtruder: self.settings.feature_g90InfluencesExtruder()
                }
            });
        });

        self._retrieveBedDimensions = function(currentProfileData) {
            if (currentProfileData == undefined) {
                currentProfileData = self.settings.printerProfiles.currentProfileData();
            }

            if (currentProfileData && currentProfileData.volume && currentProfileData.volume.formFactor() && currentProfileData.volume.width() && currentProfileData.volume.depth()) {
                var x = undefined, y = undefined, r = undefined, circular = false, centeredOrigin = false;

                var formFactor = currentProfileData.volume.formFactor();
                if (formFactor == "circular") {
                    r = currentProfileData.volume.width() / 2;
                    circular = true;
                    centeredOrigin = true;
                } else {
                    x = currentProfileData.volume.width();
                    y = currentProfileData.volume.depth();
                    if (currentProfileData.volume.origin) {
                        centeredOrigin = currentProfileData.volume.origin() == "center";
                    }
                }

                return {
                    x: x,
                    y: y,
                    r: r,
                    circular: circular,
                    centeredOrigin: centeredOrigin
                };
            } else {
                return undefined;
            }
        };

        self._retrieveToolOffsets = function(currentProfileData) {
            if (currentProfileData == undefined) {
                currentProfileData = self.settings.printerProfiles.currentProfileData();
            }

            if (currentProfileData && currentProfileData.extruder && currentProfileData.extruder.offsets() && !currentProfileData.extruder.sharedNozzle()) {
                var offsets = [];
                _.each(currentProfileData.extruder.offsets(), function(offset) {
                    offsets.push({x: offset[0], y: offset[1]})
                });
                return offsets;
            } else {
                return undefined;
            }

        };

        self._retrieveAxesConfiguration = function(currentProfileData) {
            if (currentProfileData == undefined) {
                currentProfileData = self.settings.printerProfiles.currentProfileData();
            }

            if (currentProfileData && currentProfileData.axes) {
                var invertX = false, invertY = false;
                if (currentProfileData.axes.x) {
                    invertX = currentProfileData.axes.x.inverted();
                }
                if (currentProfileData.axes.y) {
                    invertY = currentProfileData.axes.y.inverted();
                }

                return {
                    x: invertX,
                    y: invertY
                }
            } else {
                return undefined;
            }
        };

        self.loadedFilepath = undefined;
        self.loadedFileDate = undefined;
        self.status = 'idle';
        self.enabled = false;

        self.currentlyPrinting = false;

        self.errorCount = 0;

        self.layerSlider = undefined;
        self.layerCommandSlider = undefined;

        self.currentLayer = undefined;
        self.currentCommand = undefined;
        self.maxLayer = undefined;

        self.initialize = function() {
            var layerSliderElement = $("#gcode_slider_layers");
            var commandSliderElement = $("#gcode_slider_commands");
            var containerElement = $("#gcode_canvas");

            if (!(layerSliderElement.length && commandSliderElement.length && containerElement.length)) {
                return;
            }

            self._configureLayerSlider(layerSliderElement);
            self._configureLayerCommandSlider(commandSliderElement);

            self.settings.requestData()
                .done(function() {
                    var initResult = GCODE.ui.init({
                        container: "#gcode_canvas",
                        onProgress: self._onProgress,
                        onModelLoaded: self._onModelLoaded,
                        onLayerSelected: self._onLayerSelected,
                        bed: self._retrieveBedDimensions(),
                        toolOffsets: self._retrieveToolOffsets(),
                        invertAxes: self._retrieveAxesConfiguration()
                    });

                    if (!initResult) {
                        log.info("Could not initialize GCODE viewer component");
                        return;
                    }

                    self.synchronizeOptions();
                    self.enabled = true;
                });
        };

        self.reset = function() {
            self.enableReload(false);
            self.loadedFilepath = undefined;
            self.loadedFileDate = undefined;
            self.clear();
        };

        self.clear = function() {
            GCODE.ui.clear();
        };

        self._configureLayerSlider = function(layerSliderElement) {
            self.layerSlider = layerSliderElement.slider({
                id: "gcode_layer_slider",
                reversed: true,
                selection: "after",
                orientation: "vertical",
                min: 0,
                max: 1,
                step: 1,
                value: 0,
                enabled: false,
                formatter: function(value) { return "Layer #" + (value + 1); }
            }).on("slide", self.changeLayer);
        };

        self._configureLayerCommandSlider = function(commandSliderElement) {
            self.layerCommandSlider = commandSliderElement.slider({
                id: "gcode_command_slider",
                orientation: "horizontal",
                min: 0,
                max: 1,
                step: 1,
                value: [0, 1],
                enabled: false,
                tooltip: "hide"
            }).on("slide", self.changeCommandRange);
        };

        self.loadFile = function(path, date){
            self.enableReload(false);
            self.needsLoad = false;
            if (self.status == "idle" && self.errorCount < 3) {
                self.status = "request";
                OctoPrint.files.download("local", path)
                    .done(function(response, rstatus) {
                        if(rstatus === 'success'){
                            self.showGCodeViewer(response, rstatus);
                            self.loadedFilepath = path;
                            self.loadedFileDate = date;
                            self.status = "idle";
                            self.enableReload(true);
                        }
                    })
                    .fail(function() {
                        self.status = "idle";
                        self.errorCount++;
                    });
            }
        };

        self.showGCodeViewer = function(response, rstatus) {
            var par = {
                target: {
                    result: response
                }
            };
            GCODE.gCodeReader.loadFile(par);

            if (self.layerSlider != undefined) {
                self.layerSlider.slider("disable");
            }
            if (self.layerCommandSlider != undefined) {
                self.layerCommandSlider.slider("disable");
            }
        };

        self.reload = function() {
            if (!self.enableReload()) return;
            self.loadFile(self.loadedFilepath, self.loadedFileDate);
        };

        self.fromHistoryData = function(data) {
            self._processData(data);
        };

        self.fromCurrentData = function(data) {
            self._processData(data);
        };

        self._renderPercentage = function(percentage) {
            var cmdIndex = GCODE.gCodeReader.getCmdIndexForPercentage(percentage);
            if (!cmdIndex) return;

            GCODE.renderer.render(cmdIndex.layer, 0, cmdIndex.cmd);
            GCODE.ui.updateLayerInfo(cmdIndex.layer);

            if (self.layerSlider != undefined) {
                self.layerSlider.slider("setValue", cmdIndex.layer);
            }
            if (self.layerCommandSlider != undefined) {
                self.layerCommandSlider.slider("setValue", [0, cmdIndex.cmd]);
            }
        };

        self._processData = function(data) {
            if (!data.job.file || !data.job.file.path && (self.loadedFilepath || self.loadedFileDate)) {
                self.waitForApproval(false);

                self.loadedFilepath = undefined;
                self.loadedFileDate = undefined;
                self.selectedFile.path(undefined);
                self.selectedFile.date(undefined);
                self.selectedFile.size(undefined);

                self.clear();
                return;
            }
            if (!self.enabled) return;
            self.currentlyPrinting = data.state.flags && (data.state.flags.printing || data.state.flags.paused);

            if(self.loadedFilepath
                    && self.loadedFilepath == data.job.file.path
                    && self.loadedFileDate == data.job.file.date) {
                if (OctoPrint.coreui.browserTabVisible && self.tabActive && self.currentlyPrinting && self.renderer_syncProgress() && !self.waitForApproval()) {
                    self._renderPercentage(data.progress.completion);
                }
                self.errorCount = 0
            } else {
                self.clear();
                if (data.job.file.path && data.job.file.origin != "sdcard"
                        && self.status != "request"
                        && (!self.waitForApproval() || self.selectedFile.path() != data.job.file.path || self.selectedFile.date() != data.job.file.date)) {
                    self.selectedFile.path(data.job.file.path);
                    self.selectedFile.date(data.job.file.date);
                    self.selectedFile.size(data.job.file.size);

                    if (data.job.file.size > CONFIG_GCODE_SIZE_THRESHOLD || ($.browser.mobile && data.job.file.size > CONFIG_GCODE_MOBILE_SIZE_THRESHOLD)) {
                        self.waitForApproval(true);
                        self.loadedFilepath = undefined;
                        self.loadedFileDate = undefined;
                    } else {
                        self.waitForApproval(false);
                        if (self.tabActive) {
                            self.loadFile(data.job.file.path, data.job.file.date);
                        } else {
                            self.needsLoad = true;
                        }
                    }
                }
            }
        };

        self.onEventPrintDone = function() {
            if (self.renderer_syncProgress() && !self.waitForApproval()) {
                self._renderPercentage(100.0);
            }
        };

        self.approveLargeFile = function() {
            self.waitForApproval(false);
            self.loadFile(self.selectedFile.path(), self.selectedFile.date());
        };

        self._onProgress = function(type, percentage) {
            self.ui_progress_type(type);
            self.ui_progress_percentage(percentage);
        };

        self._onModelLoaded = function(model) {
            if (!model) {
                self.ui_modelInfo("");
                if (self.layerSlider != undefined) {
                    self.layerSlider.slider("disable");
                    self.layerSlider.slider("setMax", 1);
                    self.layerSlider.slider("setValue", 0);
                    self.layerSelectionEnabled(false);
                    self.layerDownEnabled(false);
                    self.layerUpEnabled(false);
                }
                self.currentLayer = 0;
                self.maxLayer = 0;
            } else {
                var output = [];
                output.push(gettext("Model size") + ": " + model.width.toFixed(2) + "mm &times; " + model.depth.toFixed(2) + "mm &times; " + model.height.toFixed(2) + "mm");
                output.push(gettext("Estimated total print time") + ": " + formatFuzzyPrintTime(model.printTime));
                output.push(gettext("Estimated layer height") + ": " + model.layerHeight.toFixed(2) + gettext("mm"));
                output.push(gettext("Layer count") + ": " + model.layersPrinted.toFixed(0) + " " + gettext("printed") + ", " + model.layersTotal.toFixed(0) + " " + gettext("visited"));

                self.ui_modelInfo(output.join("<br>"));

                self.maxLayer = model.layersPrinted - 1;
                if (self.layerSlider != undefined) {
                    self.layerSlider.slider("enable");
                    self.layerSlider.slider("setMax", self.maxLayer);
                    self.layerSlider.slider("setValue", 0);
                    self.layerSelectionEnabled(true);
                    self.layerDownEnabled(false);
                    self.layerUpEnabled(self.maxLayer > 0);
                }
            }
        };

        self._onLayerSelected = function(layer) {
            if (!layer) {
                self.ui_layerInfo("");
                if (self.layerCommandSlider != undefined) {
                    self.layerCommandSlider.slider("disable");
                    self.layerCommandSlider.slider("setMax", 1);
                    self.layerCommandSlider.slider("setValue", [0, 1]);

                    self.layerDownEnabled(false);
                    self.layerUpEnabled(false);
                }
                self.currentCommand = [0, 1];
            } else {
                var output = [];
                output.push(gettext("Layer number") + ": " + (layer.number + 1));
                output.push(gettext("Layer height") + " (mm): " + layer.height);
                output.push(gettext("GCODE commands") + ": " + layer.commands);
                if (layer.filament != undefined) {
                    if (layer.filament.length == 1) {
                        output.push(gettext("Filament") + ": " + layer.filament[0].toFixed(2) + "mm");
                    } else {
                        for (var i = 0; i < layer.filament.length; i++) {
                            output.push(gettext("Filament") + " (" + gettext("Tool") + " " + i + "): " + layer.filament[i].toFixed(2) + "mm");
                        }
                    }
                }
                output.push(gettext("Estimated print time") + ": " + formatDuration(layer.printTime));

                self.ui_layerInfo(output.join("<br>"));

                console.log("#### Layer number:", layer.number, ", max layer:", self.maxLayer);
                if (self.layerCommandSlider != undefined) {
                    self.layerCommandSlider.slider("enable");
                    self.layerCommandSlider.slider("setMax", layer.commands - 1);
                    self.layerCommandSlider.slider("setValue", [0, layer.commands - 1]);

                    self.layerDownEnabled(layer.number > 0);
                    self.layerUpEnabled(layer.number < self.maxLayer);
                }
            }
        };

        self._onInternalRendererOptionChange = function(options) {
            if (!options) return;

            for (var opt in options) {
                if (opt == "zoomInOnModel" && options[opt] != self.renderer_zoomOnModel()) {
                    self.renderer_zoomOnModel(false);
                } else if (opt == "centerViewport" && options[opt] != self.renderer_centerViewport()) {
                    self.renderer_centerViewport(false);
                } else if (opt == "moveModel" && options[opt] != self.renderer_centerModel()) {
                    self.renderer_centerModel(false);
                }
            }
        };

        self.changeLayer = function(event) {
            if (self.currentlyPrinting && self.renderer_syncProgress()) self.renderer_syncProgress(false);

            var value = event.value;
            if (self.currentLayer !== undefined && self.currentLayer == value) return;
            self.currentLayer = value;

            GCODE.ui.changeSelectedLayer(value);
        };

        self.onMouseOver = function(data, event) {
            if (!self.settings.feature_keyboardControl()) return;
            $("#canvas_container").focus();

        };
        self.onMouseOut = function(data, event) {
            if (!self.settings.feature_keyboardControl()) return;
            $("#canvas_container").blur();
        };
        self.onKeyDown = function(data, event) {
            if (!self.settings.feature_keyboardControl() || self.layerSlider === undefined) return;

            var value = self.currentLayer;
            switch(event.which){
                case 33: // Pg up
                    value = value + 10; // No need to check against max this is done by the Slider anyway
                    break;
                case 34: // Pg down
                    value = value - 10; // No need to check against min, this is done by the Slider anyway
                    break;
                case 38: // up arrow key
                    value = value + 1; // No need to check against max this is done by the Slider anyway
                    break;
                case 40: // down arrow key
                    value = value - 1; // No need to check against min, this is done by the Slider anyway
                    break;
            }
            self.shiftLayer(value);
        };

        self.changeCommandRange = function(event) {
            if (self.currentlyPrinting && self.renderer_syncProgress()) self.renderer_syncProgress(false);

            var tuple = event.value;
            if (self.currentCommand !== undefined && self.currentCommand[0] == tuple[0] && self.currentCommand[1] == tuple[1]) return;
            self.currentCommand = tuple;

            GCODE.ui.changeSelectedCommands(self.layerSlider.slider("getValue"), tuple[0], tuple[1]);
        };

        self.onDataUpdaterReconnect = function() {
            self.reset();
        };

        self.onBeforeBinding = function() {
            self.initialize();
        };

        self.onTabChange = function(current, previous) {
            self.tabActive = current == "#gcode";
            if (self.tabActive && self.needsLoad) {
                self.loadFile(self.selectedFile.path(), self.selectedFile.date());
            }
        };

        self.shiftLayer = function(value){
            if (value != self.currentLayer) {
                self.layerSlider.slider('setValue', value);
                value = self.layerSlider.slider('getValue');
                //This sets the scroll bar to the appropriate position.
                self.layerSlider
                    .trigger({
                        type: 'slideStart',
                        value: value
                    })
                    .trigger({
                        type: 'slide',
                        value: value
                    }).trigger({
                        type: 'slideStop',
                        value: value
                    });
            }
        };

        self.incrementLayer = function() {
            var value = self.layerSlider.slider('getValue') + 1;
            self.shiftLayer(value);
        };

        self.decrementLayer = function() {
            var value = self.layerSlider.slider('getValue') - 1;
            self.shiftLayer(value);
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        GcodeViewModel,
        ["loginStateViewModel", "settingsViewModel"],
        "#gcode"
    ]);
});
