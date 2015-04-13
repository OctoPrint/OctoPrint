function GcodeViewModel(loginStateViewModel, settingsViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;
    self.settings = settingsViewModel;

    self.ui_progress_percentage = ko.observable();
    self.ui_progress_type = ko.observable();
    self.ui_progress_text = ko.computed(function() {
        var text = "";
        switch (self.ui_progress_type()) {
            case "loading": {
                text = "Loading... (" + self.ui_progress_percentage().toFixed(0) + "%)";
                break;
            }
            case "analyzing": {
                text = "Analyzing... (" + self.ui_progress_percentage().toFixed(0) + "%)";
                break;
            }
            case "done": {
                text = "Analyzed";
                break;
            }
        }

        return text;
    });
    self.ui_modelInfo = ko.observable("");
    self.ui_layerInfo = ko.observable("");

    self.enableReload = ko.observable(false);

    self.waitForApproval = ko.observable(false);
    self.selectedFile = {
        name: ko.observable(undefined),
        date: ko.observable(undefined),
        size: ko.observable(undefined)
    };

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

    self.synchronizeOptions = function(additionalRendererOptions, additionalReaderOptions) {
        var renderer = {
            moveModel: self.renderer_centerModel(),
            centerViewport: self.renderer_centerViewport(),
            showMoves: self.renderer_showMoves(),
            showRetracts: self.renderer_showRetracts(),
            extrusionWidth: self.renderer_extrusionWidthEnabled() ? self.renderer_extrusionWidth() : 1,
            showNextLayer: self.renderer_showNext(),
            showPreviousLayer: self.renderer_showPrevious(),
            zoomInOnModel: self.renderer_zoomOnModel()
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
    self.settings.printer_extruderOffsets.subscribe(function() {
        if (!self.enabled) return;
        if (!self.settings.printer_extruderOffsets()) return;

        GCODE.ui.updateOptions({
            reader: {
                toolOffsets: self.settings.printer_extruderOffsets()
            }
        });
    });
    self.settings.printer_bedDimensions.subscribe(function() {
        if (!self.enabled) return;

        var bedDimensions = self.settings.printer_bedDimensions();
        if (!bedDimensions || (!bedDimensions.hasOwnProperty("x") && !bedDimensions.hasOwnProperty("y") && !bedDimensions.hasOwnProperty("r"))) return;

        GCODE.ui.updateOptions({
            renderer: {
                bed: bedDimensions
            }
        });
    });
    self.settings.printer_invertAxes.subscribe(function() {
        if (!self.enabled) return;
        if (!self.settings.printer_invertAxes()) return;

        GCODE.ui.updateOptions({
            renderer: {
                invertAxes: {
                    x: self.settings.printer_invertX(),
                    y: self.settings.printer_invertY()
                }
            }
        });
    });

    self.loadedFilename = undefined;
    self.loadedFileDate = undefined;
    self.status = 'idle';
    self.enabled = false;

    self.currentlyPrinting = false;

    self.errorCount = 0;

    self.layerSlider = undefined;
    self.layerCommandSlider = undefined;

    self.currentLayer = undefined;
    self.currentCommand = undefined;

    self.initialize = function() {
        self._configureLayerSlider();
        self._configureLayerCommandSlider();

        self.settings.requestData(function() {
            GCODE.ui.init({
                container: "#gcode_canvas",
                onProgress: self._onProgress,
                onModelLoaded: self._onModelLoaded,
                onLayerSelected: self._onLayerSelected,
                bed: self.settings.printer_bedDimensions(),
                toolOffsets: self.settings.printer_extruderOffsets()
            });
            self.synchronizeOptions();
            self.enabled = true;
        });
    };

    self.reset = function() {
        self.enableReload(false);
        self.loadedFilename = undefined;
        self.loadedFileDate = undefined;
        self.clear();
    };

    self.clear = function() {
        GCODE.ui.clear();
    }

    self._configureLayerSlider = function() {
        self.layerSlider = $("#gcode_slider_layers").slider({
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

    self._configureLayerCommandSlider = function() {
        self.layerCommandSlider = $("#gcode_slider_commands").slider({
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

    self.loadFile = function(filename, date){
        self.enableReload(false);
        if (self.status == "idle" && self.errorCount < 3) {
            self.status = "request";
            $.ajax({
                url: BASEURL + "downloads/files/local/" + filename,
                data: { "ctime": date },
                type: "GET",
                success: function(response, rstatus) {
                    if(rstatus === 'success'){
                        self.showGCodeViewer(response, rstatus);
                        self.loadedFilename = filename;
                        self.loadedFileDate = date;
                        self.status = "idle";
                        self.enableReload(true);
                    }
                },
                error: function() {
                    self.status = "idle";
                    self.errorCount++;
                }
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

        self.layerSlider.slider("disable");
        self.layerCommandSlider.slider("disable");
    };

    self.reload = function() {
        if (!self.enableReload()) return;
        self.loadFile(self.loadedFilename, self.loadedFileDate);
    };

    self.fromHistoryData = function(data) {
        self._processData(data);
    };

    self.fromCurrentData = function(data) {
        self._processData(data);
    };

    self._processData = function(data) {
        if (!data.job.file || !data.job.file.name && (self.loadedFilename || self.loadedFileDate)) {
            self.waitForApproval(false);

            self.loadedFilename = undefined;
            self.loadedFileDate = undefined;
            self.selectedFile.name(undefined);
            self.selectedFile.date(undefined);
            self.selectedFile.size(undefined);

            self.clear();
            return;
        }
        if (!self.enabled) return;
        self.currentlyPrinting = data.state.flags && (data.state.flags.printing || data.state.flags.paused);

        if(self.loadedFilename
                && self.loadedFilename == data.job.file.name
                && self.loadedFileDate == data.job.file.date) {
            if (self.currentlyPrinting && self.renderer_syncProgress() && !self.waitForApproval()) {
                var cmdIndex = GCODE.gCodeReader.getCmdIndexForPercentage(data.progress.completion);
                if(cmdIndex){
                    GCODE.renderer.render(cmdIndex.layer, 0, cmdIndex.cmd);
                    GCODE.ui.updateLayerInfo(cmdIndex.layer);

                    self.layerSlider.slider("setValue", cmdIndex.layer);
                    self.layerCommandSlider.slider("setValue", [0, cmdIndex.cmd]);
                }
            }
            self.errorCount = 0
        } else {
            self.clear();
            if (data.job.file.name && data.job.file.origin != "sdcard"
                    && (!self.waitForApproval() || (self.selectedFile.name() != data.job.file.name || self.selectedFile.date() != data.job.file.date))) {
                self.selectedFile.name(data.job.file.name);
                self.selectedFile.date(data.job.file.date);
                self.selectedFile.size(data.job.file.size);

                if (data.job.file.size > CONFIG_GCODE_SIZE_THRESHOLD || ($.browser.mobile && data.job.file.size > CONFIG_GCODE_MOBILE_SIZE_THRESHOLD)) {
                    self.waitForApproval(true);
                    self.loadedFilename = undefined;
                    self.loadedFileDate = undefined;
                } else {
                    self.waitForApproval(false);
                    self.loadFile(data.job.file.name, data.job.file.date);
                }
            }
        }
    };

    self.approveLargeFile = function() {
        self.waitForApproval(false);
        self.loadFile(self.selectedFile.name(), self.selectedFile.date());
    };

    self._onProgress = function(type, percentage) {
        self.ui_progress_type(type);
        self.ui_progress_percentage(percentage);
    };

    self._onModelLoaded = function(model) {
        if (!model) {
            self.ui_modelInfo("");
            self.layerSlider.slider("disable");
            self.layerSlider.slider("setMax", 1);
            self.layerSlider.slider("setValue", 0);
            self.currentLayer = 0;
        } else {
            var output = [];
            output.push("Model size is: " + model.width.toFixed(2) + "mm &times; " + model.depth.toFixed(2) + "mm &times; " + model.height.toFixed(2) + "mm");
            if (model.filament.length == 0) {
                output.push("Total filament used: " + model.filament.toFixed(2) + "mm");
            } else {
                for (var i = 0; i < model.filament.length; i++) {
                    output.push("Total filament used (Tool " + i + "): " + model.filament[i].toFixed(2) + "mm");
                }
            }
            output.push("Estimated print time: " + formatDuration(model.printTime));
            output.push("Estimated layer height: " + model.layerHeight.toFixed(2) + "mm");
            output.push("Layer count: " + model.layersPrinted.toFixed(0) + " printed, " + model.layersTotal.toFixed(0) + " visited");

            self.ui_modelInfo(output.join("<br>"));

            self.layerSlider.slider("enable");
            self.layerSlider.slider("setMax", model.layersPrinted - 1);
            self.layerSlider.slider("setValue", 0);
        }
    };

    self._onLayerSelected = function(layer) {
        if (!layer) {
            self.ui_layerInfo("");
            self.layerCommandSlider.slider("disable");
            self.layerCommandSlider.slider("setMax", 1);
            self.layerCommandSlider.slider("setValue", [0, 1]);
            self.currentCommand = [0, 1];
        } else {
            var output = [];
            output.push("Layer number: " + (layer.number + 1));
            output.push("Layer height (mm): " + layer.height);
            output.push("GCODE commands in layer: " + layer.commands);
            if (layer.filament.length == 1) {
                output.push("Filament used by layer: " + layer.filament[0].toFixed(2) + "mm");
            } else {
                for (var i = 0; i < layer.filament.length; i++) {
                    output.push("Filament used by layer (Tool " + i + "): " + layer.filament[i].toFixed(2) + "mm");
                }
            }
            output.push("Print time for layer: " + formatDuration(layer.printTime));

            self.ui_layerInfo(output.join("<br>"));

            self.layerCommandSlider.slider("enable");
            self.layerCommandSlider.slider("setMax", layer.commands - 1);
            self.layerCommandSlider.slider("setValue", [0, layer.commands - 1]);
        }
    };

    self.changeLayer = function(event) {
        if (self.currentlyPrinting && self.renderer_syncProgress()) self.renderer_syncProgress(false);

        var value = event.value;
        if (self.currentLayer !== undefined && self.currentLayer == value) return;
        self.currentLayer = value;

        GCODE.ui.changeSelectedLayer(value);
    };

    self.changeCommandRange = function(event) {
        if (self.currentlyPrinting && self.renderer_syncProgress()) self.renderer_syncProgress(false);

        var tuple = event.value;
        if (self.currentCommand !== undefined && self.currentCommand[0] == tuple[0] && self.currentCommand[1] == tuple[1]) return;
        self.currentCommand = tuple;

        GCODE.ui.changeSelectedCommands(self.layerSlider.slider("getValue"), tuple[0], tuple[1]);
    };
}
