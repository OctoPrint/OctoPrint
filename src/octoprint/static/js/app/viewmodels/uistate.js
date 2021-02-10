$(function () {
    function UiStateViewModel(parameters) {
        var self = this;

        self.loading = ko.observable(CONFIG_LOADINGANIMATION);
        self.loading_error = ko.observable(false);
        self.visible = ko.pureComputed(function () {
            return !self.loading();
        });

        self.showLoadingError = function (error) {
            log.error(
                "Loading error: " +
                    error +
                    " Please check prior messages and 'octoprint.log' for possible reasons."
            );

            // we can't do this with bindings since the bindings are not initialized yet if we need this
            $("#page-container-loading-header").text("Loading failed");
            $("#page-container-loading-spinner")
                .removeClass("fa-spinner fa-spin")
                .addClass("fa-exclamation-triangle text-error");
            $("#page-container-loading-error")
                .html(
                    error +
                        " " +
                        _.sprintf(
                            "Please check your <a href='%(browser)s' target='_blank' rel='noopener noreferrer'>browser's error console</a> and <code><a href='%(octoprint)s' target='_blank' rel='noopener noreferrer'>octoprint.log</a></code> for possible reasons.Also make sure that the server is actually running by reloading this page.",
                            {
                                browser: "https://faq.octoprint.org/browser-console",
                                octoprint: "https://faq.octoprint.org/logs"
                            }
                        )
                )
                .show();
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: UiStateViewModel,
        elements: ["#page-container-main", "#page-container-loading"]
    });
});
