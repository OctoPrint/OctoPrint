$(function() {
    function ConnectionViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];
        self.connectionProfiles = parameters[2];
        self.printerProfiles = parameters[3];
        self.access = parameters[4];

        var extendOption = function(option, value) {
            if (option.type === "group") {
                if (value === undefined) {
                    value = {};
                }
                _.each(option.params, function(option) {
                    extendOption(option, value[option.name]);
                });
            } else {
                if (value === undefined && option.default !== undefined) {
                    value = option.default;
                }
                if (option.value) {
                    option.value(value);
                } else {
                    option.value = ko.observable(value);
                }
            }

        };

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

        // Connection profiles
        self.availableConnectionProfiles = ko.observableArray();
        self.selectedConnectionProfile = ko.observable(undefined);

        self.selectedConnectionProfile.subscribe(function() {
            var protocolParameters, transportParameters;

            var profile = self.selectedConnectionProfile();

            if (profile) {
                self.selectedPrinter(profile.printer_profile);
                self.selectedProtocol(_.find(self.availableProtocols(), function(p) { return p.key === profile.protocol }));
                self.selectedTransport(_.find(self.availableTransports(), function(t) { return t.key === profile.transport }));

                protocolParameters = self.protocolParameters();
                _.each(protocolParameters, function(option) {
                    extendOption(option, profile.protocol_parameters[option.name]);
                });
                self.protocolParameters(protocolParameters);

                transportParameters = self.transportParameters();
                _.each(transportParameters, function(option) {
                    extendOption(option, profile.transport_parameters[option.name]);
                });
                self.transportParameters(transportParameters);
            } else {
                self.selectedPrinter(undefined);
                self.selectedProtocol(undefined);
                self.selectedTransport(undefined);

                protocolParameters = self.protocolParameters();
                _.each(protocolParameters, function(option) {
                    extendOption(option);
                });
                self.protocolParameters(protocolParameters);

                transportParameters = self.transportParameters();
                _.each(transportParameters, function(option) {
                    extendOption(option);
                });
                self.transportParameters(transportParameters);
            }
        });

        // Protocol
        self.availableProtocols = ko.observableArray();
        self.selectedProtocol = ko.observable(undefined);
        self.protocolParameters = ko.observable();
        self.advancedProtocolParameters = ko.observable();
        self.showAdvancedProtocolOptions = function() {
            $("#connection_protocol_dialog").modal("show");
        };

        self.selectedProtocol.subscribe(function() {
            var protocol = self.selectedProtocol();
            if (protocol) {
                self.protocolParameters(protocol.options);
            } else {
                self.protocolParameters([]);
            }

            self.advancedProtocolParameters(_.any(self.protocolParameters(), function(p) { return p.advanced }));
        });

        // Transport
        self.availableTransports = ko.observableArray();
        self.selectedTransport = ko.observable(undefined);
        self.transportParameters = ko.observableArray();
        self.advancedTransportParameters = ko.observable();
        self.showAdvancedTransportOptions = function() {

        };

        self.selectedTransport.subscribe(function() {
            var transport = self.selectedTransport();
            if (transport) {
                self.transportParameters(transport.options);
            } else {
                self.transportParameters([]);
            }

            self.advancedTransportParameters(_.any(self.transportParameters(), function(p) { return p.advanced }));
        });

        self.adjustConnectionParameters = ko.observable();
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
            var connections = response.options.connectionProfiles;

            var profiles = response.options.printerProfiles;

            // protocol
            var protocols = response.options.protocols;
            var protocolOptions = response.current.protocolOptions;
            if (!protocolOptions) {
                protocolOptions = {};
            }

            _.each(protocols, function(protocol) {
                _.each(protocol.options, function(option) {
                    extendOption(option, protocolOptions[option.name]);
                });
            });

            self.availableProtocols(protocols);

            // transport
            var transports = response.options.transports;
            var transportOptions = response.current.transportOptions;
            if (!transportOptions) {
                transportOptions = {};
            }

            _.each(transports, function(transport) {
                _.each(transport.options, function(option) {
                    extendOption(option, transportOptions[option.name]);
                });
            });

            self.availableTransports(transports);

            self.availableConnectionProfiles(connections);

            //~~ Connection profile or not?

            var connectionKey = response.current.connection;
            if (connectionKey) {
                var connection = _.find(connections, function(c) { return c.id === connectionKey });
                self.selectedConnectionProfile(connection);
            } else if (self.selectedConnectionProfile() === undefined) {
                var profile = response.current.profile;

                var protocolKey = response.current.protocol;
                var protocol = _.find(protocols, function(p) { return p.key === protocolKey });

                var transportKey = response.current.transport;
                var transport = _.find(transports, function(t) { return t.key === transportKey });

                if (!self.selectedPrinter() && profiles && profiles.indexOf(profile) >= 0)
                    self.selectedPrinter(profile);

                self.selectedProtocol(protocol);
                self.selectedTransport(transport);
                self.adjustConnectionParameters(true);
            }

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

        self.connect = function(save) {
            if (self.isErrorOrClosed()) {
                var toOptions = function(parameters) {
                    var result = {};
                    _.each(parameters, function(parameter) {
                        if (parameter.type === "group") {
                            result[parameter.name] = toOptions(parameter.params);
                        } else {
                            result[parameter.name] = parameter.value();
                        }
                    });
                    return result;
                };

                var data = {
                    "autoconnect": self.settings.serial_autoconnect()
                };

                var connectionProfile = self.selectedConnectionProfile();
                if (connectionProfile) {
                    data.connection = connectionProfile.id;
                }

                if (self.adjustConnectionParameters() || connectionProfile === undefined) {
                    data.printerProfile = self.selectedPrinter();
                    data.protocol = self.selectedProtocol().key;
                    data.protocolOptions = toOptions(self.protocolParameters());
                    data.transport = self.selectedTransport().key;
                    data.transportOptions = toOptions(self.transportParameters());
                }

                var finalize = function() {
                    self.settings.requestData();
                    self.settings.connectionProfiles.requestData();
                    self.settings.printerProfiles.requestData();
                };

                if (save) {
                    var profile = {
                        printer_profile: data.printerProfile,
                        protocol: data.protocol,
                        protocol_parameters: data.protocolOptions,
                        transport: data.transport,
                        transport_parameters: data.transportOptions
                    };

                    if (connectionProfile) {
                        profile.id = connectionProfile.id;
                        profile.name = connectionProfile.name;
                    }

                    self.connectionProfiles.editor.showDialog(profile, gettext("Save & Connect"))
                        .done(function(profile) {
                            OctoPrint.connection.connect({connection: profile.id})
                                .done(finalize);
                        });
                } else {
                    OctoPrint.connection.connect(data)
                        .done(finalize);
                }

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
        };

        self.onEventConnected = function() {
            self.requestData();
        };

        self.onEventDisconnected = function() {
            self.requestData();
        };

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

        self._sanitize = function(name) {
            return name.replace(/[^a-zA-Z0-9\-_\.\(\) ]/g, "").replace(/ /g, "_");
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ConnectionViewModel,
        dependencies: ["loginStateViewModel", "settingsViewModel", "connectionProfilesViewModel", "printerProfilesViewModel", "accessViewModel"],
        elements: ["#connection_wrapper", "#connection_protocol_dialog", "#connection_transport_dialog"]
    });
});
