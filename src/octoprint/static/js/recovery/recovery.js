$(function () {
    //~~ OctoPrint client setup

    var OctoPrint = window.OctoPrint;
    OctoPrint.options.baseurl = BASE_URL;

    OctoPrint.socket.connect();

    var l10n = getQueryParameterByName("l10n");
    if (l10n) {
        OctoPrint.options.locale = l10n;
    }

    //~~ Initialize i18n

    var catalog = window["BABEL_TO_LOAD_EN"];
    if (catalog === undefined) {
        catalog = {
            messages: undefined,
            plural_expr: undefined,
            locale: undefined,
            domain: undefined
        };
    }
    babel.Translations.load(catalog).install();

    //~~ Lodash setup

    _.mixin({sprintf: sprintf, vsprintf: vsprintf});

    //~~ View Model

    function RecoveryViewModel() {
        var self = this;

        self.connected = ko.observable(true);
        self.known = ko.observable(false);
        self.permitted = ko.observable(false);
        self.username = ko.observable(undefined);

        // system commands
        self.systemCommands = ko.observableArray([]);

        // systen info
        self.systemInfo = ko.observableArray([]);

        // printer
        self.printerConnected = ko.observable(false);
        self.jobInProgress = ko.observable(false);

        // backup
        self.backupSupported = ko.observable(false);
        self.restoreSupported = ko.observable(false);
        self.backups = ko.observableArray([]);
        self.excludeFromBackup = ko.observableArray([]);
        self.backupMaxUploadSize = ko.observable();
        self.backupIsAboveUploadSize = function (data) {
            return data.size > self.backupMaxUploadSize();
        };

        // working dialog
        self.workDialog = $("#workdialog");
        self.workInProgress = ko.observable(false);
        self.workLoglines = ko.observableArray([]);
        self.workTitle = ko.observable("");

        self.request = function () {
            OctoPrint.browser.passiveLogin().done(function (resp) {
                self.username(resp.name);
                self.permitted(_.includes(resp.needs.role, "admin"));
                self.known(true);

                OctoPrint.socket.sendAuth(resp.name, resp.session);
            });

            OctoPrint.system.getCommandsForSource("core").done(function (resp) {
                self.systemCommands(resp);
            });

            OctoPrint.system.getInfo().done(function (resp) {
                var systeminfo = [];
                _.forOwn(resp.systeminfo, function (value, key) {
                    systeminfo.push({key: key, value: value});
                });
                self.systemInfo(systeminfo);
            });

            OctoPrint.printer
                .getFullState()
                .done(function (resp) {
                    self.printerConnected(true);
                    self.jobInProgress(resp.state.flags.printing);
                })
                .fail(function (xhr) {
                    self.printerConnected(false);
                    self.jobInProgress(false);
                });

            if (OctoPrint.plugins.backup) {
                OctoPrint.plugins.backup.get().done(function (resp) {
                    self.backupSupported(true);
                    self.restoreSupported(resp.restore_supported);
                    self.backupMaxUploadSize(resp.max_upload_size);

                    var backups = resp.backups;
                    backups.sort(function (a, b) {
                        return b.date - a.date;
                    });
                    self.backups(backups);
                });
            } else {
                self.backupSupported(false);
                self.restoreSupported(false);
                self.backups([]);
            }
        };

        self.executeSystemCommand = function (command) {
            var process = function () {
                OctoPrint.system.executeCommand(command.source, command.action);
            };

            if (command.confirm) {
                showConfirmationDialog({
                    message: command.confirm,
                    onproceed: function () {
                        process();
                    }
                });
            } else {
                process();
            }
        };

        self.copySystemInfo = function () {
            var text = "";
            _.each(self.systemInfo(), function (entry) {
                text += entry.key + ": " + entry.value + "\r\n";
            });
            copyToClipboard(text);
        };

        self.cancelPrint = function () {
            OctoPrint.job.cancel().done(function () {
                self.request();
            });
        };

        self.disconnectPrinter = function () {
            OctoPrint.connection.disconnect().done(function () {
                self.request();
            });
        };

        self.createBackup = function () {
            self.workInProgress(true);
            self.workTitle(gettext("Creating backup..."));
            self.workLoglines.removeAll();
            self.workDialog.modal({keyboard: false, backdrop: "static", show: true});

            if (!self.backupSupported()) return;
            var excluded = self.excludeFromBackup();
            OctoPrint.plugins.backup.createBackup(excluded).done(function () {
                self.excludeFromBackup([]);
            });
        };

        self.restoreBackup = function (backup) {
            if (!self.restoreSupported()) return;

            var perform = function () {
                self.workInProgress(true);
                self.workTitle(gettext("Restoring backup..."));
                self.workLoglines.removeAll();
                self.workLoglines.push({
                    line: "Preparing to restore...",
                    stream: "message"
                });
                self.workLoglines.push({line: " ", stream: "message"});
                self.workDialog.modal({keyboard: false, backdrop: "static", show: true});

                OctoPrint.plugins.backup.restoreBackup(backup);
            };
            showConfirmationDialog(
                _.sprintf(
                    gettext(
                        'You are about to restore the backup file "%(name)s". This cannot be undone.'
                    ),
                    {name: _.escape(backup.name)}
                ),
                perform
            );
        };

        self.logout = function () {
            OctoPrint.browser.logout().done(function () {
                window.location.href = LOGIN_URL;
            });
        };

        self.reconnect = function () {
            OctoPrint.socket.reconnect();
        };

        self.onSocketConnected = function () {
            self.connected(true);
            self.request();
        };

        self.onSocketDisconnected = function () {
            self.connected(false);
        };

        self.onSocketMessage = function (event, data) {
            console.log("onSocketMessage", event, data);
            if (event === "plugin" && data.plugin === "backup") {
                switch (data.data.type) {
                    case "logline": {
                        self.workLoglines.push(
                            self._preprocessLine({
                                line: data.data.line,
                                stream: data.data.stream
                            })
                        );
                        break;
                    }
                    case "backup_started": {
                        self.workLoglines.push({
                            line: gettext("Creating backup..."),
                            stream: "message"
                        });
                        self.workLoglines.push({line: " ", stream: "message"});
                        break;
                    }
                    case "backup_failed": {
                        self.workLoglines.push({line: " ", stream: "message"});
                        self.workLoglines.push({
                            line: gettext(
                                "Backup creation failed! Check octoprint.log for reasons as to why."
                            ),
                            stream: "error"
                        });
                        self.workInProgress(false);
                        self.request();
                        break;
                    }
                    case "backup_done": {
                        self.workLoglines.push({line: " ", stream: "message"});
                        self.workLoglines.push({
                            line: gettext("Backup created successfully!"),
                            stream: "message"
                        });
                        self.workInProgress(false);
                        self.request();
                        break;
                    }
                    case "restore_started": {
                        self.workLoglines.push({
                            line: gettext("Restoring from backup..."),
                            stream: "message"
                        });
                        self.workLoglines.push({line: " ", stream: "message"});
                        break;
                    }
                    case "restore_failed": {
                        self.workLoglines.push({line: " ", stream: "message"});
                        self.workLoglines.push({
                            line: gettext(
                                "Restore failed! Check the above output and octoprint.log for reasons as to why."
                            ),
                            stream: "error"
                        });
                        self.workInProgress(false);
                        break;
                    }
                    case "restore_done": {
                        self.workLoglines.push({line: " ", stream: "message"});
                        self.workLoglines.push({
                            line: gettext(
                                "Restore successful! The server will now be restarted!"
                            ),
                            stream: "message"
                        });
                        self.workInProgress(false);
                        break;
                    }
                    case "installing_plugin": {
                        self.workLoglines.push({line: " ", stream: "message"});
                        self.workLoglines.push({
                            line: _.sprintf(
                                gettext('Installing plugin "%(plugin)s"...'),
                                {plugin: _.escape(data.data.plugin)}
                            ),
                            stream: "message"
                        });
                        break;
                    }
                }
            }
        };
    }

    var viewModel = new RecoveryViewModel();

    OctoPrint.socket.onConnected = function () {
        viewModel.onSocketConnected();
    };

    OctoPrint.socket.onDisconnected = function () {
        viewModel.onSocketDisconnected();
    };

    OctoPrint.socket.onMessage("*", function (data) {
        viewModel.onSocketMessage(data.event, data.data);
    });

    ko.applyBindings(viewModel, document.getElementById("navbar"));
    ko.applyBindings(viewModel, document.getElementById("recovery"));
    ko.applyBindings(viewModel, document.getElementById("workdialog"));
});
