(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var OctoPrintPrinterSafetyCheckClient = function(base) {
        this.base = base;
    };

    OctoPrintPrinterSafetyCheckClient.prototype.get = function(opts) {
        return this.base.get(this.base.getSimpleApiUrl("printer_safety_check"), opts);
    };

    OctoPrintClient.registerPluginComponent("printer_safety_check", OctoPrintPrinterSafetyCheckClient);
    return OctoPrintPrinterSafetyCheckClient;
});

$(function() {
    function PrinterSafetyCheckViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.printerState = parameters[1];

        self.warnings = ko.observableArray([]);

        self.requestData = function() {
            if (!self.loginState.isUser()) {
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
            _.each(data, function(message, warning_type) {
                warnings.push({type: warning_type, message: message});
            });
            self.warnings(warnings);
        };

        self.onStartup = function() {
            self.requestData();
        };

        self.onUserLoggedIn = function() {
            self.requestData();
        };

        self.onUserLoggedOut = function() {
            self.requestData();
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== "printer_safety_check") return;
            if (!data.hasOwnProperty("type")) return;

            if (data.type === "update") {
                self.requestData();
            }
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: PrinterSafetyCheckViewModel,
        dependencies: ["loginStateViewModel", "printerStateViewModel"],
        elements: ["#sidebar_plugin_printer_safety_check_wrapper"]
    });
});

