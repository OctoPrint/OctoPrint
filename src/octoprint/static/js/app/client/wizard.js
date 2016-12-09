(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint"], factory);
    } else {
        factory(window.OctoPrint);
    }
})(window || this, function(OctoPrint) {
    var url = "api/setup/wizard";

    OctoPrint.wizard = {
        get: function(opts) {
            return OctoPrint.get(url, opts);
        },
        finish: function(handled, opts) {
            return OctoPrint.postJson(url, {handled: handled || []}, opts);
        }
    };
});
