$(function () {
    function AccessViewModel(parameters) {
        var access = this;

        access.loginState = parameters[0];

        var GROUP_ADMINS = "admins";
        var GROUP_GUESTS = "guests";

        //~~ Users ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        access.users = (function () {
            var self = {};
            // initialize list helper
            self.listHelper = new ItemListHelper(
                "users",
                {
                    name: function (a, b) {
                        // sorts ascending
                        if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase())
                            return -1;
                        if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase())
                            return 1;
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

            self.currentUser = ko.observable(self.emptyUser).extend({notify: "always"});

            self.isCurrentUser = (user) => {
                return user && user.name && user.name == access.loginState.username();
            };

            self.isDeleteUserEnabled = (user) => {
                return !self.isCurrentUser(user);
            };

            self.apikeysVisible = ko.observable(false);
            self.revealingApikeys = ko.observable(false);

            self.editor = {
                name: ko.observable(undefined),
                groups: ko.observableArray([]),
                permissions: ko.observableArray([]),
                password: ko.observable(undefined),
                currentPassword: ko.observable(undefined),
                repeatedPassword: ko.observable(undefined),
                passwordMismatch: ko.pureComputed(function () {
                    return self.editor.password() !== self.editor.repeatedPassword();
                }),
                providedUsername: ko.pureComputed(function () {
                    return self.editor.name() && self.editor.name().trim();
                }),
                validUsername: ko.pureComputed(function () {
                    return (
                        !self.editor.name() ||
                        self.editor.name() == self.editor.name().trim()
                    );
                }),
                currentPasswordMismatch: ko.observable(false),
                apikey: ko.observable(undefined),
                active: ko.observable(undefined),
                permissionSelectable: function (permission) {
                    return true;
                },
                permissionSelected: function (permission) {
                    var index = self.editor.permissions().indexOf(permission);
                    return index >= 0;
                },
                togglePermission: function (permission) {
                    var permissions = self.editor.permissions();
                    var index = permissions.indexOf(permission);
                    if (index < 0) {
                        permissions.push(permission);
                    } else {
                        permissions.splice(index, 1);
                    }
                    self.editor.permissions(permissions);
                },
                groupSelected: function (group) {
                    var index = self.editor.groups().indexOf(group);
                    return index >= 0;
                },
                toggleGroup: function (group) {
                    var groups = self.editor.groups();
                    var index = groups.indexOf(group);
                    if (index < 0) {
                        groups.push(group);
                    } else {
                        groups.splice(index, 1);
                    }
                    self.editor.groups(groups);
                },
                joinedGroupPermissions: function (group) {
                    return access.permissionList(group);
                },
                header: ko.observable(undefined),
                new: ko.observable(true),
                confirm: undefined,
                valid: ko.pureComputed(function () {
                    return (
                        self.editor.providedUsername() &&
                        self.editor.validUsername() &&
                        (!self.editor.new() ||
                            (self.editor.password() &&
                                self.editor.password().trim() &&
                                !self.editor.passwordMismatch()))
                    );
                }),
                dangerRestricted: function () {
                    return false;
                },
                dangerRestrictedText: gettext(
                    "This user may not have dangerous permissions."
                )
            };

            self.userEditorDialog = undefined;
            self.changePasswordDialog = undefined;

            self.currentUser.subscribe(function (newValue) {
                if (newValue === undefined) {
                    self.editor.name(undefined);
                    self.editor.groups(access.groups.defaults.slice(0));
                    self.editor.permissions([]);
                    self.editor.active(true);
                    self.editor.apikey(undefined);
                    self.editor.header(gettext("Add user"));
                    self.editor.new(true);
                    self.editor.confirm = self.confirmAddUser;
                } else {
                    self.editor.name(newValue.name);
                    self.editor.groups(newValue.groups.slice(0));
                    self.editor.permissions(newValue.permissions.slice(0));
                    self.editor.active(newValue.active);
                    self.editor.apikey(newValue.apikey);
                    self.editor.header(
                        _.sprintf(gettext('Edit user "%(name)s"'), {name: newValue.name})
                    );
                    self.editor.new(false);
                    self.editor.confirm = self.confirmEditUser;
                }
                self.editor.password(undefined);
                self.editor.repeatedPassword(undefined);
                self.editor.currentPassword(undefined);
                self.editor.currentPasswordMismatch(false);
            });
            self.editor.currentPassword.subscribe(function () {
                self.editor.currentPasswordMismatch(false);
            });

            self.requestData = function () {
                if (!CONFIG_ACCESS_CONTROL) return;
                if (!access.loginState.hasPermissionKo(access.permissions.ADMIN)) return;

                return OctoPrint.access.users.list().done(self.fromResponse);
            };

            self.fromResponse = function (response) {
                self.listHelper.updateItems(response.users);

                // This should only be true if the request was triggered by a click on "reveal api key"
                self.apikeysVisible(self.revealingApikeys());
            };

            self.showAddUserDialog = function () {
                if (!CONFIG_ACCESS_CONTROL) return;

                access.loginState.reauthenticateIfNecessary(() => {
                    self.currentUser(undefined);

                    $(
                        'ul.nav-pills a[data-toggle="tab"]:first',
                        self.userEditorDialog
                    ).tab("show");
                    self.userEditorDialog
                        .modal({
                            minHeight: function () {
                                return Math.max(
                                    $.fn.modal.defaults.maxHeight() - 80,
                                    250
                                );
                            }
                        })
                        .css({
                            "margin-left": function () {
                                return -($(this).width() / 2);
                            }
                        });
                });
            };

            self.confirmAddUser = function () {
                if (!CONFIG_ACCESS_CONTROL) return;

                var user = {
                    name: self.editor.name(),
                    password: self.editor.password(),
                    groups: self.editor.groups(),
                    permissions: self.editor.permissions(),
                    active: self.editor.active()
                };

                access.loginState.reauthenticateIfNecessary(() => {
                    self.addUser(user).done(function () {
                        // close dialog
                        self.currentUser(undefined);
                        self.userEditorDialog.modal("hide");
                    });
                });
            };

            self.showEditUserDialog = function (user) {
                if (!CONFIG_ACCESS_CONTROL) return;

                var process = function (user) {
                    self.currentUser(user);

                    $(
                        'ul.nav-pills a[data-toggle="tab"]:first',
                        self.userEditorDialog
                    ).tab("show");
                    self.userEditorDialog
                        .modal({
                            minHeight: function () {
                                return Math.max(
                                    $.fn.modal.defaults.maxHeight() - 80,
                                    250
                                );
                            }
                        })
                        .css({
                            "margin-left": function () {
                                return -($(this).width() / 2);
                            }
                        });
                };

                access.loginState.reauthenticateIfNecessary(() => {
                    OctoPrint.users
                        .get(user.name)
                        .done(function (data) {
                            process(data);
                        })
                        .fail(function () {
                            log.warn(
                                "Could not fetch current user data, proceeding with client side data copy"
                            );
                            process(user);
                        });
                });
            };

            self.confirmEditUser = function () {
                if (!CONFIG_ACCESS_CONTROL) return;

                var user = self.currentUser();
                user.active = self.editor.active();
                user.groups = self.editor.groups();
                user.permissions = self.editor.permissions();

                access.loginState.reauthenticateIfNecessary(() => {
                    self.updateUser(user).done(function () {
                        // close dialog
                        self.currentUser(undefined);
                        self.userEditorDialog.modal("hide");
                    });
                });
            };

            self.confirmRemoveUser = (user) => {
                if (!CONFIG_ACCESS_CONTROL) return;

                if (user.name === access.loginState.username()) {
                    // we do not allow to delete ourselves
                    new PNotify({
                        title: gettext("Not possible"),
                        text: gettext("You may not delete your own account."),
                        type: "error"
                    });
                    return $.Deferred()
                        .reject("You may not delete your own account")
                        .promise();
                }

                access.loginState.reauthenticateIfNecessary(() => {
                    showConfirmationDialog({
                        title: gettext("Are you sure?"),
                        message: _.sprintf(
                            gettext('You are about to delete the user "%(name)s".'),
                            {name: _.escape(user.name)}
                        ),
                        proceed: gettext("Delete"),
                        onproceed: () => {
                            self.removeUser(user);
                        }
                    });
                });
            };

            self.showChangePasswordDialog = function (user) {
                if (!CONFIG_ACCESS_CONTROL) return;

                const proceed = () => {
                    self.currentUser(user);
                    self.changePasswordDialog.modal("show");
                };

                if (self.isCurrentUser(user)) {
                    proceed();
                } else {
                    access.loginState.reauthenticateIfNecessary(proceed);
                }
            };

            self.confirmChangePassword = function () {
                if (!CONFIG_ACCESS_CONTROL) return;

                const proceed = () => {
                    self.updatePassword(
                        self.currentUser().name,
                        self.editor.password(),
                        self.editor.currentPassword()
                    )
                        .done(function () {
                            // close dialog
                            self.currentUser(undefined);
                            self.changePasswordDialog.modal("hide");
                        })
                        .fail(function (xhr) {
                            if (xhr.status === 403) {
                                self.currentPasswordMismatch(true);
                            }
                        });
                };

                if (self.isCurrentUser()) {
                    proceed();
                } else {
                    access.loginState.reauthenticateIfNecessary(proceed);
                }
            };

            self.confirmGenerateApikey = function () {
                if (!CONFIG_ACCESS_CONTROL) return;

                access.loginState.reauthenticateIfNecessary(() => {
                    self.generateApikey(self.currentUser().name).done(function (
                        response
                    ) {
                        self._updateApikey(response.apikey);
                    });
                });
            };

            self.revealApikeys = () => {
                access.loginState.reauthenticateIfNecessary(() => {
                    self.revealingApikeys(true);
                    self.requestData().always(() => {
                        self.revealingApikeys(false);
                        if (self.currentUser()) {
                            OctoPrint.access.users
                                .get(self.currentUser().name)
                                .done((data) => {
                                    self.currentUser(data);
                                });
                        }
                    });
                });
            };

            self.copyApikey = function () {
                copyToClipboard(self.editor.apikey());
            };

            self._updateApikey = function (apikey) {
                self.editor.apikey(apikey);
                self.requestData();
            };

            self.confirmDeleteApikey = function () {
                if (!CONFIG_ACCESS_CONTROL) return;

                access.loginState.reauthenticateIfNecessary(() => {
                    self.deleteApikey(self.currentUser().name).done(function () {
                        self._updateApikey(undefined);
                    });
                });
            };

            //~~ Framework

            self.onStartup = function () {
                self.userEditorDialog = $("#settings-usersEditorDialog");
                self.changePasswordDialog = $("#settings-usersDialogChangePassword");
            };

            self.onUserCredentialsOutdated = () => {
                self.apikeysVisible(false);
                self.requestData();
                if (self.currentUser()) {
                    OctoPrint.access.users.get(self.currentUser().name).done((data) => {
                        self.currentUser(data);
                    });
                }
            };

            //~~ API calls

            self.addUser = function (user) {
                if (!user) {
                    throw OctoPrint.InvalidArgumentError("user must be set");
                }
                if (!access.loginState.hasPermissionKo(access.permissions.ADMIN)) {
                    return $.Deferred()
                        .reject("You are not authorized to perform this action")
                        .promise();
                }
                if (!access.loginState.credentialsSeen()) {
                    return $.Deferred()
                        .reject("You need to reauthenticate to perform this action")
                        .promise();
                }

                return OctoPrint.access.users.add(user).done(self.fromResponse);
            };

            self.removeUser = function (user) {
                if (!user) {
                    throw OctoPrint.InvalidArgumentError("user must be set");
                }
                if (!access.loginState.hasPermissionKo(access.permissions.ADMIN)) {
                    return $.Deferred()
                        .reject("You are not authorized to perform this action")
                        .promise();
                }
                if (!access.loginState.credentialsSeen()) {
                    return $.Deferred()
                        .reject("You need to reauthenticate to perform this action")
                        .promise();
                }

                return OctoPrint.access.users.delete(user.name).done(self.fromResponse);
            };

            self.updateUser = function (user) {
                if (!user) {
                    throw OctoPrint.InvalidArgumentError("user must be set");
                }
                if (!access.loginState.credentialsSeen()) {
                    return $.Deferred()
                        .reject("You need to reauthenticate to perform this action")
                        .promise();
                }

                return OctoPrint.access.users
                    .update(
                        user.name,
                        user.active,
                        user.admin,
                        user.permissions,
                        user.groups
                    )
                    .done(self.fromResponse);
            };

            self.updatePassword = function (username, password, current) {
                if (!access.loginState.credentialsSeen()) {
                    return $.Deferred()
                        .reject("You need to reauthenticate to perform this action")
                        .promise();
                }
                return OctoPrint.access.users.changePassword(username, password, current);
            };

            self.generateApikey = function (username) {
                if (!access.loginState.credentialsSeen()) {
                    return $.Deferred()
                        .reject("You need to reauthenticate to perform this action")
                        .promise();
                }
                return OctoPrint.access.users.generateApiKey(username).done(function () {
                    self.requestData();
                });
            };

            self.deleteApikey = function (username) {
                if (!access.loginState.credentialsSeen()) {
                    return $.Deferred()
                        .reject("You need to reauthenticate to perform this action")
                        .promise();
                }
                return OctoPrint.access.users.resetApiKey(username);
            };

            return self;
        })();

        //~~ Groups ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        access.groups = (function () {
            var self = {};
            // initialize list helper
            self.listHelper = new ItemListHelper(
                "groups",
                {
                    name: function (a, b) {
                        // sorts ascending
                        if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase())
                            return -1;
                        if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase())
                            return 1;
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
            self.defaults = [];

            self.emptyGroup = {name: ""};

            self.currentGroup = ko.observable(self.emptyGroup);

            self.editor = {
                key: ko.observable(undefined),
                name: ko.observable(undefined),
                description: ko.observable(undefined),
                permissions: ko.observableArray([]),
                subgroups: ko.observableArray([]),
                default: ko.observable(false),
                permissionSelectable: function (permission) {
                    // guests may not get dangerous permissions
                    return self.editor.key() !== GROUP_GUESTS || !permission.dangerous;
                },
                permissionSelected: function (permission) {
                    var index = self.editor.permissions().indexOf(permission);
                    return index >= 0;
                },
                togglePermission: function (permission) {
                    var permissions = self.editor.permissions();
                    var index = permissions.indexOf(permission);
                    if (index < 0) {
                        permissions.push(permission);
                    } else {
                        permissions.splice(index, 1);
                    }
                    self.editor.permissions(permissions);
                },
                subgroupSelectable: function (subgroup) {
                    // guests may not get dangerous subgroups
                    return (
                        self.editor.key() !== subgroup.key &&
                        (self.editor.key() !== GROUP_GUESTS || !subgroup.dangerous)
                    );
                },
                subgroupSelected: function (subgroup) {
                    var index = self.editor.subgroups().indexOf(subgroup);
                    return index >= 0;
                },
                toggleSubgroup: function (subgroup) {
                    var subgroups = self.editor.subgroups();
                    var index = subgroups.indexOf(subgroup);
                    if (index < 0) {
                        subgroups.push(subgroup);
                    } else {
                        subgroups.splice(index, 1);
                    }
                    self.editor.subgroups(subgroups);
                },
                joinedGroupPermissions: function (group) {
                    return access.permissionList(group);
                },
                header: ko.observable(undefined),
                new: ko.observable(true),
                confirm: undefined,
                valid: ko.pureComputed(function () {
                    return self.editor.name() && self.editor.name().trim();
                }),
                dangerRestricted: function () {
                    return self.editor.key() === GROUP_GUESTS;
                },
                dangerRestrictedText: gettext(
                    "This group may not have dangerous permissions or subgroups."
                )
            };

            self.groupEditorDialog = undefined;

            // used to delete all the groups before registering new ones
            self.groupsList.subscribe(
                function (oldValue) {
                    if (oldValue === undefined || oldValue.length === 0) return;

                    oldValue.forEach(function (p) {
                        delete self[p.key.toUpperCase()];
                    });
                },
                null,
                "beforeChange"
            );

            // used to register new groups
            self.groupsList.subscribe(function (newValue) {
                if (newValue === undefined) return;

                newValue.forEach(function (g) {
                    var needs = [];
                    g.permissions.forEach(function (p) {
                        for (var key in p.needs) {
                            p.needs[key].forEach(function (value) {
                                needs.push(access.permissions.need(key, value));
                            });
                        }
                    });

                    // if the permission has no need sets do not register it.
                    if (needs.length > 0) {
                        self.registerGroup(g.key.toUpperCase(), needs);
                    }
                });
            });

            self.registerGroup = function (name, group) {
                Object.defineProperty(self, name, {
                    value: group,
                    enumerable: true,
                    configurable: true
                });
            };

            self.currentGroup.subscribe(function (newValue) {
                if (newValue === undefined) {
                    // group add
                    self.editor.key(undefined);
                    self.editor.name(undefined);
                    self.editor.description(undefined);
                    self.editor.permissions([]);
                    self.editor.subgroups([]);
                    self.editor.default(false);
                    self.editor.header(gettext("Add group"));
                    self.editor.new(true);
                    self.editor.confirm = self.confirmAddGroup;
                } else {
                    // group update
                    self.editor.key(newValue.key);
                    self.editor.name(newValue.name);
                    self.editor.description(newValue.description);
                    self.editor.permissions(newValue.permissions.slice(0));
                    self.editor.subgroups(newValue.subgroups.slice(0));
                    self.editor.default(newValue.default);
                    self.editor.header(
                        _.sprintf(gettext('Edit group "%(name)s"'), {name: newValue.name})
                    );
                    self.editor.new(false);
                    self.editor.confirm = self.confirmEditGroup;
                }
            });

            self.requestData = function () {
                return OctoPrint.access.groups.list().done(self.fromResponse);
            };

            self.fromResponse = function (response) {
                var lookup = {};
                var defaults = [];
                _.each(response.groups, function (group) {
                    lookup[group.key] = group;
                    if (group.default) {
                        defaults.push(group.key);
                    }
                });
                self.lookup = lookup;
                self.defaults = defaults;
                self.listHelper.updateItems(response.groups);
            };

            self.showAddGroupDialog = function () {
                access.loginState.reauthenticateIfNecessary(() => {
                    self.currentGroup(undefined);
                    $(
                        'ul.nav-pills a[data-toggle="tab"]:first',
                        self.groupEditorDialog
                    ).tab("show");
                    self.groupEditorDialog
                        .modal({
                            minHeight: function () {
                                return Math.max(
                                    $.fn.modal.defaults.maxHeight() - 80,
                                    250
                                );
                            }
                        })
                        .css({
                            "margin-left": function () {
                                return -($(this).width() / 2);
                            }
                        });
                });
            };

            self.confirmAddGroup = function () {
                var group = {
                    key: self.editor
                        .name()
                        .toLowerCase()
                        .replace(/[^a-z0-9_ ]/g, "")
                        .replace(/ /g, "_"),
                    name: self.editor.name(),
                    description: self.editor.description(),
                    permissions: self.editor.permissions(),
                    subgroups: self.editor.subgroups(),
                    default: self.editor.default()
                };

                self.addGroup(group).done(function () {
                    // close dialog
                    self.currentGroup(undefined);
                    self.groupEditorDialog.modal("hide");
                });
            };

            self.showEditGroupDialog = function (group) {
                if (!group.changeable) return;

                access.loginState.reauthenticateIfNecessary(() => {
                    self.currentGroup(group);
                    $(
                        'ul.nav-pills a[data-toggle="tab"]:first',
                        self.groupEditorDialog
                    ).tab("show");
                    self.groupEditorDialog
                        .modal({
                            minHeight: function () {
                                return Math.max(
                                    $.fn.modal.defaults.maxHeight() - 80,
                                    250
                                );
                            }
                        })
                        .css({
                            "margin-left": function () {
                                return -($(this).width() / 2);
                            }
                        });
                });
            };

            self.confirmEditGroup = function () {
                var group = self.currentGroup();

                var data = {
                    key: group.key,
                    name: group.name,
                    description: self.editor.description(),
                    permissions: self.editor.permissions(),
                    subgroups: self.editor.subgroups(),
                    default: self.editor.default()
                };

                self.updateGroup(data).done(function () {
                    // close dialog
                    self.currentGroup(undefined);
                    self.groupEditorDialog.modal("hide");
                });
            };

            self.confirmRemoveGroup = (group) => {
                if (!group.removable) return;

                access.loginState.reauthenticateIfNecessary(() => {
                    showConfirmationDialog({
                        title: gettext("Are you sure?"),
                        message: _.sprintf(
                            gettext('You are about to delete the group "%(name)s".'),
                            {name: _.escape(group.name)}
                        ),
                        proceed: gettext("Delete"),
                        onproceed: () => {
                            self.removeGroup(group);
                        }
                    });
                });
            };

            //~~ Framework

            self.onStartup = function () {
                self.groupEditorDialog = $("#settings-groupsEditorDialog");
            };

            //~~ API calls

            self.addGroup = function (group) {
                if (!group) {
                    throw OctoPrint.InvalidArgumentError("group must be set");
                }
                if (!access.loginState.credentialsSeen()) {
                    return $.Deferred()
                        .reject("You need to reauthenticate to perform this action")
                        .promise();
                }

                return OctoPrint.access.groups.add(group).done(self.fromResponse);
            };

            self.removeGroup = function (group) {
                if (!group) {
                    throw OctoPrint.InvalidArgumentError("group must be set");
                }
                if (!access.loginState.credentialsSeen()) {
                    return $.Deferred()
                        .reject("You need to reauthenticate to perform this action")
                        .promise();
                }

                OctoPrint.access.groups.delete(group.key).done((response) => {
                    self.fromResponse(response);
                    access.users.requestData();
                });
            };

            self.updateGroup = function (group) {
                if (!group) {
                    throw OctoPrint.InvalidArgumentError("group must be set");
                }
                if (!access.loginState.credentialsSeen()) {
                    return $.Deferred()
                        .reject("You need to reauthenticate to perform this action")
                        .promise();
                }

                return OctoPrint.access.groups.update(group).done(self.fromResponse);
            };

            return self;
        })();

        //~~ Permissions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        access.permissions = (function () {
            var self = {};

            self.need = function (method, value) {
                return {method: method, value: value};
            };
            self.roleNeed = function (value) {
                return self.need("role", value);
            };

            self.permissionList = ko.observableArray([]);
            self.lookup = {};

            var registeredPermissions = [];
            var registerPermission = function (key, permission) {
                Object.defineProperty(self, key, {
                    value: permission,
                    enumerable: true,
                    configurable: true
                });
                registeredPermissions.push(key);
            };
            var clearAllRegisteredPermissions = function () {
                _.each(registeredPermissions, function (key) {
                    delete self[key];
                });
                registeredPermissions = [];
            };

            self.initialize = function () {
                clearAllRegisteredPermissions();

                var permissionList = [];
                var lookup = {};
                _.each(PERMISSIONS, function (permission) {
                    var needs = [];
                    _.each(permission.needs, function (value, key) {
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

        //~~ helpers ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        access.groupComparator = function (a, b) {
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

        access.permissionComparator = function (a, b) {
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

        // Maps the group names into a comma separated list
        access.groupList = function (data) {
            if (data.groups === undefined) return "";

            var mappedGroups = _.filter(
                _.map(data.groups, function (g) {
                    return access.groups.lookup[g];
                }),
                function (g) {
                    return g !== undefined;
                }
            );
            mappedGroups.sort(access.groupComparator);
            return _.map(mappedGroups, function (g) {
                return g.name;
            }).join(", ");
        };

        // Maps the sub group names into a comma separated list
        access.subgroupList = function (data) {
            if (data.subgroups === undefined) return "";

            var mappedGroups = _.filter(
                _.map(data.subgroups, function (g) {
                    return access.groups.lookup[g];
                }),
                function (g) {
                    return g !== undefined;
                }
            );
            mappedGroups.sort(access.groupComparator);
            return _.map(mappedGroups, function (g) {
                return g.name;
            }).join(", ");
        };

        // Maps the permission names into a comma separated list
        access.permissionList = function (data) {
            if (!data || data.permissions === undefined) return "";

            var mappedPermissions = _.filter(
                _.map(data.permissions, function (p) {
                    return access.permissions.lookup[p];
                }),
                function (p) {
                    return p !== undefined;
                }
            );
            mappedPermissions.sort(access.permissionComparator);
            return _.map(mappedPermissions, function (p) {
                return p.name;
            }).join(", ");
        };

        //~~ API Calls
        access.onStartup = function () {
            access.groups.onStartup();
            access.users.onStartup();
        };

        access.onServerConnect = function () {
            access.permissions.initialize();
        };

        access.onServerReconnect = function () {
            access.permissions.initialize();
        };

        access.onUserCredentialsOutdated = () => {
            access.users.onUserCredentialsOutdated();
        };

        access.onUserPermissionsChanged =
            access.onUserLoggedIn =
            access.onUserLoggedOut =
                function (user) {
                    if (access.loginState.hasPermission(access.permissions.ADMIN)) {
                        access.groups.requestData().done(function () {
                            access.users.requestData();
                        });
                    }
                };
    }

    OCTOPRINT_VIEWMODELS.push([AccessViewModel, ["loginStateViewModel"], []]);
});
