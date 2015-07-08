$(function() {
    function GcodeFilesViewModel(parameters) {
        var self = this;

        self.printerState = parameters[0];
        self.loginState = parameters[1];
        self.slicing = parameters[2];

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

        self.uploadButton = undefined;

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
                    if (b["size"] === undefined || a["size"] > b["size"]) return -1;
                    if (a["size"] < b["size"]) return 1;
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
            [],
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

            self.slicing.show(file.origin, file.name, true);
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
            return "gcode_file_" + md5(data["origin"] + ":" + data["name"]);
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
            return self.loginState.isUser() && !_.contains(self.printerState.busyFiles(), data.origin + ":" + data.name);
        };

        self.enableSelect = function(data, printAfterSelect) {
            var isLoadActionPossible = self.loginState.isUser() && self.isOperational() && !(self.isPrinting() || self.isPaused() || self.isLoading());
            return isLoadActionPossible && !self.listHelper.isSelected(data);
        };

        self.enableSlicing = function(data) {
            return self.loginState.isUser() && self.slicing.enableSlicingDialog();
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

        self.performSearch = function(e) {
            var query = self.searchQuery();
            if (query !== undefined && query.trim() != "") {
                query = query.toLocaleLowerCase();
                self.listHelper.changeSearchFunction(function(entry) {
                    return entry && entry["name"].toLocaleLowerCase().indexOf(query) > -1;
                });
            } else {
                self.listHelper.resetSearch();
            }

            return false;
        };

        self.onDataUpdaterReconnect = function() {
            self.requestData();
        };

        self.onUserLoggedIn = function(user) {
            self.uploadButton.fileupload("enable");
        };

        self.onUserLoggedOut = function() {
            self.uploadButton.fileupload("disable");
        };

        self.onStartup = function() {
            $(".accordion-toggle[data-target='#files']").click(function() {
                var files = $("#files");
                if (files.hasClass("in")) {
                    files.removeClass("overflow_visible");
                } else {
                    setTimeout(function() {
                        files.addClass("overflow_visible");
                    }, 100);
                }
            });

            $(".gcode_files").slimScroll({
                height: "306px",
                size: "5px",
                distance: "0",
                railVisible: true,
                alwaysVisible: true,
                scrollBy: "102px"
            });

            //~~ Gcode upload

            self.uploadButton = $("#gcode_upload");
            function gcode_upload_done(e, data) {
                var filename = undefined;
                var location = undefined;
                if (data.result.files.hasOwnProperty("sdcard")) {
                    filename = data.result.files.sdcard.name;
                    location = "sdcard";
                } else if (data.result.files.hasOwnProperty("local")) {
                    filename = data.result.files.local.name;
                    location = "local";
                }
                self.requestData(filename, location);

                if (_.endsWith(filename.toLowerCase(), ".stl")) {
                    self.slicing.show(location, filename);
                }

                if (data.result.done) {
                    $("#gcode_upload_progress .bar").css("width", "0%");
                    $("#gcode_upload_progress").removeClass("progress-striped").removeClass("active");
                    $("#gcode_upload_progress .bar").text("");
                }
            }

            function gcode_upload_fail(e, data) {
                var error = "<p>" + gettext("Could not upload the file. Make sure that it is a GCODE file and has the extension \".gcode\" or \".gco\" or that it is an STL file with the extension \".stl\".") + "</p>";
                error += pnotifyAdditionalInfo("<pre>" + data.jqXHR.responseText + "</pre>");
                new PNotify({
                    title: "Upload failed",
                    text: error,
                    type: "error",
                    hide: false
                });
                $("#gcode_upload_progress .bar").css("width", "0%");
                $("#gcode_upload_progress").removeClass("progress-striped").removeClass("active");
                $("#gcode_upload_progress .bar").text("");
            }

            function gcode_upload_progress(e, data) {
                var progress = parseInt(data.loaded / data.total * 100, 10);
                $("#gcode_upload_progress .bar").css("width", progress + "%");
                $("#gcode_upload_progress .bar").text(gettext("Uploading ..."));
                if (progress >= 100) {
                    $("#gcode_upload_progress").addClass("progress-striped").addClass("active");
                    $("#gcode_upload_progress .bar").text(gettext("Saving ..."));
                }
            }

            function enable_local_dropzone() {
                $("#gcode_upload").fileupload({
                    url: API_BASEURL + "files/local",
                    dataType: "json",
                    dropZone: localTarget,
                    done: gcode_upload_done,
                    fail: gcode_upload_fail,
                    progressall: gcode_upload_progress
                });
            }

            function disable_local_dropzone() {
                $("#gcode_upload").fileupload({
                    url: API_BASEURL + "files/local",
                    dataType: "json",
                    dropZone: null,
                    done: gcode_upload_done,
                    fail: gcode_upload_fail,
                    progressall: gcode_upload_progress
                });
            }

            function enable_sd_dropzone() {
                $("#gcode_upload_sd").fileupload({
                    url: API_BASEURL + "files/sdcard",
                    dataType: "json",
                    dropZone: $("#drop_sd"),
                    done: gcode_upload_done,
                    fail: gcode_upload_fail,
                    progressall: gcode_upload_progress
                });
            }

            function disable_sd_dropzone() {
                $("#gcode_upload_sd").fileupload({
                    url: API_BASEURL + "files/sdcard",
                    dataType: "json",
                    dropZone: null,
                    done: gcode_upload_done,
                    fail: gcode_upload_fail,
                    progressall: gcode_upload_progress
                });
            }

            var localTarget;
            if (CONFIG_SD_SUPPORT) {
                localTarget = $("#drop_locally");
            } else {
                localTarget = $("#drop");
            }

            self.loginState.isUser.subscribe(function(newValue) {
                if (newValue === true) {
                    enable_local_dropzone();
                } else {
                    disable_local_dropzone();
                }
            });

            if (self.loginState.isUser()) {
                enable_local_dropzone();
            } else {
                disable_local_dropzone();
            }

            if (CONFIG_SD_SUPPORT) {
                self.printerState.isSdReady.subscribe(function(newValue) {
                    if (newValue === true && self.loginState.isUser()) {
                        enable_sd_dropzone();
                    } else {
                        disable_sd_dropzone();
                    }
                });

                self.loginState.isUser.subscribe(function(newValue) {
                    if (newValue === true && self.printerState.isSdReady()) {
                        enable_sd_dropzone();
                    } else {
                        disable_sd_dropzone();
                    }
                });

                if (self.printerState.isSdReady() && self.loginState.isUser()) {
                    enable_sd_dropzone();
                } else {
                    disable_sd_dropzone();
                }
            }

            $(document).bind("dragover", function (e) {
                var dropOverlay = $("#drop_overlay");
                var dropZone = $("#drop");
                var dropZoneLocal = $("#drop_locally");
                var dropZoneSd = $("#drop_sd");
                var dropZoneBackground = $("#drop_background");
                var dropZoneLocalBackground = $("#drop_locally_background");
                var dropZoneSdBackground = $("#drop_sd_background");
                var timeout = window.dropZoneTimeout;

                if (!timeout) {
                    dropOverlay.addClass('in');
                } else {
                    clearTimeout(timeout);
                }

                var foundLocal = false;
                var foundSd = false;
                var found = false;
                var node = e.target;
                do {
                    if (dropZoneLocal && node === dropZoneLocal[0]) {
                        foundLocal = true;
                        break;
                    } else if (dropZoneSd && node === dropZoneSd[0]) {
                        foundSd = true;
                        break;
                    } else if (dropZone && node === dropZone[0]) {
                        found = true;
                        break;
                    }
                    node = node.parentNode;
                } while (node != null);

                if (foundLocal) {
                    dropZoneLocalBackground.addClass("hover");
                    dropZoneSdBackground.removeClass("hover");
                } else if (foundSd && self.printerState.isSdReady()) {
                    dropZoneSdBackground.addClass("hover");
                    dropZoneLocalBackground.removeClass("hover");
                } else if (found) {
                    dropZoneBackground.addClass("hover");
                } else {
                    if (dropZoneLocalBackground) dropZoneLocalBackground.removeClass("hover");
                    if (dropZoneSdBackground) dropZoneSdBackground.removeClass("hover");
                    if (dropZoneBackground) dropZoneBackground.removeClass("hover");
                }

                window.dropZoneTimeout = setTimeout(function () {
                    window.dropZoneTimeout = null;
                    dropOverlay.removeClass("in");
                    if (dropZoneLocal) dropZoneLocalBackground.removeClass("hover");
                    if (dropZoneSd) dropZoneSdBackground.removeClass("hover");
                    if (dropZone) dropZoneBackground.removeClass("hover");
                }, 100);
            });

            self.requestData();
        };

        self.onEventUpdatedFiles = function(payload) {
            if (payload.type == "gcode") {
                self.requestData();
            }
        };

        self.onEventSlicingDone = function(payload) {
            self.requestData();
        };

        self.onEventMetadataAnalysisFinished = function(payload) {
            self.requestData();
        };

        self.onEventMetadataStatisticsUpdated = function(payload) {
            self.requestData();
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        GcodeFilesViewModel,
        ["printerStateViewModel", "loginStateViewModel", "slicingViewModel"],
        "#files_wrapper"
    ]);
});
