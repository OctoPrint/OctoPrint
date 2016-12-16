(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint"], factory);
    } else {
        factory(window.OctoPrint);
    }
})(window || this, function(OctoPrint) {
    var url = "api/connection";

    OctoPrint.connection = {
        getSettings: function(opts) {
            return OctoPrint.get(url, opts);
        },

        connect: function(data, opts) {
            return OctoPrint.issueCommand(url, "connect", data || {}, opts);
        },

        disconnect: function(opts) {
            return OctoPrint.issueCommand(url, "disconnect", {}, opts);
        },

        fakeAck: function(opts) {
            return OctoPrint.issueCommand(url, "fake_ack", {}, opts);
        }
    }
});
