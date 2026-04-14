$(function () {
    function SerialConnectorViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];

        //~~ serial log warning in navbar

        self.serialLogWarning = ko.pureComputed(() => {
            return (
                self.settings &&
                self.settings.settings &&
                self.settings.settings.plugins &&
                self.settings.settings.plugins.serial_connector &&
                self.settings.settings.plugins.serial_connector.log()
            );
        });

        self.serialLogPopoverContent = function () {
            var content =
                "<p>" +
                _.sprintf(
                    gettext(
                        "You currently have <code>%(logfile)s</code> enabled. Please remember to turn it off " +
                            "again once you are done debugging whatever issue prompted you to turn it on."
                    ),
                    {logfile: "serial.log"}
                ) +
                "</p><p>" +
                gettext(
                    "It can negatively impact print performance and also take up a lot of storage space " +
                        "depending on how long you keep it enabled and thus should only be used for " +
                        "debugging."
                ) +
                "</p>";
            return content;
        };

        //~~ connection related

        self.lastUpdated = ko.observable(false);

        self.portOptions = ko.observableArray([]);
        self.baudrateOptions = ko.observableArray([]);
        self.currentPort = ko.observable();
        self.currentBaudrate = ko.observable();
        self.validPort = ko.pureComputed(
            () =>
                !self.lastUpdated() ||
                self.portOptions().length > 0 ||
                self.settings.settings.plugins.serial_connector.ignoreEmptyPorts()
        );
        self.portCaption = ko.pureComputed(() =>
            self.validPort() ? "AUTO" : gettext("No serial port found")
        );

        self.onConnectionDataReceived = (parameters, current, last, preferred) => {
            const ports = parameters.serial.port;
            const baudrates = parameters.serial.baudrate;

            const currentPort =
                current.connector === "serial" ? current.parameters.port : undefined;
            const currentBaudrate =
                current.connector === "serial" ? current.baudrate : undefined;

            const lastPort =
                last.connector === "serial" ? last.parameters.port : undefined;
            const lastBaudrate =
                last.connector === "serial" ? last.parameters.baudrate : undefined;

            const preferredPort =
                preferred.connector == "serial" ? preferred.parameters.port : undefined;
            const preferredBaudrate =
                preferred.connector == "serial"
                    ? preferred.parameters.baudrate
                    : undefined;

            self.portOptions(ports);
            self.baudrateOptions(baudrates);

            if (!self.currentPort() && ports) {
                if (currentPort !== undefined && ports.indexOf(currentPort) >= 0) {
                    self.currentPort(currentPort);
                } else if (lastPort !== undefined && ports.indexOf(lastPort) >= 0) {
                    self.currentPort(lastPort);
                } else if (
                    preferredPort !== undefined &&
                    ports.indexOf(preferredPort) >= 0
                ) {
                    self.currentPort(preferredPort);
                }
            }

            if (!self.currentBaudrate() && baudrates) {
                if (
                    currentBaudrate !== undefined &&
                    baudrates.indexOf(currentBaudrate) >= 0
                ) {
                    self.currentBaudrate(currentBaudrate);
                } else if (
                    lastBaudrate !== undefined &&
                    baudrates.indexOf(lastBaudrate) >= 0
                ) {
                    self.currentBaudrate(lastBaudrate);
                } else if (
                    preferredBaudrate !== undefined &&
                    baudrates.indexOf(preferredBaudrate) >= 0
                ) {
                    self.currentBaudrate(preferredBaudrate);
                }
            }

            self.lastUpdated(new Date().getTime());
        };

        self.onRenderParametersForConnector = (connector, parameters) => {
            if (connector !== "serial") return false;

            return [
                {
                    name: gettext("Port"),
                    value: !parameters.port ? "AUTO" : parameters.port
                },
                {
                    name: gettext("Baudrate"),
                    value: !parameters.baudrate ? "AUTO" : parameters.baudrate
                }
            ];
        };

        self.onReevaluateConnectionParameters = (connector) => {
            if (connector !== "serial") return null;

            return self.validPort();
        };

        //~~ Settings related

        const get_config_item = (item, defaultValue) => {
            const parts = `plugins.serial_connector.${item}`.split(".");
            let node = self.settings.settings;
            for (let part of parts) {
                node = node[part];
                if (node === undefined) {
                    return defaultValue;
                }
            }
            return node();
        };

        const set_config_item = (item, value) => {
            const parts = `plugins.serial_connector.${item}`.split(".");
            let node = self.settings.settings;
            for (let part of parts) {
                node = node[part];
                if (node === undefined) {
                    return;
                }
            }
            node(value);
        };

        self.mapped = {
            additionalPorts: ko.pureComputed({
                read: () => get_config_item("additionalPorts", []).join(", "),
                write: (value) => {
                    set_config_item("additionalPorts", commentableLinesToArray(value));
                }
            }),
            additionalBaudrates: ko.pureComputed({
                read: () => get_config_item("additionalBaudrates").join(", "),
                write: (value) => {
                    set_config_item(
                        "additionalBaudrates",
                        _.map(splitTextToArray(value, ",", true), (item) =>
                            parseInt(item)
                        )
                    );
                }
            }),
            blocklistedPorts: ko.pureComputed({
                read: () => get_config_item("blocklistedPorts", []).join("\n"),
                write: (value) => {
                    set_config_item("blocklistedPorts", commentableLinesToArray(value));
                }
            }),
            blocklistedBaudrates: ko.pureComputed({
                read: () => get_config_item("blocklistedBaudrates", []).join(", "),
                write: (value) => {
                    set_config_item(
                        "blocklistedBaudrates",
                        _.map(splitTextToArray(value, ",", true), (item) =>
                            parseInt(item)
                        )
                    );
                }
            }),
            longRunningCommands: ko.pureComputed({
                read: () => get_config_item("longRunningCommands", []).join(", "),
                write: (value) => {
                    set_config_item(
                        "longRunningCommands",
                        splitTextToArray(value, ",", true)
                    );
                }
            }),
            checksumRequiringCommands: ko.pureComputed({
                read: () => get_config_item("checksumRequiringCommands", []).join(", "),
                write: (value) => {
                    set_config_item(
                        "checksumRequiringCommands",
                        splitTextToArray(value, ",", true)
                    );
                }
            }),
            blockedCommands: ko.pureComputed({
                read: () => get_config_item("blockedCommands", []).join(", "),
                write: (value) => {
                    set_config_item(
                        "blockedCommands",
                        splitTextToArray(value, ",", true)
                    );
                }
            }),
            ignoredCommands: ko.pureComputed({
                read: () => get_config_item("ignoredCommands", []).join(", "),
                write: (value) => {
                    set_config_item(
                        "ignoredCommands",
                        splitTextToArray(value, ",", true)
                    );
                }
            }),
            pausingCommands: ko.pureComputed({
                read: () => get_config_item("pausingCommands", []).join(", "),
                write: (value) => {
                    set_config_item(
                        "pausingCommands",
                        splitTextToArray(value, ",", true)
                    );
                }
            }),
            emergencyCommands: ko.pureComputed({
                read: () => get_config_item("emergencyCommands", []).join(", "),
                write: (value) => {
                    set_config_item(
                        "emergencyCommands",
                        splitTextToArray(value, ",", true)
                    );
                }
            }),
            disableExternalHeatupDetection: ko.pureComputed({
                read: () => !get_config_item("externalHeatupDetection", true),
                write: (value) => {
                    set_config_item("externalHeatupDetection", !value);
                }
            })
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: SerialConnectorViewModel,
        dependencies: ["settingsViewModel"],
        elements: [
            "#connection_options_serial",
            "#settings_plugin_serial_connector",
            "#navbar_plugin_serial_connector_seriallog"
        ]
    });
});
