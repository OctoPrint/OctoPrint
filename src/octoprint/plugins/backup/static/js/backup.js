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

        self.excludeFromBackup = ko.observableArray([]);
        self.backupInProgress = ko.observable(false);
        self.restoreSupported = ko.observable(true);
        self.maxUploadSize = ko.observable(0);

        self.backupUploadData = undefined;
        self.backupUploadName = ko.observable();

        self.isAboveUploadSize = function (data) {
            return data.size > self.maxUploadSize();
        };

        var backupFileuploadOptions = {
            dataType: "json",
            maxNumberOfFiles: 1,
            autoUpload: false,
            headers: OctoPrint.getRequestHeaders(),
            add: function (e, data) {
                if (data.files.length === 0) {
                    // no files? ignore
                    return false;
                }

                self.backupUploadName(data.files[0].name);
                self.backupUploadData = data;
            },
            done: function (e, data) {
                self.backupUploadName(undefined);
                self.backupUploadData = undefined;
            }
        };

        $("#settings-backup-upload").fileupload(backupFileuploadOptions);
        $("#wizard-backup-upload").fileupload(backupFileuploadOptions);

        self.restoreInProgress = ko.observable(false);
        self.restoreTitle = ko.observable();
        self.restoreDialog = undefined;
        self.restoreOutput = undefined;
        self.unknownPlugins = ko.observableArray([]);

        self.loglines = ko.observableArray([]);

        self.requestData = function () {
            OctoPrint.plugins.backup.get().done(self.fromResponse);
        };

        self.fromResponse = function (response) {
            self.backups.updateItems(response.backups);
            self.unknownPlugins(response.unknown_plugins);
            self.restoreSupported(response.restore_supported);
            self.maxUploadSize(response.max_upload_size);
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

            var perform = function () {
                self.restoreInProgress(true);
                self.loglines.removeAll();
                self.loglines.push({line: "Preparing to restore...", stream: "message"});
                self.loglines.push({line: " ", stream: "message"});
                self.restoreDialog.modal({
                    keyboard: false,
                    backdrop: "static",
                    show: true
                });

                OctoPrint.plugins.backup.restoreBackup(backup);
            };
            showConfirmationDialog(
                _.sprintf(
                    gettext(
                        'You are about to restore the backup file "%(name)s". This cannot be undone.'
                    ),
                    {name: _.escape(backup)}
                ),
                perform
            );
        };

        self.performRestoreFromUpload = function () {
            if (self.backupUploadData === undefined) return;

            var perform = function () {
                self.restoreInProgress(true);
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
                perform
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
                new PNotify({
                    title: gettext("Backup created successfully"),
                    type: "success"
                });
            } else if (data.type === "backup_started") {
                self.backupInProgress(true);
            } else if (data.type === "backup_error") {
                self.requestData();
                self.backupInProgress(false);
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
            } else if (data.type === "restore_started") {
                self.loglines.push({
                    line: gettext("Restoring from backup..."),
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
            } else if (data.type === "restore_done") {
                self.loglines.push({line: " ", stream: "message"});
                self.loglines.push({
                    line: gettext(
                        "Restore successful! The server will now be restarted!"
                    ),
                    stream: "message"
                });
                self.restoreInProgress(false);
            } else if (data.type === "installing_plugin") {
                self.loglines.push({line: " ", stream: "message"});
                self.loglines.push({
                    line: _.sprintf(gettext('Installing plugin "%(plugin)s"...'), {
                        plugin: _.escape(data.plugin)
                    }),
                    stream: "message"
                });
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
