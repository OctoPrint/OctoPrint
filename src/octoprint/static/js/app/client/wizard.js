(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var url = "api/setup/wizard";

    var OctoPrintWizardClient = function(base) {
        this.base = base;
    };

    OctoPrintWizardClient.prototype.get = function(opts) {
        return this.base.get(url, opts);
    };

    OctoPrintWizardClient.prototype.finish = function(handled, opts) {
        return this.base.postJson(url, {handled: handled || []}, opts);
    };

    OctoPrintClient.registerComponent("wizard", OctoPrintWizardClient);
    return OctoPrintWizardClient;
});
