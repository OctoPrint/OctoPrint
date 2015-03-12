$(function() {
    function NavigationViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.appearance = parameters[1];
        self.settings = parameters[2];
        self.users = parameters[3];

        self.systemActions = self.settings.system_actions;

        self.appearanceClasses = ko.computed(function() {
            var classes = self.appearance.color();
            if (self.appearance.colorTransparent()) {
                classes += " transparent";
            }
            return classes;
        });

        self.triggerAction = function(action) {
            var callback = function() {
                $.ajax({
                    url: API_BASEURL + "system",
                    type: "POST",
                    dataType: "json",
                    data: "action=" + action.action,
                    success: function() {
                        new PNotify({title: "Success", text: _.sprintf(gettext("The command \"%(command)s\" executed successfully"), {command: action.name}), type: "success"});
                    },
                    error: function(jqXHR, textStatus, errorThrown) {
                        var error = "<p>" + _.sprintf(gettext("The command \"%(command)s\" could not be executed."), {command: action.name}) + "</p>";
                        error += pnotifyAdditionalInfo("<pre>" + jqXHR.responseText + "</pre>");
                        new PNotify({title: gettext("Error"), text: error, type: "error", hide: false});
                    }
                })
            };
            if (action.confirm) {
                var confirmationDialog = $("#confirmation_dialog");
                var confirmationDialogAck = $(".confirmation_dialog_acknowledge", confirmationDialog);

                $(".confirmation_dialog_message", confirmationDialog).text(action.confirm);
                confirmationDialogAck.unbind("click");
                confirmationDialogAck.bind("click", function(e) {
                    e.preventDefault();
                    $("#confirmation_dialog").modal("hide");
                    callback();
                });
                confirmationDialog.modal("show");
            } else {
                callback();
            }
        }
    }

    OCTOPRINT_VIEWMODELS.push([
        NavigationViewModel,
        ["loginStateViewModel", "appearanceViewModel", "settingsViewModel", "usersViewModel"],
        "#navbar"
    ]);

    // TODO usersViewModel is needed for what?
});