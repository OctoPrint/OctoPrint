(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var OctoPrintBackupClient = function(base) {
        this.base = base;
        this.url = this.base.getBlueprintUrl("backup");
    };

    OctoPrintBackupClient.prototype.get = function(refresh, opts) {
        return this.base.get(this.url + "backup", opts);
    };

    OctoPrintBackupClient.prototype.getWithRefresh = function(opts) {
        return this.get(true, opts);
    };

    OctoPrintBackupClient.prototype.getWithoutRefresh = function(opts) {
        return this.get(false, opts);
    };

    OctoPrintBackupClient.prototype.createBackup = function(exclude, opts) {
        exclude = exclude || [];

        var data = {
            exclude: exclude
        };

        return this.base.postJson(this.url + "backup", data, opts);
    };

    OctoPrintBackupClient.prototype.deleteBackup = function(backup, opts) {
        return this.base.delete(this.url + "backup/" + backup, opts);
    };

    OctoPrintBackupClient.prototype.restoreBackup = function(backup, opts) {
        var data = {
            path: backup
        };

        return this.base.postJson(this.url + "restore", data, opts);
    };

    OctoPrintClient.registerPluginComponent("backup", OctoPrintBackupClient);
    return OctoPrintBackupClient;
});

$(function() {
    function BackupViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];

        self.backups = new ItemListHelper(
            "plugin.backup.backups",
            {
                "date": function (a, b) {
                    // sorts descending
                    if (a["date"] > b["date"]) return -1;
                    if (a["date"] < b["date"]) return 1;
                    return 0;
                }
            },
            {
            },
            "date",
            [],
            [],
            10
        );
        self.markedForBackupDeletion = ko.observableArray([]);
        self.excludeFromBackup = ko.observableArray([]);
        self.backupInProgress = ko.observable(false);

        self.requestData = function() {
            OctoPrint.plugins.backup.get()
                .done(self.fromResponse);
        };

        self.fromResponse = function(response) {
            self.backups.updateItems(response.backups);
        };

        self.createBackup = function() {
            var excluded = self.excludeFromBackup();
            OctoPrint.plugins.backup.createBackup(excluded)
                .done(function() {
                    self.excludeFromBackup([]);
                })
        };

        self.removeBackup = function(backup) {
            OctoPrint.plugins.backup.deleteBackup(backup)
                .done(function() {
                    self.requestData();
                })
        };

        self.restoreBackup = function(backup) {
            OctoPrint.plugins.backup.restoreBackup(backup)
                .done(function() {
                    // do something
                })
        };

        self.markFilesOnPage = function() {
            self.markedForBackupDeletion(_.uniq(self.markedForBackupDeletion().concat(_.map(self.backups.paginatedItems(), "name"))));
        };

        self.markAllFiles = function() {
            self.markedForBackupDeletion(_.map(self.backups.allItems, "name"));
        };

        self.clearMarkedFiles = function() {
            self.markedForBackupDeletion.removeAll();
        };

        self.removeMarkedFiles = function() {
            var perform = function() {
                self._bulkRemove(self.markedForBackupDeletion())
                    .done(function() {
                        self.markedForBackupDeletion.removeAll();
                    });
            };

            showConfirmationDialog(_.sprintf(gettext("You are about to delete %(count)d backups."), {count: self.markedForBackupDeletion().length}),
                                   perform);
        };

        self.onSettingsShown = function() {
            self.requestData();
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== "backup") return;

            if (data.type === "backup_done") {
                self.requestData();
                self.backupInProgress(false);
            } else if (data.type === "backup_started") {
                self.backupInProgress(true);
            }
        };

        self._bulkRemove = function(files) {
            var title, message, handler;

            title = gettext("Deleting backups");
            message = _.sprintf(gettext("Deleting %(count)d backups..."), {count: files.length});
            handler = function(filename) {
                return OctoPrint.plugins.backup.deleteBackup(filename)
                    .done(function() {
                        deferred.notify(_.sprintf(gettext("Deleted %(filename)s..."), {filename: filename}), true);
                    })
                    .fail(function(jqXHR) {
                        var short = _.sprintf(gettext("Deletion of %(filename)s failed, continuing..."), {filename: filename});
                        var long = _.sprintf(gettext("Deletion of %(filename)s failed: %(error)s"), {filename: filename, error: jqXHR.responseText});
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
            _.each(files, function(filename) {
                var request = handler(filename);
                requests.push(request)
            });
            $.when.apply($, _.map(requests, wrapPromiseWithAlways))
                .done(function() {
                    deferred.resolve();
                    self.requestData();
                });

            return promise;
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: BackupViewModel,
        dependencies: ["loginStateViewModel", "settingsViewModel"],
        elements: ["#settings_plugin_backup"]
    });
});
