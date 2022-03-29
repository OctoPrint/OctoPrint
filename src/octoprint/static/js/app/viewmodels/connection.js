$(function () {
    function ConnectionViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];
        self.printerProfiles = parameters[2];
        self.access = parameters[3];

        self.printerProfiles.profiles.items.subscribe(function () {
            var allProfiles = self.printerProfiles.profiles.items();

            var printerOptions = [];
            _.each(allProfiles, function (profile) {
                printerOptions.push({id: profile.id, name: profile.name});
            });
            self.printerOptions(printerOptions);
        });

        self.printerProfiles.currentProfile.subscribe(function () {
            self.selectedPrinter(self.printerProfiles.currentProfile());
        });

        self.portOptionsFetched = ko.observable(false);
        self.portOptions = ko.observableArray(undefined);
        self.baudrateOptions = ko.observableArray(undefined);
        self.printerOptions = ko.observableArray(undefined);
        self.selectedPort = ko.observable(undefined);
        self.selectedBaudrate = ko.observable(undefined);
        self.selectedPrinter = ko.observable(undefined);
        self.saveSettings = ko.observable(undefined);
        self.autoconnect = ko.observable(undefined);

        self.isErrorOrClosed = ko.observable(undefined);
        self.isOperational = ko.observable(undefined);
        self.isPrinting = ko.observable(undefined);
        self.isPaused = ko.observable(undefined);
        self.isError = ko.observable(undefined);
        self.isReady = ko.observable(undefined);
        self.isLoading = ko.observable(undefined);

        self.enableConnect = ko.pureComputed(function () {
            //return self.enablePort() || !self.isErrorOrClosed();
            return true; // enable always for now, until we have an auto refresh in 1.9.0
        });

        self.buttonText = ko.pureComputed(function () {
            if (self.isErrorOrClosed()) return gettext("Connect");
            else return gettext("Disconnect");
        });

        self.portCaption = ko.pureComputed(function () {
            return self.validPort() ? "AUTO" : gettext("No serial port found");
        });

        self.validPort = ko.pureComputed(function () {
            return (
                !self.portOptionsFetched() ||
                self.portOptions().length > 0 ||
                self.settings.settings.serial.ignoreEmptyPorts()
            );
        });

        self.enablePort = ko.pureComputed(function () {
            return self.validPort() && self.isErrorOrClosed();
        });

        self.enableSaveSettings = ko.pureComputed(function () {
            return self.enableConnect() && self.isErrorOrClosed();
        });

        self.enableAutoConnect = ko.pureComputed(function () {
            return self.enableConnect() && self.isErrorOrClosed();
        });

        self.previousIsOperational = undefined;

        self.refreshVisible = ko.observable(true);

        self.requestData = function () {
            if (!self.loginState.hasPermission(self.access.permissions.CONNECTION)) {
                return;
            }

            OctoPrint.connection.getSettings().done(self.fromResponse);
        };

        self.fromResponse = function (response) {
            var ports = response.options.ports;
            var baudrates = response.options.baudrates;
            var currentPort = response.current.port;
            var currentBaudrate = response.current.baudrate;
            var currentPrinterProfile = response.current.printerProfile;
            var portPreference = response.options.portPreference;
            var baudratePreference = response.options.baudratePreference;
            var printerPreference = response.options.printerProfilePreference;
            var printerProfiles = response.options.printerProfiles;

            self.portOptions(ports);
            self.baudrateOptions(baudrates);

            if (!self.selectedPort() && ports) {
                if (ports.indexOf(currentPort) >= 0) {
                    self.selectedPort(currentPort);
                } else if (ports.indexOf(portPreference) >= 0) {
                    self.selectedPort(portPreference);
                }
            }
            if (!self.selectedBaudrate() && baudrates) {
                if (baudrates.indexOf(currentBaudrate) >= 0) {
                    self.selectedBaudrate(currentBaudrate);
                } else if (baudrates.indexOf(baudratePreference) >= 0) {
                    self.selectedBaudrate(baudratePreference);
                }
            }
            if (!self.selectedPrinter() && printerProfiles) {
                if (printerProfiles.indexOf(currentPrinterProfile) >= 0) {
                    self.selectedPrinter(currentPrinterProfile);
                } else if (printerProfiles.indexOf(printerPreference) >= 0) {
                    self.selectedPrinter(printerPreference);
                }
            }

            self.saveSettings(false);
            self.portOptionsFetched(true);
        };

        self.fromHistoryData = function (data) {
            self._processStateData(data.state);
        };

        self.fromCurrentData = function (data) {
            self._processStateData(data.state);
        };

        self.openOrCloseOnStateChange = function (force) {
            if (!self._startupComplete && !force) return;

            var connectionTab = $("#connection");
            if (self.isOperational() && connectionTab.hasClass("in")) {
                connectionTab.collapse("hide");
                self.refreshVisible(false);
            } else if (!self.isOperational() && !connectionTab.hasClass("in")) {
                connectionTab.collapse("show");
                self.refreshVisible(true);
            }
        };

        self._processStateData = function (data) {
            self.previousIsOperational = self.isOperational();

            self.isErrorOrClosed(data.flags.closedOrError);
            self.isOperational(data.flags.operational);
            self.isPaused(data.flags.paused);
            self.isPrinting(data.flags.printing);
            self.isError(data.flags.error);
            self.isReady(data.flags.ready);
            self.isLoading(data.flags.loading);

            if (self.previousIsOperational !== self.isOperational()) {
                // only open or close if the panel is visible (for admins) and
                // the state just changed to avoid thwarting manual open/close
                self.openOrCloseOnStateChange();
            }
        };

        self.connect = function () {
            if (self.isErrorOrClosed()) {
                var data = {
                    port: self.selectedPort() || "AUTO",
                    baudrate: self.selectedBaudrate() || 0,
                    printerProfile: self.selectedPrinter(),
                    autoconnect: self.settings.serial_autoconnect()
                };

                if (self.saveSettings()) data["save"] = true;

                OctoPrint.connection.connect(data).done(function () {
                    self.settings.requestData();
                    self.settings.printerProfiles.requestData();
                });
            } else {
                if (!self.isPrinting() && !self.isPaused()) {
                    self.requestData();
                    OctoPrint.connection.disconnect();
                } else {
                    showConfirmationDialog({
                        title: gettext("Are you sure?"),
                        message: gettext(
                            "<p><strong>You are about to disconnect from the printer while a print " +
                                "is in progress.</strong></p>" +
                                "<p>Disconnecting while a print is in progress will prevent OctoPrint from " +
                                "completing the print. If you're printing from an SD card attached directly " +
                                "to the printer, any attempt to restart OctoPrint or reconnect to the printer " +
                                "could interrupt the print.<p>"
                        ),
                        question: gettext(
                            "Are you sure you want to disconnect from the printer?"
                        ),
                        cancel: gettext("Stay Connected"),
                        proceed: gettext("Disconnect"),
                        onproceed: function () {
                            self.requestData();
                            OctoPrint.connection.disconnect();
                        }
                    });
                }
            }
        };

        self.onEventSettingsUpdated = function () {
            self.requestData();
        };

        self.onEventConnected = function () {
            self.requestData();
        };

        self.onEventDisconnected = function () {
            self.requestData();
        };

        self.onStartup = function () {
            var connectionTab = $("#connection");
            connectionTab.on("show", function () {
                self.refreshVisible(true);
            });
            connectionTab.on("hide", function () {
                self.refreshVisible(false);
            });
        };

        self.onStartupComplete = function () {
            self.openOrCloseOnStateChange(true);
        };

        self.onUserPermissionsChanged =
            self.onUserLoggedIn =
            self.onUserLoggedOut =
                function () {
                    self.requestData();
                };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ConnectionViewModel,
        dependencies: [
            "loginStateViewModel",
            "settingsViewModel",
            "printerProfilesViewModel",
            "accessViewModel"
        ],
        elements: ["#connection_wrapper"]
    });
});
