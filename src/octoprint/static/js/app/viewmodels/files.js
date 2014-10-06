function GcodeFilesViewModel(printerStateViewModel, loginStateViewModel, slicingViewModel) {
    var self = this;

    self.printerState = printerStateViewModel;
    self.loginState = loginStateViewModel;
    self.slicing = slicingViewModel;

    self.isErrorOrClosed = ko.observable(undefined);
    self.isOperational = ko.observable(undefined);
    self.isPrinting = ko.observable(undefined);
    self.isPaused = ko.observable(undefined);
    self.isError = ko.observable(undefined);
    self.isReady = ko.observable(undefined);
    self.isLoading = ko.observable(undefined);
    self.isSdReady = ko.observable(undefined);

    self.searchQuery = ko.observable(undefined);
    self.searchQuery.subscribe(function() {
        self.performSearch();
    });

    self.freeSpace = ko.observable(undefined);
    self.freeSpaceString = ko.computed(function() {
        if (!self.freeSpace())
            return "-";
        return formatSize(self.freeSpace());
    });

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
                if (b["date"] === undefined || a["date"] > b["date"]) return -1;
                if (a["date"] < b["date"]) return 1;
                return 0;
            },
            "size": function(a, b) {
                // sorts descending
                if (b["bytes"] === undefined || a["bytes"] > b["bytes"]) return -1;
                if (a["bytes"] < b["bytes"]) return 1;
                return 0;
            }
        },
        {
            "printed": function(file) {
                return !(file["prints"] && file["prints"]["success"] && file["prints"]["success"] > 0);
            },
            "sd": function(file) {
                return file["origin"] && file["origin"] == "sdcard";
            },
            "local": function(file) {
                return !(file["origin"] && file["origin"] == "sdcard");
            },
            "machinecode": function(file) {
                return file["type"] && file["type"] == "machinecode";
            },
            "model": function(file) {
                return file["type"] && file["type"] == "model";
            }
        },
        "name",
        ["machinecode"],
        [["sd", "local"], ["machinecode", "model"]],
        0
    );

    self.isLoadActionPossible = ko.computed(function() {
        return self.loginState.isUser() && !self.isPrinting() && !self.isPaused() && !self.isLoading();
    });

    self.isLoadAndPrintActionPossible = ko.computed(function() {
        return self.loginState.isUser() && self.isOperational() && self.isLoadActionPossible();
    });

    self.printerState.filename.subscribe(function(newValue) {
        self.highlightFilename(newValue);
    });

    self.highlightFilename = function(filename) {
        if (filename == undefined) {
            self.listHelper.selectNone();
        } else {
            self.listHelper.selectItem(function(item) {
                return item.name == filename;
            });
        }
    };

    self.fromCurrentData = function(data) {
        self._processStateData(data.state);
    };

    self.fromHistoryData = function(data) {
        self._processStateData(data.state);
    };

    self._processStateData = function(data) {
        self.isErrorOrClosed(data.flags.closedOrError);
        self.isOperational(data.flags.operational);
        self.isPaused(data.flags.paused);
        self.isPrinting(data.flags.printing);
        self.isError(data.flags.error);
        self.isReady(data.flags.ready);
        self.isLoading(data.flags.loading);
        self.isSdReady(data.flags.sdReady);
    };

    self._otherRequestInProgress = false;
    self.requestData = function(filenameToFocus, locationToFocus) {
        if (self._otherRequestInProgress) return;

        self._otherRequestInProgress = true;
        $.ajax({
            url: API_BASEURL + "files",
            method: "GET",
            dataType: "json",
            success: function(response) {
                self.fromResponse(response, filenameToFocus, locationToFocus);
                self._otherRequestInProgress = false;
            },
            error: function() {
                self._otherRequestInProgress = false;
            }
        });
    };

    self.fromResponse = function(response, filenameToFocus, locationToFocus) {
        var files = response.files;
        _.each(files, function(element, index, list) {
            if (!element.hasOwnProperty("size")) element.size = undefined;
            if (!element.hasOwnProperty("date")) element.date = undefined;
        });
        self.listHelper.updateItems(files);

        if (filenameToFocus) {
            // got a file to scroll to
            if (locationToFocus === undefined) {
                locationToFocus = "local";
            }
            var entryElement = self.getEntryElement({name: filenameToFocus, origin: locationToFocus});
            if (entryElement) {
                var entryOffset = entryElement.offsetTop;
                $(".gcode_files").slimScroll({ scrollTo: entryOffset + "px" });
            }
        }

        if (response.free) {
            self.freeSpace(response.free);
        }

        self.highlightFilename(self.printerState.filename());
    };

    self.loadFile = function(file, printAfterLoad) {
        if (!file || !file.refs || !file.refs.hasOwnProperty("resource")) return;

        $.ajax({
            url: file.refs.resource,
            type: "POST",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify({command: "select", print: printAfterLoad})
        });
    };

    self.removeFile = function(file) {
        if (!file || !file.refs || !file.refs.hasOwnProperty("resource")) return;

        $.ajax({
            url: file.refs.resource,
            type: "DELETE",
            success: function() {
                self.requestData();
            }
        });
    };

    self.sliceFile = function(file) {
        if (!file) return;

        self.slicing.show(file.origin, file.name);
    };

    self.initSdCard = function() {
        self._sendSdCommand("init");
    };

    self.releaseSdCard = function() {
        self._sendSdCommand("release");
    };

    self.refreshSdFiles = function() {
        self._sendSdCommand("refresh");
    };

    self._sendSdCommand = function(command) {
        $.ajax({
            url: API_BASEURL + "printer/sd",
            type: "POST",
            dataType: "json",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify({command: command})
        });
    };

    self.downloadLink = function(data) {
        if (data["refs"] && data["refs"]["download"]) {
            return data["refs"]["download"];
        } else {
            return false;
        }
    };

    self.lastTimePrinted = function(data) {
        if (data["prints"] && data["prints"]["last"] && data["prints"]["last"]["date"]) {
            return data["prints"]["last"]["date"];
        } else {
            return "-";
        }
    };

    self.getSuccessClass = function(data) {
        if (!data["prints"] || !data["prints"]["last"]) {
            return "";
        }
        return data["prints"]["last"]["success"] ? "text-success" : "text-error";
    };

    self.templateFor = function(data) {
        return "files_template_" + data.type;
    };

    self.getEntryId = function(data) {
        return "gcode_file_" + md5(data["name"] + ":" + data["origin"]);
    };

    self.getEntryElement = function(data) {
        var entryId = self.getEntryId(data);
        var entryElements = $("#" + entryId);
        if (entryElements && entryElements[0]) {
            return entryElements[0];
        } else {
            return undefined;
        }
    };

    self.enableRemove = function(data) {
        return self.loginState.isUser() && !(self.listHelper.isSelected(data) && (self.isPrinting() || self.isPaused()));
    };

    self.enableSelect = function(data, printAfterSelect) {
        var isLoadActionPossible = self.loginState.isUser() && self.isOperational() && !(self.isPrinting() || self.isPaused() || self.isLoading());
        return isLoadActionPossible && !self.listHelper.isSelected(data);
    };

    self.enableAdditionalData = function(data) {
        return data["gcodeAnalysis"] || data["prints"] && data["prints"]["last"];
    };

    self.toggleAdditionalData = function(data) {
        var entryElement = self.getEntryElement(data);
        if (!entryElement) return;

        var additionalInfo = $(".additionalInfo", entryElement);
        additionalInfo.slideToggle("fast", function() {
            $(".toggleAdditionalData i", entryElement).toggleClass("icon-chevron-down icon-chevron-up");
        });
    };

    self.getAdditionalData = function(data) {
        var output = "";
        if (data["gcodeAnalysis"]) {
            if (data["gcodeAnalysis"]["filament"] && typeof(data["gcodeAnalysis"]["filament"]) == "object") {
                var filament = data["gcodeAnalysis"]["filament"];
                if (_.keys(filament).length == 1) {
                    output += gettext("Filament") + ": " + formatFilament(data["gcodeAnalysis"]["filament"]["tool" + 0]) + "<br>";
                } else if (_.keys(filament).length > 1) {
                    for (var toolKey in filament) {
                        if (!_.startsWith(toolKey, "tool") || !filament[toolKey] || !filament[toolKey].hasOwnProperty("length") || filament[toolKey]["length"] <= 0) continue;

                        output += gettext("Filament") + " (" + gettext("Tool") + " " + toolKey.substr("tool".length) + "): " + formatFilament(filament[toolKey]) + "<br>";
                    }
                }
            }
            output += gettext("Estimated Print Time") + ": " + formatDuration(data["gcodeAnalysis"]["estimatedPrintTime"]) + "<br>";
        }
        if (data["prints"] && data["prints"]["last"]) {
            output += gettext("Last Printed") + ": " + formatTimeAgo(data["prints"]["last"]["date"]) + "<br>";
            if (data["prints"]["last"]["lastPrintTime"]) {
                output += gettext("Last Print Time") + ": " + formatDuration(data["prints"]["last"]["lastPrintTime"]);
            }
        }
        return output;
    };

    self.performSearch = function() {
        var query = self.searchQuery();
        if (query !== undefined && query.trim() != "") {
            self.listHelper.changeSearchFunction(function(entry) {
                return entry && entry["name"].toLocaleLowerCase().indexOf(query) > -1;
            });
        } else {
            self.listHelper.resetSearch();
        }
    };

    self.onDataUpdaterReconnect = function() {
        self.requestData();
    };

    self.onStartup = function() {
        self.requestData();
    };

    self.onUpdatedFiles = function(payload) {
        if (payload.type == "gcode") {
            self.requestData();
        }
    };

    self.onSlicingDone = function(payload) {
        self.requestData();
    };

    self.onMetadataAnalysisFinished = function(payload) {
        self.requestData();
    };
}

