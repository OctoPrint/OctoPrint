(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var OctoPrintOctoPiSupportClient = function(base) {
        this.base = base;
    };

    OctoPrintOctoPiSupportClient.prototype.get = function(opts) {
        return this.base.get(this.base.getSimpleApiUrl("octopi_support"));
    };

    OctoPrintClient.registerPluginComponent("octopi_support", OctoPrintOctoPiSupportClient);
    return OctoPrintOctoPiSupportClient;
});

$(function() {

    function OctoPiSupportViewModel(parameters) {
        var self = this;

        self.requestData = function() {
            OctoPrint.plugins.octopi_support.get()
                .done(function(response) {
                    $("#octopi_support_footer").remove();
                    if (!response.version) return;

                    var octoPrintVersion = $(".footer span.version");
                    var octoPiVersion = $("<span id='octopi_support_footer'> " + gettext("running on") + " " + gettext("OctoPi")
                        + " <span class='octopi_version'>" + response.version + "</span></span>")
                    $(octoPiVersion).insertAfter(octoPrintVersion);
                })
        };

        self.onStartup = function() {
            self.requestData();
        };

        self.onServerReconnect = function() {
            self.requestData();
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: OctoPiSupportViewModel
    });
});
