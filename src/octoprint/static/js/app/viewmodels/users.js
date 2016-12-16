$(function() {
    function UsersViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.permissions = parameters[1];
        self.groups = parameters[2];

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

        self.emptyUser = {name: "", active: false};

        self.currentUser = ko.observable(self.emptyUser);

        self.editorUsername = ko.observable(undefined);
        self.editorGroups = ko.observableArray([]);
        self.editorPermissions = ko.observableArray([]);
        self.editorPassword = ko.observable(undefined);
        self.editorRepeatedPassword = ko.observable(undefined);
        self.editorApikey = ko.observable(undefined);
        self.editorActive = ko.observable(undefined);

        self.addUserDialog = undefined;
        self.editUserDialog = undefined;
        self.changePasswordDialog = undefined;

        self.currentUser.subscribe(function(newValue) {
            if (newValue === undefined) {
                self.editorUsername(undefined);
                self.editorGroups([]);
                self.editorPermissions([]);
                self.editorActive(undefined);
                self.editorApikey(undefined);
            } else {
                self.editorUsername(newValue.name);
                self.editorGroups(newValue.groups);
                self.editorPermissions(newValue.permissions);
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
            // Switch permissions with PermissionList references, so the checked attribute will catch it
            rereferenceGroupsList = function(list) {
                new_groups = [];
                _.each(list, function(group) {
                    var done = false;
                    var groups = self.groups.groupsList();
                    for (var i = 0; i < groups.length && !done; i++) {
                        var g = groups[i];
                        if (group.name != g.name)
                            continue;

                        new_groups.push(g);
                        done = true;
                    }
                });
                return new_groups;
            };
            rereferencePermissionsList = function(list) {
                new_permissions = [];
                _.each(list, function(permission) {
                    var done = false;
                    var permissions = self.permissions.permissionsList();
                    for (var i = 0; i < permissions.length && !done; i++) {
                        var p = permissions[i];
                        if (permission.name != p.name)
                            continue;

                        new_permissions.push(p);
                        done = true;
                    }
                });
                return new_permissions;
            };

            _.each(response.users, function(user) {
                user.groups = rereferenceGroupsList(user.groups);
                user.permissions = rereferencePermissionsList(user.permissions);
            });

            self.listHelper.updateItems(response.users);
        };

        self.groupList = function(data) {
            if (data.groups === undefined)
                return "";

            var list = "";
            _.each(data.groups, function(g) {
                list += g.name + " ";
            })

            return list.trim();
        };
        self.permissionList = function(data) {
            if (data.permissions === undefined)
                return "";

            var list = "";
            _.each(data.permissions, function(p) {
                list += p.name + " ";
            })

            return list.trim();
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
                groups: self.editorGroups(),
                permissions: self.editorPermissions(),
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
            user.groups = self.editorGroups();
            user.permissions = self.editorPermissions();

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

            return OctoPrint.users.update(user.name, user.active, user.admin, user.permissions, user.groups)
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
            if (self.loginState.hasPermission(self.permissions.SETTINGS)()) {
                self.requestData();
            }
        }
    }

    OCTOPRINT_VIEWMODELS.push([
        UsersViewModel,
        ["loginStateViewModel", "permissionsViewModel", "groupsViewModel"],
        []
    ]);
});
