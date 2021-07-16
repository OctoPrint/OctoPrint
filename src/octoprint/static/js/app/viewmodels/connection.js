$(function () {
    var checkRecursively = function (params, check) {
        return _.any(params, function (p) {
            if (p.type === "group") {
                return check(p) || checkRecursively(p.params, check);
            } else if (p.type === "presetchoice" && p.group) {
                return (
                    check(p) || check(p.group) || checkRecursively(p.group.params, check)
                );
            } else {
                return check(p);
            }
        });
    };

    var convertValueFromBackend = function (value, option, override) {
        /**
         * Picks the right value to apply based on value, defaults and overrides.
         *
         * override > value > override
         *
         * In case of list or smalllist, the value will also be converted from a
         * list to a comma separated string.
         *
         * @param value the value to apply
         * @param option the option object, to lookup a default if needed
         * @param override the current override value, or undefined
         */
        if (override !== undefined) {
            value = override;
        }

        if (value === undefined && option.default !== undefined) {
            value = option.default;
        }

        if (value) {
            if (option.type === "list") {
                value = value.join("\n");
            } else if (option.type === "smalllist") {
                value = value.join(",");
            }
        }

        return value;
    };

    var convertValueToBackend = function (value, option) {
        if (option.type === "list") {
            value = splitTextToArray(value, "\n", true);
        } else if (option.type === "smalllist") {
            value = splitTextToArray(value, ",", true);
        } else if (option.type === "integer") {
            value = parseInt(value);
        } else if (option.type === "float") {
            value = parseFloat(value);
        }
        return value;
    };

    var setOptionValue = function (option, value, data) {
        /**
         * Sets the given value on the given option.
         *
         * In case of a group option, the value will be considered a dictionary of values
         * to apply to the children of the group.
         *
         * @param option the option to extend
         * @param value the value to apply to the option, or undefined
         * @param data the currently active data object, or undefined
         */

        if (option.type === "group") {
            if (value === undefined) {
                value = {};
            }
            _.each(option.params, function (option) {
                setOptionValue(
                    option,
                    value[option.name],
                    data ? data[option.name] : undefined
                );
            });
        } else {
            if (option.type === "presetchoice") {
                value = convertValueFromBackend(
                    value,
                    option,
                    data ? data[option.name] : undefined
                );
                _.each(option.group.params, function (p) {
                    setOptionValue(
                        p,
                        option.defaults[value]
                            ? option.defaults[value][p.name]
                            : undefined,
                        data ? data[option.group.name] : undefined
                    );
                });
            } else if (option.type === "conditionalgroup") {
                value = convertValueFromBackend(
                    value,
                    option,
                    data ? data[option.name] : undefined
                );
                option.expertParameters = {};
                _.each(option.groups, function (group, key) {
                    _.each(group, function (p) {
                        setOptionValue(p, undefined, data);
                    });
                    option.expertParameters[key] = _.any(group, function (p) {
                        return p.expert;
                    });
                });
            } else {
                value = convertValueFromBackend(
                    value,
                    option,
                    data ? data[option.name] : undefined
                );
            }

            option.value(value);
        }
    };

    var toOptions = function (parameters) {
        var result = {};
        _.each(parameters, function (parameter) {
            var value;
            if (parameter.type === "group") {
                value = toOptions(parameter.params);
            } else if (parameter.type === "presetchoice") {
                value = parameter.value();
                result[parameter.group.name] = toOptions(parameter.group.params);
            } else if (parameter.type === "conditionalgroup") {
                value = parameter.value();
                result = Object.assign(result, toOptions(parameter.groups[value]));
            } else {
                value = convertValueToBackend(parameter.value(), parameter);
            }

            // set the value on the result, if it differs from the default
            if (parameter.modified()) {
                result[parameter.name] = value;
            }
        });
        return result;
    };

    function EditedConnectionProfile(connectionViewModel) {
        var self = this;

        self.connectionViewModel = connectionViewModel;

        self.isNew = ko.observable(true);

        self.name = ko.observable();
        self.name.subscribe(function (value) {
            self.identifierPlaceholder(self._sanitize(value));
        });
        self.identifier = ko.observable();
        self.identifierPlaceholder = ko.observable();

        self.printerProfile = ko.observable();

        self.protocol = ko.observable();
        self.protocolParameters = ko.observableArray();
        self.advancedProtocolParameters = ko.observable(false);
        self.expertProtocolParameters = ko.observable(false);
        self.protocol.subscribe(function () {
            var protocol = self.protocol();

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

        self.transport = ko.observable();
        self.transportParameters = ko.observableArray();
        self.advancedTransportParameters = ko.observable(false);
        self.expertTransportParameters = ko.observable(false);
        self.transport.subscribe(function () {
            var transport = self.transport();

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

        self.fromProfileData = function (data) {
            self.isNew(data === undefined);

            if (data === undefined) {
                data = self.connectionViewModel.cleanProfile();
            }

            self.identifier(data.id);
            self.name(data.name);
            self.printerProfile(
                self.connectionViewModel.printerProfileLookup[data.printer_profile]
            );
            self.protocol(self.connectionViewModel.protocolLookup[data.protocol]);
            self.transport(self.connectionViewModel.transportLookup[data.transport]);

            var processParameters = function (parameters, profile_parameters) {
                _.each(parameters, function (option) {
                    extendOption(
                        option,
                        profile_parameters[option.name],
                        profile_parameters
                    );
                });
            };

            protocolParameters = self.protocolParameters();
            processParameters(protocolParameters, data.protocol_parameters);
            self.protocolParameters(protocolParameters);

            transportParameters = self.transportParameters();
            processParameters(transportParameters, data.transport_parameters);
            self.transportParameters(transportParameters);
        };

        self.toProfileData = function () {
            var identifier = self.identifier();
            if (!identifier) {
                identifier = self.identifierPlaceholder();
            }

            var profile = {
                id: identifier,
                name: self.name(),
                printer_profile: self.printerProfile().id,
                protocol: self.protocol().key,
                protocol_parameters: toOptions(self.protocolParameters()),
                transport: self.transport().key,
                transport_parameters: toOptions(self.transportParameters())
            };
            return profile;
        };

        self._sanitize = function (name) {
            return name
                ? name.replace(/[^a-zA-Z0-9\-_\.\(\) ]/g, "").replace(/ /g, "_")
                : undefined;
        };
    }

    function ConnectionProfileEditorViewModel(connectionViewModel) {
        var self = this;

        self.connection = connectionViewModel;

        self.active = ko.observable(false);
        self.deferred = undefined;

        self.dialogTitle = ko.observable(gettext("Save connection profile"));
        self.buttonText = ko.observable(gettext("Save"));

        self.dialog = $("#connectionprofiles_editor_dialog");

        self.profile = new EditedConnectionProfile(self.connection);
        self.overwrite = ko.observable(false);
        self.showOverwrite = ko.observable(true);

        self.makeDefault = ko.observable(false);
        self.showMakeDefault = ko.observable(false);

        self.showAddDialog = function (options) {
            options = options || {};
            return self.showDialog(undefined, options);
        };

        self.showEditDialog = function (profile, options) {
            options = options || {};
            options.title = options.title || gettext("Edit connection profile");
            options.button = options.button || gettext("Update");
            options.showOverwrite =
                options.showOverwrite !== undefined ? options.showOverwrite : false;

            return self.showDialog(profile, options);
        };

        self.showSaveAsDialog = function (profile, options) {
            options = options || {};
            options.title = options.title || gettext("Edit connection profile");
            options.button = options.button || gettext("Update");
            options.showOverwrite =
                options.showOverwrite !== undefined ? options.showOverwrite : true;

            return self.showDialog(profile, options);
        };

        self.showDialog = function (profile, options) {
            if (options.title) {
                self.dialogTitle(options.title);
            } else {
                self.dialogTitle(gettext("Save connection profile"));
            }

            if (options.button) {
                self.buttonText(options.button);
            } else {
                self.buttonText(gettext("Save"));
            }

            self.showOverwrite(!!options.showOverwrite);
            self.showMakeDefault(!!options.showMakeDefault);

            self.profile.fromProfileData(profile);
            self.deferred = $.Deferred();
            self.dialog
                .modal({
                    minHeight: function () {
                        return Math.max($.fn.modal.defaults.maxHeight() - 80, 250);
                    }
                })
                .css({
                    "margin-left": function () {
                        return -($(this).width() / 2);
                    }
                });
            return self.deferred.promise();
        };

        self.confirm = function () {
            var profile = self.profile.toProfileData();
            var overwrite = !self.showOverwrite() || self.overwrite();
            var makeDefault = self.showMakeDefault() && self.makeDefault();

            OctoPrint.connectionprofiles
                .set(profile.id, profile, overwrite, makeDefault)
                .done(function (response) {
                    self.dialog.modal("hide");
                    if (self.deferred) {
                        self.deferred.resolve(response.profile);
                    }
                });
        };
    }

    function ConnectionViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];
        self.printerProfiles = parameters[2];
        self.access = parameters[3];

        self.sychronizeSettings = function (observable, settings) {
            var parameters = observable();
            _.each(parameters, function (option) {
                setOptionValue(
                    option,
                    settings ? settings[option.name] : undefined,
                    settings
                );
            });
            observable(parameters);
        };

        // Connection profiles

        self.availableConnectionProfiles = ko.observableArray();
        self.preferredConnectionProfile = ko.observable();
        self.selectedConnectionProfile = ko.observable(undefined);
        self.selectedConnectionProfile.subscribe(function () {
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
            } else {
                self.selectedPrinter(undefined);
                self.selectedProtocol(undefined);
                self.selectedTransport(undefined);
            }
        });

        // Printer profiles

        self.availablePrinterProfiles = ko.observableArray();
        self.selectedPrinter = ko.observable();
        self.preferredPrinter = ko.observable();
        self.printerProfileLookup = {};

        self.availablePrinterProfiles.subscribe(function () {
            self.printerProfileLookup = {};
            _.each(self.availablePrinterProfiles(), function (profile) {
                self.printerProfileLookup[profile.id] = profile;
            });
        });

        self.lookupPrinterProfileName = function (id) {
            var profile = self.printerProfileLookup[id];
            return profile ? profile.name : id;
        };

        // Protocols

        self.availableProtocols = ko.observableArray();
        self.selectedProtocol = ko.observable();
        self.preferredProtocol = ko.observable();
        self.protocolParameters = ko.observable();
        self.advancedProtocolParameters = ko.pureComputed(function () {
            return _.any(self.protocolParameters(), function (p) {
                return p.advanced;
            });
        });
        self.expertProtocolParameters = ko.pureComputed(function () {
            return _.any(self.protocolParameters(), function (p) {
                return p.expert;
            });
        });

        self.showAdvancedProtocolOptions = function () {
            $("#connection_protocol_dialog").modal("show");
        };
        self.protocolLookup = {};

        self.availableProtocols.subscribe(function () {
            self.protocolLookup = {};
            _.each(self.availableProtocols(), function (protocol) {
                self.protocolLookup[protocol.key] = protocol;
            });
        });

        self.selectedProtocol.subscribe(function () {
            var protocol = self.selectedProtocol();
            var protocolOptions = [];
            if (protocol) {
                protocolOptions = protocol.options;
            }
            self.protocolParameters(protocolOptions);

            var connectionProfile = self.selectedConnectionProfile();
            self.sychronizeSettings(
                self.protocolParameters,
                connectionProfile ? connectionProfile.protocol_parameters : undefined
            );
        });

        self.lookupProtocolName = function (key) {
            var protocol = self.protocolLookup[key];
            return protocol ? protocol.name : key;
        };

        // Transports

        self.availableTransports = ko.observableArray();
        self.selectedTransport = ko.observable();
        self.preferredTransport = ko.observable();
        self.transportParameters = ko.observableArray();
        self.advancedTransportParameters = ko.pureComputed(function () {
            return _.any(self.transportParameters(), function (p) {
                return p.advanced;
            });
        });
        self.expertTransportParameters = ko.pureComputed(function () {
            return _.any(self.transportParameters(), function (p) {
                return p.expert;
            });
        });
        self.showAdvancedTransportOptions = function () {
            $("#connection_transport_dialog").modal("show");
        };
        self.transportLookup = {};

        self.availableTransports.subscribe(function () {
            self.transportLookup = {};
            _.each(self.availableTransports(), function (transport) {
                self.transportLookup[transport.key] = transport;
            });
        });

        self.selectedTransport.subscribe(function () {
            var transport = self.selectedTransport();
            var transportOptions = [];
            if (transport) {
                transportOptions = transport.options;
            }
            self.transportParameters(transportOptions);

            var connectionProfile = self.selectedConnectionProfile();
            self.sychronizeSettings(
                self.transportParameters,
                connectionProfile ? connectionProfile.transport_parameters : undefined
            );
        });

        self.lookupTransportName = function (key) {
            var transport = self.transportLookup[key];
            return transport ? transport.name : key;
        };

        // Profile editor

        self.cleanProfile = function () {
            return {
                id: "",
                name: "",
                printerProfile: self.preferredPrinter(),
                protocol: self.availableProtocols()[0],
                protocol_parameters: {},
                transport: self.availableTransports()[0],
                transport_parameters: {}
            };
        };

        self.editor = new ConnectionProfileEditorViewModel(self);

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

        // Data exchange

        self.requestData = function () {
            if (!self.loginState.hasPermission(self.access.permissions.CONNECTION)) {
                return;
            }

            var deferred = $.Deferred();

            var options = OctoPrint.connection.getOptions();
            var current = OctoPrint.connection.getSettings();

            $.when(options, current).done(function (options, current) {
                var data = {
                    options: options[0].options,
                    current: current[0].current
                };

                self.fromResponse(data);

                deferred.resolve(data);
            });

            return deferred.promise();
        };

        self.requestOptionsData = function () {
            if (!self.loginState.hasPermission(self.access.permissions.CONNECTION)) {
                return;
            }
            return OctoPrint.connection.getOptions().done(self.fromOptionsRespons);
        };

        self.requestCurrentData = function () {
            if (!self.loginState.hasPermission(self.access.permissions.CONNECTION)) {
                return;
            }
            return OctoPrint.connection.getSettings().done(self.fromCurrentResponse);
        };

        self.fromResponse = function (data) {
            // first the options...
            self.fromOptionsResponse(data.options);

            // ...then the current config
            self.fromCurrentResponse(data.current);
        };

        self.fromOptionsResponse = function (options) {
            var extendOption = function (option, valueNode) {
                if (!valueNode) {
                    valueNode = {};
                }

                if (option.type === "group") {
                    _.each(option.params, function (param) {
                        extendOption(param, valueNode[option.name]);
                    });

                    option.modified = ko.pureComputed(function () {
                        return _.any(option.params, function (p) {
                            return p.modified();
                        });
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
                        _.each(option.group.params, function (option) {
                            extendOption(option, valueNode[option.name]); // TODO
                        });
                    }

                    if (option.type === "conditionalgroup") {
                        option.expertParameters = {};
                        _.each(option.groups, function (group, key) {
                            _.each(group, function (option) {
                                extendOption(option, valueNode[option.name]); // TODO
                            });
                            option.expertParameters[key] = _.any(group, function (p) {
                                return p.expert;
                            });
                        });
                    }

                    var defaultValue = convertValueFromBackend(option.default, option);
                    option.defaultValue = ko.observable(defaultValue);

                    if (valueNode && _.isFunction(valueNode)) {
                        option.value = ko.pureComputed({
                            read: function () {
                                return convertValueFromBackend(valueNode(), option);
                            },
                            write: function (value) {
                                valueNode(convertValueToBackend(value, option));
                            },
                            owner: this
                        });
                        option.reset = function () {
                            valueNode(defaultValue);
                        };
                    } else {
                        option.value = ko.observable(defaultValue);
                        option.reset = function () {
                            option.value(defaultValue);
                        };
                    }
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
                                            p.defaultValue(convertValueFromBackend(d, p));
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
            };

            var extendOptions = function (input, settings) {
                if (!settings) settings = {};
                _.each(input, function (i) {
                    var node = settings[i.key];

                    _.each(i.options, function (option) {
                        extendOption(option);
                    });
                    _.each(i.settings, function (option) {
                        extendOption(option, node ? node[option.name] : {});
                    });
                });
            };

            // printer profiles
            self.preferredPrinter(options.printerProfilePreference);
            var printers = options.printerProfiles;
            _.each(printers, function (p) {
                p.isDefault = ko.pureComputed(function () {
                    return p.id === self.preferredPrinter();
                });
                p.isCurrent = ko.pureComputed(function () {
                    return p.id === self.selectedPrinter();
                });
            });
            self.availablePrinterProfiles(printers);

            // protocols
            var protocols = options.protocols;
            extendOptions(protocols, self.settings.settings.connection.protocols);
            self.availableProtocols(protocols);

            // transports
            var transports = options.transports;
            extendOptions(transports, self.settings.settings.connection.transports);
            self.availableTransports(transports);

            // connection profiles
            //
            // this has to be processed after the rest for the
            // subscriptions to fire off in the right order

            self.preferredConnectionProfile(options.connectionProfilePreference);
            var connections = options.connectionProfiles;
            _.each(connections, function (c) {
                c.isDefault = ko.pureComputed(function () {
                    return c.id === self.preferredConnectionProfile();
                });
                c.isCurrent = ko.pureComputed(function () {
                    return c.id === self.selectedConnectionProfile();
                });
            });
            self.availableConnectionProfiles(connections);
        };

        self.fromCurrentResponse = function (current) {
            var connectionKey = current.connection;
            if (!connectionKey) {
                connectionKey = self.preferredConnectionProfile();
            }

            if (connectionKey) {
                // there's currently a connection profile selected on the server
                var connection = _.find(self.availableConnectionProfiles(), function (c) {
                    return c.id === connectionKey;
                });

                // this will also set printer profile, protocol and transport through
                // subscriptions
                self.selectedConnectionProfile(connection);
            } else {
                self.adjustConnectionParameters(true);
                self.saveSettings(false);
            }

            var printerKey = current.profile;
            if (!connectionKey && !printerKey) {
                printerKey = self.preferredPrinter();
            }

            if (printerKey) {
                var printer = _.find(self.availablePrinterProfiles(), function (p) {
                    return p.id === printerKey;
                });
                self.selectedPrinter(printer);
            }

            var protocolKey = current.protocol;
            if (protocolKey) {
                var protocol = _.find(self.availableProtocols(), function (p) {
                    return p.key === protocolKey;
                });
                self.selectedProtocol(protocol);
            } else {
                self.selectedProtocol(self.availableProtocols()[0]);
            }

            var protocolParameters = self.protocolParameters();
            _.each(protocolParameters, function (option) {
                setOptionValue(
                    option,
                    current.protocolOptions[option.name],
                    current.protocolOptions
                );
            });
            self.protocolParameters(protocolParameters);
            console.log(protocolParameters);

            var transportKey = current.transport;
            if (transportKey) {
                var transport = _.find(self.availableTransports(), function (t) {
                    return t.key === transportKey;
                });
                self.selectedTransport(transport);
            } else {
                self.selectedProtocol(self.availableProtocols()[0]);
            }

            var transportParameters = self.transportParameters();
            _.each(transportParameters, function (option) {
                setOptionValue(
                    option,
                    current.transportOptions[option.name],
                    current.transportOptions
                );
            });
            self.transportParameters(transportParameters);
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

                    self.editor
                        .showSaveAsDialog(profile, {button: gettext("Save & Connect")})
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

        // events

        self.onEventSettingsUpdated = function () {
            self.requestData();
        };

        self.onEventConnected = function () {
            self.requestCurrentData();
        };

        self.onEventDisconnected = function () {
            self.requestCurrentData();
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
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ConnectionViewModel,
        dependencies: [
            "loginStateViewModel",
            "settingsViewModel",
            "printerProfilesViewModel",
            "accessViewModel"
        ],
        elements: [
            "#connection_wrapper",
            "#settings_connection",
            "#connection_protocol_dialog",
            "#connection_transport_dialog",
            "#connectionprofiles_editor_dialog"
        ]
    });
});
