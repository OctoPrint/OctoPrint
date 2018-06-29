$(function() {
    function ConnectionViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];
        self.printerProfiles = parameters[2];
        self.access = parameters[3];

        self.printerProfiles.profiles.items.subscribe(function() {
            var allProfiles = self.printerProfiles.profiles.items();

            var printerOptions = [];
            _.each(allProfiles, function(profile) {
                printerOptions.push({id: profile.id, name: profile.name});
            });
            self.printerOptions(printerOptions);
        });

        self.printerProfiles.currentProfile.subscribe(function() {
            self.selectedPrinter(self.printerProfiles.currentProfile());
        });

        self.printerOptions = ko.observableArray(undefined);
        self.selectedPrinter = ko.observable(undefined);

        // Protocol
        self.availableProtocols = ko.observableArray();
        self.selectedProtocol = ko.observable(undefined);
        self.protocolParameters = ko.observable();

        self.selectedProtocol.subscribe(function() {
            var protocol = self.selectedProtocol();
            if (protocol) {
                self.protocolParameters(protocol.options);
            } else {
                self.protocolParameters([]);
            }
        });

        // Transport
        self.availableTransports = ko.observableArray();
        self.selectedTransport = ko.observable(undefined);
        self.transportParameters = ko.observableArray();

        self.selectedTransport.subscribe(function() {
            var transport = self.selectedTransport();
            if (transport) {
                self.transportParameters(transport.options);
            } else {
                self.transportParameters([]);
            }
        });

        self.adjustConnectionParameters = ko.observable(undefined);
        self.updateProfile = ko.observable(undefined);
        self.saveSettings = ko.observable(undefined);
        self.autoconnect = ko.observable(undefined);

        self.isErrorOrClosed = ko.observable(undefined);
        self.isOperational = ko.observable(undefined);
        self.isPrinting = ko.observable(undefined);
        self.isPaused = ko.observable(undefined);
        self.isError = ko.observable(undefined);
        self.isReady = ko.observable(undefined);
        self.isLoading = ko.observable(undefined);

        self.buttonText = ko.pureComputed(function() {
            if (self.isErrorOrClosed())
                return gettext("Connect");
            else
                return gettext("Disconnect");
        });

        self.previousIsOperational = undefined;

        self.refreshVisible = ko.observable(true);

        self.requestData = function() {
            if (!self.loginState.hasPermission(self.access.permissions.CONNECTION)) {
                return;
            }

            OctoPrint.connection.getSettings()
                .done(self.fromResponse);
        };

        self.fromResponse = function(response) {
            var profile = response.current.profile;
            var profiles = response.options.printerProfiles;

            var protocol = response.current.protocol;
            var protocolOptions = response.current.protocolOptions;
            if (!protocolOptions) {
                protocolOptions = {};
            }
            var protocols = response.options.protocols;

            var transport = response.current.transport;
            var transportOptions = response.current.transportOptions;
            if (!transportOptions) {
                transportOptions = {};
            }
            var transports = response.options.transports;

            if (!self.selectedPrinter() && profiles && profiles.indexOf(profile) >= 0)
                self.selectedPrinter(profile);

            var extendOption = function(option, value) {
                if (value === undefined && option.default !== undefined) {
                    value = option.default;
                }
                option.value = ko.observable(value);
            };

            // protocol
            _.each(protocols, function(protocol) {
                _.each(protocol.options, function(option) {
                    extendOption(option, protocolOptions[option.name]);
                });
            });

            self.availableProtocols(protocols);
            self.selectedProtocol(protocol);

            // transport
            _.each(transports, function(transport) {
                _.each(transport.options, function(option) {
                    extendOption(option, transportOptions[option.name]);
                });
            });

            self.availableTransports(transports);
            self.selectedTransport(transport);

            self.saveSettings(false);
        };

        self.fromHistoryData = function(data) {
            self._processStateData(data.state);
        };

        self.fromCurrentData = function(data) {
            self._processStateData(data.state);
        };

        self.openOrCloseOnStateChange = function(force) {
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

        self._processStateData = function(data) {
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

        self.connect = function() {
            if (self.isErrorOrClosed()) {
                var toOptions = function(parameters) {
                    var result = {};
                    _.each(parameters, function(parameter) {
                        result[parameter.name] = parameter.value();
                    });
                    return result;
                };

                var data = {
                    "protocol": self.selectedProtocol().key,
                    "protocolOptions": toOptions(self.protocolParameters()),
                    "transport": self.selectedTransport().key,
                    "transportOptions": toOptions(self.transportParameters()),
                    "printerProfile": self.selectedPrinter(),
                    "autoconnect": self.settings.serial_autoconnect()
                };

                if (self.saveSettings())
                    data["save"] = true;

                OctoPrint.connection.connect(data)
                    .done(function() {
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
                        message: gettext("<p><strong>You are about to disconnect from the printer while a print "
                            + "is in progress.</strong></p>"
                            + "<p>Disconnecting while a print is in progress will prevent OctoPrint from "
                            + "completing the print. If you're printing from an SD card attached directly "
                            + "to the printer, any attempt to restart OctoPrint or reconnect to the printer "
                            + "could interrupt the print.<p>"),
                        question: gettext("Are you sure you want to disconnect from the printer?"),
                        cancel: gettext("Stay Connected"),
                        proceed: gettext("Disconnect"),
                        onproceed:  function() {
                            self.requestData();
                            OctoPrint.connection.disconnect();
                        }
                    })
                }
            }
        };

        self.onEventSettingsUpdated = function() {
            self.requestData();
        }

        self.onStartup = function() {
            var connectionTab = $("#connection");
            connectionTab.on("show", function() {
                self.refreshVisible(true);
            });
            connectionTab.on("hide", function() {
                self.refreshVisible(false);
            });
        };

        self.onStartupComplete = function() {
            self.openOrCloseOnStateChange(true);
        };

        self.onUserPermissionsChanged = self.onUserLoggedIn = self.onUserLoggedOut = function() {
            self.requestData();
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ConnectionViewModel,
        dependencies: ["loginStateViewModel", "settingsViewModel", "printerProfilesViewModel", "accessViewModel"],
        elements: ["#connection_wrapper"]
    });
});
