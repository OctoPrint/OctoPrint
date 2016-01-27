$(function() {
    function LoginStateViewModel() {
        var self = this;

        self.loginUser = ko.observable("");
        self.loginPass = ko.observable("");
        self.loginRemember = ko.observable(false);

        self.loggedIn = ko.observable(false);
        self.username = ko.observable(undefined);
        self.isAdmin = ko.observable(false);
        self.isUser = ko.observable(false);

        self.allViewModels = undefined;

        self.currentUser = ko.observable(undefined);

        self.elementUsernameInput = undefined;
        self.elementPasswordInput = undefined;
        self.elementLoginButton = undefined;

        self.userMenuText = ko.pureComputed(function() {
            if (self.loggedIn()) {
                return self.username();
            } else {
                return gettext("Login");
            }
        });

        self.reloadUser = function() {
            if (self.currentUser() == undefined) {
                return;
            }

            OctoPrint.users.get(self.currentUser().name)
                .done(self.fromResponse);
        };

        self.requestData = function() {
            OctoPrint.browser.passiveLogin()
                .done(self.fromResponse);
        };

        self.fromResponse = function(response) {
            if (response && response.name) {
                self.loggedIn(true);
                self.username(response.name);
                self.isUser(response.user);
                self.isAdmin(response.admin);

                self.currentUser(response);

                callViewModels(self.allViewModels, "onUserLoggedIn", [response]);
            } else {
                self.loggedIn(false);
                self.username(undefined);
                self.isUser(false);
                self.isAdmin(false);

                self.currentUser(undefined);

                callViewModels(self.allViewModels, "onUserLoggedOut");
            }
        };

        self.login = function(u, p, r) {
            var username = u || self.loginUser();
            var password = p || self.loginPass();
            var remember = (r != undefined ? r : self.loginRemember());

            return OctoPrint.browser.login(username, password, remember)
                .done(function(response) {
                    new PNotify({title: gettext("Login successful"), text: _.sprintf(gettext('You are now logged in as "%(username)s"'), {username: response.name}), type: "success"});
                    self.fromResponse(response);

                    self.loginUser("");
                    self.loginPass("");
                    self.loginRemember(false);
                })
                .fail(function() {
                    new PNotify({title: gettext("Login failed"), text: gettext("User unknown or wrong password"), type: "error"});
                });
        };

        self.logout = function() {
            OctoPrint.browser.logout()
                .done(function(response) {
                    new PNotify({title: gettext("Logout successful"), text: gettext("You are now logged out"), type: "success"});
                    self.fromResponse(response);
                });
        };

        self.onLoginUserKeyup = function(data, event) {
            if (event.keyCode == 13) {
                self.elementPasswordInput.focus();
            }
        };

        self.onLoginPassKeyup = function(data, event) {
            if (event.keyCode == 13) {
                self.login();
            }
        };

        self.onAllBound = function(allViewModels) {
            self.allViewModels = allViewModels;
        };

        self.onDataUpdaterReconnect = function() {
            self.requestData();
        };

        self.onStartup = function() {
            self.elementUsernameInput = $("#login_user");
            self.elementPasswordInput = $("#login_pass");
            self.elementLoginButton = $("#login_button");
            if (self.elementUsernameInput && self.elementUsernameInput.length
                && self.elementLoginButton && self.elementLoginButton.length) {
                self.elementLoginButton.blur(function() {
                    self.elementUsernameInput.focus();
                })
            }
        };

        self.onStartupComplete = function() {
            self.requestData();
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        LoginStateViewModel,
        [],
        []
    ]);
});
