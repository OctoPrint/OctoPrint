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

    OctoPrintBackupClient.prototype.createBackup = function(excludes, opts) {
        excludes = excludes || [];

        var data = {
            excludes: excludes
        };

        return this.base.postJson(this.url + "backup", data, opts);
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
            0
        );

        self.requestData = function() {
            OctoPrint.plugins.backup.get()
                .done(self.fromResponse);
        };

        self.fromResponse = function(response) {
            self.backups.updateItems(response.backups);
        };

        self.createBackup = function() {
            OctoPrint.plugins.backup.createBackup();
        };

        self.onSettingsShown = function() {
            self.requestData();
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== "backup") return;

            if (data.type === "backup_done") {
                self.requestData();
            }
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: BackupViewModel,
        dependencies: ["loginStateViewModel", "settingsViewModel"],
        elements: ["#settings_plugin_backup"]
    });
});
