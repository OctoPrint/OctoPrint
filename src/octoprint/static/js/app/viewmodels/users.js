$(function() {
    function UsersViewModel(parameters) {
        var self = this;

        self.deprecatedUsers = function (deprecatedFct, newFct, fn) {
            return OctoPrintClient.deprecated("UsersViewModel." + deprecatedFct, "AccessViewModel." + newFct, fn);
        };

        self.access = parameters[0];

        // initialize list helper
        self.listHelper = self.access.listHelper;

        self.emptyUser = self.access.emptyUser;

        self.currentUser = self.access.currentUser;

        self.editorUsername = self.access.editorUsername;
        self.editorGroups = self.access.editorGroups;
        self.editorPermissions = self.access.editorPermissions;
        self.editorPassword = self.access.editorPassword;
        self.editorRepeatedPassword = self.access.editorRepeatedPassword;
        self.editorApikey = self.access.editorApikey;
        self.editorActive = self.access.editorActive;

        self.editorPasswordMismatch = self.access.editorPasswordMismatch;

        self.requestData = self.deprecatedUsers("requestData", "requestUserData", function() {
            self.access.requestData();
        });

        self.fromResponse = self.deprecatedUsers("fromResponse", "fromResponseUserData", function(response) {
            self.access.fromResponse(response);
        });

        self.showAddUserDialog = self.deprecatedUsers("showAddUserDialog", "showAddUserDialog", function() {
            self.access.showAddUserDialog();
        });

        self.confirmAddUser = self.deprecatedUsers("confirmAddUser", "confirmAddUser", function() {
            self.access.confirmAddUser();
        });

        self.showEditUserDialog = self.deprecatedUsers("showEditUserDialog", "showEditUserDialog", function(user) {
            self.access.showEditUserDialog(ser);
        });

        self.confirmEditUser = self.deprecatedUsers("confirmEditUser", "confirmEditUser", function() {
            self.access.confirmEditUser();
        });

        self.showChangePasswordDialog = self.deprecatedUsers("showChangePasswordDialog", "showChangePasswordDialog", function(user) {
            self.access.showChangePasswordDialog(user);
        });

        self.confirmChangePassword = self.deprecatedUsers("confirmChangePassword", "confirmChangePassword", function() {
            self.access.confirmChangePassword();
        });

        self.confirmGenerateApikey = self.deprecatedUsers("confirmGenerateApikey", "confirmGenerateApikey", function() {
            self.access.confirmGenerateApikey();
        });

        self.confirmDeleteApikey = self.deprecatedUsers("confirmDeleteApikey", "confirmDeleteApikey", function() {
            self.access.confirmDeleteApikey();
        });

        self._updateApikey = self.deprecatedUsers("_updateApikey", "_updateApikey", function(apikey) {
            self.access._updateApikey(apikey);
        });

        //~~ API calls

        self.addUser = self.deprecatedUsers("addUser", "addUser", function(user) {
            self.access.addUser(user);
        });

        self.removeUser = self.deprecatedUsers("removeUser", "removeUser", function(user) {
            self.access.removeUser(user);
        });

        self.updateUser = self.deprecatedUsers("updateUser", "updateUser", function(user) {
            self.access.updateUser(user);
        });

        self.updatePassword = self.deprecatedUsers("updatePassword", "updatePassword", function(username, password) {
            self.access.updatePassword(username, password);
        });

        self.generateApikey = self.deprecatedUsers("generateApikey", "generateApikey", function(username) {
            self.access.generateApikey(username);
        });

        self.deleteApikey = self.deprecatedUsers("deleteApikey", "deleteApikey", function(username) {
            self.access.deleteApikey(username);
        });
    }

    OCTOPRINT_VIEWMODELS.push([
        UsersViewModel,
        ["accessViewModel"],
        []
    ]);
});
