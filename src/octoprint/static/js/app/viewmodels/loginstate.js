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

            $.ajax({
                url: API_BASEURL + "users/" + self.currentUser().name,
                type: "GET",
                success: self.fromResponse
            })
        };

        self.requestData = function() {
            $.ajax({
                url: API_BASEURL + "login",
                type: "POST",
                data: {"passive": true},
                success: self.fromResponse
            })
        };

        self.fromResponse = function(response) {
            if (response && response.name) {
                self.loggedIn(true);
                self.username(response.name);
                self.isUser(response.user);
                self.isAdmin(response.admin);

                self.currentUser(response);

                _.each(self.allViewModels, function(viewModel) {
                    if (viewModel.hasOwnProperty("onUserLoggedIn")) {
                        viewModel.onUserLoggedIn(response);
                    }
                });
            } else {
                self.loggedIn(false);
                self.username(undefined);
                self.isUser(false);
                self.isAdmin(false);

                self.currentUser(undefined);

                _.each(self.allViewModels, function(viewModel) {
                    if (viewModel.hasOwnProperty("onUserLoggedOut")) {
                        viewModel.onUserLoggedOut();
                    }
                });
            }
        };

        self.login = function() {
            var username = self.loginUser();
            var password = self.loginPass();
            var remember = self.loginRemember();

            $.ajax({
                url: API_BASEURL + "login",
                type: "POST",
                data: {"user": username, "pass": password, "remember": remember},
                success: function(response) {
                    new PNotify({title: gettext("Login successful"), text: _.sprintf(gettext('You are now logged in as "%(username)s"'), {username: response.name}), type: "success"});
                    self.fromResponse(response);

                    self.loginUser("");
                    self.loginPass("");
                    self.loginRemember(false);
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    new PNotify({title: gettext("Login failed"), text: gettext("User unknown or wrong password"), type: "error"});
                }
            })
        };

        self.logout = function() {
            $.ajax({
                url: API_BASEURL + "logout",
                type: "POST",
                success: function(response) {
                    new PNotify({title: gettext("Logout successful"), text: gettext("You are now logged out"), type: "success"});
                    self.fromResponse(response);
                },
                error: function(error) {
                    if (error && error.status === 401) {
                         self.fromResponse(false);
                    }
                }
            })
        };

        self.onLoginUserKeyup = function(data, event) {
            if (event.keyCode == 13) {
                $("#login_pass").focus();
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
