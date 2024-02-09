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
        self.credentialsSeen = ko.observable(undefined);

        // system commands
        self.systemCommands = ko.observableArray([]);

        // system info
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
        self.backupIsAboveUploadSize = (data) => {
            return data.size > self.backupMaxUploadSize();
        };

        // working dialog
        self.workDialog = $("#workdialog");
        self.workInProgress = ko.observable(false);
        self.workLoglines = ko.observableArray([]);
        self.workTitle = ko.observable("");

        // reauthentication dialog
        self.reauthenticateDialog = $("#reauthenticate_dialog");
        self.reauthenticateDialog.on("shown", function () {
            $("input[type=password]", self.reauthenticateDialog).focus();
        });
        self.reauthenticatePass = ko.observable("");
        self.reauthenticateFailed = ko.observable(false);
        self._reauthenticated = false;

        self.request = () => {
            OctoPrint.browser.passiveLogin().done((resp) => {
                self.username(resp.name);
                self.permitted(_.includes(resp.needs.role, "admin"));
                self.credentialsSeen(resp._credentials_seen);
                self.known(true);

                OctoPrint.socket.sendAuth(resp.name, resp.session);
            });

            OctoPrint.system.getCommandsForSource("core").done((resp) => {
                self.systemCommands(resp);
            });

            OctoPrint.system.getInfo().done((resp) => {
                var systeminfo = [];
                _.forOwn(resp.systeminfo, (value, key) => {
                    systeminfo.push({key: key, value: value});
                });
                self.systemInfo(systeminfo);
            });

            OctoPrint.printer
                .getFullState()
                .done((resp) => {
                    self.printerConnected(true);
                    self.jobInProgress(resp.state.flags.printing);
                })
                .fail((xhr) => {
                    self.printerConnected(false);
                    self.jobInProgress(false);
                });

            if (OctoPrint.plugins.backup) {
                OctoPrint.plugins.backup.get().done((resp) => {
                    self.backupSupported(true);
                    self.restoreSupported(resp.restore_supported);
                    self.backupMaxUploadSize(resp.max_upload_size);

                    var backups = resp.backups;
                    backups.sort((a, b) => b.date - a.date);
                    self.backups(backups);
                });
            } else {
                self.backupSupported(false);
                self.restoreSupported(false);
                self.backups([]);
            }
        };

        self.showReauthenticationDialog = () => {
            const result = $.Deferred();

            self._reauthenticated = false;
            self.reauthenticateDialog.off("hidden");
            self.reauthenticateDialog.on("hidden", () => {
                self.reauthenticatePass("");
                self.reauthenticateFailed(false);
                if (self._reauthenticated) {
                    result.resolve();
                } else {
                    result.reject();
                }
            });
            self.reauthenticateDialog.modal("show");

            return result.promise();
        };

        self.reauthenticate = () => {
            const user = self.username();
            const pass = self.reauthenticatePass();
            return OctoPrint.browser
                .login(user, pass)
                .done((response) => {
                    self.credentialsSeen(response._credentials_seen);
                    self.reauthenticateFailed(false);
                    self._reauthenticated = self.credentialsSeen();
                    $("#reauthenticate_dialog").modal("hide");
                })
                .fail((response) => {
                    self.reauthenticatePass("");
                    self.reauthenticateFailed(true);
                });
        };

        self.forceReauthentication = (callback) => {
            self.showReauthenticationDialog()
                .done(() => {
                    callback();
                })
                .fail(() => {
                    // Do nothing
                });
        };

        self.checkCredentialsSeen = () => {
            if (CONFIG_REAUTHENTICATION_TIMEOUT <= 0) return true;

            const credentialsSeen = self.credentialsSeen();
            if (!credentialsSeen) {
                return false;
            }

            const now = new Date();
            const seen = new Date(credentialsSeen);
            return now - seen < CONFIG_REAUTHENTICATION_TIMEOUT * 60 * 1000;
        };

        self.reauthenticateIfNecessary = (callback) => {
            if (!self.checkCredentialsSeen()) {
                self.forceReauthentication(callback);
            } else {
                callback();
            }
        };

        self.executeSystemCommand = (command) => {
            var process = () => {
                OctoPrint.system.executeCommand(command.source, command.action);
            };

            if (command.confirm) {
                showConfirmationDialog({
                    message: command.confirm,
                    onproceed: () => {
                        process();
                    }
                });
            } else {
                process();
            }
        };

        self.copySystemInfo = () => {
            var text = "";
            _.each(self.systemInfo(), (entry) => {
                text += entry.key + ": " + entry.value + "\r\n";
            });
            copyToClipboard(text);
        };

        self.cancelPrint = function () {
            OctoPrint.job.cancel().done(() => {
                self.request();
            });
        };

        self.disconnectPrinter = function () {
            OctoPrint.connection.disconnect().done(() => {
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
            OctoPrint.plugins.backup.createBackup(excluded).done(() => {
                self.excludeFromBackup([]);
            });
        };

        self.restoreBackup = (backup) => {
            if (!self.restoreSupported()) return;

            showConfirmationDialog(
                _.sprintf(
                    gettext(
                        'You are about to restore the backup file "%(name)s". This cannot be undone.'
                    ),
                    {name: _.escape(backup)}
                ),
                () => {
                    this.reauthenticateIfNecessary(() => {
                        self.workInProgress(true);
                        self.workTitle(gettext("Restoring backup..."));
                        self.workLoglines.removeAll();
                        self.workLoglines.push({
                            line: "Preparing to restore...",
                            stream: "message"
                        });
                        self.workLoglines.push({line: " ", stream: "message"});
                        self.workDialog.modal({
                            keyboard: false,
                            backdrop: "static",
                            show: true
                        });

                        OctoPrint.plugins.backup.restoreBackup(backup);
                    });
                }
            );
        };

        self.reauthenticateDownload = (url) => {
            self.reauthenticateIfNecessary(() => {
                const link = document.createElement("a");
                link.href = url;
                link.download = "";
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            });
        };

        self.logout = () => {
            OctoPrint.browser.logout().done(() => {
                window.location.href = LOGIN_URL;
            });
        };

        self.reconnect = () => {
            OctoPrint.socket.reconnect();
        };

        self.onSocketConnected = () => {
            self.connected(true);
            self.request();
        };

        self.onSocketDisconnected = () => {
            self.connected(false);
        };

        self.onSocketMessage = (event, data) => {
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

    OctoPrint.socket.onConnected = () => {
        viewModel.onSocketConnected();
    };

    OctoPrint.socket.onDisconnected = () => {
        viewModel.onSocketDisconnected();
    };

    OctoPrint.socket.onMessage("*", (data) => {
        viewModel.onSocketMessage(data.event, data.data);
    });

    ko.applyBindings(viewModel, document.getElementById("navbar"));
    ko.applyBindings(viewModel, document.getElementById("recovery"));
    ko.applyBindings(viewModel, document.getElementById("workdialog"));
    ko.applyBindings(viewModel, document.getElementById("reauthenticate_dialog"));
});
