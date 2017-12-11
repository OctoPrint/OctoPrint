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
        self.startupDeferred = $.Deferred();

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

        self.userMenuTitle = ko.pureComputed(function() {
            if (self.loggedIn()) {
                return _.sprintf(gettext("Logged in as %(name)s"), {name: self.username()});
            } else {
                return gettext("Login");
            }
        });

        self.reloadUser = function() {
            if (self.currentUser() === undefined) {
                return;
            }

            return OctoPrint.users.get(self.currentUser().name)
                .done(self.updateCurrentUserData);
        };

        self.requestData = function() {
            return OctoPrint.browser.passiveLogin()
                .done(self.fromResponse);
        };

        self.fromResponse = function(response) {
            var process = function() {
                var currentLoggedIn = self.loggedIn();
                if (response && response.name) {
                    self.loggedIn(true);
                    self.updateCurrentUserData(response);
                    if (!currentLoggedIn) {
                        callViewModels(self.allViewModels, "onUserLoggedIn", [response]);
                        log.info("User " + response.name + " logged in")
                    }
                } else {
                    self.loggedIn(false);
                    self.resetCurrentUserData();
                    if (currentLoggedIn) {
                        callViewModels(self.allViewModels, "onUserLoggedOut");
                        log.info("User logged out");
                    }
                }
            };

            if (self.startupDeferred !== undefined) {
                // Make sure we only fire our "onUserLogged(In|Out)" message after the application
                // has started up.
                self.startupDeferred.done(process);
            } else {
                process();
            }
        };

        self.updateCurrentUserData = function(data) {
            self.username(data.name);
            self.isUser(data.user);
            self.isAdmin(data.admin);

            self.currentUser(data);
        };

        self.resetCurrentUserData = function() {
            self.username(undefined);
            self.isUser(false);
            self.isAdmin(false);

            self.currentUser(undefined);
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

                    if (history && history.replaceState) {
                        history.replaceState({success: true}, document.title, window.location.pathname);
                    }
                })
                .fail(function(response) {
                    switch(response.status) {
                        case 401: {
                            new PNotify({
                                title: gettext("Login failed"),
                                text: gettext("User unknown or wrong password"),
                                type: "error"
                            });
                            break;
                        }
                        case 403: {
                            new PNotify({
                                title: gettext("Login failed"),
                                text: gettext("Your account is deactivated"),
                                type: "error"
                            });
                            break;
                        }
                    }
                });
        };

        self.logout = function() {
            return OctoPrint.browser.logout()
                .done(function(response) {
                    new PNotify({title: gettext("Logout successful"), text: gettext("You are now logged out"), type: "success"});
                    self.fromResponse(response);
                })
                .error(function(error) {
                    if (error && error.status === 401) {
                         self.fromResponse(false);
                    }
                });
        };

        self.prepareLogin = function(data, event) {
            if(event && event.preventDefault) {
                event.preventDefault();
            }
            self.login();
        };

        self.onAllBound = function(allViewModels) {
            self.allViewModels = allViewModels;
            self.startupDeferred.resolve();
            self.startupDeferred = undefined;
        };

        self.onStartup = function() {
            self.elementUsernameInput = $("#login_user");
            self.elementPasswordInput = $("#login_pass");
            self.elementLoginButton = $("#login_button");

            var toggle = $("li.dropdown#navbar_login");
            var button = $("a", toggle);

            button.on("click", function(e) {
                $(this).parent().toggleClass("open");
            });

            $("body").on("click", function(e) {
                if (!toggle.hasClass("open")) {
                    return;
                }

                var anyFormLinkOrButton = $("#login_dropdown_loggedout a, #login_dropdown_loggedin a, #login_dropdown_loggedout button, #login_dropdown_loggedin button");
                var dropdown = $("li.dropdown#navbar_login");
                var anyLastpassButton = $("#__lpform_login_user, #__lpform_login_pass");

                var isLinkOrButton = anyFormLinkOrButton.is(e.target) || anyFormLinkOrButton.has(e.target).length !== 0;
                var isDropdown = dropdown.is(e.target) || dropdown.has(e.target).length !== 0;
                var isLastpass = anyLastpassButton.is(e.target) || anyLastpassButton.has(e.target).length !== 0;

                if (isLinkOrButton || !(isDropdown || isLastpass)) {
                    toggle.removeClass("open");
                }
            });

            if (self.elementUsernameInput && self.elementUsernameInput.length
                && self.elementLoginButton && self.elementLoginButton.length) {
                self.elementLoginButton.blur(function() {
                    self.elementUsernameInput.focus();
                })
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: LoginStateViewModel
    });
});
