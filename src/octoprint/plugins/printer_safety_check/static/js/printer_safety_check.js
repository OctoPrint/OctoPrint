$(function() {
    function PrinterSafetyCheckViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.printerState = parameters[1];
        self.access = parameters[2];

        self.warnings = ko.observableArray([]);

        self.requestData = function() {
            if (!self.loginState.hasPermission(self.access.permissions.PLUGIN_PRINTER_SAFETY_CHECK_DISPLAY)) {
                self.warnings([]);
                return;
            }

            OctoPrint.plugins.printer_safety_check.get()
                .done(self.fromResponse)
                .fail(function() {
                    self.warnings([]);
                });
        };

        self.fromResponse = function(data) {
            var warnings = [];
            _.each(data, function(data, warning_type) {
                warnings.push({
                    type: warning_type,
                    message: gettext(data.message),
                    severity: data.severity,
                    url: data.url
                });
            });
            self.warnings(warnings);
        };

        self.onStartup = function() {
            self.requestData();
        };

        self.onUserPermissionsChanged = self.onUserLoggedIn = self.onUserLoggedOut = function() {
            self.requestData();
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== "printer_safety_check") return;
            if (!data.hasOwnProperty("type")) return;

            if (data.type === "update") {
                self.requestData();
            }
        };

        self.cssClass = function(data) {
            if (data.severity) {
                return "printer_safety_warning_" + data.severity;
            } else {
                return undefined;
            }
        };

        self.warningText = function(data) {
            switch (data.severity) {
                case "critical": return gettext("Critical Warning");
                default: return gettext("Warning");
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: PrinterSafetyCheckViewModel,
        dependencies: ["loginStateViewModel", "printerStateViewModel", "accessViewModel"],
        elements: ["#sidebar_plugin_printer_safety_check_wrapper"]
    });
});

