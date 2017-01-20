(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var url = "api/languages";

    var OctoPrintLanguagesClient = function(base) {
        this.base = base;
    };

    OctoPrintLanguagesClient.prototype.list = function(opts) {
        return this.base.get(url, opts);
    };

    OctoPrintLanguagesClient.prototype.upload = function(file) {
        return this.base.upload(url, file);
    };

    OctoPrintLanguagesClient.prototype.delete = function(locale, pack, opts) {
        var packUrl = url + "/" + locale + "/" + pack;
        return this.base.delete(packUrl, opts);
    };

    OctoPrintClient.registerComponent("languages", OctoPrintLanguagesClient);
    return OctoPrintLanguagesClient;
});
