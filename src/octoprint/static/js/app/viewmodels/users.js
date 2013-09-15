function UsersViewModel(loginStateViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;

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
    self.editorAdmin = ko.observable(undefined);
    self.editorActive = ko.observable(undefined);

    self.currentUser.subscribe(function(newValue) {
        if (newValue === undefined) {
            self.editorUsername(undefined);
            self.editorAdmin(undefined);
            self.editorActive(undefined);
        } else {
            self.editorUsername(newValue.name);
            self.editorAdmin(newValue.admin);
            self.editorActive(newValue.active);
        }
        self.editorPassword(undefined);
        self.editorRepeatedPassword(undefined);
    });

    self.editorPasswordMismatch = ko.computed(function() {
        return self.editorPassword() != self.editorRepeatedPassword();
    });

    self.requestData = function() {
        if (!CONFIG_ACCESS_CONTROL) return;

        $.ajax({
            url: AJAX_BASEURL + "users",
            type: "GET",
            dataType: "json",
            success: self.fromResponse
        });
    }

    self.fromResponse = function(response) {
        self.listHelper.updateItems(response.users);
    }

    self.showAddUserDialog = function() {
        if (!CONFIG_ACCESS_CONTROL) return;

        self.currentUser(undefined);
        self.editorActive(true);
        $("#settings-usersDialogAddUser").modal("show");
    }

    self.confirmAddUser = function() {
        if (!CONFIG_ACCESS_CONTROL) return;

        var user = {name: self.editorUsername(), password: self.editorPassword(), admin: self.editorAdmin(), active: self.editorActive()};
        self.addUser(user, function() {
            // close dialog
            self.currentUser(undefined);
            $("#settings-usersDialogAddUser").modal("hide");
        });
    }

    self.showEditUserDialog = function(user) {
        if (!CONFIG_ACCESS_CONTROL) return;

        self.currentUser(user);
        $("#settings-usersDialogEditUser").modal("show");
    }

    self.confirmEditUser = function() {
        if (!CONFIG_ACCESS_CONTROL) return;

        var user = self.currentUser();
        user.active = self.editorActive();
        user.admin = self.editorAdmin();

        // make AJAX call
        self.updateUser(user, function() {
            // close dialog
            self.currentUser(undefined);
            $("#settings-usersDialogEditUser").modal("hide");
        });
    }

    self.showChangePasswordDialog = function(user) {
        if (!CONFIG_ACCESS_CONTROL) return;

        self.currentUser(user);
        $("#settings-usersDialogChangePassword").modal("show");
    }

    self.confirmChangePassword = function() {
        if (!CONFIG_ACCESS_CONTROL) return;

        self.updatePassword(self.currentUser().name, self.editorPassword(), function() {
            // close dialog
            self.currentUser(undefined);
            $("#settings-usersDialogChangePassword").modal("hide");
        });
    }

    //~~ AJAX calls

    self.addUser = function(user, callback) {
        if (!CONFIG_ACCESS_CONTROL) return;
        if (user === undefined) return;

        $.ajax({
            url: AJAX_BASEURL + "users",
            type: "POST",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify(user),
            success: function(response) {
                self.fromResponse(response);
                callback();
            }
        });
    }

    self.removeUser = function(user, callback) {
        if (!CONFIG_ACCESS_CONTROL) return;
        if (user === undefined) return;

        if (user.name == loginStateViewModel.username()) {
            // we do not allow to delete ourselves
            $.pnotify({title: "Not possible", text: "You may not delete your own account.", type: "error"});
            return;
        }

        $.ajax({
            url: AJAX_BASEURL + "users/" + user.name,
            type: "DELETE",
            success: function(response) {
                self.fromResponse(response);
                callback();
            }
        });
    }

    self.updateUser = function(user, callback) {
        if (!CONFIG_ACCESS_CONTROL) return;
        if (user === undefined) return;

        $.ajax({
            url: AJAX_BASEURL + "users/" + user.name,
            type: "PUT",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify(user),
            success: function(response) {
                self.fromResponse(response);
                callback();
            }
        });
    }

    self.updatePassword = function(username, password, callback) {
        if (!CONFIG_ACCESS_CONTROL) return;

        $.ajax({
            url: AJAX_BASEURL + "users/" + username + "/password",
            type: "PUT",
            contentType: "application/json; charset=UTF-8",
            data: JSON.stringify({password: password}),
            success: callback
        });
    }
}
