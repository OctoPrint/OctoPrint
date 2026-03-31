$(function () {
    function ConnectionViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];
        self.printerProfiles = parameters[2];
        self.access = parameters[3];

        self.allViewModels = undefined;

        self.printerProfiles.profiles.items.subscribe(function () {
            var allProfiles = self.printerProfiles.profiles.items();

            var printerOptions = [];
            _.each(allProfiles, function (profile) {
                printerOptions.push({id: profile.id, name: profile.name});
            });
            self.profileOptions(printerOptions);
        });

        self.printerProfiles.currentProfile.subscribe(function () {
            self.currentProfile(self.printerProfiles.currentProfile());
        });

        self.connectionOptionsLastUpdated = ko.observable(false);
        self.selectedConnector = ko.observable(undefined);
        self.connectorOptions = ko.observableArray([]);
        self.connectorParameters = {};

        self.connectorParametersFor = (connector) => {
            if (!self.connectorParameters[connector]) return {};
            return self.connectorParameters[connector];
        };
        self.connectorParamOptionsFor = (connector, parameter) => {
            return ko.pureComputed(() => {
                self.connectionOptionsLastUpdated();
                const parameters = self.connectorParametersFor(connector);
                return parameters[parameter] !== undefined ? parameters[parameter] : [];
            });
        };

        self.currentConnectorCapabilities = ko.observable({});

        self.preferredConnectorName = ko.observable("-");
        self.preferredConnectorParameters = ko.observableArray([]);

        self.lastConnector = undefined;
        self.lastConnectorParameters = {};
        self.lastProfile = undefined;

        self.profileOptions = ko.observableArray(undefined);
        self.currentProfile = ko.observable(undefined);

        self.saveSettings = ko.observable(undefined);
        self.autoconnect = ko.observable(undefined);

        self.isErrorOrClosed = ko.observable(undefined);
        self.isOperational = ko.observable(undefined);
        self.isPrinting = ko.observable(undefined);
        self.isPaused = ko.observable(undefined);
        self.isError = ko.observable(undefined);
        self.isReady = ko.observable(undefined);
        self.isLoading = ko.observable(undefined);

        self.connectionParametersValidated = ko.observable(true);
        self.enableConnect = ko.pureComputed(function () {
            return self.connectionParametersValidated() || !self.isErrorOrClosed();
        });
        self.reevaluateConnectionParameters = (connector) => {
            window.setTimeout(() => {
                let reevaluateResult = undefined;
                callViewModels(
                    self.allViewModels,
                    "onReevaluateConnectionParameters",
                    (method) => {
                        if (reevaluateResult !== undefined) return;

                        const result = method(connector);
                        if (result === undefined || result === null) return;

                        reevaluateResult = result;
                        self.connectionParametersValidated(result);
                    }
                );
            }, 10);
        };
        self.setConnectionInputsEnabled = (enabled) => {
            self.doOnAllInputs((element) => {
                if (enabled) {
                    $(element).removeClass("disabled").attr("disabled", false);
                } else {
                    $(element).addClass("disabled").attr("disabled", true);
                }
            });
        };

        self.selectedConnector.subscribe(self.reevaluateConnectionParameters);

        self.isErrorOrClosed.subscribe((disconnected) => {
            self.setConnectionInputsEnabled(disconnected);
        });

        self.buttonText = ko.pureComputed(function () {
            if (self.isErrorOrClosed()) return gettext("Connect");
            else return gettext("Disconnect");
        });

        self.enableSaveSettings = ko.pureComputed(function () {
            return self.enableConnect() && self.isErrorOrClosed();
        });

        self.enableAutoConnect = ko.pureComputed(function () {
            return self.enableSaveSettings() && self.saveSettings();
        });

        self.previousIsOperational = undefined;

        self.refreshVisible = ko.observable(true);

        self.doOnAllInputsForConnector = (connector, callback) => {
            const container = $(`#connection_options_${connector}`);
            ["input", "select", "textarea"].forEach((tag) => {
                $(`${tag}[data-connection-parameter]`, container).each(
                    (index, element) => {
                        callback(element);
                    }
                );
            });
        };
        self.doOnAllInputs = (callback) => {
            self.connectorOptions().forEach((c) => {
                const connector = c.connector;
                self.doOnAllInputsForConnector(connector, callback);
            });
        };

        self.requestData = function () {
            if (!self.loginState.hasPermission(self.access.permissions.CONNECTION)) {
                return;
            }

            OctoPrint.connection.getSettings().done(self.fromResponse);
        };

        self.fromResponse = function (response) {
            const connectors = response.options.connectors;
            const currentConnector = response.current.connector;

            // preferred connection

            const preferredConnector = response.options.preferredConnector.connector;
            const preferredConnectorParameters =
                response.options.preferredConnector.parameters;
            const preferredConnectorData = connectors.find(
                (c) => c.connector === preferredConnector
            );

            if (preferredConnectorData) {
                self.preferredConnectorName(preferredConnectorData.name);
            } else {
                // fallback
                self.preferredConnectorName(`<code>${preferredConnector}</code>`);
            }

            let preferredConnectorParametersRendered = false;
            callViewModels(
                self.allViewModels,
                "onRenderParametersForConnector",
                (method) => {
                    if (preferredConnectorParametersRendered) return;

                    const result = method(
                        preferredConnector,
                        preferredConnectorParameters
                    );
                    if (result === false || !Array.isArray(result)) return;

                    preferredConnectorParametersRendered = true;
                    self.preferredConnectorParameters(
                        result
                            .filter(
                                // make sure everything has name & value
                                (item) =>
                                    item.name !== undefined && item.value !== undefined
                            )
                            .map((item) => `${item.name}: ${item.value}`)
                    );
                }
            );

            if (!preferredConnectorParametersRendered) {
                // fallback
                const params = [];
                for (const key in preferredConnectorParameters) {
                    params.push(
                        `<code>${key}</code>: <code>${JSON.stringify(preferredConnectorParameters[key])}</code>`
                    );
                }
                self.preferredConnectorParameters(params);
            }

            // available connectors, parameters & capabilities

            self.connectorOptions(connectors);

            const connectorParameters = {};
            connectors.forEach((item) => {
                connectorParameters[item.connector] = item.parameters;
            });
            self.connectorParameters = connectorParameters;

            self.currentConnectorCapabilities(response.current.capabilities);

            // determine active parameters

            let selectedConnector;
            let activeParameters;
            if (currentConnector && connectorParameters[currentConnector]) {
                selectedConnector = currentConnector;
                activeParameters = response.current.parameters;

                // also set last connector here
                self.lastConnector = currentConnector;
                self.lastConnectorParameters = response.current.parameters;
            } else if (self.lastConnector && connectorParameters[self.lastConnector]) {
                selectedConnector = self.lastConnector;
                activeParameters = self.lastConnectorParameters;
            } else if (preferredConnector && connectorParameters[preferredConnector]) {
                selectedConnector = preferredConnector;
                activeParameters = preferredConnectorParameters;
            } else {
                selectedConnector = connectors[0].connector;
                activeParameters = undefined;
            }

            // set parameters on connection form & inform viewmodels of received data

            if (activeParameters) {
                self.doOnAllInputsForConnector(selectedConnector, (element) => {
                    const jqueryElement = $(element);
                    const parameter = jqueryElement.data("connection-parameter");
                    const value = activeParameters[parameter];
                    if (value !== undefined) {
                        jqueryElement.val(value);
                    }
                });
            }

            callViewModels(self.allViewModels, "onConnectionDataReceived", [
                connectorParameters,
                response.current,
                {connector: self.lastConnector, parameters: self.lastConnectorParameters},
                response.options.preferredConnector
            ]);

            // add listeners to inputs to detect changes & reevaluate connection availability

            const event = "input.revalidate";
            self.doOnAllInputs((element) => {
                $(element)
                    .off(event)
                    .on(event, () => {
                        if (self.selectedConnector() === connector) {
                            self.reevaluateConnectionParameters(connector);
                        }
                    });
            });

            self.selectedConnector(selectedConnector);

            self.setConnectionInputsEnabled(self.isErrorOrClosed());

            // printer profile

            const printerProfiles = response.options.profiles;
            const preferredProfile = response.options.preferredProfile;
            const currentProfile = response.current.profile;

            if (!self.currentProfile() && printerProfiles) {
                if (printerProfiles.indexOf(currentProfile) >= 0) {
                    self.currentProfile(currentProfile);
                    self.lastProfile = currentProfile;
                } else if (printerProfiles.indexOf(self.lastProfile) >= 0) {
                    self.currentProfile(self.lastProfile);
                } else if (printerProfiles.indexOf(preferredProfile) >= 0) {
                    self.currentProfile(preferredProfile);
                }
            }

            self.saveSettings(false);
            self.autoconnect(false);
            self.connectionOptionsLastUpdated(new Date().getTime());
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
                const connector = self.selectedConnector();
                const profile = self.currentProfile();

                const parameters = {};
                self.doOnAllInputsForConnector(connector, (element) => {
                    const jqueryElement = $(element);
                    const parameter = jqueryElement.data("connection-parameter");
                    parameters[parameter] = jqueryElement.val();
                });

                const data = {
                    connector: connector,
                    parameters: parameters,
                    printerProfile: profile,
                    autoconnect: self.autoconnect()
                };

                if (self.saveSettings()) data["save"] = true;

                self.autoconnect(false);
                self.saveSettings(false);

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
                                "could interrupt the print.</p>"
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

        self.onEventSettingsUpdated =
            self.onEventConnected =
            self.onEventDisconnected =
            self.onEventConnectionsAutorefreshed =
                function () {
                    self.requestData();
                };

        self.onAllBound = function (allViewModels) {
            self.allViewModels = allViewModels;
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
        elements: ["#connection_wrapper", "#settings_printerconnection"]
    });
});
