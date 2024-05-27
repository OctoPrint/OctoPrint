$(function () {
    function FilesViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];
        self.loginState = parameters[1];
        self.printerState = parameters[2];
        self.slicing = parameters[3];
        self.printerProfiles = parameters[4];
        self.access = parameters[5];

        self.allViewModels = undefined;

        self.filesListVisible = ko.observable(true);
        self.showInternalFilename = ko.observable(true);

        self.isErrorOrClosed = ko.observable(undefined);
        self.isOperational = ko.observable(undefined);
        self.isPrinting = ko.observable(undefined);
        self.isPaused = ko.observable(undefined);
        self.isError = ko.observable(undefined);
        self.isReady = ko.observable(undefined);
        self.isLoading = ko.observable(undefined);
        self.isSdReady = ko.observable(undefined);

        self.searchQuery = ko.observable(undefined);
        self.searchQuery.subscribe(function () {
            self.performSearch();
        });

        self.freeSpace = ko.observable(undefined);
        self.totalSpace = ko.observable(undefined);
        self.freeSpaceString = ko.pureComputed(function () {
            if (!self.freeSpace()) return "-";
            return formatSize(self.freeSpace());
        });
        self.totalSpaceString = ko.pureComputed(function () {
            if (!self.totalSpace()) return "-";
            return formatSize(self.totalSpace());
        });

        self.diskusageWarning = ko.pureComputed(function () {
            return (
                self.freeSpace() !== undefined &&
                self.freeSpace() < self.settingsViewModel.server_diskspace_warning()
            );
        });
        self.diskusageCritical = ko.pureComputed(function () {
            return (
                self.freeSpace() !== undefined &&
                self.freeSpace() < self.settingsViewModel.server_diskspace_critical()
            );
        });
        self.diskusageString = ko.pureComputed(function () {
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

        self.dropOverlay = undefined;
        self.dropZone = undefined;
        self.dropZoneLocal = undefined;
        self.dropZoneSd = undefined;
        self.dropZoneBackground = undefined;
        self.dropZoneLocalBackground = undefined;
        self.dropZoneSdBackground = undefined;
        self.listElement = undefined;

        self.ignoreUpdatedFilesEvent = false;

        self.addingFolder = ko.observable(false);
        self.activeRemovals = ko.observableArray([]);

        self.movingFileOrFolder = ko.observable(false);
        self.moveEntry = ko.observable({name: "", display: "", path: ""}); // is there a better way to do this?
        self.moveSource = ko.observable(undefined);
        self.moveDestination = ko.observable(undefined);
        self.moveSourceFilename = ko.observable(undefined);
        self.moveDestinationFilename = ko.observable(undefined);
        self.moveDestinationFullpath = ko.pureComputed(function () {
            // Join the paths for renaming
            if (self.moveSourceFilename() !== self.moveDestinationFilename()) {
                if (self.moveDestination() === "/") {
                    return self.moveDestination() + self.moveDestinationFilename();
                } else {
                    return self.moveDestination() + "/" + self.moveDestinationFilename();
                }
            } else {
                return self.moveDestination();
            }
        });
        self.moveError = ko.observable("");
        self.moveButtonText = ko.pureComputed(function () {
            if (self.moveSource() === self.moveDestination()) {
                return gettext("Rename");
            } else {
                // Moving, but maybe also renaming
                if (self.moveSourceFilename() !== self.moveDestinationFilename()) {
                    return gettext("Move & Rename");
                } else return gettext("Move");
            }
        });

        self.folderList = ko.observableArray(["/"]);
        self.addFolderDialog = undefined;
        self.addFolderName = ko.observable(undefined);
        self.enableAddFolder = ko.pureComputed(function () {
            return (
                self.loginState.hasPermission(self.access.permissions.FILES_UPLOAD) &&
                self.addFolderName() &&
                self.addFolderName().trim() !== "" &&
                !self.addingFolder()
            );
        });

        self.uploadExistsDialog = undefined;
        self.uploadFilename = ko.observable(undefined);

        self.allItems = ko.observable(undefined);

        var optionsLocalStorageKey = "gcodeFiles.options";
        self._toLocalStorage = function () {
            saveToLocalStorage(optionsLocalStorageKey, {currentPath: self.currentPath()});
        };

        self._fromLocalStorage = function () {
            var data = loadFromLocalStorage(optionsLocalStorageKey);
            if (
                data["currentPath"] !== undefined &&
                self.settingsViewModel.feature_rememberFileFolder()
            ) {
                self.currentPath(data["currentPath"]);
            }
        };

        self.currentPath = ko.observable("");
        self.currentPath.subscribe(function () {
            self._toLocalStorage();
        });

        self.uploadProgressText = ko.observable();
        self.uploadProgressPercentage = ko.observable();

        // list style incl. persistence
        var listStyleStorageKey = "gcodeFiles.currentListStyle";
        var defaultListStyle = "folders_files";
        var saveListStyleToLocalStorage = function () {
            if (initListStyleLocalStorage()) {
                localStorage[listStyleStorageKey] = self.listStyle();
            }
        };
        var loadListStyleFromLocalStorage = function () {
            if (initListStyleLocalStorage()) {
                self.listStyle(localStorage[listStyleStorageKey]);
            }
        };
        var initListStyleLocalStorage = function () {
            if (!Modernizr.localstorage) return false;

            if (localStorage[listStyleStorageKey] !== undefined) return true;

            localStorage[listStyleStorageKey] = defaultListStyle;
            return true;
        };

        self.listStyle = ko.observable(defaultListStyle);
        self.listStyle.subscribe(saveListStyleToLocalStorage);
        loadListStyleFromLocalStorage();

        const recursiveFilter = (data, filter) => {
            if (filter(data)) {
                return true;
            } else if (data.children) {
                return data.children.some((child) => recursiveFilter(child, filter));
            } else {
                return false;
            }
        };

        const isCurrentlySelected = (data) => {
            const selected = self.selectedFile;
            return (
                selected !== undefined &&
                selected.origin === data.origin &&
                selected.path === data.path
            );
        };

        // initialize list helper
        const listHelperFilters = {
            printed: (data) =>
                recursiveFilter(
                    data,
                    (child) =>
                        isCurrentlySelected(child) ||
                        !(
                            child.prints !== undefined &&
                            child.prints.success !== undefined &&
                            child.prints.success > 0
                        )
                ),
            sd: (data) => data["origin"] && data["origin"] === "sdcard",
            local: (data) => !(data["origin"] && data["origin"] === "sdcard")
        };
        var listHelperExclusiveFilters = [["sd", "local"]];

        if (SUPPORTED_FILETYPES.length > 1) {
            _.each(SUPPORTED_FILETYPES, function (filetype) {
                listHelperFilters[filetype] = function (data) {
                    return (
                        data["type"] &&
                        (data["type"] === filetype || data["type"] === "folder")
                    );
                };
            });
            listHelperExclusiveFilters.push(SUPPORTED_FILETYPES);
        }

        var sortByName = function (a, b) {
            // sorts ascending
            if (a["display"].toLowerCase() < b["display"].toLowerCase()) return -1;
            if (a["display"].toLowerCase() > b["display"].toLowerCase()) return 1;
            return 0;
        };

        self.listHelper = new ItemListHelper(
            "gcodeFiles",
            {
                name: sortByName,
                upload: function (a, b) {
                    // sorts descending
                    if (a["date"] === undefined && b["date"] === undefined) {
                        return sortByName(a, b);
                    }
                    if (b["date"] === undefined || a["date"] > b["date"]) return -1;
                    if (a["date"] === undefined || a["date"] < b["date"]) return 1;
                    return 0;
                },
                last_printed: function (a, b) {
                    // sorts descending
                    var valA =
                        a.prints && a.prints.last && a.prints.last.date
                            ? a.prints.last.date
                            : "";
                    var valB =
                        b.prints && b.prints.last && b.prints.last.date
                            ? b.prints.last.date
                            : "";

                    if (valA > valB) {
                        return -1;
                    } else if (valA < valB) {
                        return 1;
                    } else {
                        return 0;
                    }
                },
                size: function (a, b) {
                    // sorts descending
                    if (b["size"] === undefined || a["size"] > b["size"]) return -1;
                    if (a["size"] === undefined || a["size"] < b["size"]) return 1;
                    return 0;
                }
            },
            listHelperFilters,
            "name",
            [],
            listHelperExclusiveFilters,
            0
        );
        self.selectedFile = undefined;

        self.availableFiletypes = ko.pureComputed(function () {
            var mapping = {
                model: gettext("Only show model files"),
                machinecode: gettext("Only show machine code files")
            };

            var result = [];
            _.each(SUPPORTED_FILETYPES, function (filetype) {
                if (mapping[filetype]) {
                    result.push({key: filetype, text: mapping[filetype]});
                } else {
                    result.push({
                        key: filetype,
                        text: _.sprintf(gettext("Only show %(type)s files"), {
                            type: _.escape(filetype)
                        })
                    });
                }
            });

            return result;
        });

        self.folderDestinations = ko.pureComputed(function () {
            if (self.allItems()) {
                return ko.utils.arrayFilter(self.allItems(), function (item) {
                    return item.type === "folder";
                });
            }
        });
        self.foldersOnlyList = ko.dependentObservable(function () {
            var filter = function (data) {
                return data["type"] && data["type"] === "folder";
            };
            return _.filter(self.listHelper.paginatedItems(), filter);
        });

        self.filesOnlyList = ko.dependentObservable(function () {
            var filter = function (data) {
                return data["type"] && data["type"] !== "folder";
            };
            return _.filter(self.listHelper.paginatedItems(), filter);
        });

        self.filesAndFolders = ko.dependentObservable(function () {
            var style = self.listStyle();
            if (style === "folders_files" || style === "files_folders") {
                var files = self.filesOnlyList();
                var folders = self.foldersOnlyList();

                if (style === "folders_files") {
                    return folders.concat(files);
                } else {
                    return files.concat(folders);
                }
            } else {
                return self.listHelper.paginatedItems();
            }
        });

        self.isLoadActionPossible = ko.pureComputed(function () {
            return (
                self.loginState.hasPermission(self.access.permissions.FILES_SELECT) &&
                self.isOperational() &&
                !self.isPrinting() &&
                !self.isPaused() &&
                !self.isLoading()
            );
        });

        self.isLoadAndPrintActionPossible = ko.pureComputed(function () {
            return (
                self.loginState.hasPermission(self.access.permissions.PRINT) &&
                self.isOperational() &&
                self.isLoadActionPossible()
            );
        });

        self.highlightCurrentFile = function () {
            self.highlightFile(self.selectedFile);
        };

        self.highlightFile = function (file) {
            if (!file || !file.origin || !file.path) {
                self.listHelper.selectNone();
                return;
            }

            var result = self.listHelper.selectItem(function (item) {
                if (item.origin !== file.origin) return false;

                if (item.type === "folder") {
                    return _.startsWith(file.path, item.path + "/");
                } else {
                    return item.path === file.path;
                }
            });
            if (!result) {
                if (log.getLevel() <= log.levels.DEBUG) {
                    log.info(
                        "Couldn't find file " +
                            file.origin +
                            ":" +
                            file.path +
                            " in current items, not selecting"
                    );
                }
                self.listHelper.selectNone();
            }
        };

        self.fromCurrentData = function (data) {
            self._processStateData(data.state);
            self._processJobData(data.job);
        };

        self.fromHistoryData = function (data) {
            self._processStateData(data.state);
            self._processJobData(data.job);
        };

        self._processStateData = function (data) {
            self.isErrorOrClosed(data.flags.closedOrError);
            self.isOperational(data.flags.operational);
            self.isPaused(data.flags.paused);
            self.isPrinting(data.flags.printing);
            self.isError(data.flags.error);
            self.isReady(data.flags.ready);
            self.isLoading(data.flags.loading);
            self.isSdReady(data.flags.sdReady);
        };

        self._processJobData = function (data) {
            if (!data) return;

            if (
                self.selectedFile &&
                self.file &&
                self.selectedFile.origin === data.file.origin &&
                self.selectedFile.path === data.file.path
            )
                return;

            self.selectedFile = data.file;
            self.highlightFile(data.file);
            self.listHelper.refresh();
        };

        self._otherRequestInProgress = undefined;
        self._filesToFocus = [];
        self._switchToPath = undefined;
        self.requestData = function (params) {
            if (!self.loginState.hasPermission(self.access.permissions.FILES_LIST)) {
                return;
            }

            var focus, switchToPath, force;

            if (_.isObject(params)) {
                focus = params.focus;
                switchToPath = params.switchToPath;
                force = params.force;
            } else if (arguments.length) {
                // old argument list type call signature
                log.warn(
                    "FilesViewModel.requestData called with old argument list. That is deprecated, please use parameter object instead."
                );
                if (arguments.length >= 1) {
                    if (arguments.length >= 2) {
                        focus = {location: arguments[1], path: arguments[0]};
                    } else {
                        focus = {location: "local", path: arguments[0]};
                    }
                }
                if (arguments.length >= 3) {
                    switchToPath = arguments[2];
                }
                if (arguments.length >= 4) {
                    force = arguments[3];
                }
            }

            self._filesToFocus = self._filesToFocus || focus;
            self._switchToPath = self._switchToPath || switchToPath;

            if (self._otherRequestInProgress !== undefined) {
                return self._otherRequestInProgress;
            }

            return (self._otherRequestInProgress = OctoPrint.files
                .list(true, force)
                .done(function (response) {
                    self.fromResponse(response, {
                        focus: self._filesToFocus,
                        switchToPath: self._switchToPath
                    });
                })
                .fail(function () {
                    self.allItems(undefined);
                    self.listHelper.updateItems([]);
                })
                .always(function () {
                    self._otherRequestInProgress = undefined;
                    self._filesToFocus = [];
                    self._switchToPath = undefined;
                }));
        };

        self.fromResponse = function (response, params) {
            var focus = [];
            var switchToPath;

            if (_.isObject(params)) {
                focus = params.focus || undefined;
                switchToPath = params.switchToPath || undefined;
            } else if (arguments.length > 1) {
                log.warn(
                    "FilesViewModel.fromResponse called with old argument list. That is deprecated, please use parameter object instead."
                );
                if (arguments.length > 2) {
                    focus = {location: arguments[2], path: arguments[1]};
                } else {
                    focus = {location: "local", path: arguments[1]};
                }
                if (arguments.length > 3) {
                    switchToPath = arguments[3] || undefined;
                }
            }

            var files = response.files;

            self.allItems(files);

            var createFolderList = function (entries) {
                var result = [];
                _.each(entries, function (entry) {
                    if (entry.type !== "folder") return;

                    result.push("/" + entry.path);

                    if (entry.children) {
                        result = result.concat(createFolderList(entry.children));
                    }
                });
                return result;
            };
            const folders = createFolderList(files);
            folders.sort();
            self.folderList(["/"].concat(folders));

            // Sanity check file list - see #2572
            var nonrecursive = false;
            _.each(files, function (file) {
                if (file.type === "folder" && file.children === undefined) {
                    nonrecursive = true;
                }
            });
            if (nonrecursive) {
                log.error(
                    "At least one folder doesn't have a 'children' element defined. That means the file list request " +
                        "wasn't actually made with 'recursive=true' in the query.\n\n" +
                        "This can happen on wrong reverse proxy configs that " +
                        "swallow up query parameters, see https://github.com/OctoPrint/OctoPrint/issues/2572"
                );
            }

            if (!switchToPath) {
                var currentPath = self.currentPath();
                if (currentPath === undefined) {
                    self.listHelper.updateItems(files);
                    self.currentPath("");
                } else {
                    // if we have a current path, make sure we stay on it
                    self.changeFolderByPath(currentPath);
                }
            } else {
                self.changeFolderByPath(switchToPath);
            }

            if (focus.length) {
                _.each(focus, function (focusItem, index) {
                    // got a file to scroll to
                    var entryElement = self.getEntryElement({
                        path: focusItem.path,
                        origin: focusItem.location
                    });
                    if (entryElement) {
                        // scroll to uploaded element
                        if (index + 1 === focus.length) {
                            self.listElement.scrollTop(entryElement.offsetTop);
                        }

                        // highlight uploaded element
                        var element = $(entryElement);
                        element.on(
                            "webkitAnimationEnd oanimationend msAnimationEnd animationend",
                            function (e) {
                                // remove highlight class again
                                element.removeClass("highlight");
                            }
                        );
                        element.addClass("highlight");
                    }
                });
            }

            if (response.free !== undefined) {
                self.freeSpace(response.free);
            }

            if (response.total !== undefined) {
                self.totalSpace(response.total);
            }

            self.highlightCurrentFile();
        };

        self.changeFolder = function (data) {
            if (data.children === undefined) {
                log.error(
                    "Can't switch to folder '" + data.path + "', no children available"
                );
                return;
            }

            self.currentPath(data.path);
            self.listHelper.updateItems(data.children);
            self.highlightCurrentFile();
        };

        self.navigateUp = function () {
            var path = self.currentPath().split("/");
            path.pop();
            self.changeFolderByPath(path.join("/"));
        };

        self.changeFolderByPath = function (path) {
            var element = self.elementByPath(path);
            if (element) {
                self.currentPath(path);
                self.listHelper.updateItems(element.children);
            } else {
                self.currentPath("");
                self.listHelper.updateItems(self.allItems());
            }
            self.highlightCurrentFile();
        };

        self.showAddFolderDialog = function () {
            if (!self.loginState.hasPermission(self.access.permissions.FILES_UPLOAD))
                return;

            if (self.addFolderDialog) {
                self.addFolderName("");
                self.addFolderDialog.modal("show");
            }
        };

        self.addFolder = function () {
            if (!self.loginState.hasPermission(self.access.permissions.FILES_UPLOAD))
                return;

            var name = self.addFolderName();

            // "local" only for now since we only support local and sdcard,
            // and sdcard doesn't support creating folders...
            var location = "local";

            self.ignoreUpdatedFilesEvent = true;
            self.addingFolder(true);
            OctoPrint.files
                .createFolder(location, name, self.currentPath())
                .done(function (data) {
                    self.requestData({
                        focus: {
                            path: data.folder.name,
                            location: data.folder.origin
                        }
                    })
                        .done(function () {
                            self.addFolderDialog.modal("hide");
                        })
                        .always(function () {
                            self.addingFolder(false);
                        });
                })
                .fail(function () {
                    self.addingFolder(false);
                })
                .always(function () {
                    self.ignoreUpdatedFilesEvent = false;
                });
        };

        self.removeFolder = function (folder, event) {
            if (!self.loginState.hasPermission(self.access.permissions.FILES_DELETE))
                return;

            if (!folder) {
                return;
            }

            if (folder.type !== "folder") {
                return;
            }

            if (folder.weight > 0) {
                // confirm recursive delete
                var options = {
                    message: _.sprintf(
                        gettext(
                            'You are about to delete the folder "%(folder)s" which still contains files and/or sub folders.'
                        ),
                        {folder: _.escape(folder.name)}
                    ),
                    onproceed: function () {
                        self._removeEntry(folder, event);
                    }
                };
                showConfirmationDialog(options);
            } else {
                self._removeEntry(folder, event);
            }
        };

        self.loadFile = function (data, printAfterLoad) {
            if (!self.loginState.hasPermission(self.access.permissions.FILES_SELECT))
                return;

            if (!data) {
                return;
            }

            var proceed = function (p) {
                var prevented = false;
                var callback = function () {
                    OctoPrint.files.select(data.origin, data.path, p);
                };

                if (p) {
                    callViewModels(
                        self.allViewModels,
                        "onBeforePrintStart",
                        function (method) {
                            prevented = prevented || method(callback) === false;
                        }
                    );
                }

                if (!prevented) {
                    callback();
                }
            };

            if (
                printAfterLoad &&
                self.listHelper.isSelectedByMatcher(function (item) {
                    return item && item.origin === data.origin && item.path === data.path;
                }) &&
                self.enablePrint(data)
            ) {
                // file was already selected, just start the print job
                self.printerState.print();
            } else {
                // select file, start print job (if requested and within dimensions)
                var withinPrintDimensions = self.evaluatePrintDimensions(data, true);
                var print = printAfterLoad && withinPrintDimensions;

                if (print && self.settingsViewModel.feature_printStartConfirmation()) {
                    showConfirmationDialog({
                        message: gettext(
                            "This will start a new print job. Please check that the print bed is clear."
                        ),
                        question: gettext("Do you want to start the print job now?"),
                        cancel: gettext("No"),
                        proceed: gettext("Yes"),
                        onproceed: function () {
                            proceed(print);
                        },
                        nofade: true
                    });
                } else {
                    proceed(print);
                }
            }
        };

        self.showMoveDialog = function (entry, event) {
            if (
                !self.loginState.hasAllPermissions(
                    self.access.permissions.FILES_UPLOAD,
                    self.access.permissions.FILES_DELETE
                )
            ) {
                return;
            }

            if (!entry) {
                return;
            }

            if (entry.origin !== "local") {
                return;
            }

            if (!self.moveDialog) {
                return;
            }

            var slashPos = entry.path.lastIndexOf("/");
            var current;
            if (slashPos >= 0) {
                current = "/" + entry.path.substr(0, slashPos);
            } else {
                current = "/";
            }

            self.moveEntry(entry);
            self.moveError("");
            self.moveSource(current);
            self.moveDestination(current);
            self.moveSourceFilename(entry.name);
            self.moveDestinationFilename(entry.name);
            self.moveDialog.modal("show");
        };

        self.removeFile = function (file, event) {
            if (!self.loginState.hasPermission(self.access.permissions.FILES_DELETE))
                return;

            if (!file) {
                return;
            }

            if (file.type === "folder") {
                return;
            }

            self._removeEntry(file, event);
        };

        self.sliceFile = function (file) {
            if (!self.loginState.hasPermission(self.access.permissions.SLICE)) return;

            if (!file) {
                return;
            }

            self.slicing.show(file.origin, file.path, true, undefined, {
                display: file.display
            });
        };

        self.initSdCard = function () {
            if (!self.loginState.hasPermission(self.access.permissions.CONTROL)) return;
            OctoPrint.printer.initSd();
        };

        self.releaseSdCard = function () {
            if (!self.loginState.hasPermission(self.access.permissions.CONTROL)) return;
            OctoPrint.printer.releaseSd();
        };

        self.refreshSdFiles = function () {
            if (!self.loginState.hasPermission(self.access.permissions.CONTROL)) return;
            OctoPrint.printer.refreshSd();
        };

        self.moveFileOrFolder = function (source, destination) {
            self.movingFileOrFolder(true);
            return OctoPrint.files
                .move("local", source, destination)
                .done(function () {
                    self.requestData()
                        .done(function () {
                            self.moveDialog.modal("hide");
                        })
                        .always(function () {
                            self.movingFileOrFolder(false);
                        });
                })
                .fail(function () {
                    self.moveError(
                        gettext("Unable to move file or folder") +
                            " " +
                            self.moveEntry().display +
                            " " +
                            gettext("to") +
                            " " +
                            self.moveDestination()
                    );
                    self.movingFileOrFolder(false);
                });
        };

        self._removeEntry = function (entry, event) {
            self.activeRemovals.push(entry.origin + ":" + entry.path);
            var finishActiveRemoval = function () {
                self.activeRemovals(
                    _.filter(self.activeRemovals(), function (e) {
                        return e !== entry.origin + ":" + entry.path;
                    })
                );
            };

            var activateSpinner = function () {},
                finishSpinner = function () {};

            if (event) {
                var element = $(event.currentTarget);
                if (element.length) {
                    var icon = $("i.fa-trash-alt", element);
                    if (icon.length) {
                        activateSpinner = function () {
                            icon.removeClass("far fa-trash-alt").addClass(
                                "fas fa-spinner fa-spin"
                            );
                        };
                        finishSpinner = function () {
                            icon.removeClass("fas fa-spinner fa-spin").addClass(
                                "far fa-trash-alt"
                            );
                        };
                    }
                }
            }

            activateSpinner();

            var deferred = $.Deferred();
            OctoPrint.files
                .delete(entry.origin, entry.path)
                .done(function () {
                    self.requestData()
                        .done(function () {
                            deferred.resolve();
                        })
                        .fail(function () {
                            deferred.reject();
                        });
                })
                .fail(function (data) {
                    deferred.reject();

                    // Notify user
                    var error =
                        "<p>" +
                        gettext(
                            "Could not remove entry. Please check octoprint.log for possible reasons."
                        ) +
                        "</p>";
                    if (data.responseJSON && data.responseJSON.error) {
                        error += pnotifyAdditionalInfo(
                            "<pre>" + _.escape(data.responseJSON.error) + "</pre>"
                        );
                    }
                    new PNotify({
                        title: gettext("Failed to remove entry"),
                        text: error,
                        type: "error",
                        hide: false
                    });
                });

            return deferred.promise().always(function () {
                finishActiveRemoval();
                finishSpinner();
            });
        };

        self.downloadLink = function (data) {
            if (data["refs"] && data["refs"]["download"]) {
                return data["refs"]["download"];
            } else {
                return false;
            }
        };

        self.lastTimePrinted = function (data) {
            if (
                data["prints"] &&
                data["prints"]["last"] &&
                data["prints"]["last"]["date"]
            ) {
                return data["prints"]["last"]["date"];
            } else {
                return "-";
            }
        };

        self.getSuccessClass = function (data) {
            if (!data["prints"] || !data["prints"]["last"]) {
                return "";
            }
            return data["prints"]["last"]["success"] ? "text-success" : "text-error";
        };

        self.templateFor = function (data) {
            return "files_template_" + data.type;
        };

        self.getEntryId = function (data) {
            return "gcode_file_" + md5(data["origin"] + ":" + data["path"]);
        };

        self.getEntryElement = function (data) {
            var entryId = self.getEntryId(data);
            var entryElements = $("#" + entryId);
            if (entryElements && entryElements[0]) {
                return entryElements[0];
            } else {
                return undefined;
            }
        };

        self.enableRemove = function (data) {
            if (_.contains(self.activeRemovals(), data.origin + ":" + data.path)) {
                return false;
            }

            var busy = false;
            if (data.type === "folder") {
                busy = _.any(self.printerState.busyFiles(), function (name) {
                    return _.startsWith(name, data.origin + ":" + data.path + "/");
                });
            } else {
                busy = _.contains(
                    self.printerState.busyFiles(),
                    data.origin + ":" + data.path
                );
            }
            return (
                self.loginState.hasPermission(self.access.permissions.FILES_DELETE) &&
                !busy
            );
        };

        self.enableMove = function (data) {
            return (
                self.loginState.hasAllPermissions(
                    self.access.permissions.FILES_UPLOAD,
                    self.access.permissions.FILES_DELETE
                ) && data.origin === "local"
            ); // && some way to figure out if there are subfolders;
        };
        self.enableSelect = function (data) {
            return (
                self.isLoadAndPrintActionPossible() && !self.listHelper.isSelected(data)
            );
        };

        self.enablePrint = function (data) {
            return (
                self.loginState.hasPermission(self.access.permissions.PRINT) &&
                self.isOperational() &&
                !(self.isPrinting() || self.isPaused() || self.isLoading())
            );
        };

        self.enableSelectAndPrint = function (data, printAfterSelect) {
            return self.isLoadAndPrintActionPossible();
        };

        self.enableSlicing = function (data) {
            return (
                self.loginState.hasPermission(self.access.permissions.SLICE) &&
                self.slicing.enableSlicingDialog() &&
                self.slicing.enableSlicingDialogForFile(data.name)
            );
        };

        self.enableAdditionalData = function (data) {
            return data["gcodeAnalysis"] || (data["prints"] && data["prints"]["last"]);
        };

        self.toggleAdditionalData = function (data) {
            var entryElement = self.getEntryElement(data);
            if (!entryElement) return;

            var additionalInfo = $(".additionalInfo", entryElement);
            additionalInfo.slideToggle("fast", function () {
                $(".toggleAdditionalData i", entryElement).toggleClass(
                    "fa-chevron-down fa-chevron-up"
                );
            });
        };

        self.getAdditionalData = function (data) {
            var output = "";
            if (data["gcodeAnalysis"]) {
                if (
                    data["gcodeAnalysis"]["_empty"] ||
                    !data["gcodeAnalysis"]["dimensions"] ||
                    (data["gcodeAnalysis"]["dimensions"]["width"] === 0 &&
                        data["gcodeAnalysis"]["dimensions"]["depth"] === 0 &&
                        data["gcodeAnalysis"]["dimensions"]["height"] === 0)
                ) {
                    output += gettext("Model contains no extrusion.<br>");
                } else {
                    if (data["gcodeAnalysis"]["dimensions"]) {
                        var dimensions = data["gcodeAnalysis"]["dimensions"];
                        output +=
                            gettext("Model size") +
                            ": " +
                            _.sprintf(
                                "%(width).2fmm (X) &times; %(depth).2fmm (Y) &times; %(height).2fmm (Z)",
                                dimensions
                            );
                        output += "<br>";
                    }
                    if (
                        data["gcodeAnalysis"]["filament"] &&
                        typeof data["gcodeAnalysis"]["filament"] === "object"
                    ) {
                        var filament = data["gcodeAnalysis"]["filament"];
                        if (_.keys(filament).length === 1) {
                            output +=
                                gettext("Filament") +
                                ": " +
                                formatFilament(
                                    data["gcodeAnalysis"]["filament"]["tool" + 0]
                                ) +
                                "<br>";
                        } else if (_.keys(filament).length > 1) {
                            _.each(filament, function (f, k) {
                                if (
                                    !_.startsWith(k, "tool") ||
                                    !f ||
                                    !f.hasOwnProperty("length") ||
                                    f["length"] <= 0
                                )
                                    return;
                                output +=
                                    gettext("Filament") +
                                    " (" +
                                    gettext("Tool") +
                                    " " +
                                    k.substr("tool".length) +
                                    "): " +
                                    formatFilament(f) +
                                    "<br>";
                            });
                        }
                    }
                    output +=
                        gettext("Estimated print time") +
                        ": " +
                        (self.settingsViewModel.appearance_fuzzyTimes()
                            ? formatFuzzyPrintTime(
                                  data["gcodeAnalysis"]["estimatedPrintTime"]
                              )
                            : formatDuration(
                                  data["gcodeAnalysis"]["estimatedPrintTime"]
                              )) +
                        "<br>";
                }
            }
            if (data["prints"] && data["prints"]["last"]) {
                output +=
                    gettext("Last printed") +
                    ": " +
                    formatTimeAgo(data["prints"]["last"]["date"]) +
                    "<br>";
                if (data["prints"]["last"]["printTime"]) {
                    output +=
                        gettext("Last print time") +
                        ": " +
                        formatDuration(data["prints"]["last"]["printTime"]);
                }
            }
            return output;
        };

        self.evaluatePrintDimensions = function (data, notify) {
            if (!self.settingsViewModel.feature_modelSizeDetection()) {
                return true;
            }

            var analysis = data["gcodeAnalysis"];
            if (!analysis) {
                return true;
            }

            var printingArea = data["gcodeAnalysis"]["printingArea"];
            if (!printingArea) {
                return true;
            }

            var travelArea = data["gcodeAnalysis"]["travelArea"];
            if (!travelArea) {
                return true;
            }

            var printerProfile = self.printerProfiles.currentProfileData();
            if (!printerProfile) {
                return true;
            }

            var volumeInfo = printerProfile.volume;
            if (!volumeInfo) {
                return true;
            }

            // set print volume boundaries
            var boundaries;
            if (_.isPlainObject(volumeInfo.custom_box)) {
                boundaries = {
                    minX: volumeInfo.custom_box.x_min(),
                    minY: volumeInfo.custom_box.y_min(),
                    minZ: volumeInfo.custom_box.z_min(),
                    maxX: volumeInfo.custom_box.x_max(),
                    maxY: volumeInfo.custom_box.y_max(),
                    maxZ: volumeInfo.custom_box.z_max()
                };
            } else {
                boundaries = {
                    minX: 0,
                    maxX: volumeInfo.width(),
                    minY: 0,
                    maxY: volumeInfo.depth(),
                    minZ: 0,
                    maxZ: volumeInfo.height()
                };
                if (volumeInfo.origin() === "center") {
                    boundaries["maxX"] = volumeInfo.width() / 2;
                    boundaries["minX"] = -1 * boundaries["maxX"];
                    boundaries["maxY"] = volumeInfo.depth() / 2;
                    boundaries["minY"] = -1 * boundaries["maxY"];
                }
            }

            var info = "";
            var objectFits = true;
            var travelFits = true;

            function _area_exceeds_boundaries(ax, area) {
                return (
                    area["min" + ax] < boundaries["min" + ax] ||
                    area["max" + ax] > boundaries["max" + ax]
                );
            }

            function _exceed_warning(culprit, dimension) {
                return _.sprintf(
                    gettext("%(culprit)s exceeds print volume in %(dimension)s.<br>"),
                    {culprit: culprit, dimension: dimension}
                );
            }

            // check if printing area exceeds boundaries
            if (_area_exceeds_boundaries("X", printingArea)) {
                info += _exceed_warning(gettext("Object"), gettext("width"));
                objectFits = false;
            }
            if (_area_exceeds_boundaries("Y", printingArea)) {
                info += _exceed_warning(gettext("Object"), gettext("depth"));
                objectFits = false;
            }
            if (_area_exceeds_boundaries("Z", printingArea)) {
                info += _exceed_warning(gettext("Object"), gettext("height"));
                objectFits = false;
            }

            // check if travel area exceeds boundaries
            if (_area_exceeds_boundaries("X", travelArea)) {
                info += _exceed_warning(gettext("Travel"), gettext("width"));
                travelFits = false;
            }
            if (_area_exceeds_boundaries("Y", travelArea)) {
                info += _exceed_warning(gettext("Travel"), gettext("depth"));
                travelFits = false;
            }
            if (_area_exceeds_boundaries("Z", travelArea)) {
                info += _exceed_warning(gettext("Travel"), gettext("height"));
                travelFits = false;
            }

            if (travelFits && objectFits) {
                return true;
            } else {
                // model not within bounds, we need to prepare a warning
                if (notify) {
                    var formatData = {
                        name: _.escape(data.name),
                        profile: boundaries,
                        object: printingArea,
                        travel: travelArea,
                        culprit: !objectFits ? "Object" : "Travel area"
                    };

                    info += _.sprintf(
                        gettext(
                            "Travel area: (%(travel.minX).2f, %(travel.minY).2f, %(travel.minZ).2f) &times; (%(travel.maxX).2f, %(travel.maxY).2f, %(travel.maxZ).2f)"
                        ),
                        formatData
                    );
                    info += "<br>";
                    info += _.sprintf(
                        gettext(
                            "Object's bounding box: (%(object.minX).2f, %(object.minY).2f, %(object.minZ).2f) &times; (%(object.maxX).2f, %(object.maxY).2f, %(object.maxZ).2f)"
                        ),
                        formatData
                    );
                    info += "<br>";
                    info += _.sprintf(
                        gettext(
                            "Print volume: (%(profile.minX).2f, %(profile.minY).2f, %(profile.minZ).2f) &times; (%(profile.maxX).2f, %(profile.maxY).2f, %(profile.maxZ).2f)"
                        ),
                        formatData
                    );

                    // prepare a warning message
                    var warning =
                        "<p>" +
                        _.sprintf(
                            gettext(
                                "%(culprit)s in %(name)s exceeds the print volume of the currently selected printer profile, be careful when printing this."
                            ),
                            formatData
                        ) +
                        "</p>";

                    warning += pnotifyAdditionalInfo(info);

                    warning +=
                        '<p><small>You can disable this check via Settings &gt; Features &gt; "Enable model size detection [...]"</small></p>';

                    //warn user
                    new PNotify({
                        title: _.sprintf(
                            gettext("%(culprit)s exceeds print volume"),
                            formatData
                        ),
                        text: warning,
                        type: "warning",
                        hide: false
                    });
                }
                return false;
            }
        };

        self.clearSearchQuery = function () {
            self.searchQuery("");
        };

        self.performSearch = function (e) {
            var query = self.searchQuery();
            if (query !== undefined && query.trim() !== "") {
                query = query.toLocaleLowerCase();

                var recursiveSearch = function (entry) {
                    if (entry === undefined) {
                        return false;
                    }

                    var success =
                        (entry["display"] &&
                            entry["display"].toLocaleLowerCase().indexOf(query) > -1) ||
                        entry["name"].toLocaleLowerCase().indexOf(query) > -1;
                    if (!success && entry["type"] === "folder" && entry["children"]) {
                        return _.any(entry["children"], recursiveSearch);
                    }

                    return success;
                };

                self.listHelper.changeSearchFunction(recursiveSearch);
            } else {
                self.listHelper.resetSearch();
            }

            return false;
        };

        self.elementByPath = function (path, root) {
            root = root || {children: self.allItems()};

            var recursiveSearch = function (location, element) {
                if (location.length === 0) {
                    return element;
                }

                if (!element.hasOwnProperty("children") || !element.children) {
                    return undefined;
                }

                var name = location.shift();
                for (var i = 0; i < element.children.length; i++) {
                    if (name === element.children[i].name) {
                        return recursiveSearch(location, element.children[i]);
                    }
                }

                return undefined;
            };

            return recursiveSearch(path.split("/"), root);
        };

        self.updateButtons = function () {
            if (self.loginState.hasPermission(self.access.permissions.FILES_UPLOAD)) {
                self.uploadButton.fileupload("enable");
                if (self.uploadSdButton) {
                    self.uploadSdButton.fileupload("enable");
                }
            } else {
                self.uploadButton.fileupload("disable");
                if (self.uploadSdButton) {
                    self.uploadSdButton.fileupload("disable");
                }
            }
        };

        self.onUserPermissionsChanged =
            self.onUserLoggedIn =
            self.onUserLoggedOut =
                function () {
                    self.updateButtons();
                    self.requestData();
                    self._fromLocalStorage();
                };

        self.onStartup = function () {
            $(".accordion-toggle[data-target='#files']").click(function () {
                var files = $("#files");
                if (files.hasClass("in")) {
                    files.removeClass("overflow_visible");
                    self.filesListVisible(false);
                } else {
                    setTimeout(function () {
                        files.addClass("overflow_visible");
                        self.filesListVisible(true);
                    }, 100);
                }
            });

            self.listElement = $("#files").find(".scroll-wrapper");

            self.moveDialog = $("#move_file_or_folder_dialog");
            self.addFolderDialog = $("#add_folder_dialog");
            self.addFolderDialog.on("shown", function () {
                $("input", self.addFolderDialog).focus();
            });
            $("form", self.addFolderDialog).on("submit", function (e) {
                e.preventDefault();
                if (self.enableAddFolder()) {
                    self.addFolder();
                }
            });

            self.uploadExistsDialog = $("#upload_exists_dialog");
            self.uploadExistsDialog.on("shown", () => {
                self._uploadExistsOpen = true;
            });
            self.uploadExistsDialog.on("hidden", () => {
                self._uploadExistsOpen = false;
            });

            //~~ Gcode upload

            self.uploadButton = $("#gcode_upload");
            self.uploadSdButton = $("#gcode_upload_sd");
            if (!self.uploadSdButton.length) {
                self.uploadSdButton = undefined;
            }

            self.uploadProgress = $("#gcode_upload_progress");
            self.uploadProgressBar = $(".bar", self.uploadProgress);

            self.dropOverlay = $("#drop_overlay");
            self.dropZone = $("#drop");
            self.dropZoneLocal = $("#drop_locally");
            self.dropZoneSd = $("#drop_sd");
            self.dropZoneBackground = $("#drop_background");
            self.dropZoneLocalBackground = $("#drop_locally_background");
            self.dropZoneSdBackground = $("#drop_sd_background");

            if (CONFIG_SD_SUPPORT) {
                self.localTarget = self.dropZoneLocal;
            } else {
                self.localTarget = self.dropZone;
                self.listHelper.removeFilter("sd");
            }
            self.sdTarget = self.dropZoneSd;

            self.dropOverlay.on("drop", self._forceEndDragNDrop);

            function evaluateDropzones() {
                var enableLocal = self.loginState.hasPermission(
                    self.access.permissions.FILES_UPLOAD
                );
                var enableSd =
                    enableLocal &&
                    CONFIG_SD_SUPPORT &&
                    self.printerState.isSdReady() &&
                    !self.isPrinting();

                self._setDropzone("local", enableLocal);
                self._setDropzone("sdcard", enableSd);
            }
            self.loginState.currentUser.subscribe(evaluateDropzones);
            self.printerState.isSdReady.subscribe(evaluateDropzones);
            self.isPrinting.subscribe(evaluateDropzones);
            evaluateDropzones();
        };

        self.onEventUpdatedFiles = function (payload) {
            if (self.ignoreUpdatedFilesEvent) {
                return;
            }

            if (payload.type !== "printables") {
                return;
            }

            self.requestData();
        };

        self.onEventSlicingStarted = function (payload) {
            self.uploadProgress.addClass("progress-striped").addClass("active");
            self.uploadProgressBar.css("width", "100%");
            if (payload.progressAvailable) {
                self.uploadProgressPercentage(0);
                self.uploadProgressText(
                    _.sprintf(gettext("Slicing ... (%(percentage)d%%)"), {percentage: 0})
                );
            } else {
                self.uploadProgressText(gettext("Slicing ..."));
            }
        };

        self.onSlicingProgress = function (slicer, modelPath, machinecodePath, progress) {
            self.uploadProgressText(
                _.sprintf(gettext("Slicing ... (%(percentage)d%%)"), {
                    percentage: Math.round(progress)
                })
            );
            self.uploadProgressPercentage(Math.round(progress));
        };

        self.onEventSlicingCancelled = function (payload) {
            self.uploadProgress.removeClass("progress-striped").removeClass("active");
            self.uploadProgressBar.css("width", "0%");
            self.uploadProgressText("");
            self.uploadProgressPercentage(0);
        };

        self.onEventSlicingDone = function (payload) {
            self.uploadProgress.removeClass("progress-striped").removeClass("active");
            self.uploadProgressBar.css("width", "0%");
            self.uploadProgressText("");
            self.uploadProgressPercentage(0);

            new PNotify({
                title: gettext("Slicing done"),
                text: _.sprintf(
                    gettext("Sliced %(stl)s to %(gcode)s, took %(time).2f seconds"),
                    {
                        stl: _.escape(payload.stl),
                        gcode: _.escape(payload.gcode),
                        time: payload.time
                    }
                ),
                type: "success"
            });

            self.requestData();
        };

        self.onEventSlicingFailed = function (payload) {
            self.uploadProgress.removeClass("progress-striped").removeClass("active");
            self.uploadProgressBar.css("width", "0%");
            self.uploadProgressText("");
            self.uploadProgressPercentage(0);

            var html = _.sprintf(
                gettext("Could not slice %(stl)s to %(gcode)s: %(reason)s"),
                {
                    stl: _.escape(payload.stl),
                    gcode: _.escape(payload.gcode),
                    reason: _.escape(payload.reason)
                }
            );
            new PNotify({
                title: gettext("Slicing failed"),
                text: html,
                type: "error",
                hide: false
            });
        };

        self.onEventMetadataAnalysisFinished = function (payload) {
            self.requestData();
        };

        self.onEventMetadataStatisticsUpdated = function (payload) {
            self.requestData();
        };

        self.onEventTransferStarted = function (payload) {
            self.uploadProgress.addClass("progress-striped").addClass("active");
            self.uploadProgressBar.css("width", "100%");
            self.uploadProgressPercentage(100);
            self.uploadProgressText(gettext("Streaming ..."));
        };

        self.onEventTransferDone = function (payload) {
            self.uploadProgress.removeClass("progress-striped").removeClass("active");
            self.uploadProgressBar.css("width", "0");
            self.uploadProgressText("");
            self.uploadProgressPercentage(0);

            new PNotify({
                title: gettext("Streaming done"),
                text: _.sprintf(
                    gettext(
                        "Streamed %(local)s to %(remote)s on SD, took %(time).2f seconds"
                    ),
                    {
                        local: _.escape(payload.local),
                        remote: _.escape(payload.remote),
                        time: payload.time
                    }
                ),
                type: "success"
            });

            self.requestData({focus: {location: "sdcard", path: payload.remote}});
        };

        self.onEventTransferFailed = function (payload) {
            self.uploadProgress.removeClass("progress-striped").removeClass("active");
            self.uploadProgressBar.css("width", "0");
            self.uploadProgressText("");
            self.uploadProgressPercentage(0);

            new PNotify({
                title: gettext("Streaming failed"),
                text: _.sprintf(
                    gettext("Did not finish streaming %(local)s to %(remote)s on SD"),
                    {local: _.escape(payload.local), remote: _.escape(payload.remote)}
                ),
                type: "error"
            });

            self.requestData();
        };

        self._setDropzone = function (dropzone, enable) {
            var button = dropzone === "local" ? self.uploadButton : self.uploadSdButton;
            var drop = dropzone === "local" ? self.localTarget : self.sdTarget;
            var url = API_BASEURL + "files/" + dropzone;

            if (button === undefined) return;

            button.fileupload({
                url: url,
                dataType: "json",
                dropZone: enable ? drop : null,
                sequentialUploads: true,
                drop: function (e, data) {},
                add: self._handleUploadAdd,
                submit: self._handleUploadStart,
                done: self._handleUploadDone,
                fail: self._handleUploadFail,
                stop: self._handleUploadStop,
                progressall: self._handleUploadProgress
            });
        };

        self._dragNDropEnabled = false;
        self._enableDragNDrop = () => {
            if (!self.settingsViewModel.feature_enableDragDropUpload()) return;

            if (self._dragNDropEnabled) return;
            self._dragNDropEnabled = true;

            $(document).bind("dragenter", self._handleDragEnter);
            $(document).bind("dragleave", self._handleDragLeave);
            log.debug("Enabled drag-n-drop");
        };

        self._disableDragNDrop = () => {
            if (!self._dragNDropEnabled) return;
            self._dragNDropEnabled = false;

            $(document).unbind("dragenter", self._handleDragEnter);
            $(document).unbind("dragleave", self._handleDragLeave);
            log.debug("Disabled drag-n-drop");
        };

        self._setProgressBar = function (percentage, text, active) {
            self.uploadProgressBar.css("width", percentage + "%");
            self.uploadProgressText(text);
            self.uploadProgressPercentage(percentage);

            if (active) {
                self.uploadProgress.addClass("progress-striped active");
            } else {
                self.uploadProgress.removeClass("progress-striped active");
            }
        };

        self._uploadExistsQueue = []; // Files will be in this queue if their test fails and something needs to be done
        self._uploadExistsOpen = false;

        self._processUploadQueue = function () {
            if (!self._uploadExistsQueue.length > 0 || self._uploadExistsOpen) return;

            const hideAndSubmit = function (data) {
                self.uploadExistsDialog.modal("hide");
                data.submit();
                // Recursively move on to process the queue every time a dialog is closed
                if (self._uploadExistsQueue.length > 0) {
                    self._processUploadQueue();
                }
            };

            // Collect an item from the queue that needs an overwrite dialog
            const {data, response, path, fileSizeTooBig} =
                self._uploadExistsQueue.shift();
            const file = data.files[0];

            const formData = {};
            if (path !== "") {
                formData.path = path;
            }

            // Build and show a dialog
            $("h3", self.uploadExistsDialog).text(
                _.sprintf(gettext("File already exists: %(name)s"), {
                    name: file.name
                })
            );
            $("span.existing_size", self.uploadExistsDialog).text(
                response.size ? formatSize(response.size) : "unknown"
            );
            $("span.existing_date", self.uploadExistsDialog).text(
                response.date
                    ? new Date(response.date * 1000).toLocaleString()
                    : "unknown"
            );
            $("span.new_size", self.uploadExistsDialog).text(formatSize(file.size));
            $("span.new_date", self.uploadExistsDialog).text(
                new Date(file.lastModified).toLocaleString()
            );
            $("p, form, .file_data", self.uploadExistsDialog).toggle(!fileSizeTooBig);
            $("span.not_enough_space", self.uploadExistsDialog).toggle(fileSizeTooBig);
            $("input", self.uploadExistsDialog)
                .val("")
                .prop("placeholder", response.suggestion);
            $("a.upload-rename", self.uploadExistsDialog)
                .toggle(!fileSizeTooBig)
                .prop("disabled", false)
                .off("click")
                .on("click", function () {
                    var newName = $("input", self.uploadExistsDialog).val();
                    if (newName === "") newName = response.suggestion;

                    OctoPrint.files.exists("local", path, newName).done(function (r) {
                        if (r.exists) {
                            $(".control-group", self.uploadExistsDialog).addClass(
                                "error"
                            );
                            $(".help-block", self.uploadExistsDialog).show();
                        } else {
                            $(".control-group", self.uploadExistsDialog).removeClass(
                                "error"
                            );
                            $(".help-block", self.uploadExistsDialog).hide();

                            formData.filename = newName;
                            formData.noOverwrite = true;
                            data.formData = formData;

                            hideAndSubmit(data);
                        }
                    });
                });
            if (self.loginState.hasPermission(self.access.permissions.FILES_DELETE)) {
                $("a.upload-overwrite", self.uploadExistsDialog)
                    .off("click")
                    .show()
                    .on("click", function () {
                        data.formData = formData;
                        hideAndSubmit(data);
                    });
            } else {
                $("a.upload-overwrite", self.uploadExistsDialog).hide();
            }

            self.uploadExistsDialog.modal("show");
        };

        self._handleUploadAdd = function (e, data) {
            var file = data.files[0];
            var path = self.currentPath();
            var fileSizeTooBig = file.size > self.freeSpace();

            var formData = {};
            if (path !== "") {
                formData.path = path;
            }

            if (self.settingsViewModel.feature_uploadOverwriteConfirmation()) {
                OctoPrint.files
                    .exists("local", path, file.name)
                    .done(function (response) {
                        if (response.exists) {
                            const queueEntry = {
                                data,
                                response,
                                path,
                                fileSizeTooBig
                            };
                            self._uploadExistsQueue.push(queueEntry);
                            // Start processing queue - if already processing, this will do nothing
                            self._processUploadQueue();
                        } else {
                            data.formData = formData;
                            data.submit();
                        }
                    });
            } else {
                if (fileSizeTooBig) {
                    var error =
                        "<p>" +
                        gettext(
                            "Could not upload the file. There is not enough disk space remaining."
                        ) +
                        "</p>";

                    error +=
                        "<pre>" +
                        _.sprintf(gettext("Free Space: %(freespace)s"), {
                            freespace: self.freeSpaceString()
                        }) +
                        "<br>" +
                        _.sprintf(gettext("File Size: %(filesize)s"), {
                            filesize: formatSize(file.size)
                        }) +
                        "</pre>";

                    new PNotify({
                        title: "Upload failed",
                        text: error,
                        type: "error",
                        hide: false
                    });
                } else {
                    data.formData = formData;
                    data.submit();
                }
            }
        };

        self._handleUploadStart = function (e, data) {
            self.ignoreUpdatedFilesEvent = true;
            return true;
        };

        self._handleUploadDone = function (e, data) {
            var focus = undefined;
            if (data.result.files.hasOwnProperty("sdcard")) {
                focus = {location: "sdcard", path: data.result.files.sdcard.path};
            } else if (data.result.files.hasOwnProperty("local")) {
                focus = {location: "local", path: data.result.files.local.path};
            }

            if (focus) {
                self._filesToFocus.push(focus);
            }

            if (focus && _.endsWith(focus.path.toLowerCase(), ".stl")) {
                self.slicing.show(focus.location, focus.path);
            }
        };

        self._handleUploadStop = function (e, data) {
            var reset = function () {
                self.ignoreUpdatedFilesEvent = false;
                self._setProgressBar(0, "", false);
            };

            if (self._filesToFocus.length > 0) {
                // Only refresh the list if there were files uploaded successfully
                self._setProgressBar(100, gettext("Refreshing list ..."), true);
                self.requestData({focus: self._filesToFocus}).always(function () {
                    reset();
                });
            } else {
                reset();
            }
        };

        self._handleUploadFail = function (e, data) {
            var extensions = _.map(SUPPORTED_EXTENSIONS, function (extension) {
                return extension.toLowerCase();
            }).sort();
            extensions = extensions.join(", ");

            var error = "<p><pre>" + _.escape(data.files[0].name) + "</pre></p><p>";
            switch (data.jqXHR.status) {
                case 409:
                    // already printing or otherwise busy
                    if (e.target.id === "gcode_upload_sd") {
                        error += gettext(
                            "Could not upload the file to the printer's SD. Make sure the SD is initialized and the printer is not busy with a print already."
                        );
                    } else {
                        error += gettext(
                            "Could not upload the file, overwrite not possible. Make sure it is not already printing and that you have allowed overwriting."
                        );
                    }
                    break;

                case 415:
                    // unknown file type
                    error += _.sprintf(
                        gettext(
                            "Could not upload the file. Make sure that it is a readable, valid file with one of these extensions: %(extensions)s"
                        ),
                        {extensions: _.escape(extensions)}
                    );
                    break;

                default:
                    // any other kind of error
                    error += gettext(
                        "Could not upload the file. Please check octoprint.log for possible reasons."
                    );
                    break;
            }
            error += "</p>";

            if (data.jqXHR.responseJSON && data.jqXHR.responseJSON.error) {
                error += pnotifyAdditionalInfo(
                    "<pre>" + _.escape(data.jqXHR.responseJSON.error) + "</pre>"
                );
            }
            new PNotify({
                title: "Upload failed",
                text: error,
                type: "error",
                hide: false
            });
        };

        self._handleUploadProgress = function (e, data) {
            var progress = parseInt((data.loaded / data.total) * 100, 10);
            var uploaded = progress >= 100;

            self._setProgressBar(
                progress,
                uploaded ? gettext("Saving ...") : gettext("Uploading ..."),
                uploaded
            );
        };

        self._dragNDropTarget = null;
        self._dragNDropFFTimeout = undefined;
        self._dragNDropFFTimeoutDelay = 100;
        self._forceEndDragNDrop = function () {
            self.dropOverlay.removeClass("in");
            if (self.dropZoneLocal) self.dropZoneLocalBackground.removeClass("hover");
            if (self.dropZoneSd) self.dropZoneSdBackground.removeClass("hover");
            if (self.dropZone) self.dropZoneBackground.removeClass("hover");
            self._dragNDropTarget = null;
        };

        self._handleDragLeave = function (e) {
            if (e.target !== self._dragNDropTarget) return;
            self._forceEndDragNDrop();
        };

        self._handleDragEnter = function (e) {
            if (!self.settingsViewModel.feature_enableDragDropUpload()) {
                return;
            }

            const draggedFiles = Array.from(e.originalEvent.dataTransfer.items).filter(
                (item) => item.kind === "file"
            );

            // Now, on every sane browser, we can just check if we have dragged files,
            // but Safari wants to be special and doesn't give us that info so we
            // just assume we have files, even if that means we might show the overlay
            // when we shouldn't. To anyone annoyed by this, blame Apple. See #5004
            if (!draggedFiles.length && !OctoPrint.coreui.browser.safari) {
                return;
            }

            self.dropOverlay.addClass("in");

            var foundLocal = false;
            var foundSd = false;
            var found = false;
            var node = e.target;
            do {
                if (self.dropZoneLocal && node === self.dropZoneLocal[0]) {
                    foundLocal = true;
                    break;
                } else if (self.dropZoneSd && node === self.dropZoneSd[0]) {
                    foundSd = true;
                    break;
                } else if (self.dropZone && node === self.dropZone[0]) {
                    found = true;
                    break;
                }
                node = node.parentNode;
            } while (node !== null);

            if (foundLocal) {
                self.dropZoneLocalBackground.addClass("hover");
                self.dropZoneSdBackground.removeClass("hover");
            } else if (foundSd && self.printerState.isSdReady() && !self.isPrinting()) {
                self.dropZoneSdBackground.addClass("hover");
                self.dropZoneLocalBackground.removeClass("hover");
            } else if (found) {
                self.dropZoneBackground.addClass("hover");
            } else {
                if (self.dropZoneLocalBackground)
                    self.dropZoneLocalBackground.removeClass("hover");
                if (self.dropZoneSdBackground)
                    self.dropZoneSdBackground.removeClass("hover");
                if (self.dropZoneBackground) self.dropZoneBackground.removeClass("hover");
            }
            self._dragNDropTarget = e.target;
            self._dragNDropLastOver = Date.now();
        };

        self.onServerConnect = self.onServerReconnect = function (payload) {
            self._enableDragNDrop();
            self.requestData();
        };

        self.onServerDisconnect = function (payload) {
            self._disableDragNDrop();
        };

        self.onBeforeBinding = function () {
            self.showInternalFilename(
                self.settingsViewModel.settings.appearance.showInternalFilename()
            );
        };

        self.onAllBound = function (allViewModels) {
            self.allViewModels = allViewModels;
        };

        self.onStartupComplete = () => {
            self.showInternalFilename(
                self.settingsViewModel.settings.appearance.showInternalFilename()
            );
            self.settingsViewModel.settings.appearance.showInternalFilename.subscribe(
                (value) => {
                    self.showInternalFilename(value);
                }
            );

            self._enableDragNDrop();
            self.settingsViewModel.settings.feature.enableDragDropUpload.subscribe(
                (value) => {
                    if (value) {
                        self._enableDragNDrop();
                    } else {
                        self._disableDragNDrop();
                    }
                }
            );
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: FilesViewModel,
        name: "filesViewModel",
        additionalNames: ["gcodeFilesViewModel"],
        dependencies: [
            "settingsViewModel",
            "loginStateViewModel",
            "printerStateViewModel",
            "slicingViewModel",
            "printerProfilesViewModel",
            "accessViewModel"
        ],
        elements: [
            "#files_wrapper",
            "#add_folder_dialog",
            "#move_file_or_folder_dialog",
            "#upload_exists_dialog"
        ]
    });
});
