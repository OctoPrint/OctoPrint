$(function() {
    function UiStateViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];

        self.loading = ko.observable(CONFIG_LOADINGANIMATION);
        self.loading_error = ko.observable(false);
        self.needlogin = ko.computed(function() {
            return !self.loading() && !self.loginState.hasAllPermissionsKo(self.access.permissions.STATUS, self.access.permissions.SETTINGS_READ)();
        });
        self.visible = ko.pureComputed(function() {
            return !self.loading() && !self.needlogin();
        });

        self.login_username = ko.observable();
        self.login_password = ko.observable();
        self.login_remember = ko.observable(false);
        self.login_error = ko.observable(false);

        self.login = function() {
            self.login_error(false);
            self.loginState.login(self.login_username(), self.login_password(), self.login_remember(), false)
                .done(function() {
                    self.login_username(undefined);
                    self.login_password(undefined);
                })
                .fail(function(response) {
                    switch(response.status) {
                        case 401: {
                            self.login_error(gettext("User unknown or wrong password"));
                            break;
                        }
                        case 403: {
                            self.login_error(gettext("Your account is deactivated"));
                            break;
                        }
                    }
                });
        };

        self.onUserLoggedOut = self.onUserPermissionsChanged = function() {
            if (!self.loginState.hasAllPermissions(self.access.permissions.STATUS, self.access.permissions.SETTINGS_READ) && !CONFIG_FIRST_RUN) {
                location.reload();
            }
        };

        self.showLoadingError = function(error) {
            log.error("Loading error: " + error + " Please check prior messages and 'octoprint.log' for possible reasons.");

            // we can't do this with bindings since the bindings are not initialized yet if we need this
            $("#page-container-loading-header").text("Loading failed");
            $("#page-container-loading-spinner").removeClass("fa-spinner fa-spin").addClass("fa-exclamation-triangle text-error");
            $("#page-container-loading-error").html(error + " " + _.sprintf("Please check your <a href='%(browser)s' target='_blank' rel='noopener noreferrer'>browser's error console</a> and <code><a href='%(octoprint)s' target='_blank' rel='noopener noreferrer'>octoprint.log</a></code> for possible reasons.Also make sure that the server is actually running by reloading this page.", {browser: "https://faq.octoprint.org/browser-console", octoprint: "https://faq.octoprint.org/logs"})).show();
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: UiStateViewModel,
        dependencies: ["loginStateViewModel", "accessViewModel"],
        elements: ["#page-container-main", "#page-container-loading", "#page-container-needlogin"]
    });
});
