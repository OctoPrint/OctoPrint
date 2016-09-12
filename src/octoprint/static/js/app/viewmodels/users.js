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

            OctoPrint.users.list()
                .done(self.fromResponse);
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

            var user = {
                name: self.editorUsername(),
                password: self.editorPassword(),
                admin: self.editorAdmin(),
                active: self.editorActive()
            };

            self.addUser(user)
                .done(function() {
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

            self.updateUser(user)
                .done(function() {
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

            self.updatePassword(self.currentUser().name, self.editorPassword())
                .done(function() {
                    // close dialog
                    self.currentUser(undefined);
                    self.changePasswordDialog.modal("hide");
                });
        };

        self.confirmGenerateApikey = function() {
            if (!CONFIG_ACCESS_CONTROL) return;

            self.generateApikey(self.currentUser().name)
                .done(function(response) {
                    self._updateApikey(response.apikey);
                });
        };

        self.confirmDeleteApikey = function() {
            if (!CONFIG_ACCESS_CONTROL) return;

            self.deleteApikey(self.currentUser().name)
                .done(function() {
                    self._updateApikey(undefined);
                });
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

        //~~ API calls

        self.addUser = function(user) {
            if (!user) {
                throw OctoPrint.InvalidArgumentError("user must be set");
            }

            return OctoPrint.users.add(user)
                .done(self.fromResponse);
        };

        self.removeUser = function(user) {
            if (!user) {
                throw OctoPrint.InvalidArgumentError("user must be set");
            }

            if (user.name == self.loginState.username()) {
                // we do not allow to delete ourselves
                new PNotify({
                    title: gettext("Not possible"),
                    text: gettext("You may not delete your own account."),
                    type: "error"
                });
                return $.Deferred().reject("You may not delete your own account").promise();
            }

            return OctoPrint.users.delete(user.name)
                .done(self.fromResponse);
        };

        self.updateUser = function(user) {
            if (!user) {
                throw OctoPrint.InvalidArgumentError("user must be set");
            }

            return OctoPrint.users.update(user.name, user.active, user.admin)
                .done(self.fromResponse);
        };

        self.updatePassword = function(username, password) {
            return OctoPrint.users.changePassword(username, password);
        };

        self.generateApikey = function(username) {
            return OctoPrint.users.generateApiKey(username);
        };

        self.deleteApikey = function(username) {
            return OctoPrint.users.resetApiKey(username);
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
