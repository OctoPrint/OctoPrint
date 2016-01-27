$(function() {
    function UsersViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];

        // initialize list helper
        self.listHelper = new ItemListHelper(
            "users",
            {
                "name": function(a, b) {
                    // sorts ascending
                    if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase()) return -1;
                    if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase()) return 1;
                    return 0;
                }
            },
            {},
            "name",
            [],
            [],
            CONFIG_USERSPERPAGE
        );

        self.emptyUser = {name: "", admin: false, active: false};

        self.currentUser = ko.observable(self.emptyUser);

        self.editorUsername = ko.observable(undefined);
        self.editorPassword = ko.observable(undefined);
        self.editorRepeatedPassword = ko.observable(undefined);
        self.editorApikey = ko.observable(undefined);
        self.editorAdmin = ko.observable(undefined);
        self.editorActive = ko.observable(undefined);

        self.addUserDialog = undefined;
        self.editUserDialog = undefined;
        self.changePasswordDialog = undefined;

        self.currentUser.subscribe(function(newValue) {
            if (newValue === undefined) {
                self.editorUsername(undefined);
                self.editorAdmin(undefined);
                self.editorActive(undefined);
                self.editorApikey(undefined);
            } else {
                self.editorUsername(newValue.name);
                self.editorAdmin(newValue.admin);
                self.editorActive(newValue.active);
                self.editorApikey(newValue.apikey);
            }
            self.editorPassword(undefined);
            self.editorRepeatedPassword(undefined);
        });

        self.editorPasswordMismatch = ko.pureComputed(function() {
            return self.editorPassword() != self.editorRepeatedPassword();
        });

        self.requestData = function() {
            if (!CONFIG_ACCESS_CONTROL) return;

            $.ajax({
                url: API_BASEURL + "users",
                type: "GET",
                dataType: "json",
                success: self.fromResponse
            });
        };

        self.fromResponse = function(response) {
            self.listHelper.updateItems(response.users);
        };

        self.showAddUserDialog = function() {
            if (!CONFIG_ACCESS_CONTROL) return;

            self.currentUser(undefined);
            self.editorActive(true);
            self.addUserDialog.modal("show");
        };

        self.confirmAddUser = function() {
            if (!CONFIG_ACCESS_CONTROL) return;

            var user = {name: self.editorUsername(), password: self.editorPassword(), admin: self.editorAdmin(), active: self.editorActive()};
            self.addUser(user, function() {
                // close dialog
                self.currentUser(undefined);
                self.addUserDialog.modal("hide");
            });
        };

        self.showEditUserDialog = function(user) {
            if (!CONFIG_ACCESS_CONTROL) return;

            self.currentUser(user);
            self.editUserDialog.modal("show");
        };

        self.confirmEditUser = function() {
            if (!CONFIG_ACCESS_CONTROL) return;

            var user = self.currentUser();
            user.active = self.editorActive();
            user.admin = self.editorAdmin();

            // make AJAX call
            self.updateUser(user, function() {
                // close dialog
                self.currentUser(undefined);
                self.editUserDialog.modal("hide");
            });
        };

        self.showChangePasswordDialog = function(user) {
            if (!CONFIG_ACCESS_CONTROL) return;

            self.currentUser(user);
            self.changePasswordDialog.modal("show");
        };

        self.confirmChangePassword = function() {
            if (!CONFIG_ACCESS_CONTROL) return;

            self.updatePassword(self.currentUser().name, self.editorPassword(), function() {
                // close dialog
                self.currentUser(undefined);
                self.changePasswordDialog.modal("hide");
            });
        };

        self.confirmGenerateApikey = function() {
            if (!CONFIG_ACCESS_CONTROL) return;

            self.generateApikey(self.currentUser().name, function(response) {
                self._updateApikey(response.apikey);
            })
        };

        self.confirmDeleteApikey = function() {
            if (!CONFIG_ACCESS_CONTROL) return;

            self.deleteApikey(self.currentUser().name, function() {
                self._updateApikey(undefined);
            })
        };

        self._updateApikey = function(apikey) {
            self.editorApikey(apikey);
            self.requestData();
        };

        //~~ Framework

        self.onStartup = function() {
            self.addUserDialog = $("#settings-usersDialogAddUser");
            self.editUserDialog = $("#settings-usersDialogEditUser");
            self.changePasswordDialog = $("#settings-usersDialogChangePassword");
        };

        //~~ AJAX calls

        self.addUser = function(user, callback) {
            if (!CONFIG_ACCESS_CONTROL) return;
            if (user === undefined) return;

            $.ajax({
                url: API_BASEURL + "users",
                type: "POST",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify(user),
                success: function(response) {
                    self.fromResponse(response);
                    if (callback) {
                        callback(response);
                    }
                }
            });
        };

        self.removeUser = function(user, callback) {
            if (!CONFIG_ACCESS_CONTROL) return;
            if (user === undefined) return;

            if (user.name == self.loginState.username()) {
                // we do not allow to delete ourselves
                new PNotify({title: "Not possible", text: "You may not delete your own account.", type: "error"});
                return;
            }

            $.ajax({
                url: API_BASEURL + "users/" + user.name,
                type: "DELETE",
                success: function(response) {
                    self.fromResponse(response);
                    if (callback) {
                        callback(response);
                    }
                }
            });
        };

        self.updateUser = function(user, callback) {
            if (!CONFIG_ACCESS_CONTROL) return;
            if (user === undefined) return;

            $.ajax({
                url: API_BASEURL + "users/" + user.name,
                type: "PUT",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify(user),
                success: function(response) {
                    self.fromResponse(response);
                    if (callback) {
                        callback(response);
                    }
                }
            });
        };

        self.updatePassword = function(username, password, callback) {
            if (!CONFIG_ACCESS_CONTROL) return;

            $.ajax({
                url: API_BASEURL + "users/" + username + "/password",
                type: "PUT",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({password: password}),
                success: function(response) {
                    if (callback) {
                        callback(response);
                    }
                }
            });
        };

        self.generateApikey = function(username, callback) {
            if (!CONFIG_ACCESS_CONTROL) return;

            $.ajax({
                url: API_BASEURL + "users/" + username + "/apikey",
                type: "POST",
                success: function(response) {
                    if (callback) {
                        callback(response);
                    }
                }
            });
        };

        self.deleteApikey = function(username, callback) {
            if (!CONFIG_ACCESS_CONTROL) return;

            $.ajax({
                url: API_BASEURL + "users/" + username + "/apikey",
                type: "DELETE",
                success: function(response) {
                    if (callback) {
                        callback(response);
                    }
                }
            });
        };

        self.onUserLoggedIn = function(user) {
            if (user.admin) {
                self.requestData();
            }
        }
    }

    OCTOPRINT_VIEWMODELS.push([
        UsersViewModel,
        ["loginStateViewModel"],
        []
    ]);
});
