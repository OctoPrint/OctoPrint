$(function() {
    function GcodeFilesViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];
        self.loginState = parameters[1];
        self.printerState = parameters[2];
        self.slicing = parameters[3];

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
        self.totalSpace = ko.observable(undefined);
        self.freeSpaceString = ko.pureComputed(function() {
            if (!self.freeSpace())
                return "-";
            return formatSize(self.freeSpace());
        });
        self.totalSpaceString = ko.pureComputed(function() {
            if (!self.totalSpace())
                return "-";
            return formatSize(self.totalSpace());
        });

        self.diskusageWarning = ko.pureComputed(function() {
            return self.freeSpace() != undefined
                && self.freeSpace() < self.settingsViewModel.server_diskspace_warning();
        });
        self.diskusageCritical = ko.pureComputed(function() {
            return self.freeSpace() != undefined
                && self.freeSpace() < self.settingsViewModel.server_diskspace_critical();
        });
        self.diskusageString = ko.pureComputed(function() {
            if (self.diskusageCritical()) {
                return gettext("Your available free disk space is critically low.");
            } else if (self.diskusageWarning()) {
                return gettext("Your available free disk space is starting to run low.");
            } else {
                return gettext("Your current disk usage.");
            }
        });

        self.uploadButton = undefined;
        self.uploadSdButton = undefined;
        self.uploadProgressBar = undefined;
        self.localTarget = undefined;
        self.sdTarget = undefined;

        self.addFolderDialog = undefined;
        self.addFolderName = ko.observable(undefined);
        self.enableAddFolder = ko.computed(function() {
            return self.loginState.isUser() && self.addFolderName() && self.addFolderName().trim() != "";
        });

        self.allItems = ko.observable(undefined);
        self.listStyle = ko.observable("folders_files");
        self.currentPath = ko.observable("");

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
                "printed": function(data) {
                    return !(data["prints"] && data["prints"]["success"] && data["prints"]["success"] > 0) || (data["type"] && data["type"] == "folder");
                },
                "sd": function(data) {
                    return data["origin"] && data["origin"] == "sdcard";
                },
                "local": function(data) {
                    return !(data["origin"] && data["origin"] == "sdcard");
                },
                "machinecode": function(data) {
                    return data["type"] && (data["type"] == "machinecode" || data["type"] == "folder");
                },
                "model": function(data) {
                    return data["type"] && (data["type"] == "model" || data["type"] == "folder");
                },
                "emptyFolder": function(data) {
                    return data["type"] && (data["type"] != "folder" || data["children"].length != 0);
                }
            },
            "name",
            ["emptyFolder"],
            [["sd", "local"], ["machinecode", "model"]],
            0
        );

        self.foldersOnlyList = ko.dependentObservable(function() {
            var filter = function(data) { return data["type"] && data["type"] == "folder"; };
            return _.filter(self.listHelper.paginatedItems(), filter);
        });

        self.filesOnlyList = ko.dependentObservable(function() {
            var filter = function(data) { return data["type"] && data["type"] != "folder"; };
            return _.filter(self.listHelper.paginatedItems(), filter);
        });

        self.filesAndFolders = ko.dependentObservable(function() {
            var style = self.listStyle();
            if (style == "folders_files" || style == "files_folders") {
                var files = self.filesOnlyList();
                var folders = self.foldersOnlyList();

                if (style == "folders_files") {
                    return folders.concat(files);
                } else {
                    return files.concat(folders);
                }
            } else {
                return self.listHelper.paginatedItems();
            }
        });

        self.isLoadActionPossible = ko.pureComputed(function() {
            return self.loginState.isUser() && !self.isPrinting() && !self.isPaused() && !self.isLoading();
        });

        self.isLoadAndPrintActionPossible = ko.pureComputed(function() {
            return self.loginState.isUser() && self.isOperational() && self.isLoadActionPossible();
        });

        self.printerState.filename.subscribe(function(newValue) {
            self.highlightFilename(newValue);
        });

        self.highlightCurrentFilename = function() {
            self.highlightFilename(self.printerState.filename());
        };

        self.highlightFilename = function(filename) {
            if (filename == undefined) {
                self.listHelper.selectNone();
            } else {
                self.listHelper.selectItem(function(item) {
                    if (item.type == "folder") {
                        return _.startsWith(filename, OctoPrint.files.pathForElement(item) + "/");
                    } else {
                        return OctoPrint.files.pathForElement(item) == filename;
                    }
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
        self.requestData = function(filenameToFocus, locationToFocus, switchToPath) {
            if (self._otherRequestInProgress) return;

            self._otherRequestInProgress = true;
            OctoPrint.files.list({ data: { recursive: true} })
                .done(function(response) {
                    self.fromResponse(response, filenameToFocus, locationToFocus, switchToPath);
                })
                .always(function() {
                    self._otherRequestInProgress = false;
                });
        };

        self.fromResponse = function(response, filenameToFocus, locationToFocus, switchToPath) {
            var files = response.files;

            self.allItems(files);
            self.currentPath("");

            if (!switchToPath) {
                self.listHelper.updateItems(files);
            } else {
                self.changeFolderByPath(switchToPath);
            }

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

            if (response.free != undefined) {
                self.freeSpace(response.free);
            }

            if (response.total != undefined) {
                self.totalSpace(response.total);
            }

            self.highlightCurrentFilename();
        };

        self.changeFolder = function(data) {
            self.currentPath(OctoPrint.files.pathForElement(data));
            self.listHelper.updateItems(data.children);
            self.highlightCurrentFilename();
        };

        self.navigateUp = function() {
            var path = self.currentPath().split("/");
            path.pop();
            self.changeFolderByPath(path.join("/"));
        };

        self.changeFolderByPath = function(path) {
            var element = OctoPrint.files.elementByPath(path, { children: self.allItems() });
            if (element) {
                self.currentPath(path);
                self.listHelper.updateItems(element.children);
            } else{
                self.currentPath("");
                self.listHelper.updateItems(self.allItems());
            }
            self.highlightCurrentFilename();
        };

        self.showAddFolderDialog = function() {
            if (self.addFolderDialog) {
                self.addFolderDialog.modal("show");
            }
        };

        self.addFolder = function() {
            var name = self.addFolderName();

            // "local" only for now since we only support local and sdcard,
            // and sdcard doesn't support creating folders...
            OctoPrint.files.createFolder("local", name, self.currentPath())
                .done(function() {
                    self.addFolderDialog.modal("hide");
                });
        };

        self.loadFile = function(file, printAfterLoad) {
            if (!file) {
                return;
            }
            OctoPrint.files.select(file.origin, OctoPrint.files.pathForElement(file))
                .done(function() {
                    if (printAfterLoad) {
                        OctoPrint.job.start();
                    }
                });
        };

        self.removeFile = function(file) {
            if (!file) {
                return;
            }

            var index = self.listHelper.paginatedItems().indexOf(file) + 1;
            if (index >= self.listHelper.paginatedItems().length) {
                index = index - 2;
            }
            if (index < 0) {
                index = 0;
            }

            var filenameToFocus = undefined;
            var fileToFocus = self.listHelper.paginatedItems()[index];
            if (fileToFocus) {
                filenameToFocus = fileToFocus.name;
            }

            OctoPrint.files.delete(file.origin, OctoPrint.files.pathForElement(file))
                .done(function() {
                    self.requestData(undefined, filenameToFocus, OctoPrint.files.pathForElement(file.parent));
                })
        };

        self.sliceFile = function(file) {
            if (!file) {
                return;
            }

            self.slicing.show(file.origin, OctoPrint.files.pathForElement(file), true);
        };

        self.initSdCard = function() {
            OctoPrint.printer.initSd();
        };

        self.releaseSdCard = function() {
            OctoPrint.printer.releaseSd();
        };

        self.refreshSdFiles = function() {
            OctoPrint.printer.refreshSd();
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

                var recursiveSearch = function(entry) {
                    if (entry === undefined) {
                        return false;
                    }

                    if (entry["type"] == "folder" && entry["children"]) {
                        return _.any(entry["children"], recursiveSearch);
                    } else {
                        return entry["name"].toLocaleLowerCase().indexOf(query) > -1;
                    }
                };

                self.listHelper.changeSearchFunction(recursiveSearch);
            } else {
                self.listHelper.resetSearch();
            }

            return false;
        };

        self.onUserLoggedIn = function(user) {
            self.uploadButton.fileupload("enable");
            if (self.uploadSdButton) {
                self.uploadSdButton.fileupload("enable");
            }
        };

        self.onUserLoggedOut = function() {
            self.uploadButton.fileupload("disable");
            if (self.uploadSdButton) {
                self.uploadSdButton.fileupload("disable");
            }
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

            self.addFolderDialog = $("#add_folder_dialog");

            //~~ Gcode upload

            self.uploadButton = $("#gcode_upload");
            self.uploadSdButton = $("#gcode_upload_sd");
            if (!self.uploadSdButton.length) {
                self.uploadSdButton = undefined;
            }

            self.uploadProgress = $("#gcode_upload_progress");
            self.uploadProgressBar = $(".bar", self.uploadProgress);

            self.localTarget = CONFIG_SD_SUPPORT ? $("#drop_locally") : $("#drop");
            self.sdTarget = $("#drop_sd");

            function evaluateDropzones() {
                var enableLocal = self.loginState.isUser();
                var enableSd = enableLocal && CONFIG_SD_SUPPORT && self.printerState.isSdReady();

                self._setDropzone("local", enableLocal);
                self._setDropzone("sdcard", enableSd);
            }
            self.loginState.isUser.subscribe(evaluateDropzones);
            self.printerState.isSdReady.subscribe(evaluateDropzones);
            evaluateDropzones();

            self.requestData();
        };

        self.onEventUpdatedFiles = function(payload) {
            if (payload.type == "gcode") {
                self.requestData(undefined, undefined, self.currentPath());
            }
        };

        self.onEventSlicingDone = function(payload) {
            self.requestData(undefined, undefined, self.currentPath());
        };

        self.onEventMetadataAnalysisFinished = function(payload) {
            self.requestData(undefined, undefined, self.currentPath());
        };

        self.onEventMetadataStatisticsUpdated = function(payload) {
            self.requestData(undefined, undefined, self.currentPath());
        };

        self.onEventTransferDone = function(payload) {
            self.requestData(payload.remote, "sdcard");
        };

        self.onServerConnect = function(payload) {
            self._enableDragNDrop(true);
            self.requestData(undefined, undefined, self.currentPath());
        };

        self.onServerReconnect = function(payload) {
            self._enableDragNDrop(true);
            self.requestData(undefined, undefined, self.currentPath());
        };

        self.onServerDisconnect = function(payload) {
            self._enableDragNDrop(false);
        };

        self._setDropzone = function(dropzone, enable) {
            var button = (dropzone == "local") ? self.uploadButton : self.uploadSdButton;
            var drop = (dropzone == "local") ? self.localTarget : self.sdTarget;
            var url = API_BASEURL + "files/" + dropzone;

            if (button === undefined)
                return;

            button.fileupload({
                url: url,
                dataType: "json",
                dropZone: enable ? drop : null,
                drop: function(e, data) {

                },
                done: self._handleUploadDone,
                fail: self._handleUploadFail,
                progressall: self._handleUploadProgress
            }).bind('fileuploadsubmit', function(e, data) {
                if (self.currentPath() != "")
                    data.formData = { path: self.currentPath() };
            });
        };

        self._enableDragNDrop = function(enable) {
            if (enable) {
                $(document).bind("dragover", self._handleDragNDrop);
                log.debug("Enabled drag-n-drop");
            } else {
                $(document).unbind("dragover", self._handleDragNDrop);
                log.debug("Disabled drag-n-drop");
            }
        };

        self._setProgressBar = function(percentage, text, active) {
            self.uploadProgressBar
                .css("width", percentage + "%")
                .text(text);

            if (active) {
                self.uploadProgress
                    .addClass("progress-striped active");
            } else {
                self.uploadProgress
                    .removeClass("progress-striped active");
            }
        };

        self._handleUploadDone = function(e, data) {
            var filename = undefined;
            var location = undefined;
            if (data.result.files.hasOwnProperty("sdcard")) {
                filename = data.result.files.sdcard.name;
                location = "sdcard";
            } else if (data.result.files.hasOwnProperty("local")) {
                filename = data.result.files.local.name;
                location = "local";
            }
            self.requestData(filename, location, self.currentPath());

            if (data.result.done) {
                self._setProgressBar(0, "", false);
            }
        };

        self._handleUploadFail = function(e, data) {
            var error = "<p>" + gettext("Could not upload the file. Make sure that it is a GCODE file and has the extension \".gcode\" or \".gco\" or that it is an STL file with the extension \".stl\".") + "</p>";
            error += pnotifyAdditionalInfo("<pre>" + data.jqXHR.responseText + "</pre>");
            new PNotify({
                title: "Upload failed",
                text: error,
                type: "error",
                hide: false
            });
            self._setProgressBar(0, "", false);
        };

        self._handleUploadProgress = function(e, data) {
            var progress = parseInt(data.loaded / data.total * 100, 10);
            var uploaded = progress >= 100;

            self._setProgressBar(progress, uploaded ? gettext("Saving ...") : gettext("Uploading ..."), uploaded);
        };

        self._handleDragNDrop = function (e) {
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
        }
    }

    OCTOPRINT_VIEWMODELS.push([
        GcodeFilesViewModel,
        ["settingsViewModel", "loginStateViewModel", "printerStateViewModel", "slicingViewModel"],
        ["#files_wrapper", "#add_folder_dialog"]
    ]);
});
