$(function () {
    function UsageViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];

        self.setup = ko.observable(false);

        self.decision = ko.observable();
        self.active = ko.observable();
        self.required = false;

        self.onStartupComplete = function () {
            OctoPrint.plugins.tracking.track("webui_load", {
                browser_name: OctoPrint.coreui.browser.browser_name,
                browser_version: OctoPrint.coreui.browser.browser_version,
                os_name: OctoPrint.coreui.browser.os_name,
                os_version: OctoPrint.coreui.browser.os_version
            });
        };

        self.enableUsage = function () {
            self.settingsViewModel.settings.plugins.tracking.enabled(true);
            self.decision(true);
            self._sendData();
        };

        self.disableUsage = function () {
            self.settingsViewModel.settings.plugins.tracking.enabled(false);
            self.decision(false);
            self._sendData();
        };

        self.onBeforeWizardTabChange = function (next, current) {
            if (!self.required) return true;

            if (
                !current ||
                !_.startsWith(current, "wizard_plugin_tracking") ||
                self.setup()
            ) {
                return true;
            }

            self._showDecisionNeededDialog();
            return false;
        };

        self.onBeforeWizardFinish = function () {
            if (!self.required) return true;

            if (self.setup()) {
                return true;
            }

            self._showDecisionNeededDialog();
            return false;
        };

        self.onWizardDetails = function (response) {
            self.required = response && response.tracking && response.tracking.required;
        };

        self._showDecisionNeededDialog = function () {
            showMessageDialog({
                title: gettext("Please set up anonymous usage tracking"),
                message: gettext(
                    "You haven't yet decided on whether to enable or disable anonymous usage tracking. You need to either enable or disable it before continuing."
                )
            });
        };

        self._sendData = function () {
            var data = {
                plugins: {
                    tracking: {
                        enabled:
                            self.settingsViewModel.settings.plugins.tracking.enabled()
                    }
                }
            };

            self.active(true);
            self.settingsViewModel
                .saveData(data)
                .done(function () {
                    self.setup(true);
                    self.active(false);
                })
                .fail(function () {
                    self.decision(false);
                    self.setup(true);
                    self.active(false);

                    var message = gettext(
                        "Please open a <a href='%(bugreport)s' target='_blank' rel='noopener noreferrer'>" +
                            "bug report</a> on this. Make sure to include all requested information, including your " +
                            "<a href='%(jsconsole)s' target='_blank' rel='noopener noreferrer'>JS console</a> and " +
                            "<code>octoprint.log</code>."
                    );
                    new PNotify({
                        title: gettext("Something went wrong"),
                        text: _.sprintf(message, {
                            bugreport:
                                "https://github.com/OctoPrint/OctoPrint/blob/master/CONTRIBUTING.md#how-to-file-a-bug-report",
                            jsconsole: "https://webmasters.stackexchange.com/a/77337"
                        }),
                        type: "error",
                        hide: false
                    });
                });
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        UsageViewModel,
        ["settingsViewModel"],
        "#wizard_plugin_tracking"
    ]);
});
