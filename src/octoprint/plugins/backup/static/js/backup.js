$(function () {
    function BackupViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];

        self.backups = new ItemListHelper(
            "plugin.backup.backups",
            {
                date: function (a, b) {
                    // sorts descending
                    if (a["date"] > b["date"]) return -1;
                    if (a["date"] < b["date"]) return 1;
                    return 0;
                }
            },
            {},
            "date",
            [],
            [],
            10
        );

        self.markedForBackupDeletion = ko.observableArray([]);

        self.backupInProgress = ko.observable(false);

        self.backupTarget = ko.observable("");
        self.backupProgress = ko.observable(-1);
        self.backupProgressUnknown = ko.pureComputed(() => {
            return !self.backupTarget() || self.backupProgress() < 0;
        });
        self.backupProgressString = ko.pureComputed(() => {
            if (self.backupProgressUnknown()) {
                return 0;
            }

            return self.backupProgress();
        });
        self.backupProgressBarString = ko.pureComputed(() => {
            if (self.backupProgressUnknown()) {
                return gettext("Creating backup...");
            }

            return _.sprintf(gettext("Creating backup %(target)s... (%(progress)d%%)"), {
                target: self.backupTarget(),
                progress: self.backupProgress()
            });
        });

        self.excludeFromBackup = ko.observableArray([]);
        self.restoreSupported = ko.observable(true);
        self.maxUploadSize = ko.observable(0);
        self.freeTempSpace = ko.observable(0);

        self.backupUploadData = undefined;
        self.backupUploadName = ko.observable();
        self.backupUploadSource = undefined;
        self.backupUploadCompressed = ko.observable(undefined);
        self.backupUploadUncompressed = ko.observable(undefined);
        self.backupUploadTooBig = ko.observable(false);
        self.backupUploadVersion = ko.observable("-");
        self.backupUploadVersionIncompatible = ko.observable(false);
        self.backupUploadValid = ko.observable(false);
        self.backupUploadUploadsIncluded = ko.observable(false);
        self.backupUploadTimelapseIncluded = ko.observable(false);

        self.config_path = ko.observable();
        self.testPathConfigOk = ko.observable(false);
        self.testPathConfigBroken = ko.observable(false);
        self.testPathConfigBusy = ko.observable(false);
        self.testPathConfigText = ko.observable("");
        self.testPathConfig = () => {
            self.loginState.reauthenticateIfNecessary(() => {
                self.testPathConfigBusy(true);

                const path = self.config_path();
                const opts = {
                    check_type: "dir",
                    check_access: "w",
                    allow_create_dir: true,
                    check_writable_dir: true
                };

                OctoPrint.util
                    .testPath(path, opts)
                    .done((response) => {
                        if (!response.result) {
                            if (response.broken_symlink) {
                                self.testPathConfigText(
                                    gettext("The path is a broken symlink.")
                                );
                            } else if (!response.exists) {
                                self.testPathConfigText(
                                    gettext(
                                        "The path does not exist and cannot be created."
                                    )
                                );
                            } else if (!response.typeok) {
                                self.testPathConfigText(
                                    gettext("The path is not a folder.")
                                );
                            } else if (!response.access) {
                                self.testPathConfigText(
                                    gettext("The path is not writable.")
                                );
                            }
                        } else {
                            self.testPathConfigText(gettext("The path is valid"));
                        }
                        self.testPathConfigOk(response.result);
                        self.testPathConfigBroken(!response.result);
                    })
                    .always(() => {
                        self.testPathConfigBusy(false);
                    });
            });
        };

        self.configurationDialog = $("#settings_plugin_backup_configurationdialog");
        self.showPluginSettings = function () {
            self._copyConfig();
            self.configurationDialog.modal();
        };
        self.savePluginSettings = function () {
            let path = self.config_path();
            if (path !== null && path.trim() === "") {
                path = null;
            }
            var data = {
                plugins: {
                    backup: {
                        path: path
                    }
                }
            };
            self.settings.saveData(data, () => {
                self.configurationDialog.modal("hide");
                self._copyConfig();
                self.requestData();
            });
        };

        self._copyConfig = () => {
            self.config_path(self.settings.settings.plugins.backup.path());
        };

        self.isAboveUploadSize = function (data) {
            return data.size > self.maxUploadSize();
        };

        self.isAboveFreeTempSpace = function (data) {
            return (
                data.uncompressed !== undefined &&
                data.uncompressed > self.freeTempSpace()
            );
        };

        self.isVersionIncompatible = function (data) {
            const version = data.version;
            if (version === undefined) return false;

            const [backupMajor, backupMinor, backupRest] = version
                .split(".", 2)
                .map((x) => parseInt(x));
            const [octoMajor, octoMinor, octoRest] = DISPLAY_VERSION.split(".", 2).map(
                (x) => parseInt(x)
            );

            return (
                backupMajor > octoMajor ||
                (backupMajor === octoMajor && backupMinor > octoMinor)
            );
        };

        self.isRestoreImpossible = function (data) {
            return (
                !self.restoreSupported() ||
                self.isAboveFreeTempSpace(data) ||
                self.isVersionIncompatible(data)
            );
        };

        self.enableRestore = function (data) {
            return !(
                self.backupInProgress() ||
                self.restoreInProgress() ||
                self.isRestoreImpossible(data)
            );
        };

        self.enableUploadAndRestore = ko.pureComputed(() => {
            const data = {
                uncompressed: self.backupUploadUncompressed(),
                version: self.backupUploadVersion()
            };
            return (
                self.enableRestore(data) &&
                self.backupUploadData !== undefined &&
                self.backupUploadValid()
            );
        });

        const backupFileuploadOptionsFactory = (source) => {
            return {
                dataType: "json",
                maxNumberOfFiles: 1,
                autoUpload: false,
                add: (e, data) => {
                    if (data.files.length === 0) {
                        // no files? ignore
                        return false;
                    }

                    self.backupUploadName(data.files[0].name);
                    self.backupUploadData = data;
                    self.backupUploadSource = source;
                    self.backupUploadCompressed(data.files[0].size);

                    const zipfile = new zip.ZipReader(new zip.BlobReader(data.files[0]));

                    let size = 0;
                    let basedirIncluded = false;
                    let metadataIncluded = false;
                    let uploadsIncluded = false;
                    let timelapseIncluded = false;

                    zipfile.getEntries().then((entries) => {
                        entries.forEach((entry) => {
                            size += entry.uncompressedSize;
                            if (entry.filename === "metadata.json" && !entry.directory) {
                                metadataIncluded = true;
                                const metadata = entry
                                    .getData(new zip.TextWriter())
                                    .then((text) => {
                                        const parsed = JSON.parse(text);
                                        self.backupUploadVersion(parsed.version);
                                        self.backupUploadVersionIncompatible(
                                            self.isVersionIncompatible({
                                                version: parsed.version
                                            })
                                        );
                                    });
                            } else if (entry.filename.startsWith("basedir/")) {
                                basedirIncluded = true;
                                if (entry.filename.startsWith("basedir/uploads/")) {
                                    uploadsIncluded = true;
                                } else if (
                                    entry.filename.startsWith("basedir/timelapse/")
                                ) {
                                    timelapseIncluded = true;
                                }
                            }
                        });
                        self.backupUploadUncompressed(size);
                        self.backupUploadTooBig(
                            self.isAboveFreeTempSpace({uncompressed: size})
                        );
                        self.backupUploadValid(basedirIncluded && metadataIncluded);
                        self.backupUploadUploadsIncluded(uploadsIncluded);
                        self.backupUploadTimelapseIncluded(timelapseIncluded);
                    });
                },
                done: (e, data) => {
                    self.backupUploadName(undefined);
                    self.backupUploadData = undefined;
                    self.backupUploadSource = undefined;
                    self.backupUploadVersion("-");
                    self.backupUploadVersionIncompatible(false);
                    self.backupUploadCompressed(undefined);
                    self.backupUploadUncompressed(undefined);
                    self.backupUploadTooBig(false);
                    self.backupUploadUploadsIncluded(false);
                    self.backupUploadTimelapseIncluded(false);
                    self.backupUploadValid(false);
                },
                fail: (e, data) => {
                    self.setRestoreProgress(
                        "Upload failed!",
                        self.restoreProgressPercentage()
                    );
                    if (data && data.jqXHR && data.status === 409) {
                        self.loglines.push({
                            line: "Backup file already exists, please rename before upload!",
                            stream: "error"
                        });
                    }
                    self.restoreInProgress(false);
                },
                progressall: (e, data) => {
                    const progress = parseInt((data.loaded / data.total) * 100, 10);
                    self.setRestoreProgress("Uploading", progress);
                }
            };
        };

        $("#settings-backup-upload").fileupload(
            backupFileuploadOptionsFactory("settings")
        );
        $("#wizard-backup-upload").fileupload(backupFileuploadOptionsFactory("wizard"));

        self.restoreInProgress = ko.observable(false);
        self.restoreTitle = ko.observable();
        self.restoreDialog = undefined;
        self.restoreOutput = undefined;
        self.unknownPlugins = ko.observableArray([]);

        self.restoreProgressPercentage = ko.observable(0);
        self.restoreProgressText = ko.observable("");
        self.restoreProgressError = ko.observable(false);
        self.restoreProgressActive = ko.observable(false);
        self.restoreProgressClass = ko.computed(() => {
            if (self.restoreProgressError()) {
                return "bar-danger";
            } else {
                return "";
            }
        });
        self.setRestoreProgress = (operation, progress) => {
            if (progress === undefined || progress < 0) {
                self.restoreProgressPercentage(100);
                self.restoreProgressText(operation);
                self.restoreProgressActive(true);
            } else {
                self.restoreProgressPercentage(progress);
                self.restoreProgressText(`${operation} (${progress}%)`);
                self.restoreProgressActive(false);
            }
        };

        self.loglines = ko.observableArray([]);

        self.requestData = function () {
            OctoPrint.plugins.backup.get().done(self.fromResponse);
        };

        self.fromResponse = function (response) {
            self.backups.updateItems(response.backups);
            self.unknownPlugins(response.unknown_plugins);
            self.restoreSupported(response.restore_supported);
            self.maxUploadSize(response.max_upload_size);
            self.freeTempSpace(response.free_temp_space);
        };

        self.reauthenticateDownload = (url) => {
            self.loginState.reauthenticateIfNecessary(() => {
                const link = document.createElement("a");
                link.href = url;
                link.download = "";
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            });
        };

        self.createBackup = function () {
            var excluded = self.excludeFromBackup();
            OctoPrint.plugins.backup.createBackup(excluded).done(function () {
                self.excludeFromBackup([]);
            });
        };

        self.removeBackup = function (backup) {
            var perform = function () {
                OctoPrint.plugins.backup.deleteBackup(backup).done(function () {
                    self.requestData();
                });
            };
            showConfirmationDialog(
                _.sprintf(gettext('You are about to delete backup file "%(name)s".'), {
                    name: _.escape(backup)
                }),
                perform
            );
        };

        self.restoreBackup = function (backup) {
            if (!self.restoreSupported()) return;

            showConfirmationDialog(
                _.sprintf(
                    gettext(
                        'You are about to restore the backup file "%(name)s". This cannot be undone.'
                    ),
                    {name: _.escape(backup)}
                ),
                () => {
                    self.loginState.reauthenticateIfNecessary(() => {
                        self.restoreInProgress(true);
                        self.loglines.removeAll();
                        self.loglines.push({
                            line: "Preparing to restore...",
                            stream: "message"
                        });
                        self.loglines.push({line: " ", stream: "message"});
                        self.restoreDialog.modal({
                            keyboard: false,
                            backdrop: "static",
                            show: true
                        });

                        OctoPrint.plugins.backup.restoreBackup(backup);
                    });
                }
            );
        };

        self.performRestoreFromUpload = function () {
            if (!self.enableUploadAndRestore()) return;

            const proceed = () => {
                self.restoreInProgress(true);
                self.setRestoreProgress("Uploading...", 0);
                self.restoreProgressError(false);
                self.loglines.removeAll();
                self.loglines.push({
                    line: "Uploading backup, this can take a while. Please wait...",
                    stream: "message"
                });
                self.loglines.push({line: " ", stream: "message"});
                self.restoreDialog.modal({
                    keyboard: false,
                    backdrop: "static",
                    show: true
                });

                self.backupUploadData.submit();
            };

            showConfirmationDialog(
                _.sprintf(
                    gettext(
                        'You are about to upload and restore the backup file "%(name)s". This cannot be undone.'
                    ),
                    {name: _.escape(self.backupUploadName())}
                ),
                () => {
                    if (self.backupUploadSource === "wizard") {
                        proceed();
                    } else {
                        self.loginState.reauthenticateIfNecessary(proceed);
                    }
                }
            );
        };

        self.deleteUnknownPluginRecord = function () {
            var perform = function () {
                OctoPrint.plugins.backup.deleteUnknownPlugins().done(function () {
                    self.requestData();
                });
            };
            showConfirmationDialog(
                gettext(
                    "You are about to delete the record of plugins unknown during the last restore."
                ),
                perform
            );
        };

        self.markFilesOnPage = function () {
            self.markedForBackupDeletion(
                _.uniq(
                    self
                        .markedForBackupDeletion()
                        .concat(_.map(self.backups.paginatedItems(), "name"))
                )
            );
        };

        self.markAllFiles = function () {
            self.markedForBackupDeletion(_.map(self.backups.allItems, "name"));
        };

        self.clearMarkedFiles = function () {
            self.markedForBackupDeletion.removeAll();
        };

        self.removeMarkedFiles = function () {
            var perform = function () {
                self._bulkRemove(self.markedForBackupDeletion()).done(function () {
                    self.markedForBackupDeletion.removeAll();
                });
            };

            showConfirmationDialog(
                _.sprintf(gettext("You are about to delete %(count)d backups."), {
                    count: self.markedForBackupDeletion().length
                }),
                perform
            );
        };

        self.onStartup = function () {
            self.restoreDialog = $("#settings_plugin_backup_restoredialog");
            self.restoreOutput = $("#settings_plugin_backup_restoredialog_output");
        };

        self.onSettingsShown = function () {
            self.requestData();
        };

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin !== "backup") return;

            if (data.type === "backup_done") {
                self.requestData();
                self.backupInProgress(false);
                self.backupProgress(-1);
                self.backupTarget("");
                new PNotify({
                    title: gettext("Backup created successfully"),
                    type: "success"
                });
            } else if (data.type === "backup_started") {
                self.backupTarget(data.name);
                self.backupProgress(0);
                self.backupInProgress(true);
            } else if (data.type === "backup_error") {
                self.requestData();
                self.backupInProgress(false);
                self.backupProgress(-1);
                self.backupTarget("");
                new PNotify({
                    title: gettext("Creating the backup failed"),
                    text: _.sprintf(
                        gettext(
                            "OctoPrint could not create your backup. Please consult <code>octoprint.log</code> for details. Error: %(error)s"
                        ),
                        {error: _.escape(data.error)}
                    ),
                    type: "error",
                    hide: false
                });
            } else if (data.type === "backup_progress") {
                self.backupTarget(data.name);
                self.backupProgress(Math.round(data.progress * 100));
                self.backupInProgress(true);
            } else if (data.type === "restore_started") {
                const line = gettext("Restoring from backup...");
                self.setRestoreProgress(line);
                self.loglines.push({
                    line: line,
                    stream: "message"
                });
                self.loglines.push({line: " ", stream: "message"});
            } else if (data.type === "restore_failed") {
                self.loglines.push({line: " ", stream: "message"});
                self.loglines.push({
                    line: gettext(
                        "Restore failed! Check the above output and octoprint.log for reasons as to why."
                    ),
                    stream: "error"
                });
                self.restoreInProgress(false);
                self.setRestoreProgress(
                    gettext("Restore failed!"),
                    self.restoreProgressPercentage()
                );
            } else if (data.type === "restore_done") {
                self.loglines.push({line: " ", stream: "message"});
                self.loglines.push({
                    line: gettext(
                        "Restore successful! The server will now be restarted!"
                    ),
                    stream: "message"
                });
                self.restoreInProgress(false);
                self.setRestoreProgress(gettext("Restore successful!"), 100);
            } else if (data.type === "installing_plugin") {
                self.loglines.push({line: " ", stream: "message"});

                const line = _.sprintf(gettext('Installing plugin "%(plugin)s"...'), {
                    plugin: _.escape(data.plugin)
                });
                self.loglines.push({
                    line: line,
                    stream: "message"
                });
                self.setRestoreProgress(line);
            } else if (data.type === "plugin_incompatible") {
                self.loglines.push({line: " ", stream: "message"});
                self.loglines.push({
                    line: _.sprintf(
                        gettext(
                            'Cannot install plugin "%(plugin)s" due to it being incompatible to this OctoPrint version and/or underlying operating system'
                        ),
                        {plugin: _.escape(data.plugin.key)}
                    ),
                    stream: "stderr"
                });
            } else if (data.type === "unknown_plugins") {
                if (data.plugins.length > 0) {
                    self.loglines.push({line: " ", stream: "message"});
                    self.loglines.push({
                        line: _.sprintf(
                            gettext(
                                "There are %(count)d plugins you'll need to install manually since they aren't registered on the repository:"
                            ),
                            {count: data.plugins.length}
                        ),
                        stream: "message"
                    });
                    _.each(data.plugins, function (plugin) {
                        self.loglines.push({
                            line: plugin.name + ": " + plugin.url,
                            stream: "message"
                        });
                    });
                    self.loglines.push({line: " ", stream: "message"});
                    self.unknownPlugins(data.plugins);
                }
            } else if (data.type === "logline") {
                self.loglines.push(
                    self._preprocessLine({line: data.line, stream: data.stream})
                );
                self._scrollRestoreOutputToEnd();
            }
        };

        self._scrollRestoreOutputToEnd = function () {
            self.restoreOutput.scrollTop(
                self.restoreOutput[0].scrollHeight - self.restoreOutput.height()
            );
        };

        self._forcedStdoutLine =
            /You are using pip version .*?, however version .*? is available\.|You should consider upgrading via the '.*?' command\./;
        self._preprocessLine = function (line) {
            if (line.stream === "stderr" && line.line.match(self._forcedStdoutLine)) {
                line.stream = "stdout";
            }
            return line;
        };

        self._bulkRemove = function (files) {
            var title, message, handler;

            title = gettext("Deleting backups");
            message = _.sprintf(gettext("Deleting %(count)d backups..."), {
                count: files.length
            });
            handler = function (filename) {
                return OctoPrint.plugins.backup
                    .deleteBackup(filename)
                    .done(function () {
                        deferred.notify(
                            _.sprintf(gettext("Deleted %(filename)s..."), {
                                filename: _.escape(filename)
                            }),
                            true
                        );
                    })
                    .fail(function (jqXHR) {
                        var short = _.sprintf(
                            gettext("Deletion of %(filename)s failed, continuing..."),
                            {filename: _.escape(filename)}
                        );
                        var long = _.sprintf(
                            gettext("Deletion of %(filename)s failed: %(error)s"),
                            {
                                filename: _.escape(filename),
                                error: _.escape(jqXHR.responseText)
                            }
                        );
                        deferred.notify(short, long, false);
                    });
            };

            var deferred = $.Deferred();

            var promise = deferred.promise();

            var options = {
                title: title,
                message: message,
                max: files.length,
                output: true
            };
            showProgressModal(options, promise);

            var requests = [];
            _.each(files, function (filename) {
                var request = handler(filename);
                requests.push(request);
            });
            $.when.apply($, _.map(requests, wrapPromiseWithAlways)).done(function () {
                deferred.resolve();
                self.requestData();
            });

            return promise;
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: BackupViewModel,
        dependencies: ["loginStateViewModel", "settingsViewModel"],
        elements: ["#settings_plugin_backup", "#wizard_plugin_backup"]
    });
});
