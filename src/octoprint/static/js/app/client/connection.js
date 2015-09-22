OctoPrint.connection = (function() {
    var self = {};

    self.getSettings = function(opts) {
        opts = opts || {};

        var params = $.extend({}, opts);
        params.url = "api/connection";

        return OctoPrint.getJson(params);
    };

    self.connect = function(data, opts) {
        data = data || {};

        return self.issueCommand("connect", data, opts);
    };

    self.disconnect = function(opts) {
        return self.issueCommand("disconnect", {}, opts);
    };

    self.fakeAck = function(opts) {
        return self.issueCommand("fake_ack", {}, opts);
    };

    self.issueCommand = function(command, data, opts) {
        opts = opts || {};
        data = data || {};

        var payload = $.extend({}, data);
        payload.command = command;

        var params = $.extend({}, opts);
        params.url = "api/connection";

        return OctoPrint.postJson(payload, params);
    };

    return self;
})($, _);
