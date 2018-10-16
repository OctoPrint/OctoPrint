(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var OctoPrintPiSupportClient = function(base) {
        this.base = base;
    };

    OctoPrintPiSupportClient.prototype.get = function(opts) {
        return this.base.get(this.base.getSimpleApiUrl("pi_support"));
    };

    OctoPrintClient.registerPluginComponent("pi_support", OctoPrintPiSupportClient);
    return OctoPrintPiSupportClient;
});

$(function() {

    function PiSupportViewModel(parameters) {
        var self = this;

        self.model = ko.observable();

        self.currentUndervoltage = ko.observable(false);
        self.currentOverheat = ko.observable(false);
        self.pastUndervoltage = ko.observable(false);
        self.pastOverheat = ko.observable(false);
        self.currentIssue = ko.observable(false);
        self.pastIssue = ko.observable(false);

        self.requestData = function() {
            OctoPrint.plugins.pi_support.get()
                .done(function(response) {
                    // Raspberry Pi model
                    self.model(response.model);

                    // Throttle state
                    self.fromThrottleState(response.throttle_state);

                    // OctoPi version
                    $("#octopi_support_footer").remove();
                    if (!response.octopi_version) return;

                    var octoPrintVersion = $(".footer span.version");
                    var octoPiVersion = $("<span id='octopi_support_footer'> " + gettext("running on") + " " + gettext("OctoPi")
                        + " <span class='octopi_version'>" + response.octopi_version + "</span></span>")
                    $(octoPiVersion).insertAfter(octoPrintVersion);
                })
        };

        self.fromThrottleState = function(state) {
            self.currentUndervoltage(state.current_undervoltage);
            self.pastUndervoltage(state.past_undervoltage);
            self.currentOverheat(state.current_overheat);
            self.pastOverheat(state.past_overheat);
            self.currentIssue(state.current_issue);
            self.pastIssue(state.past_issue);
        };

        self.issuePopoverContent = function() {
            return "<p><strong><i class=\"fa fa-bolt\"></i><i class=\"fa fa-exclamation\"></i></strong></strong> - " + gettext("Undervoltage. Make sure your power supply and cabling are providing enough power to the Pi.") + "</p>"
                + "<p><strong><i class=\"fa fa-thermometer-full\"></i><i class=\"fa fa-exclamation\"></i></strong> - " + gettext("Frequency capping due to overheating. Improve cooling of the CPU and GPU.") + "</p>"
                + "<p>" + gettext("A blinking icon indicates an acute issue!") + "</p>"
        };

        self.onStartup = function() {
            self.requestData();
        };

        self.onServerReconnect = function() {
            self.requestData();
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== "pi_support") return;
            if (!data.hasOwnProperty("state") || !data.hasOwnProperty("type")) return;
            if (data.type !== "throttle_state") return;

            self.fromThrottleState(data.state);
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: PiSupportViewModel,
        elements: ["#navbar_plugin_pi_support"]
    });
});
