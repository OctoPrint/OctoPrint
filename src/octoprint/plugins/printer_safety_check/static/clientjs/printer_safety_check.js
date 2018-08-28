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
