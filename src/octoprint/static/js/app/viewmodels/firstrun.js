$(function() {
    function FirstRunViewModel() {
        var self = this;

        self.username = ko.observable(undefined);
        self.password = ko.observable(undefined);
        self.confirmedPassword = ko.observable(undefined);

        self.passwordMismatch = ko.pureComputed(function() {
            return self.password() != self.confirmedPassword();
        });

        self.validUsername = ko.pureComputed(function() {
            return self.username() && self.username().trim() != "";
        });

        self.validPassword = ko.pureComputed(function() {
            return self.password() && self.password().trim() != "";
        });

        self.validData = ko.pureComputed(function() {
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
            $("#confirmation_dialog .confirmation_dialog_message").html(gettext("If you disable Access Control <strong>and</strong> your OctoPrint installation is accessible from the internet, your printer <strong>will be accessible by everyone - that also includes the bad guys!</strong>"));
            $("#confirmation_dialog .confirmation_dialog_acknowledge").unbind("click");
            $("#confirmation_dialog .confirmation_dialog_acknowledge").click(function(e) {
                e.preventDefault();
                $("#confirmation_dialog").modal("hide");

                var data = {
                    "ac": false
                };
                self._sendData(data, function() {
                    // if the user indeed disables access control, we'll need to reload the page for this to take effect
                    showReloadOverlay();
                });
            });
            $("#confirmation_dialog").modal("show");
        };

        self._sendData = function(data, callback) {
            $.ajax({
                url: API_BASEURL + "setup",
                type: "POST",
                dataType: "json",
                data: data,
                success: function() {
                    self.closeDialog();
                    if (callback) callback();
                }
            });
        };

        self.showDialog = function() {
            $("#first_run_dialog").modal("show");
        };

        self.closeDialog = function() {
            $("#first_run_dialog").modal("hide");
        };

        self.onAllBound = function(allViewModels) {
            if (CONFIG_FIRST_RUN) {
                self.showDialog();
            }
        }
    }

    OCTOPRINT_VIEWMODELS.push([
        FirstRunViewModel,
        [],
        "#first_run_dialog"
    ]);
});
