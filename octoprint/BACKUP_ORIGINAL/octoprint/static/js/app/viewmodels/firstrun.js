function FirstRunViewModel() {
    var self = this;

    self.username = ko.observable(undefined);
    self.password = ko.observable(undefined);
    self.confirmedPassword = ko.observable(undefined);

    self.passwordMismatch = ko.computed(function() {
        return self.password() != self.confirmedPassword();
    });

    self.validUsername = ko.computed(function() {
        return self.username() && self.username().trim() != "";
    });

    self.validPassword = ko.computed(function() {
        return self.password() && self.password().trim() != "";
    });

    self.validData = ko.computed(function() {
        return !self.passwordMismatch() && self.validUsername() && self.validPassword();
    });

    self.keepAccessControl = function() {
        if (!self.validData()) return;

        var data = {
            "ac": true,
            "user": self.username(),
            "pass1": self.password(),
            "pass2": self.confirmedPassword()
        };
        self._sendData(data);
    };

    self.disableAccessControl = function() {
        $("#confirmation_dialog .confirmation_dialog_message").html("If you disable Access Control <strong>and</strong> your OctoPrint " +
            "installation is accessible from the internet, your printer <strong>will be accessible by everyone - " +
            "that also includes the bad guys!</strong>");
        $("#confirmation_dialog .confirmation_dialog_acknowledge").click(function(e) {
            e.preventDefault();
            $("#confirmation_dialog").modal("hide");

            var data = {
                "ac": false
            };
            self._sendData(data, function() {
                // if the user indeed disables access control, we'll need to reload the page for this to take effect
                location.reload();
            });
        });
        $("#confirmation_dialog").modal("show");
    };

    self._sendData = function(data, callback) {
        $.ajax({
            url: AJAX_BASEURL + "setup",
            type: "POST",
            dataType: "json",
            data: data,
            success: function() {
                self.closeDialog();
                if (callback) callback();
            }
        });
    }

    self.showDialog = function() {
        $("#first_run_dialog").modal("show");
    }

    self.closeDialog = function() {
        $("#first_run_dialog").modal("hide");
    }
}
