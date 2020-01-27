$(function() {

    function PiSupportViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];

        self.model = ko.observable();

        self.currentUndervoltage = ko.observable(false);
        self.currentOverheat = ko.observable(false);
        self.pastUndervoltage = ko.observable(false);
        self.pastOverheat = ko.observable(false);
        self.currentIssue = ko.observable(false);
        self.pastIssue = ko.observable(false);

        self.requestData = function() {
            if (!self.loginState.hasPermission(self.access.permissions.PLUGIN_PI_SUPPORT_STATUS)) {
                return;
            }

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
                        + " <span class='octopi_version'>" + response.octopi_version + "</span></span>");
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

        self.popoverContent = ko.pureComputed(function() {
            var undervoltageParagraphClasses = "muted";
            var undervoltageSymbolClasses = "";

            var overheatParagraphClasses = "muted";
            var overheatSymbolClasses = "";

            if (self.currentUndervoltage()) {
                undervoltageSymbolClasses = "text-error pi_support_state_pulsate";
                undervoltageParagraphClasses = "";
            } else if (self.pastUndervoltage()) {
                undervoltageSymbolClasses = "text-error";
                undervoltageParagraphClasses = "";
            }

            if (self.currentOverheat()) {
                overheatSymbolClasses = "text-error pi_support_state_pulsate";
                overheatParagraphClasses = "";
            } else if (self.pastOverheat()) {
                overheatSymbolClasses = "text-error";
                overheatParagraphClasses = "";
            }

            return "<p class='" + undervoltageParagraphClasses + "'><strong class='" + undervoltageSymbolClasses + "'><i class=\"fa fa-bolt\"></i><i class=\"fa fa-exclamation\"></i></strong></strong> - " + gettext("Undervoltage. Make sure your power supply and cabling are providing enough power to the Pi.") + "</p>"
                + "<p class='" + overheatParagraphClasses + "'><strong class='" + overheatSymbolClasses + "'><i class=\"fa fa-thermometer-full\"></i><i class=\"fa fa-exclamation\"></i></strong> - " + gettext("Frequency capping due to overheating. Improve cooling of the CPU and GPU.") + "</p>"
                + "<p>" + gettext("A blinking symbol indicates a current issue, a non blinking symbol one that was observed some time since the Pi booted up.") + "</p>"
                + "<p><small>" + gettext("Click the symbol in the navbar for more information.") + "</small></p>";
        });

        self.onStartup = self.onServerReconnect = self.onUserLoggedIn = self.onUserLoggedOut = function() {
            self.requestData();
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== "pi_support") return;
            if (!data.hasOwnProperty("state") || !data.hasOwnProperty("type")) return;
            if (data.type !== "throttle_state") return;
            if (!self.loginState.hasPermission(self.access.permissions.PLUGIN_PI_SUPPORT_STATUS)) return;

            self.fromThrottleState(data.state);
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: PiSupportViewModel,
        elements: ["#navbar_plugin_pi_support"],
        dependencies: ["loginStateViewModel", "accessViewModel"]
    });
});
