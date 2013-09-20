function LoginStateViewModel() {
    var self = this;

    self.loggedIn = ko.observable(false);
    self.username = ko.observable(undefined);
    self.isAdmin = ko.observable(false);
    self.isUser = ko.observable(false);

    self.currentUser = ko.observable(undefined);

    self.userMenuText = ko.computed(function() {
        if (self.loggedIn()) {
            return "\"" + self.username() + "\"";
        } else {
            return "Login";
        }
    })

    self.subscribers = [];
    self.subscribe = function(callback) {
        if (callback === undefined) return;
        self.subscribers.push(callback);
    }

    self.requestData = function() {
        $.ajax({
            url: AJAX_BASEURL + "login",
            type: "POST",
            data: {"passive": true},
            success: self.fromResponse
        })
    }

    self.fromResponse = function(response) {
        if (response && response.name) {
            self.loggedIn(true);
            self.username(response.name);
            self.isUser(response.user);
            self.isAdmin(response.admin);

            self.currentUser(response);

            _.each(self.subscribers, function(callback) { callback("login", response); });
        } else {
            self.loggedIn(false);
            self.username(undefined);
            self.isUser(false);
            self.isAdmin(false);

            self.currentUser(undefined);

            _.each(self.subscribers, function(callback) { callback("logout", {}); });
        }
    }

    self.login = function() {
        var username = $("#login_user").val();
        var password = $("#login_pass").val();
        var remember = $("#login_remember").is(":checked");

        $("#login_user").val("");
        $("#login_pass").val("");
        $("#login_remember").prop("checked", false);

        $.ajax({
            url: AJAX_BASEURL + "login",
            type: "POST",
            data: {"user": username, "pass": password, "remember": remember},
            success: function(response) {
                $.pnotify({title: "Login successful", text: "You are now logged in as \"" + response.name + "\"", type: "success"});
                self.fromResponse(response);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                $.pnotify({title: "Login failed", text: "User unknown or wrong password", type: "error"});
            }
        })
    }

    self.logout = function() {
        $.ajax({
            url: AJAX_BASEURL + "logout",
            type: "POST",
            success: function(response) {
                $.pnotify({title: "Logout successful", text: "You are now logged out", type: "success"});
                self.fromResponse(response);
            }
        })
    }
}
