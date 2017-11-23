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

            self.editor = {
                name: ko.observable(undefined),
                groups: ko.observableArray([]),
                permissions: ko.observableArray([]),
                password: ko.observable(undefined),
                repeatedPassword: ko.observable(undefined),
                passwordMismatch: ko.pureComputed(function() {
                    return self.editor.password() !== self.editor.repeatedPassword();
                }),
                apikey: ko.observable(undefined),
                active: ko.observable(undefined),
                permissionSelected: function(permission) {
                    var index = self.editor.permissions().indexOf(permission);
                    return index >= 0;
                },
                togglePermission: function(permission) {
                    var permissions = self.editor.permissions();
                    var index = permissions.indexOf(permission);
                    if (index < 0) {
                        permissions.push(permission);
                    } else {
                        permissions.splice(index, 1);
                    }
                    self.editor.permissions(permissions);
                },
                groupSelected: function(group) {
                    var index = self.editor.groups().indexOf(group);
                    return index >= 0;
                },
                toggleGroup: function(group) {
                    var groups = self.editor.groups();
                    var index = groups.indexOf(group);
                    if (index < 0) {
                        groups.push(group);
                    } else {
                        groups.splice(index, 1);
                    }
                    self.editor.groups(groups);
                },
                joinedGroupPermissions: function(group) {
                    return access.permissionList(group);
                }
            };

            self.addUserDialog = undefined;
            self.editUserDialog = undefined;
            self.changePasswordDialog = undefined;

            self.currentUser.subscribe(function(newValue) {
                if (newValue === undefined) {
                    self.editor.name(undefined);
                    self.editor.groups(access.groups.getDefaultGroups());
                    self.editor.permissions([]);
                    self.editor.active(undefined);
                    self.editor.apikey(undefined);
                } else {
                    self.editor.name(newValue.name);
                    self.editor.groups(newValue.groups);
                    self.editor.permissions(newValue.permissions);
                    self.editor.active(newValue.active);
                    self.editor.apikey(newValue.apikey);
                }
                self.editor.password(undefined);
                self.editor.repeatedPassword(undefined);
            });

            self.requestData = function() {
                if (!CONFIG_ACCESS_CONTROL) return;

                OctoPrint.access.users.list()
                    .done(self.fromResponse);
            };

            self.fromResponse = function(response) {
                self.listHelper.updateItems(response.users);
            };

            self.showAddUserDialog = function() {
                if (!CONFIG_ACCESS_CONTROL) return;

                self.currentUser(undefined);
                self.editor.active(true);

                $('ul.nav-pills a[data-toggle="tab"]:first', self.addUserDialog).tab("show");
                self.addUserDialog.modal({
                    minHeight: function() { return Math.max($.fn.modal.defaults.maxHeight() - 80, 250); }
                }).css({
                    width: 'auto',
                    'margin-left': function() { return -($(this).width() /2); }
                });
            };

            self.confirmAddUser = function() {
                if (!CONFIG_ACCESS_CONTROL) return;

                var user = {
                    name: self.editor.name(),
                    password: self.editor.password(),
                    groups: self.editor.groups(),
                    permissions: self.editor.permissions(),
                    active: self.editor.active()
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

                $('ul.nav-pills a[data-toggle="tab"]:first', self.editUserDialog).tab("show");
                self.editUserDialog.modal({
                    minHeight: function() { return Math.max($.fn.modal.defaults.maxHeight() - 80, 250); }
                }).css({
                    width: 'auto',
                    'margin-left': function() { return -($(this).width() /2); }
                });
            };

            self.confirmEditUser = function() {
                if (!CONFIG_ACCESS_CONTROL) return;

                var user = self.currentUser();
                user.active = self.editor.active();
                user.groups = self.editor.groups();
                user.permissions = self.editor.permissions();

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

                self.updatePassword(self.currentUser().name, self.editor.password())
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

            self.copyApikey = function() {
                copyToClipboard(self.editorApikey());
            };

            self._updateApikey = function(apikey) {
                self.editorApikey(apikey);
                self.requestData();
            };

            self.confirmDeleteApikey = function() {
                if (!CONFIG_ACCESS_CONTROL) return;

                self.deleteApikey(self.currentUser().name)
                    .done(function() {
                        self._updateApikey(undefined);
                    });
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

                if (user.name === access.loginState.username()) {
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

            self.groupsList = self.listHelper.items; // Alias for easier reference
            self.lookup = {};

            self.emptyGroup = {name: ""};

            self.currentGroup = ko.observable(self.emptyGroup);

            self.editor = {
                name: ko.observable(undefined),
                description: ko.observable(undefined),
                permissions: ko.observableArray([]),
                default: ko.observable(false),
                permissionSelected: function(permission) {
                    var index = self.editor.permissions().indexOf(permission);
                    return index >= 0;
                },
                togglePermission: function(permission) {
                    var permissions = self.editor.permissions();
                    var index = permissions.indexOf(permission);
                    if (index < 0) {
                        permissions.push(permission);
                    } else {
                        permissions.splice(index, 1);
                    }
                    self.editor.permissions(permissions);
                }
            };

            self.addGroupDialog = undefined;
            self.editGroupDialog = undefined;

            // used to delete all the groups before registering new ones
            self.groupsList.subscribe(function(oldValue) {
                if (oldValue === undefined || oldValue.length === 0)
                    return;

                oldValue.forEach(function (p) {
                    delete self[p.name.toUpperCase()];
                });
            }, null, "beforeChange");

            // used to register new groups
            self.groupsList.subscribe(function(newValue) {
                if (newValue === undefined)
                    return;

                newValue.forEach(function(g) {
                    var needs = [];
                    g.permissions.forEach(function(p) {
                        for (var key in p.needs) {
                            p.needs[key].forEach(function(value) {
                                needs.push(access.permissions.need(key, value));
                            });
                        }
                    });

                    // if the permission has no need sets do not register it.
                    if (needs.length > 0) {
                        self.registerGroup(g.name.toUpperCase(), needs);
                    }
                });
            });

            self.registerGroup = function(name, group) {
                Object.defineProperty(self, name, {
                    value: group,
                    enumerable: true,
                    configurable: true
                });
            };

            self.currentGroup.subscribe(function(newValue) {
                if (newValue === undefined) {
                    self.editor.name(undefined);
                    self.editor.description(undefined);
                    self.editor.permissions([]);
                    self.editor.default(false);
                } else {
                    self.editor.name(newValue.name);
                    self.editor.description(newValue.description);
                    self.editor.permissions(newValue.permissions);
                    self.editor.default(newValue.defaultOn);
                }
            });

            self.requestData = function() {
                OctoPrint.access.groups.list()
                    .done(self.fromResponse);
            };

            self.fromResponse = function(response) {
                self.listHelper.updateItems(response.groups);

                var lookup = {};
                _.each(response.groups, function(group) {
                    lookup[group.name] = group;
                });
                self.lookup = lookup;
            };

            self.getDefaultGroups = function() {
                return _.map(_.where(self.groupsList(), {defaultOn: true}), function(g) {
                    return g.name;
                });
            };

            self.showAddGroupDialog = function() {
                self.currentGroup(undefined);
                self.addGroupDialog.modal("show");
            };

            self.confirmAddGroup = function() {
                var group = {
                    name: self.editor.name(),
                    description: self.editor.description(),
                    permissions: self.editor.permissions(),
                    defaultOn: self.editor.default()
                };

                self.addGroup(group)
                    .done(function() {
                        // close dialog
                        self.currentGroup(undefined);
                        self.addGroupDialog.modal("hide");
                    });
            };

            self.showEditGroupDialog = function(group) {
                if (!group.changeable) return;

                self.currentGroup(group);
                self.editGroupDialog.modal("show");
            };

            self.confirmEditGroup = function() {
                var group = self.currentGroup();
                group.description = self.editor.description();
                group.permissions = self.editor.permissions();
                group.defaultOn = self.editor.default();

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

                if (!group.removable) return;

                showConfirmationDialog({
                    title: gettext("Are you sure?"),
                    message: _.sprintf(gettext("You are about to delete the group \"%(name)s\"."), {name: group.name}),
                    proceed: gettext("Delete"),
                    onproceed: function() {
                        OctoPrint.access.groups.delete(group.name).done(function(response) {
                            self.fromResponse(response);
                            access.users.requestData();
                        });
                    }
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

            self.need = function(method, value) { return {method: method, value: value}; };
            self.roleNeed = function(value) { return self.need("role", value); };

            self.permissionList = ko.observableArray([]);
            self.lookup = {};

            var registeredPermissions = [];
            var registerPermission = function(key, permission) {
                Object.defineProperty(self, key, {
                    value: permission,
                    enumerable: true,
                    configurable: true
                });
                registeredPermissions.push(key);
            };
            var clearAllRegisteredPermissions = function() {
                _.each(registeredPermissions, function(key) {
                    delete self[key];
                });
                registeredPermissions = [];
            };

            self.initialize = function() {
                clearAllRegisteredPermissions();

                var permissionList = [];
                var lookup = {};
                _.each(PERMISSIONS, function(permission) {
                    var needs = [];
                    _.each(permission.needs, function(value, key) {
                        needs.push(self.need(key, value));
                    });

                    if (needs.length > 0) {
                        registerPermission(permission.key, needs);
                    }

                    if (!permission.combined) {
                        permissionList.push(permission);
                    }
                    lookup[permission.key] = permission;
                });

                permissionList.sort(access.permissionComparator);
                self.permissionList(permissionList);
                self.lookup = lookup;
            };

            return self;
        })();

        access.groupComparator = function(a, b) {
            var nameA = a.name ? a.name.toUpperCase() : "";
            var nameB = b.name ? b.name.toUpperCase() : "";

            if (nameA < nameB) {
                return -1;
            } else if (nameA > nameB) {
                return 1;
            } else {
                return 0;
            }
        };

        access.permissionComparator = function(a, b) {
            var nameA = a.name ? a.name.toUpperCase() : "";
            var nameB = b.name ? b.name.toUpperCase() : "";

            var pluginA = a.plugin || "";
            var pluginB = b.plugin || "";

            var compA = pluginA + ":" + nameA;
            var compB = pluginB + ":" + nameB;

            if (compA < compB) {
                return -1;
            } else if (compA > compB) {
                return 1;
            } else {
                return 0;
            }
        };

        // Maps the group names into a comma seperated list
        access.groupList = function(data) {
            if (data.groups === undefined)
                return "";

            return data.groups.join(", ");
        };

        // Maps the permission names into a comma seperated list
        access.permissionList = function(data) {
            if (!data || data.permissions === undefined)
                return "";

            var mappedPermissions = _.filter(_.map(data.permissions, function(p) { return access.permissions.lookup[p] }), function(p) { return p !== undefined });
            mappedPermissions.sort(access.permissionComparator);
            return _.map(mappedPermissions, function(p) {
                return p.name;
            }).join(", ");
        };

        //~~ API Calls
        access.onStartup = function() {
            access.groups.onStartup();
            access.users.onStartup();
        };

        access.onServerConnect = function() {
            access.permissions.initialize();
        };

        access.onServerReconnect = function() {
            access.permissions.initialize();
        };

        access.onUserLoggedIn = function(user) {
            if (access.loginState.hasPermission(access.permissions.SETTINGS)) {
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
