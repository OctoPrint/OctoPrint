/**
 * Originally based on "Filemanager", created by Marc Hannappel
 *
 * Rewritten and maintained as part of OctoPrint since 09/2024
 */

$(function () {
    function UploadmanagerViewModel(parameters) {
        var self = this;

        self.files = parameters[0];
        self.loginState = parameters[1];
        self.access = parameters[2];
        self.slicing = parameters[3];
        self.settings = parameters[4];

        self.dialog = undefined;
        self.copyMoveDialog = undefined;

        self.selectedFiles = ko.observableArray([]);
        self.currentStorage = ko.observable("local");
        self.currentStorage.subscribe(() => {
            self.deselectAll();
            self.changeFolderByPath(self.currentPath(), self.currentStorage());
        });

        self.selectedIndices = () => {
            const files = self.filesAndFolders();
            const selected = self.selectedFiles();
            const indices = selected.map((item) => files.indexOf(item));
            indices.sort((a, b) => a - b);
            return indices;
        };

        self.selectedRanges = () => {
            const indices = self.selectedIndices();
            log.debug("UPMGR: Selected indices", indices);

            const selectedRanges = [];
            let lastIdx = -1;
            let startIdx = -1;

            for (let i = 0; i < indices.length; i++) {
                const idx = indices[i];
                if (lastIdx > -1 && idx == lastIdx + 1) {
                    // the range continues
                } else {
                    // we found the start of a new range
                    if (startIdx > -1 && lastIdx > -1) {
                        // push the current one
                        selectedRanges.push([startIdx, lastIdx]);
                    }
                    startIdx = idx;
                }

                lastIdx = idx;
            }

            if (startIdx > -1 && lastIdx > -1) {
                selectedRanges.push([startIdx, lastIdx]);
            }

            return selectedRanges;
        };

        self.currentPath = ko.observable("");
        self.listStyle = ko.observable("folders_files");

        self.currentStorageCapabilities = ko.pureComputed(() => {
            const storage = self.currentStorage();
            return self.files.storageCapabilities(storage);
        });
        self.currentStorageCanAddFolder = ko.pureComputed(() => {
            const storage = self.currentStorage();
            return self.files.storageCanAddFolder(storage);
        });

        self.listHelper = new ItemListHelper(
            "uploadmanagerList",
            {
                nameAsc: (a, b) => {
                    // sorts ascending
                    if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase())
                        return -1;
                    if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase())
                        return 1;
                    return 0;
                },
                nameDsc: (a, b) => {
                    // sorts descending
                    if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase())
                        return 1;
                    if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase())
                        return -1;
                    return 0;
                },
                uploadAsc: (a, b) => {
                    // sorts ascending
                    if (b["date"] === undefined || a["date"] > b["date"]) return 1;
                    if (a["date"] < b["date"]) return -1;
                    return 0;
                },
                uploadDsc: (a, b) => {
                    // sorts descending
                    if (b["date"] === undefined || a["date"] > b["date"]) return -1;
                    if (a["date"] < b["date"]) return 1;
                    return 0;
                },
                lastPrintAsc: (a, b) => {
                    // sorts ascending
                    const valA =
                        a.prints && a.prints.last && a.prints.last.date
                            ? a.prints.last.date
                            : "";
                    const valB =
                        b.prints && b.prints.last && b.prints.last.date
                            ? b.prints.last.date
                            : "";

                    if (valA > valB) {
                        return 1;
                    } else if (valA < valB) {
                        return -1;
                    } else {
                        return 0;
                    }
                },
                lastPrintDsc: (a, b) => {
                    // sorts descending
                    const valA =
                        a.prints && a.prints.last && a.prints.last.date
                            ? a.prints.last.date
                            : "";
                    const valB =
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
                sizeAsc: (a, b) => {
                    // sorts ascending
                    if (b["size"] === undefined || a["size"] > b["size"]) return 1;
                    if (a["size"] < b["size"]) return -1;
                    return 0;
                },
                sizeDsc: (a, b) => {
                    // sorts descending
                    if (b["size"] === undefined || a["size"] > b["size"]) return -1;
                    if (a["size"] < b["size"]) return 1;
                    return 0;
                }
            },
            {
                printed: (data) => {
                    return !(
                        data["prints"] &&
                        data["prints"]["success"] &&
                        data["prints"]["success"] > 0
                    );
                },
                machinecode: (data) => {
                    return data["type"] && data["type"] == "machinecode";
                },
                model: (data) => {
                    return data["type"] && data["type"] == "model";
                }
            },
            "nameAsc",
            [],
            [["machinecode", "model"]],
            0
        );

        self.toggleSort = (sort) => {
            const current = self.listHelper.currentSorting();
            if (current.startsWith(sort)) {
                // switch direction
                const dir = current.endsWith("Dsc") ? "Asc" : "Dsc";
                self.listHelper.changeSorting(sort + dir);
            } else {
                // set asc by default
                self.listHelper.changeSorting(sort + "Asc");
            }
        };

        self.columnIcon = (sort) => {
            const current = self.listHelper.currentSorting();
            if (current.startsWith(sort)) {
                if (current.endsWith("Asc")) {
                    return "fa-solid fa-arrow-down-short-wide";
                } else {
                    return "fa-solid fa-arrow-down-wide-short";
                }
            } else {
                return "";
            }
        };

        self.lastPrint = (data) => {
            if (data.prints && data.prints.last && data.prints.last.date) {
                return data.prints.last.date;
            }
            return null;
        };

        self.searchQuery = ko.observable(undefined);
        self.searchQuery.subscribe(function () {
            self.performSearch();
        });

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

        self.foldersOnlyList = ko.dependentObservable(function () {
            var filter = function (data) {
                return data["type"] && data["type"] == "folder";
            };
            return _.filter(self.listHelper.paginatedItems(), filter);
        });
        self.filesOnlyList = ko.dependentObservable(function () {
            var filter = function (data) {
                return data["type"] && data["type"] != "folder";
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

        self.showDialog = () => {
            self.currentStorage(self.files.currentStorage());

            if (!self.dialog.hasClass("in")) {
                self.dialog
                    .modal({
                        minHeight: function () {
                            return Math.max($.fn.modal.defaults.maxHeight() - 80, 250);
                        }
                    })
                    .css({
                        "margin-left": function () {
                            return -($(this).width() / 2);
                        }
                    });
            }

            return false;
        };

        self._lastClickedItem = undefined;

        self.selectionText = ko.pureComputed(() => {
            const count = self.selectedFiles().length;
            return _.sprintf(gettext("%(count)d selected"), {count: count});
        });

        self.selectionSize = ko.pureComputed(() => {
            const files = self.selectedFiles();
            let sum = 0;
            _.each(files, (item) => {
                if (item.size == undefined) return;
                sum += item.size;
            });
            return _.sprintf(gettext("Size: %(size)s"), {size: formatSize(sum)});
        });

        self.handleSingleClick = function (data, event) {
            // prevent shift click from highlighting text
            document.getSelection().removeAllRanges();

            const last = self._lastClickedItem;
            self._lastClickedItem = data;

            // Command for Mac, Control for everything else
            const isMacOS = OctoPrint.coreui.browser.is_mac;
            const multiSelectEnabled =
                (!isMacOS && event.ctrlKey) || (isMacOS && event.metaKey);

            const isShiftSelect = event.shiftKey && last;

            if (isShiftSelect) {
                // handle shift click
                const files = self.filesAndFolders();
                const indexCurrent = files.indexOf(data);
                const indexLast = files.indexOf(last);
                log.debug(
                    "UPMGR: Current index:",
                    indexCurrent,
                    ", last index:",
                    indexLast
                );

                const selectedRanges = self.selectedRanges();
                log.debug("UPMGR: Selected ranges", selectedRanges);

                if (
                    indexCurrent >= 0 &&
                    indexLast >= 0 &&
                    Math.abs(indexCurrent - indexLast) > 0
                ) {
                    let from, to;
                    if (indexCurrent > indexLast) {
                        from = indexLast;
                        to = indexCurrent;
                    } else {
                        from = indexCurrent;
                        to = indexLast;
                    }

                    let range = undefined;
                    selectedRanges.forEach(([start, end]) => {
                        if (start <= indexLast && indexLast <= end) {
                            range = [start, end];
                        }
                    });
                    log.debug("UPMGR: Current range", range);

                    const currentWithinRange =
                        range && range[0] <= indexCurrent && indexCurrent <= range[1];
                    const currentAboveRange =
                        !currentWithinRange && range && range[0] > indexCurrent;
                    const currentBelowRange =
                        !currentWithinRange && range && range[1] < indexCurrent;
                    const rangeLength = range ? range[1] - range[0] : -1;

                    log.debug(
                        "UPMGR:",
                        "within",
                        currentWithinRange,
                        ", above",
                        currentAboveRange,
                        ", below",
                        currentBelowRange
                    );

                    for (let i = from; i <= to; i++) {
                        const item = files[i];
                        const selected = self.isSelected(item);
                        if (rangeLength > 0 && selected) {
                            if (
                                (currentWithinRange && i !== indexCurrent) ||
                                (currentAboveRange && i > range[0]) ||
                                (currentBelowRange && i < range[1])
                            ) {
                                self.selectedFiles.remove(item);
                            }
                        } else if (!selected) {
                            self.selectedFiles.push(item);
                        }
                    }
                }
            } else {
                if (!multiSelectEnabled) {
                    // single selection & no shift: remove all first
                    self.selectedFiles.removeAll();
                }

                if (self.isSelected(data)) {
                    self.selectedFiles.remove(data);
                } else {
                    self.selectedFiles.push(data);
                }
            }
        };

        self.handleDoubleClick = function (data) {
            if (!data.hasOwnProperty("type")) return;

            if (data.type == "folder") {
                self.changeFolder(data);
            } else if (
                data.type == "machinecode" &&
                self.files.enableSelect(data, false)
            ) {
                self.files.loadFile(data, false);
            }
        };

        self.invertSelection = () => {
            const files = self.filesAndFolders();
            const selectedFiles = self.selectedFiles();

            const newSelection = [];
            _.each(files, (file) => {
                if (selectedFiles.indexOf(file) < 0) {
                    newSelection.push(file);
                }
            });
            self.selectedFiles(newSelection);
        };

        self.changeFolder = (data) => {
            self.deselectAll();

            self.currentPath(data.path);
            self.listHelper.updateItems(data.children);
        };

        self.changeFolderByPath = (path, storage) => {
            storage = storage || self.currentStorage();

            self.deselectAll();

            const element = self.files.elementByPathAndStorage(path, storage);
            if (element) {
                self.currentPath(path);
                self.listHelper.updateItems(element.children);
            } else {
                self.currentPath("");
                self.listHelper.updateItems(self.files.itemsForStorage(storage));
            }
        };
        self.changeStorage = (key) => {
            if (self.files.availableStorages().indexOf(key) < 0) return;
            self.currentStorage(key);
        };

        self.navigateUp = () => {
            const path = self.currentPath().split("/");
            path.pop();
            self.changeFolderByPath(path.join("/"));
        };

        self.selectAll = function () {
            const list = self.filesAndFolders();

            _.each(list, (element) => {
                if (!self.isSelected(element)) {
                    self.selectedFiles.push(element);
                }
            });
        };

        self.selectAllOfOrigin = (origin) => {
            const list = self.filesAndFolders();

            _.each(list, (element) => {
                if (element.origin == origin && !self.isSelected(element)) {
                    self.selectedFiles.push(element);
                }
            });
        };

        self.selectAllOfType = (type) => {
            const list = self.filesAndFolders();

            _.each(list, (element) => {
                if (element.type == type && !self.isSelected(element)) {
                    self.selectedFiles.push(element);
                }
            });
        };

        self.deselectAll = function () {
            self.selectedFiles.removeAll();
            self._lastClickedItem = undefined;
        };

        self.isSelected = function (data) {
            return self.selectedFiles.indexOf(data) != -1;
        };

        self.templateFor = function (data) {
            return "uploadmanager_template_" + data.type;
        };

        self.getEntryId = function (data) {
            return "uploadmanager_entry_" + md5(data["origin"] + ":" + data["name"]);
        };

        self.checkSelectedOrigin = (origin) => {
            return self.currentStorage() === origin;
        };

        self.enableRemove = () => {
            if (!self.loginState.isUser() || self.selectedFiles().length === 0)
                return false;

            return _.every(self.selectedFiles(), (item) => {
                return self.files.enableRemove(item);
            });
        };
        self.slicingAvailable = ko.pureComputed(() => {
            return self.files.slicing.enableSlicingDialog();
        });
        self.enableSlicing = () => {
            const selected = self.selectedFiles();
            if (!selected || selected.length !== 1) return false;

            const data = selected[0];

            return data.type == "model" && self.files.enableSlicing(data);
        };
        self.enableLoad = (printAfterLoad) => {
            const selected = self.selectedFiles();
            if (!selected || selected.length !== 1) return false;

            const data = selected[0];
            if (data.type !== "machinecode") return false;

            return printAfterLoad
                ? self.files.enableSelectAndPrint(data, printAfterLoad)
                : self.files.enableSelect(data);
        };
        self.renameSupported = () => {
            // rename supported: in storage move is possible
            const selected = self.selectedFiles();
            if (!selected || selected.length === 0) return false;

            const data = selected[0];
            if (!data) return false;

            const type = data.type;
            const capabilities = self.files.storageCapabilities(data.origin);

            const inStorageRenamePossible =
                (type != "folder" && capabilities.move_file) ||
                (type == "folder" && capabilities.move_folder);

            return (
                self.loginState.hasAllPermissions(
                    self.access.permissions.FILES_UPLOAD,
                    self.access.permissions.FILES_DELETE
                ) && inStorageRenamePossible
            );
        };
        self.enableRename = () => {
            // rename enabled: only one item selected
            const selected = self.selectedFiles();
            if (!selected || selected.length !== 1) return false;

            return self.renameSupported();
        };
        self.enableCopy = () => {
            // copy enabled: in or cross storage creation is possible
            const selected = self.selectedFiles();
            if (!selected || selected.length === 0) return false;

            const data = selected[0];
            if (!data) return false;

            const type = data.type;
            const capabilities = self.files.storageCapabilities(data.origin);

            const inStorageCopyPossible =
                (type != "folder" && capabilities.copy_file) ||
                (type == "folder" && capabilities.copy_folder);
            const crossStorageCopyPossible = _.any(
                _.map(
                    self.files.storageOptions(),
                    (storage) =>
                        storage.key !== data.origin &&
                        ((type === "folder" && storage.capabilities.add_folder) ||
                            (type !== "folder" && storage.capabilities.upload_file))
                )
            );

            return (
                self.loginState.hasPermission(self.access.permissions.FILES_UPLOAD) &&
                (inStorageCopyPossible || crossStorageCopyPossible)
            );
        };
        self.enableMove = () => {
            // move enabled: rename is possible or in storage remove & cross storage creation is possible
            const renamePossible = self.renameSupported();

            const selected = self.selectedFiles();
            if (!selected || selected.length === 0) return false;

            const data = selected[0];
            if (!data) return false;

            const type = data.type;
            const capabilities = self.files.storageCapabilities(data.origin);

            const inStorageRemovePossible =
                (type != "folder" && capabilities.remove_file) ||
                (type == "folder" && capabilities.remove_folder);
            const crossStorageMovePossible = _.any(
                _.map(
                    self.files.storageOptions(),
                    (storage) =>
                        storage.key !== data.origin &&
                        ((type === "folder" && storage.capabilities.add_folder) ||
                            (type !== "folder" && storage.capabilities.upload_file)) &&
                        inStorageRemovePossible
                )
            );

            return (
                self.loginState.hasAllPermissions(
                    self.access.permissions.FILES_UPLOAD,
                    self.access.permissions.FILES_DELETE
                ) &&
                (renamePossible || crossStorageMovePossible)
            );
        };

        self.enableDownload = ko.pureComputed(() => {
            if (!self.loginState.hasPermission(self.access.permissions.FILES_DOWNLOAD))
                return false;
            return !!self.downloadUrl();
        });

        self.downloadUrl = ko.pureComputed(() => {
            const files = self.selectedFiles();
            if (files.length === 0) return "";

            const currentStorage = self.currentStorage();
            if (!self.files.storageCapabilities(currentStorage).read_file) return "";

            if (!_.all(files, (item) => item.origin === currentStorage)) return "";

            // pick all files & ensure they can all be downloaded
            const allFiles = _.filter(files, (item) => item.type !== "folder");
            const downloadableFiles = _.filter(
                allFiles,
                (item) => item.refs && item.refs.download
            );
            if (allFiles.length !== downloadableFiles.length) return "";

            // pick all folders
            const allFolders = _.filter(files, (item) => item.type === "folder");

            // calculate total list of downloadables
            const downloadables = [...downloadableFiles, ..._collectFiles(allFolders)];
            if (downloadables.length === 0) return "";

            if (downloadables.length > 1 || downloadables[0].type === "folder") {
                const bulkUrl = OctoPrint.files.bulkDownloadUrl(
                    currentStorage,
                    _.map(_collectFiles(downloadables), (item) => item.path)
                );
                if (BASEURL.length + bulkUrl.length >= 2000) return "";
                return bulkUrl;
            } else {
                return downloadables[0].refs.download;
            }
        });

        self.download = () => {
            if (!self.enableDownload()) return;
            const url = self.downloadUrl();
            if (url) window.location.href = url;
        };

        self.slice = () => {
            if (!self.enableSlicing()) return;

            self.files.sliceFile(self.selectedFiles()[0]);
        };

        self.loadFile = (printAfterLoad) => {
            if (!self.enableLoad(printAfterLoad)) return;

            const file = self.selectedFiles()[0];
            self.files.loadFile(file, printAfterLoad);
        };

        self.showAddFolderDialog = () => {
            if (!self.currentStorageCanAddFolder()) return;

            if (!self.loginState.hasPermission(self.access.permissions.FILES_UPLOAD))
                return;

            showTextboxDialog({
                title: gettext("Create a new folder"),
                message: gettext("Please specify the name:"),
                validator: (value) => {
                    // check that the name is valid
                    const path = self.currentPath()
                        ? self.currentPath() + "/" + value
                        : value;
                    if (!_isPathUnique(path)) {
                        return gettext("This name is already in use!");
                    }
                    return true;
                },
                onproceed: (value) => {
                    const storage = self.currentStorage();
                    const path = self.currentPath();
                    OctoPrint.files.createFolder(storage, value, path).fail((jqXHR) => {
                        showMessageDialog({
                            title: gettext("Operation failed"),
                            message: _.sprintf(
                                gettext(
                                    "Creating new folder %(filename)s failed: %(error)s"
                                ),
                                {
                                    filename: _.escape(`${storage}:${value}`),
                                    error: _.escape(_errorFromJqXHR(jqXHR))
                                }
                            )
                        });
                    });
                }
            });
        };

        self.renameSanitizer = undefined;
        self.rename = () => {
            if (!self.enableRename()) return;

            const file = self.selectedFiles()[0];
            const folder = self.currentPath();

            const titleElement = $("[data-id='title']", self.renameDialog);
            const nameControlElement = $("[data-id='nameControl'", self.renameDialog);
            const nameCurrentElement = $("[data-id='nameCurrent'", self.renameDialog);
            const nameNewElement = $("[data-id='nameNew'", self.renameDialog);
            const nameNewInternalElement = $(
                "[data-id='nameNewInternal']",
                self.renameDialog
            );
            const errorElement = $("[data-id='error']", self.renameDialog);
            const proceedElement = $("[data-id='proceed']", self.renameDialog);

            titleElement.text(
                _.sprintf(gettext("Rename %(type)s"), {
                    type: file.type === "folder" ? gettext("folder") : gettext("file")
                })
            );
            nameCurrentElement.text(file.display);
            nameNewInternalElement.text(file.name);

            nameNewElement.val(file.display);

            const updateInternalName = () => {
                if (self.renameSanitizer) {
                    window.clearTimeout(self.renameSanitizer);
                    self.renameSanitizer = undefined;
                }

                self.renameSanitizer = window.setTimeout(() => {
                    const name = nameNewElement.val();
                    OctoPrint.files.exists(file.origin, folder, name).done((resp) => {
                        nameNewInternalElement.text(resp.sanitized_name);
                        if (resp.exists && resp.sanitized_name !== file.name) {
                            nameControlElement.addClass("text-error");
                            errorElement.show();
                            proceedElement
                                .attr("disabled", "disabled")
                                .addClass("disabled");
                        } else {
                            nameControlElement.removeClass("text-error");
                            errorElement.hide();
                            proceedElement.removeAttr("disabled").removeClass("disabled");
                        }
                    });
                }, 200);
            };
            nameNewElement.off("change.upmgr").on("change.upmgr", updateInternalName);
            nameNewElement.off("keyup.upmgr").on("keyup.upmgr", updateInternalName);
            nameNewElement.off("blur.upmgr").on("blur.upmgr", updateInternalName);

            proceedElement.off("click.upmgr").on("click.upmgr", () => {
                const newName = nameNewElement.val();
                if (file.display === newName) return;

                const from = `${folder}/${file.name}`;
                const to = `${folder}/${newName}`;
                log.info(`Renaming ${from} to ${to}`);

                OctoPrint.files
                    .move(file.origin, file.path, to)
                    .done(() => {
                        self.deselectAll();
                        self.renameDialog.modal("hide");
                    })
                    .fail((jqXHR) => {
                        showMessageDialog({
                            title: gettext("Operation failed"),
                            message: _.sprintf(
                                gettext("Renaming %(filename)s failed: %(error)s"),
                                {
                                    filename: _.escape(file.name),
                                    error: _.escape(_errorFromJqXHR(jqXHR))
                                }
                            )
                        });
                    });
            });

            self.renameDialog.modal("show");
        };

        self.showCopyMoveDialog = (action) => {
            const files = self.selectedFiles();
            if (files.length === 0) return;

            const hasFiles = _.any(_.map(files, (f) => f.type !== "folder"));
            const hasFolders = _.any(_.map(files, (f) => f.type === "folder"));

            const location = files[0].origin;
            const capabilities = self.files.storageCapabilities(location);
            const inStorageCopyPossible =
                (!hasFiles || capabilities.copy_file) &&
                (!hasFolders || capabilities.copy_folder);
            const inStorageMovePossible =
                (!hasFiles || capabilities.move_file) &&
                (!hasFolders || capabilities.move_folder);
            const inStorageActionPossible =
                (action === "copy" && inStorageCopyPossible) ||
                (action === "move" && inStorageMovePossible);

            const titleElement = $("[data-id='title']", self.copyMoveDialog);
            const sourceStorageElement = $(
                "[data-id='sourceStorage']",
                self.copyMoveDialog
            );
            const selectStorageElement = $(
                "[data-id='selectStorage']",
                self.copyMoveDialog
            );
            const sourcePathElement = $("[data-id='sourcePath']", self.copyMoveDialog);
            const selectPathElement = $("[data-id='selectPath']", self.copyMoveDialog);
            const allowOverwriteElement = $(
                "[data-id='allowOverwrite']",
                self.copyMoveDialog
            );
            const proceedElement = $("[data-id='proceed']", self.copyMoveDialog);

            if (action === "copy") {
                titleElement.text(gettext("Select destination for copy"));
            } else if (action === "move") {
                titleElement.text(gettext("Select destination for move"));
            } else {
                return;
            }

            sourceStorageElement.text(location);

            const storageOptions = self.files.storageOptions();
            selectStorageElement.empty();
            _.each(storageOptions, (storage) => {
                if (storage.key === location && !inStorageActionPossible) {
                    // skip current storage if it doesn't support copy/move
                    return;
                }
                if (
                    storage.key !== location &&
                    ((hasFiles && !self.files.storageCanUpload(storage.key)) ||
                        (hasFolders && !self.files.storageCanAddFolder(storage.key)))
                ) {
                    // skip other storages that can't write files or add folders
                    return;
                }

                const element = $("<option></option>")
                    .text(storage.name)
                    .val(storage.key);
                if (storage.key === location) {
                    element.attr("selected", "selected");
                }
                selectStorageElement.append(element);
            });

            const currentPath = "/" + self.currentPath();
            sourcePathElement.text(currentPath);

            const updateFolders = (loc) => {
                const folders = _collectFolders(loc);
                selectPathElement.empty();
                _.each(folders, (folder) => {
                    const element = $("<option></option>").text(folder).val(folder);
                    if (folder === currentPath) {
                        element.attr("selected", "selected");
                    }
                    selectPathElement.append(element);
                });
            };

            selectStorageElement.off("change.upmgr").on("change.upmgr", () => {
                const destinationStorage = $(
                    "option:selected",
                    selectStorageElement
                ).val();
                updateFolders(destinationStorage);
            });
            updateFolders(location);

            proceedElement.off("click.upmgr").on("click.upmgr", () => {
                const destinationStorage = $(
                    "option:selected",
                    selectStorageElement
                ).val();
                const destinationPath = $("option:selected", selectPathElement).val();
                const allowOverwrite = !!allowOverwriteElement.prop("checked");
                self.copyMoveDialog.modal("hide");
                if (action === "copy") {
                    self.copy(destinationStorage, destinationPath, allowOverwrite);
                } else if (action === "move") {
                    self.move(destinationStorage, destinationPath, allowOverwrite);
                }
            });

            allowOverwriteElement.prop("checked", false);

            self.copyMoveDialog.modal("show");
        };

        self.copy = (storage, destination, allowOverwrite) => {
            if (!self.enableCopy()) return;
            if (!storage) return;
            if (!destination) return;

            destination = destination.substr(1);
            if (storage == self.currentStorage() && destination === self.currentPath())
                return;

            self._bulkAction(
                (file) => {
                    if (file.origin === storage) {
                        return OctoPrint.files.copy(
                            file.origin,
                            file.path,
                            destination + "/",
                            allowOverwrite
                        );
                    } else {
                        return OctoPrint.files.copyAcrossStorage(
                            file.origin,
                            file.path,
                            storage,
                            destination + "/",
                            allowOverwrite
                        );
                    }
                },
                gettext("Copying"),
                _.sprintf(gettext("Copying %%(count)d items to %(destination)s..."), {
                    destination
                }),
                _.sprintf(
                    gettext("Copying %%(filename)s to %(storage)s:%(destination)s..."),
                    {storage, destination}
                ),
                _.sprintf(
                    gettext("Copied %%(filename)s to %(storage)s:%(destination)s..."),
                    {storage, destination}
                ),
                _.sprintf(
                    gettext(
                        "Copying %%(filename)s to %(storage)s:%(destination)s failed, continuing..."
                    ),
                    {storage, destination}
                ),
                _.sprintf(
                    gettext(
                        "Copying %%(filename)s to %(storage)s:%(destination)s failed: %%(error)s"
                    ),
                    {storage, destination}
                ),
                (file) => file.path != destination
            );
        };

        self.move = (storage, destination, allowOverwrite) => {
            if (!self.enableMove()) return;
            if (!storage) return;
            if (!destination) return;

            destination = destination.substr(1);
            if (storage == self.currentStorage() && destination === self.currentPath())
                return;

            self._bulkAction(
                (file) => {
                    if (file.origin === storage) {
                        return OctoPrint.files.move(
                            file.origin,
                            file.path,
                            destination + "/",
                            allowOverwrite
                        );
                    } else {
                        return OctoPrint.files.moveAcrossStorage(
                            file.origin,
                            file.path,
                            storage,
                            destination + "/",
                            allowOverwrite
                        );
                    }
                },
                gettext("Moving"),
                _.sprintf(gettext("Moving %%(count)d items to %(destination)s..."), {
                    destination
                }),
                _.sprintf(
                    gettext("Moving %%(filename)s to %(storage)s:%(destination)s..."),
                    {storage, destination}
                ),
                _.sprintf(
                    gettext("Moved %%(filename)s to %(storage)s:%(destination)s..."),
                    {storage, destination}
                ),
                _.sprintf(
                    gettext(
                        "Moving %%(filename)s to %(storage)s:%(destination)s failed, continuing..."
                    ),
                    {storage, destination}
                ),
                _.sprintf(
                    gettext(
                        "Moving %%(filename)s to %(storage)s:%(destination)s failed: %%(error)s"
                    ),
                    {storage, destination}
                ),
                (file) => file.path != destination
            );
        };

        self.remove = () => {
            if (!self.enableRemove()) return;

            const files = self.selectedFiles();
            if (files.length === 0) return;

            let message;
            let confirm = true;
            if (files.length > 1) {
                message = _.sprintf(
                    gettext("You are about to delete %(count)d items forever."),
                    {count: files.length}
                );
            } else {
                if (files[0].type === "folder") {
                    message = _.sprintf(
                        gettext(
                            'You are about to delete the folder "%(folder)s" forever which still contains files and/or sub folders.'
                        ),
                        {folder: files[0].name}
                    );
                    confirm = !!files[0].weight;
                } else {
                    message = _.sprintf(
                        gettext('You are about to delete "%(file)s" forever.'),
                        {file: files[0].name}
                    );
                }
            }

            const proceed = () => {
                self._bulkAction(
                    (file) => {
                        return OctoPrint.files.delete(file.origin, file.path);
                    },
                    gettext("Deleting"),
                    gettext("Deleting %(count)d items..."),
                    gettext("Deleting %(filename)s..."),
                    gettext("Deleted %(filename)s..."),
                    gettext("Deletion of %(filename)s failed, continuing..."),
                    gettext("Deletion of %(filename)s failed: %(error)s")
                );
            };

            if (confirm) {
                showConfirmationDialog(message, proceed);
            } else {
                proceed();
            }
        };

        self.refreshingThumbnails = ko.observable(false);
        self.enableRefreshThumbnails = () => {
            const selected = self.selectedFiles();
            if (!selected || selected.length === 0) return false;

            const capabilities = self.files.storageCapabilities(selected[0].origin);
            return capabilities.thumbnails;
        };
        self.refreshThumbnails = () => {
            if (!self.enableRefreshThumbnails()) return;

            const files = self.selectedFiles();
            if (files.length === 0) return;

            self.refreshingThumbnails(true);
            if (files.length > 1) {
                self._bulkAction(
                    (file) => {
                        return OctoPrint.files.refreshThumbnails(file.origin, file.path, {
                            force: true
                        });
                    },
                    gettext("Refreshing thumbnails"),
                    gettext("Refreshing thumbnails for %(count)d items..."),
                    gettext("Refreshing thumbnails for %(filename)s..."),
                    gettext("Refreshed thumbnails for %(filename)s..."),
                    gettext(
                        "Refreshing thumbnails of %(filename)s failed, continuing..."
                    ),
                    gettext("Refreshing thumbnails of %(filename)s failed: %(error)s")
                ).always(() => {
                    self.refreshingThumbnails(false);
                });
            } else {
                OctoPrint.files
                    .refreshThumbnails(files[0].origin, files[0].path, {
                        force: true
                    })
                    .always(() => {
                        self.refreshingThumbnails(false);
                    });
            }
        };

        self._bulkAction = (
            callback,
            title,
            message,
            inProgress,
            ok,
            nokShort,
            nokLong,
            fileFilter
        ) => {
            const files =
                fileFilter && _.isFunction(fileFilter)
                    ? _.filter(self.selectedFiles(), fileFilter)
                    : self.selectedFiles();
            if (!files || files.length === 0) return;

            const handler = (file) => {
                const filename = `${file.origin}:${file.path}`;

                deferred.notify(_.sprintf(inProgress, {filename: _.escape(filename)}));
                return callback(file)
                    .done(() => {
                        deferred.notify(
                            _.sprintf(ok, {
                                filename: _.escape(filename)
                            }),
                            true
                        );
                    })
                    .fail((jqXHR) => {
                        const short = _.sprintf(nokShort, {
                            filename: _.escape(filename)
                        });
                        const long = _.sprintf(nokLong, {
                            filename: _.escape(filename),
                            error: _.escape(_errorFromJqXHR(jqXHR))
                        });
                        deferred.notify(short, long, false);
                    });
            };

            const deferred = $.Deferred();
            const promise = deferred.promise();

            const options = {
                title: title,
                message: _.sprintf(message, {
                    count: files.length
                }),
                max: files.length,
                output: true,
                close: files.length == 1
            };
            showProgressModal(options, promise);

            self.files.ignoreUpdatedFilesEvent = true;
            const requests = [];
            _.each(files, (file) => {
                const request = handler(file);
                requests.push(request);
            });

            const finish = () => {
                self.files.ignoreUpdatedFilesEvent = false;
                deferred.resolve();
                self.deselectAll();
                self.files.requestData();
            };

            if (requests.length == 1) {
                requests[0].always(finish);
            } else {
                $.when.apply($, _.map(requests, wrapPromiseWithAlways)).done(finish);
            }

            return promise;
        };

        self.onStartup = () => {
            self.dialog = $("#plugin_uploadmanager_dialog");
            self.renameDialog = $("#plugin_uploadmanager_rename");
            self.copyMoveDialog = $("#plugin_uploadmanager_copymove");
        };

        self.onAfterBinding = () => {
            const link = $(
                "<a href='javascript:void(0)'><i class='fa-solid fa-folder-tree'></i></a>"
            );
            link.click(() => {
                self.showDialog();
            });

            const button = $("<div class='accordion-heading-button btn-group'></div>");
            button.append(link);
            button.insertAfter("#files_wrapper .accordion-heading .settings-trigger");
        };

        self.onStartupComplete = () => {
            self.files.storageFiles.subscribe(() => {
                self.deselectAll();
                self.changeFolderByPath(self.currentPath(), self.currentStorage());
            });
            self.files.availableStorages.subscribe((val) => {
                if (val.indexOf(self.currentStorage()) < 0) {
                    self.currentStorage("local");
                }
            });
        };

        self.fromCurrentData = self.fromHistoryData = (data) => {
            if (data.job && data.job.file && data.job.file.path && data.job.file.origin) {
                // emphasize currently selected file
                if (
                    self.listHelper.selectItem((item) => {
                        if (item.origin !== data.job.file.origin) return false;

                        if (item.type === "folder") {
                            return _.startsWith(data.job.file.path, item.path + "/");
                        } else {
                            return item.path === data.job.file.path;
                        }
                    })
                ) {
                    return;
                }
            }

            self.listHelper.selectNone();
        };

        const _isPathUnique = (path, exceptions) => {
            exceptions = exceptions || [];
            if (_.contains(exceptions, path)) return true;

            const paths = _collectPaths();
            return !_.contains(paths, path);
        };

        const _collectPaths = () => {
            const files = self.files.allItems();

            const pathPicker = (items) => {
                const paths = [];
                _.each(items, (item) => {
                    paths.push(item.path);
                    if (item.children) {
                        paths.push(...pathPicker(item.children));
                    }
                });
                return paths;
            };

            return pathPicker(files);
        };

        const _collectFolders = (location) => {
            const files = self.files.allItems();

            const folderPicker = (items) => {
                const folders = [];
                _.each(items, (item) => {
                    if (item.type !== "folder") return;
                    if (item.origin !== location) return;
                    folders.push(`/${item.path}`);
                    if (item.children) {
                        folders.push(...folderPicker(item.children));
                    }
                });
                return folders;
            };

            const folders = folderPicker(files);
            folders.push("/");
            folders.sort();
            return folders;
        };

        const _collectFiles = (items) => {
            const files = [];
            _.each(items, (item) => {
                if (item.type !== "folder" && item.refs && item.refs.download) {
                    files.push(item);
                } else if (item.type === "folder" && item.children) {
                    files.push(..._collectFiles(item.children));
                }
            });
            return files;
        };

        const _errorFromJqXHR = (jqXHR) => {
            let error = jqXHR.responseText;
            try {
                const json = JSON.parse(jqXHR.responseText);
                if (json.error) error = json.error;
            } catch (e) {
                // no json apparently
            }
            return error;
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: UploadmanagerViewModel,
        dependencies: [
            "filesViewModel",
            "loginStateViewModel",
            "accessViewModel",
            "slicingViewModel",
            "settingsViewModel"
        ],
        elements: ["#plugin_uploadmanager_dialog"]
    });
});
