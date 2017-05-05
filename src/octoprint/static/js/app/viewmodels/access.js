$(function() {
    function AccessViewModel(parameters) {
        var access = this;

        access.loginState = parameters[0];

        //~~ Users
        access.users = (function() {
            var self = {};
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

            self.currentUser = ko.observable(self.emptyUser).extend({ notify: 'always' });

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
                    self.editorGroups(access.groups.getDefaultGroups());
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

                OctoPrint.access.users.list()
                    .done(self.fromResponse);
            };

            self.fromResponse = function(response) {
                _.each(response.users, function(user) {
                    user.groups = access.rereferenceGroupsList(user.groups);
                    user.permissions = access.rereferencePermissionsList(user.permissions);
                });

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

                return OctoPrint.access.users.add(user)
                    .done(self.fromResponse);
            };

            self.removeUser = function(user) {
                if (!user) {
                    throw OctoPrint.InvalidArgumentError("user must be set");
                }

                if (user.name == access.loginState.username()) {
                    // we do not allow to delete ourselves
                    new PNotify({
                        title: gettext("Not possible"),
                        text: gettext("You may not delete your own account."),
                        type: "error"
                    });
                    return $.Deferred().reject("You may not delete your own account").promise();
                }

                return OctoPrint.access.users.delete(user.name)
                    .done(self.fromResponse);
            };

            self.updateUser = function(user) {
                if (!user) {
                    throw OctoPrint.InvalidArgumentError("user must be set");
                }

                return OctoPrint.access.users.update(user.name, user.active, user.admin, user.permissions, user.groups)
                    .done(self.fromResponse);
            };

            self.updatePassword = function(username, password) {
                return OctoPrint.access.users.changePassword(username, password);
            };

            self.generateApikey = function(username) {
                return OctoPrint.access.users.generateApiKey(username);
            };

            self.deleteApikey = function(username) {
                return OctoPrint.access.users.resetApiKey(username);
            };

            return self;
        })();

        //~~ Groups
        access.groups = (function() {
            var self = {};
            // initialize list helper
            self.listHelper = new ItemListHelper(
                "groups",
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
                CONFIG_GROUPSPERPAGE
            );

            self.groupsList = ko.observableArray([]);

            self.emptyGroup = {name: ""};

            self.currentGroup = ko.observable(self.emptyGroup);

            self.editorGroupname = ko.observable(undefined);
            self.editorGroupdesc = ko.observable(undefined);
            self.editorPermissions = ko.observableArray([]);
            self.editorDefaultOn = ko.observable(false);

            self.addGroupDialog = undefined;
            self.editGroupDialog = undefined;

            self.currentGroup.subscribe(function(newValue) {
                if (newValue === undefined) {
                    self.editorGroupname(undefined);
                    self.editorGroupdesc(undefined);
                    self.editorPermissions([]);
                    self.editorDefaultOn(false);
                } else {
                    self.editorGroupname(newValue.name);
                    self.editorGroupdesc(newValue.description);
                    self.editorPermissions(newValue.permissions);
                    self.editorDefaultOn(newValue.defaultOn);
                }
            });

            self.requestData = function() {
                if (!CONFIG_GROUPS_ENABLED) return;

                OctoPrint.access.groups.list()
                    .done(self.fromResponse);
            };

            self.fromResponse = function(response) {
                _.each(response.groups, function(group) {
                    group.permissions = access.rereferencePermissionsList(group.permissions);
                });

                self.groupsList(response.groups);
                self.listHelper.updateItems(response.groups);
            };

            self.getDefaultGroups = function() {
                return _.where(self.groupsList(), {defaultOn: true});
            }

            self.showAddGroupDialog = function() {
                if (!CONFIG_GROUPS_ENABLED) return;

                self.currentGroup(undefined);
                self.addGroupDialog.modal("show");
            };

            self.confirmAddGroup = function() {
                if (!CONFIG_GROUPS_ENABLED) return;

                var group = {
                    name: self.editorGroupname(),
                    description: self.editorGroupdesc(),
                    permissions: self.editorPermissions(),
                    defaultOn: self.editorDefaultOn()
                };

                self.addGroup(group)
                    .done(function() {
                        // close dialog
                        self.currentGroup(undefined);
                        self.addGroupDialog.modal("hide");
                    });
            };

            self.showEditGroupDialog = function(group) {
                if (!CONFIG_GROUPS_ENABLED) return;

                self.currentGroup(group);
                self.editGroupDialog.modal("show");
            };

            self.confirmEditGroup = function() {
                if (!CONFIG_GROUPS_ENABLED) return;

                var group = self.currentGroup();
                group.description = self.editorGroupdesc();
                group.permissions = self.editorPermissions();
                group.defaultOn = self.editorDefaultOn();

                self.updateGroup(group)
                    .done(function() {
                        // close dialog
                        self.currentGroup(undefined);
                        self.editGroupDialog.modal("hide");
                    });
            };

            //~~ Framework

            self.onStartup = function() {
                self.addGroupDialog = $("#settings-groupsDialogAddGroup");
                self.editGroupDialog = $("#settings-groupsDialogEditGroup");
            };

            //~~ API calls

            self.addGroup = function(group) {
                if (!group) {
                    throw OctoPrint.InvalidArgumentError("group must be set");
                }

                return OctoPrint.access.groups.add(group)
                    .done(self.fromResponse);
            };

            self.removeGroup = function(group) {
                if (!group) {
                    throw OctoPrint.InvalidArgumentError("group must be set");
                }

                return OctoPrint.access.groups.delete(group.name)
                    .done(function(response) {
                        self.fromResponse(response);
                        if (self.users === undefined)
                            return;

                        access.users.requestData();
                    });
            };

            self.updateGroup = function(group) {
                if (!group) {
                    throw OctoPrint.InvalidArgumentError("group must be set");
                }

                return OctoPrint.access.groups.update(group.name, group.description, group.permissions, group.defaultOn)
                    .done(self.fromResponse);
            };

            return self;
        })();

        //~~ Permissions
        access.permissions = (function() {
            var self = {};

            self.permissionsList = ko.observableArray([]);

            self.need = function(method, value) { return {method: method, value: value}; };
            self.roleNeed = function(value) { return self.need("role", value); };

            self.ADMIN = self.roleNeed("admin");
            self.USER = self.roleNeed("user");

            self.STATUS = self.roleNeed("status");
            self.CONNECTION = self.roleNeed("connection");
            self.WEBCAM = self.roleNeed("webcam");
            self.SYSTEM = self.roleNeed("system");
            self.UPLOAD = self.roleNeed("upload");
            self.DOWNLOAD = self.roleNeed("download");
            self.DELETE = self.roleNeed("delete");
            self.SELECT = self.roleNeed("select");
            self.PRINT = self.roleNeed("print");
            self.TERMINAL = self.roleNeed("terminal");
            self.CONTROL = self.roleNeed("control");
            self.SLICE = self.roleNeed("slice");
            self.TIMELAPSE = self.roleNeed("timelapse");
            self.TIMELAPSE_ADMIN = self.roleNeed("timelapse_admin");
            self.SETTINGS = self.roleNeed("settings");
            self.LOGS = self.roleNeed("logs");

            self.requestData = function() {
                if (!CONFIG_ACCESS_CONTROL) return;

                OctoPrint.access.permissions.list().done(function(response) {
                    self.permissionsList(response.permissions);
                });
            };

            self.onAllBound = function(allViewModels) {
                self.allViewModels = allViewModels;
                self.requestData();
            };

            self.onServerConnect = self.onServerReconnect = function() {
                if (self.allViewModels == undefined) return;
                self.requestData();
            };

            return self;
        })();

        //~~ Shared Functions across the submenus

        /////////////////////////////////////////////////////////////////
        //                                                             //
        // Rereference functions are taking e.g. the groups data       //
        // delivered with the user data and replacing with             //
        // the groups data delivered by the groups submenu.            //
        //                                                             //
        // This is necessary for the editor to automatically check the //
        // groups the user belongs to.                                 //
        //                                                             //
        /////////////////////////////////////////////////////////////////
        access.rereferenceGroupsList = function(list) {
            return _.filter(access.groups.groupsList(), function(group) {
                return _.findWhere(list, { name: group.name }) != undefined;
            });
        };

        access.rereferencePermissionsList = function(list) {
            return _.filter(access.permissions.permissionsList(), function(permission) {
                return _.findWhere(list, { name: permission.name }) != undefined;
            });
        };

        // Maps the group names into a comma seperated list
        access.groupList = function(data) {
            if (data.groups === undefined)
                return "";

            return _.map(data.groups, function(p) { return p.name; }).join(", ");
        };

        // Maps the permission names into a comma seperated list
        access.permissionList = function(data) {
            if (data.permissions === undefined)
                return "";

            return _.map(data.permissions, function(p) { return p.name; }).join(", ");
        };

        //~~ API Calls
        access.onAllBound = function(allViewModels) {
            access.permissions.onAllBound(allViewModels);
        };

        access.onStartup = function() {
            access.groups.onStartup();
            access.users.onStartup();
        };

        access.onServerConnect = function() {
            access.permissions.onServerConnect();
        };

        access.onServerReconnect = function() {
            access.permissions.onServerReconnect();
        };

        access.onUserLoggedIn = function(user) {
            if (access.loginState.hasPermission(access.permissions.SETTINGS)()) {
                access.groups.requestData();
                access.users.requestData();
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        AccessViewModel,
        ["loginStateViewModel"],
        []
    ]);
});
