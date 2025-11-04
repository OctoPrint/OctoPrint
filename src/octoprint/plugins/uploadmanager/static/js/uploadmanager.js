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
                sd: (data) => {
                    return data["origin"] && data["origin"] == "printer";
                },
                local: (data) => {
                    return !(data["origin"] && data["origin"] == "printer");
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
            if (data.origin === "printer") return "uploadmanager_template_printer";
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

        self.enableUploadSD = () => {
            return (
                self.loginState.isUser() &&
                self.selectedFiles().length === 1 &&
                self.files.isSdReady() &&
                self.checkSelectedOrigin("local")
            );
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
            const files = self.selectedFiles();
            if (files.length !== 1) return false;

            return files[0].type == "model" && self.files.enableSlicing(files[0]);
        };
        self.enableLoad = (printAfterLoad) => {
            const files = self.selectedFiles();
            if (files.length !== 1) return false;

            return files[0].type == "machinecode" && printAfterLoad
                ? self.files.enableSelectAndPrint(files[0], printAfterLoad)
                : self.files.enableSelect(files[0]);
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

        self.enableDownload = ko.pureComputed(() => {
            if (!self.loginState.hasPermission(self.access.permissions.FILES_DOWNLOAD))
                return false;
            return !!self.downloadUrl();
        });

        self.downloadUrl = ko.pureComputed(() => {
            const files = self.selectedFiles();
            if (files.length === 0) return "";
            if (!_.all(files, (item) => item.origin === "local")) return "";

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
                const bulkUrl = OctoPrint.files.bulkDownloadUrlLocal(
                    _.map(_collectFiles(downloadables), (item) => item.path)
                );
                if (BASEURL.length + bulkUrl.length >= 2000) return "";
                return bulkUrl;
            } else {
                return downloadables[0].refs.download;
            }
        });

        self.uploadSD = () => {
            if (!self.enableUploadSD()) return;

            const file = self.selectedFiles()[0];
            if (file.origin !== "local") return;

            OctoPrint.files.issueEntryCommand(file.origin, file.path, "copy_storage", {
                storage: "printer",
                destination: file.path
            });
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
                    const path = self.currentPath();
                    OctoPrint.files.createFolder("local", value, path).fail((jqXHR) => {
                        showMessageDialog({
                            title: gettext("Operation failed"),
                            message: _.sprintf(
                                gettext(
                                    "Creating new folder %(filename)s failed: %(error)s"
                                ),
                                {
                                    filename: _.escape(`local:${value}`),
                                    error: _.escape(_errorFromJqXHR(jqXHR))
                                }
                            )
                        });
                    });
                }
            });
        };

        self.rename = () => {
            if (!self.enableRename()) return;

            const file = self.selectedFiles()[0];
            const name = file.name;
            const origin = file.origin;
            const from = file.path;

            showTextboxDialog({
                title: _.sprintf(gettext("Rename %(name)s"), {name: name}),
                message: gettext("Please specify the new name:"),
                value: name,
                validator: (value) => {
                    // check that the name is valid
                    log.info("checking validity of ", value);
                    const path = self.currentPath()
                        ? self.currentPath() + "/" + value
                        : value;
                    if (!_isPathUnique(path, [from])) {
                        return gettext("This name is already in use!");
                    }
                    return true;
                },
                onproceed: (value) => {
                    if (name === value) return;
                    const folder = self.currentPath();
                    const to = `${folder}/${value}`;
                    log.info(`Renaming ${from} to ${to}`);
                    OctoPrint.files
                        .move(origin, from, to)
                        .done(() => {
                            self.deselectAll();
                        })
                        .fail((jqXHR) => {
                            showMessageDialog({
                                title: gettext("Operation failed"),
                                message: _.sprintf(
                                    gettext("Renaming %(filename)s failed: %(error)s"),
                                    {
                                        filename: _.escape(filename),
                                        error: _.escape(_errorFromJqXHR(jqXHR))
                                    }
                                )
                            });
                        });
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
                gettext("Copying %(filename)s failed: %(error)s"),
                (file) => file.path != destination
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
                gettext("Moving %(filename)s failed: %(error)s"),
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

        self._bulkAction = (
            callback,
            title,
            message,
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
                const file = self.selectedFiles()[0];
                const filename = `${file.origin}:${file.path}`;
                return callback(file)
                    .done(() => {
                        self.deselectAll();
                    })
                    .fail((jqXHR) => {
                        showMessageDialog({
                            title: gettext("Operation failed"),
                            message: _.sprintf(nokLong, {
                                filename: _.escape(filename),
                                error: _.escape(_errorFromJqXHR(jqXHR))
                            })
                        });
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
