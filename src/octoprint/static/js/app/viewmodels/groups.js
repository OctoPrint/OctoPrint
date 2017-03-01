$(function() {
    function GroupsViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.permissions = parameters[1];

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

            OctoPrint.groups.list()
                .done(self.fromResponse);
        };

        self.fromResponse = function(response) {
            // Switch permissions with PermissionList references, so the checked attribute will catch it
            rereferencePermissionsList = function(list) {
                new_permissions = [];
                _.each(list, function(permission) {
                    var done = false;
                    for (var i = 0; i < self.permissions.permissionsList().length && !done; i++) {
                        var p = self.permissions.permissionsList()[i];
                        if (permission.name != p.name)
                            continue;

                        new_permissions.push(p);
                        done = true;
                    }
                });
                return new_permissions;
            };

            _.each(response.groups, function(group) {
                group.permissions = rereferencePermissionsList(group.permissions);
            });

            self.groupsList(response.groups);
            self.listHelper.updateItems(response.groups);
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

        self.getDefaultGroups = function() {
            groups = [];
            _.each(self.groupsList(), function(group) {
                if (group.defaultOn)
                {
                    groups.push(group);
                }
            });
            return groups;
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

            return OctoPrint.groups.add(group)
                .done(self.fromResponse);
        };

        self.removeGroup = function(group) {
            if (!group) {
                throw OctoPrint.InvalidArgumentError("group must be set");
            }

            return OctoPrint.groups.delete(group.name)
                .done(self.fromResponse);
        };

        self.updateGroup = function(group) {
            if (!group) {
                throw OctoPrint.InvalidArgumentError("group must be set");
            }

            return OctoPrint.groups.update(group.name, group.description, group.permissions, group.defaultOn)
                .done(self.fromResponse);
        };
        self.onUserLoggedIn = function(user) {
            if (self.loginState.hasPermission(self.permissions.SETTINGS)()) {
                self.requestData();
            }
        }
    }

    OCTOPRINT_VIEWMODELS.push([
        GroupsViewModel,
        ["loginStateViewModel", "permissionsViewModel"],
        []
    ]);
});
