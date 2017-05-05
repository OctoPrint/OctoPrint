$(function() {
    function UsersViewModel(parameters) {
        var self = this;

        self.deprecatedUsers = function (deprecatedFct, newFct, fn) {
            return OctoPrintClient.deprecated("UsersViewModel." + deprecatedFct, "AccessViewModel.users." + newFct, fn);
        };

        self.access = parameters[0];

        // initialize list helper
        self.listHelper = self.access.users.listHelper;

        self.emptyUser = self.access.users.emptyUser;

        self.currentUser = self.access.users.currentUser;

        self.editorUsername = self.access.users.editorUsername;
        self.editorGroups = self.access.users.editorGroups;
        self.editorPermissions = self.access.users.editorPermissions;
        self.editorPassword = self.access.users.editorPassword;
        self.editorRepeatedPassword = self.access.users.editorRepeatedPassword;
        self.editorApikey = self.access.users.editorApikey;
        self.editorActive = self.access.users.editorActive;

        self.editorPasswordMismatch = self.access.users.editorPasswordMismatch;

        self.requestData = self.deprecatedUsers("requestData", "requestData", function() {
            self.access.users.requestData();
        });

        self.fromResponse = self.deprecatedUsers("fromResponse", "fromResponse", function(response) {
            self.access.users.fromResponse(response);
        });

        self.showAddUserDialog = self.deprecatedUsers("showAddUserDialog", "showAddUserDialog", function() {
            self.access.users.showAddUserDialog();
        });

        self.confirmAddUser = self.deprecatedUsers("confirmAddUser", "confirmAddUser", function() {
            self.access.users.confirmAddUser();
        });

        self.showEditUserDialog = self.deprecatedUsers("showEditUserDialog", "showEditUserDialog", function(user) {
            self.access.users.showEditUserDialog(ser);
        });

        self.confirmEditUser = self.deprecatedUsers("confirmEditUser", "confirmEditUser", function() {
            self.access.users.confirmEditUser();
        });

        self.showChangePasswordDialog = self.deprecatedUsers("showChangePasswordDialog", "showChangePasswordDialog", function(user) {
            self.access.users.showChangePasswordDialog(user);
        });

        self.confirmChangePassword = self.deprecatedUsers("confirmChangePassword", "confirmChangePassword", function() {
            self.access.users.confirmChangePassword();
        });

        self.confirmGenerateApikey = self.deprecatedUsers("confirmGenerateApikey", "confirmGenerateApikey", function() {
            self.access.users.confirmGenerateApikey();
        });

        self.confirmDeleteApikey = self.deprecatedUsers("confirmDeleteApikey", "confirmDeleteApikey", function() {
            self.access.users.confirmDeleteApikey();
        });

        self._updateApikey = self.deprecatedUsers("_updateApikey", "_updateApikey", function(apikey) {
            self.access.users._updateApikey(apikey);
        });

        //~~ API calls

        self.addUser = self.deprecatedUsers("addUser", "addUser", function(user) {
            self.access.users.addUser(user);
        });

        self.removeUser = self.deprecatedUsers("removeUser", "removeUser", function(user) {
            self.access.users.removeUser(user);
        });

        self.updateUser = self.deprecatedUsers("updateUser", "updateUser", function(user) {
            self.access.users.updateUser(user);
        });

        self.updatePassword = self.deprecatedUsers("updatePassword", "updatePassword", function(username, password) {
            self.access.users.updatePassword(username, password);
        });

        self.generateApikey = self.deprecatedUsers("generateApikey", "generateApikey", function(username) {
            self.access.users.generateApikey(username);
        });

        self.deleteApikey = self.deprecatedUsers("deleteApikey", "deleteApikey", function(username) {
            self.access.users.deleteApikey(username);
        });
    }

    OCTOPRINT_VIEWMODELS.push([
        UsersViewModel,
        ["accessViewModel"],
        []
    ]);
});
