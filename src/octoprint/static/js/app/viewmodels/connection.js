$(function () {
    function ConnectionViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];
        self.connectionProfiles = parameters[2];
        self.printerProfiles = parameters[3];
        self.access = parameters[4];

        var checkRecursively = function (params, check) {
            return _.any(params, function (p) {
                if (p.type === "group") {
                    return check(p) || checkRecursively(p.params, check);
                } else if (p.type === "presetchoice" && p.group) {
                    return (
                        check(p) ||
                        check(p.group) ||
                        checkRecursively(p.group.params, check)
                    );
                } else {
                    return check(p);
                }
            });
        };

        var convertValue = function (value, option, override) {
            if (override !== undefined) {
                value = override;
            }

            if (value === undefined && option.default !== undefined) {
                value = option.default;
            }

            if (value && (option.type === "list" || option.type === "smalllist")) {
                value = value.join(", ");
            }

            return value;
        };

        var extendOption = function (option, value, override) {
            if (option.type === "group") {
                if (value === undefined) {
                    value = {};
                }
                _.each(option.params, function (option) {
                    extendOption(option, value[option.name]);
                });

                option.advancedParameters =
                    option.advanced ||
                    _.any(option.params, function (p) {
                        return p.advanced;
                    });
                option.expertParameters =
                    option.expert ||
                    _.any(option.params, function (p) {
                        return p.expert;
                    });
            } else {
                if (option.type === "presetchoice") {
                    value = convertValue(value, option);
                    _.each(option.group.params, function (p) {
                        extendOption(
                            p,
                            option.defaults[option.default][p.name],
                            override ? override[p.name] : undefined
                        );
                    });
                } else if (option.type === "conditionalgroup") {
                    value = convertValue(value, option);
                    option.expertParameters = {};
                    _.each(option.groups, function (group, key) {
                        _.each(group, function (p) {
                            extendOption(
                                p,
                                undefined,
                                override ? override[p.name] : undefined
                            );
                        });
                        option.expertParameters[key] = _.any(group, function (p) {
                            return p.expert;
                        });
                    });
                } else {
                    value = convertValue(value, option, override);
                }

                if (option.value) {
                    option.value(value);
                } else {
                    option.value = ko.observable(value);
                    option.defaultValue = ko.observable(option.default);
                    option.reset = function () {
                        option.value(option.defaultValue());
                    };

                    option.modified = ko.pureComputed(function () {
                        // noinspection EqualityComparisonWithCoercionJS
                        return option.value() != option.defaultValue();
                    });

                    if (option.type === "presetchoice" && option.defaults) {
                        option.group.advancedParameters =
                            option.group.advanced ||
                            _.any(option.group.params, function (p) {
                                return p.advanced;
                            });
                        option.group.expertParameters =
                            option.group.expert ||
                            _.any(option.group.params, function (p) {
                                return p.expert;
                            });

                        var updateDefaults = function (keepValue) {
                            keepValue = !!keepValue;

                            var choice = _.find(option.choices, function (c) {
                                return c.value === option.value();
                            });
                            if (choice) {
                                _.each(option.group.params, function (p) {
                                    if (option.defaults[choice.value]) {
                                        var d = option.defaults[choice.value][p.name];
                                        if (d !== undefined) {
                                            p.defaultValue(
                                                convertValue(
                                                    d,
                                                    p,
                                                    override
                                                        ? override[p.name]
                                                        : undefined
                                                )
                                            );
                                            if (!keepValue) {
                                                p.value(p.defaultValue());
                                            }
                                        }
                                    }
                                });
                            }
                        };
                        option.value.subscribe(function () {
                            updateDefaults();
                        });
                        updateDefaults(true);
                    }
                }
            }
        };

        // Connection profiles

        self.availableConnectionProfiles = ko.observableArray();

        self.selectedConnectionProfile = ko.observable(undefined);
        self.selectedConnectionProfile.subscribe(function () {
            var protocolParameters, transportParameters;

            var profile = self.selectedConnectionProfile();

            if (profile) {
                self.selectedPrinter(
                    _.find(self.availablePrinterProfiles(), function (p) {
                        return p.id === profile.printer_profile;
                    })
                );
                self.selectedProtocol(
                    _.find(self.availableProtocols(), function (p) {
                        return p.key === profile.protocol;
                    })
                );
                self.selectedTransport(
                    _.find(self.availableTransports(), function (t) {
                        return t.key === profile.transport;
                    })
                );

                var processParameters = function (parameters, profile_parameters) {
                    _.each(parameters, function (option) {
                        var override = profile_parameters;
                        if (option.group) {
                            override = profile_parameters[option.group.name];
                        }
                        extendOption(option, profile_parameters[option.name], override);
                    });
                };

                protocolParameters = self.protocolParameters();
                processParameters(protocolParameters, profile.protocol_parameters);
                self.protocolParameters(protocolParameters);

                transportParameters = self.transportParameters();
                processParameters(transportParameters, profile.transport_parameters);
                self.transportParameters(transportParameters);
            } else {
                self.selectedPrinter(undefined);
                self.selectedProtocol(undefined);
                self.selectedTransport(undefined);

                protocolParameters = self.protocolParameters();
                _.each(protocolParameters, function (option) {
                    extendOption(option);
                });
                self.protocolParameters(protocolParameters);

                transportParameters = self.transportParameters();
                _.each(transportParameters, function (option) {
                    extendOption(option);
                });
                self.transportParameters(transportParameters);
            }
        });

        // Printer profiles

        self.availablePrinterProfiles = ko.observableArray();
        self.selectedPrinter = ko.observable(undefined);

        // Protocols

        self.availableProtocols = ko.observableArray();
        self.selectedProtocol = ko.observable(undefined);
        self.protocolParameters = ko.observable();
        self.advancedProtocolParameters = ko.observable();
        self.expertProtocolParameters = ko.observable();
        self.showAdvancedProtocolOptions = function () {
            $("#connection_protocol_dialog").modal("show");
        };

        self.selectedProtocol.subscribe(function () {
            var protocol = self.selectedProtocol();
            if (protocol) {
                self.protocolParameters(protocol.options);
            } else {
                self.protocolParameters([]);
            }

            self.advancedProtocolParameters(
                _.any(self.protocolParameters(), function (p) {
                    return p.advanced;
                })
            );
            self.expertProtocolParameters(
                _.any(self.protocolParameters(), function (p) {
                    return p.expert;
                })
            );
        });

        // Transports

        self.availableTransports = ko.observableArray();
        self.selectedTransport = ko.observable(undefined);
        self.transportParameters = ko.observableArray();
        self.advancedTransportParameters = ko.observable();
        self.expertTransportParameters = ko.observable();
        self.showAdvancedTransportOptions = function () {
            $("#connection_transport_dialog").modal("show");
        };

        self.selectedTransport.subscribe(function () {
            var transport = self.selectedTransport();
            if (transport) {
                self.transportParameters(transport.options);
            } else {
                self.transportParameters([]);
            }

            self.advancedTransportParameters(
                _.any(self.transportParameters(), function (p) {
                    return p.advanced;
                })
            );
            self.expertTransportParameters(
                _.any(self.transportParameters(), function (p) {
                    return p.expert;
                })
            );
        });

        // Various other bits

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

        self.buttonText = ko.pureComputed(function () {
            if (self.isErrorOrClosed()) return gettext("Connect");
            else return gettext("Disconnect");
        });

        self.previousIsOperational = undefined;

        self.refreshVisible = ko.observable(true);

        self.requestData = function () {
            if (!self.loginState.hasPermission(self.access.permissions.CONNECTION)) {
                return;
            }

            return OctoPrint.connection.getSettings().done(self.fromResponse);
        };

        self.fromResponse = function (response) {
            //~~ Available options...

            // connection profiles
            var connections = response.options.connectionProfiles;
            self.availableConnectionProfiles(connections);

            // printer profiles
            var printers = response.options.printerProfiles;
            self.availablePrinterProfiles(printers);

            // protocols
            var protocols = response.options.protocols;
            var protocolOptions = response.current.protocolOptions;
            if (!protocolOptions) {
                protocolOptions = {};
            }

            _.each(protocols, function (protocol) {
                _.each(protocol.options, function (option) {
                    extendOption(
                        option,
                        protocolOptions[option.name],
                        option.group ? protocolOptions[option.group.name] : undefined
                    );
                });
            });

            self.availableProtocols(protocols);

            // transports
            var transports = response.options.transports;
            var transportOptions = response.current.transportOptions;
            if (!transportOptions) {
                transportOptions = {};
            }

            _.each(transports, function (transport) {
                _.each(transport.options, function (option) {
                    extendOption(
                        option,
                        transportOptions[option.name],
                        option.group ? transportOptions[option.group.name] : undefined
                    );
                });
            });

            self.availableTransports(transports);

            //~~ Currently active config

            var connectionKey = response.current.connection;
            if (!connectionKey) {
                connectionKey = response.options.connectionProfilePreference;
            }

            if (connectionKey) {
                // there's currently a connection profile selected on the server
                var connection = _.find(connections, function (c) {
                    return c.id === connectionKey;
                });
                self.selectedConnectionProfile(connection);
            } else {
                self.adjustConnectionParameters(true);
                self.saveSettings(false);
            }

            var printerKey = response.current.profile;
            if (!connectionKey && !printerKey) {
                printerKey = response.options.printerProfilePreference;
            }

            if (printerKey) {
                var printer = _.find(printers, function (p) {
                    return p.id === printerKey;
                });
                self.selectedPrinter(printer);
            }

            var protocolKey = response.current.protocol;
            if (protocolKey) {
                var protocol = _.find(protocols, function (p) {
                    return p.key === protocolKey;
                });
                self.selectedProtocol(protocol);
                var protocolParameters = self.protocolParameters();
                _.each(protocolParameters, function (option) {
                    extendOption(option, response.current.protocolOptions[option.name]);
                });
                self.protocolParameters(protocolParameters);
            }

            var transportKey = response.current.transport;
            if (transportKey) {
                var transport = _.find(transports, function (t) {
                    return t.key === transportKey;
                });
                self.selectedTransport(transport);
                var transportParameters = self.transportParameters();
                _.each(transportParameters, function (option) {
                    extendOption(option, response.current.transportOptions[option.name]);
                });
                self.transportParameters(transportParameters);
            }
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

        self.connect = function (save) {
            if (self.isErrorOrClosed()) {
                var toOptions = function (parameters) {
                    var result = {};
                    _.each(parameters, function (parameter) {
                        if (parameter.type === "group") {
                            result[parameter.name] = toOptions(parameter.params);
                        } else if (parameter.type === "presetchoice") {
                            result[parameter.name] = parameter.value();
                            result[parameter.group.name] = toOptions(
                                parameter.group.params
                            );
                        } else if (parameter.type === "conditionalgroup") {
                            result[parameter.name] = parameter.value();
                            result = Object.assign(
                                result,
                                toOptions(parameter.groups[parameter.value()])
                            );
                        } else if (
                            parameter.type === "list" ||
                            parameter.type === "smalllist"
                        ) {
                            result[parameter.name] = splitTextToArray(
                                parameter.value(),
                                ",",
                                true
                            );
                        } else if (parameter.type === "integer") {
                            result[parameter.name] = parseInt(parameter.value());
                        } else if (parameter.type === "float") {
                            result[parameter.name] = parseFloat(parameter.value());
                        } else {
                            result[parameter.name] = parameter.value();
                        }
                    });
                    return result;
                };

                var data = {
                    autoconnect: self.settings.serial_autoconnect()
                };

                var connectionProfile = self.selectedConnectionProfile();
                if (connectionProfile) {
                    data.connection = connectionProfile.id;
                }

                if (
                    self.adjustConnectionParameters() ||
                    connectionProfile === undefined
                ) {
                    data.printerProfile = self.selectedPrinter().id;
                    data.protocol = self.selectedProtocol().key;
                    data.protocolOptions = toOptions(self.protocolParameters());
                    data.transport = self.selectedTransport().key;
                    data.transportOptions = toOptions(self.transportParameters());
                }

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

                    self.connectionProfiles.editor
                        .showDialog(profile, gettext("Save & Connect"))
                        .done(function (profile) {
                            OctoPrint.connection.connect({connection: profile.id});
                        });
                } else {
                    OctoPrint.connection.connect(data);
                }
            } else {
                if (!self.isPrinting() && !self.isPaused()) {
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

        self.onUserPermissionsChanged = self.onUserLoggedIn = self.onUserLoggedOut = function () {
            self.requestData();
        };

        self._sanitize = function (name) {
            return name.replace(/[^a-zA-Z0-9\-_.() ]/g, "").replace(/ /g, "_");
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ConnectionViewModel,
        dependencies: [
            "loginStateViewModel",
            "settingsViewModel",
            "connectionProfilesViewModel",
            "printerProfilesViewModel",
            "accessViewModel"
        ],
        elements: [
            "#connection_wrapper",
            "#connection_protocol_dialog",
            "#connection_transport_dialog"
        ]
    });
});
