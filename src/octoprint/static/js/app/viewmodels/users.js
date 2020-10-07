$(function () {
    function UsersViewModel(parameters) {
        var self = this;

        self.access = parameters[0];

        self.deprecatedUsersMethod = function (oldFct) {
            var newFct = oldFct;
            if (arguments.length === 2) {
                newFct = arguments[1];
            }

            OctoPrintClient.deprecatedMethod(
                self,
                "UsersViewModel",
                oldFct,
                "AccessViewModel.users",
                newFct,
                function () {
                    self.access.users[newFct](this.arguments);
                }
            );
        };

        self.deprecatedUsersVariable = function (oldVar) {
            var newVar = oldVar;
            if (arguments.length === 2) {
                newVar = arguments[1];
            }

            OctoPrintClient.deprecatedVariable(
                self,
                "UsersViewModel",
                oldVar,
                "AccessViewModel.users",
                newVar,
                function () {
                    return self.access.users[newVar];
                },
                function (val) {
                    self.access.users[newVar] = val;
                }
            );
        };

        // initialize deprecated Variables
        self.deprecatedUsersVariable("listHelper");

        self.deprecatedUsersVariable("emptyUser");

        self.deprecatedUsersVariable("currentUser");

        self.deprecatedUsersVariable("editorUsername");
        self.deprecatedUsersVariable("editorGroups");
        self.deprecatedUsersVariable("editorPermissions");
        self.deprecatedUsersVariable("editorPassword");
        self.deprecatedUsersVariable("editorRepeatedPassword");
        self.deprecatedUsersVariable("editorApikey");
        self.deprecatedUsersVariable("editorActive");

        self.deprecatedUsersVariable("editorPasswordMismatch");

        self.deprecatedUsersMethod("requestData");
        self.deprecatedUsersMethod("fromResponse");
        self.deprecatedUsersMethod("showAddUserDialog");
        self.deprecatedUsersMethod("confirmAddUser");
        self.deprecatedUsersMethod("showEditUserDialog");
        self.deprecatedUsersMethod("confirmEditUser");
        self.deprecatedUsersMethod("showChangePasswordDialog");
        self.deprecatedUsersMethod("confirmChangePassword");
        self.deprecatedUsersMethod("confirmGenerateApikey");
        self.deprecatedUsersMethod("copyApikey");
        self.deprecatedUsersMethod("confirmDeleteApikey");
        self.deprecatedUsersMethod("_updateApikey");

        //~~ API calls
        self.deprecatedUsersMethod("addUser");
        self.deprecatedUsersMethod("removeUser");
        self.deprecatedUsersMethod("updateUser");
        self.deprecatedUsersMethod("updatePassword");
        self.deprecatedUsersMethod("generateApikey");
        self.deprecatedUsersMethod("deleteApikey");
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: UsersViewModel,
        dependencies: ["accessViewModel"]
    });
});
