$(function () {
    function SerialConnectorViewModel(parameters) {
        var self = this;

        self.lastUpdated = ko.observable(false);

        self.portOptions = ko.observableArray([]);
        self.baudrateOptions = ko.observableArray([]);
        self.currentPort = ko.observable();
        self.currentBaudrate = ko.observable();
        self.validPort = ko.pureComputed(
            () =>
                !self.lastUpdated() ||
                self.portOptions().length > 0 ||
                self.settings.settings.serial.ignoreEmptyPorts()
        );
        self.portCaption = ko.pureComputed(() =>
            self.validPort() ? "AUTO" : gettext("No serial port found")
        );
        self.enablePort = ko.pureComputed(
            () => self.validPort() && self.isErrorOrClosed()
        );

        self.onConnectionDataReceived = (parameters, current, preferred) => {
            const ports = parameters.serial.port;
            const baudrates = parameters.serial.baudrate;

            const currentPort =
                current.connector === "serial" ? current.parameters.port : null;
            const currentBaudrate =
                current.connector === "serial" ? current.baudrate : null;

            const preferredPort =
                preferred.connector == "serial" ? preferred.parameters.port : null;
            const preferredBaudrate =
                preferred.connector == "serial" ? preferred.parameters.baudrate : null;

            self.portOptions(ports);
            self.baudrateOptions(baudrates);

            if (!self.currentPort() && ports) {
                if (currentPort && ports.indexOf(currentPort) >= 0) {
                    self.currentPort(currentPort);
                } else if (preferredPort && ports.indexOf(preferredPort) >= 0) {
                    self.currentPort(preferredPort);
                }
            }

            if (!self.currentBaudrate() && baudrates) {
                if (currentBaudrate && baudrates.indexOf(currentBaudrate) >= 0) {
                    self.currentBaudrate(currentBaudrate);
                } else if (
                    preferredBaudrate &&
                    baudrates.indexOf(preferredBaudrate) >= 0
                ) {
                    self.currentBaudrate(preferredBaudrate);
                }
            }

            self.lastUpdated(new Date().getTime());
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: SerialConnectorViewModel,
        dependencies: [],
        elements: ["#connection_options_serial"]
    });
});
