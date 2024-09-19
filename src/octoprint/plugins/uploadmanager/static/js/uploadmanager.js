/**
 * Created by Salandora on 06.09.2015.
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
        self.currentPath = ko.observable("");
        self.listStyle = ko.observable("folders_files");

        if (self.files.hasOwnProperty("allItems")) {
            self.files.allItems.subscribe(function (newValue) {
                self.listHelper.updateItems(newValue);
                self.selectedFiles([]);
                self.changeFolderByPath(self.currentPath());
            });
        }

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
                    if (b.prints && b.prints.last && b.prints.date) {
                        if (a.prints.last.date > b.prints.last.date) return 1;
                        if (a.prints.last.date < b.prints.last.date) return -1;
                        return 0;
                    }
                    return 1;
                },
                lastPrintDsc: (a, b) => {
                    // sorts descending
                    if (b.prints && b.prints.last && b.prints.date) {
                        if (a.prints.last.date > b.prints.last.date) return -1;
                        if (a.prints.last.date < b.prints.last.date) return 1;
                        return 0;
                    }
                    return -1;
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
                sd: (data) => {
                    return data["origin"] && data["origin"] == "sdcard";
                },
                local: (data) => {
                    return !(data["origin"] && data["origin"] == "sdcard");
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
            [
                ["sd", "local"],
                ["machinecode", "model"]
            ],
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
            filter = function (data) {
                return data["type"] && data["type"] == "folder";
            };
            return _.filter(self.listHelper.paginatedItems(), filter);
        });
        self.filesOnlyList = ko.dependentObservable(function () {
            filter = function (data) {
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

        self.handleSingleClick = function (data, event) {
            // prevent shift click from highlighting text
            document.getSelection().removeAllRanges();

            const last = self._lastClickedItem;
            self._lastClickedItem = data;

            if (self.isSelected(data)) {
                self.selectedFiles.remove(data);
            } else {
                if (!event.ctrlKey) {
                    // single selection if ctrl isn't pressed
                    self.selectedFiles.removeAll();
                }
                self.selectedFiles.push(data);
            }

            if (event.shiftKey && last) {
                // handle shift click
                const files = self.filesAndFolders();
                const indexCurrent = files.indexOf(data);
                const indexLast = files.indexOf(last);

                if (
                    indexCurrent >= 0 &&
                    indexLast >= 0 &&
                    Math.abs(indexCurrent - indexLast) > 1
                ) {
                    let from, to;
                    if (indexCurrent > indexLast) {
                        from = indexLast;
                        to = indexCurrent;
                    } else {
                        from = indexCurrent;
                        to = indexLast;
                    }

                    for (let i = from; i <= to; i++) {
                        if (i === indexCurrent || i === indexLast) {
                            // already handled
                            continue;
                        }

                        const item = files[i];
                        if (self.isSelected(item)) {
                            self.selectedFiles.remove(item);
                        } else {
                            self.selectedFiles.push(item);
                        }
                    }
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

            self.currentPath(OctoPrint.files.pathForEntry(data));
            self.listHelper.updateItems(data.children);
        };

        self.changeFolderByPath = (path) => {
            self.deselectAll();

            const element = self.files.elementByPath(path, {
                children: self.files.allItems()
            });
            if (element) {
                self.currentPath(path);
                self.listHelper.updateItems(element.children);
            } else {
                self.currentPath("");
                self.listHelper.updateItems(self.files.allItems());
            }
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
                    self._lastClickedItem = element;
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
            return _.every(self.selectedFiles(), (item) => {
                return item.hasOwnProperty("origin") && item.origin === origin;
            });
        };

        self.enableDownload = function () {
            var selected = self.selectedFiles();

            var data = self.selectedFiles();
            for (var i = 0; i < data.length; i++) {
                var element = data[i];
                if (
                    !element.hasOwnProperty("type") ||
                    !element.hasOwnProperty("origin") ||
                    element.type == "folder" ||
                    element.origin != "local"
                )
                    return false;
            }

            return selected.length != 0;
        };
        self.enableUploadSD = function () {
            return (
                self.loginState.isUser() &&
                self.selectedFiles().length === 1 &&
                self.files.isSdReady() &&
                self.checkSelectedOrigin("local")
            );
        };
        self.enableRemove = function () {
            if (!self.loginState.isUser() || self.selectedFiles().length === 0)
                return false;

            return _.every(self.selectedFiles(), (item) => {
                return self.files.enableRemove(item);
            });
        };
        self.enableSlicing = function () {
            const files = self.selectedFiles();
            if (files.length !== 1) return false;

            return files[0].type == "model" && self.files.enableSlicing(files[0]);
        };
        self.enableSelect = function (printAfterSelect) {
            const files = self.selectedFiles();
            if (files.length !== 1) return false;

            return (
                files[0].type == "machinecode" &&
                self.files.enableSelect(files[0], printAfterSelect)
            );
        };
        self.enableRename = () => {
            return (
                self.loginState.hasAllPermissions(
                    self.access.permissions.FILES_UPLOAD,
                    self.access.permissions.FILES_DELETE
                ) &&
                self.selectedFiles().length == 1 &&
                self.checkSelectedOrigin("local")
            );
        };
        self.enableCopy = () => {
            return (
                self.loginState.hasPermission(self.access.permissions.FILES_UPLOAD) &&
                self.selectedFiles().length > 0 &&
                self.checkSelectedOrigin("local")
            );
        };
        self.enableMove = () => {
            return (
                self.loginState.hasAllPermissions(
                    self.access.permissions.FILES_UPLOAD,
                    self.access.permissions.FILES_DELETE
                ) &&
                self.selectedFiles().length > 0 &&
                self.checkSelectedOrigin("local")
            );
        };

        self.download = function () {
            if (!self.enableDownload()) return;

            _.each(self.selectedFiles(), function (file, index) {
                $.fileDownload(self.files.downloadLink(file), {
                    data: {cookie: "fileDownload" + index},
                    cookieName: "fileDownload" + index
                });
            });
        };

        self.uploadSD = () => {
            if (!self.enableUploadSD()) return;

            const file = self.selectedFiles()[0];
            if (file.origin !== "local") return;

            OctoPrint.files.issueEntryComand(file.origin, file.path, "uploadSd", {});
        };

        self.slice = () => {
            if (!self.enableSlicing()) return;

            self.files.sliceFile(self.selectedFiles()[0]);
        };

        self.loadFile = (printAfterSelect) => {
            if (!self.enableSelect(printAfterSelect)) return;

            const file = self.selectedFiles()[0];
            OctoPrint.files.select(file.origin, file.path, printAfterSelect);
        };

        self.showAddFolderDialog = () => {
            if (!self.loginState.hasPermission(self.access.permissions.FILES_UPLOAD))
                return;

            showTextboxDialog({
                title: gettext("Create a new folder"),
                message: gettext("Please specify the name:"),
                validator: (value) => {
                    // check that the name is valid
                    if (!_isNameUnique(value)) {
                        return gettext("This name is already in use!");
                    }
                    return true;
                },
                onproceed: (value) => {
                    const path = self.currentPath();
                    OctoPrint.files.createFolder("local", value, path);
                }
            });
        };

        self.rename = () => {
            if (!self.enableRename()) return;

            const name = self.selectedFiles()[0].name;
            const origin = self.selectedFiles()[0].origin;
            const from = self.selectedFiles()[0].path;

            showTextboxDialog({
                title: _.sprintf(gettext("Rename %(name)s"), {name: name}),
                message: gettext("Please specify the new name:"),
                value: name,
                validator: (value) => {
                    // check that the name is valid
                    log.info("checking validity of ", value);
                    if (!_isNameUnique(value, [name])) {
                        return gettext("This name is already in use!");
                    }
                    return true;
                },
                onproceed: (value) => {
                    if (name === value) return;
                    const folder = self.currentPath();
                    const to = `${folder}/${value}`;
                    log.info(`Renaming ${from} to ${to}`);
                    OctoPrint.files.move(origin, from, to);
                }
            });
        };

        self.showCopyMoveDialog = (action) => {
            const files = self.selectedFiles();
            if (files.length === 0) return;

            const location = files[0].origin;

            const titleElement = $("[data-id='title']", self.copyMoveDialog);
            const sourceElement = $("[data-id='source']", self.copyMoveDialog);
            const selectElement = $("[data-id='select']", self.copyMoveDialog);
            const proceedElement = $("[data-id='proceed']", self.copyMoveDialog);

            if (action === "copy") {
                titleElement.text(gettext("Select destination for copy"));
            } else if (action === "move") {
                titleElement.text(gettext("Select destination for move"));
            } else {
                return;
            }

            const currentPath = "/" + self.currentPath();
            sourceElement.text(currentPath);

            const folders = _collectFolders(location);
            selectElement.empty();
            _.each(folders, (folder) => {
                const element = $("<option></option>").text(folder).val(folder);
                if (folder === currentPath) {
                    element.attr("selected", "selected");
                }
                selectElement.append(element);
            });

            proceedElement.unbind("click").bind("click", () => {
                const destination = $("option:selected", selectElement).val();
                self.copyMoveDialog.modal("hide");
                if (action === "copy") {
                    self.copy(destination);
                } else if (action === "move") {
                    self.move(destination);
                }
            });

            self.copyMoveDialog.modal("show");
        };

        self.copy = (destination) => {
            if (!self.enableCopy()) return;
            if (!destination) return;

            destination = destination.substr(1);
            if (destination === self.currentPath()) return;

            self._bulkAction(
                (file) => {
                    return OctoPrint.files.copy(file.origin, file.path, destination);
                },
                gettext("Copying"),
                _.sprintf(gettext("Copying %%(count)d items to %(destination)s..."), {
                    destination
                }),
                gettext("Copied %(filename)s..."),
                gettext("Copying %(filename)s failed, continuing..."),
                gettext("Copying %(filename)s failed: %(error)s")
            );
        };

        self.move = (destination) => {
            if (!self.enableMove()) return;
            if (!destination) return;

            destination = destination.substr(1);
            if (destination === self.currentPath()) return;

            self._bulkAction(
                (file) => {
                    return OctoPrint.files.move(file.origin, file.path, destination);
                },
                gettext("Moving"),
                _.sprintf(gettext("Moving %%(count)d items to %(destination)s..."), {
                    destination
                }),
                gettext("Moved %(filename)s..."),
                gettext("Moving %(filename)s failed, continuing..."),
                gettext("Moving %(filename)s failed: %(error)s")
            );
        };

        self.remove = () => {
            if (!self.enableRemove()) return;

            return self._bulkAction(
                (file) => {
                    return OctoPrint.files.delete(file.origin, file.path);
                },
                gettext("Deleting"),
                gettext("Deleting %(count)d items..."),
                gettext("Deleted %(filename)s..."),
                gettext("Deletion of %(filename)s failed, continuing..."),
                gettext("Deletion of %(filename)s failed: %(error)s")
            );
        };

        self._bulkAction = (callback, title, message, ok, nokShort, nokLong) => {
            const files = self.selectedFiles();
            if (!files) return;

            if (files.length > 1) {
                // bulk operation
                const handler = (file) => {
                    const filename = `${file.origin}:${file.path}`;

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
                                error: _.escape(jqXHR.responseText)
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
                    output: true
                };
                showProgressModal(options, promise);

                self.files.ignoreUpdatedFilesEvent = true;
                const requests = [];
                _.each(files, (file) => {
                    const request = handler(file);
                    requests.push(request);
                });
                $.when.apply($, _.map(requests, wrapPromiseWithAlways)).done(() => {
                    self.files.ignoreUpdatedFilesEvent = false;
                    deferred.resolve();
                    self.deselectAll();
                    self.files.requestData();
                });

                return promise;
            } else {
                // only one file
                return callback(self.selectedFiles()[0]).done(() => {
                    self.deselectAll();
                });
            }
        };

        self.onStartup = () => {
            self.dialog = $("#plugin_uploadmanager_dialog");
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

        const _isNameUnique = (name, exceptions) => {
            exceptions = exceptions || [];
            const files = self.files.allItems();
            return _.every(files, (item) => {
                return item.name !== name || _.contains(exceptions, item.name);
            });
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
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: UploadmanagerViewModel,
        dependencies: [
            "gcodeFilesViewModel",
            "loginStateViewModel",
            "accessViewModel",
            "slicingViewModel",
            "settingsViewModel"
        ],
        elements: ["#plugin_uploadmanager_dialog"]
    });
});
