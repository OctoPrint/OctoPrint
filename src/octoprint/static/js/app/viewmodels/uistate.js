$(function() {
    function UiStateViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];

        self.loading = ko.observable(true);
        self.needlogin = ko.computed(function() {
            return !self.loading() && !self.loginState.hasPermissionKo(self.access.permissions.STATUS)();
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
    }

    OCTOPRINT_VIEWMODELS.push([
        UiStateViewModel,
        ["loginStateViewModel", "accessViewModel"],
        ["#page-container-main", "#page-container-loading", "#page-container-needlogin"]
    ]);
});
