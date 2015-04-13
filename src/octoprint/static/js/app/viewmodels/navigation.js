function NavigationViewModel(loginStateViewModel, appearanceViewModel, settingsViewModel, usersViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;
    self.appearance = appearanceViewModel;
    self.systemActions = settingsViewModel.system_actions;
    self.users = usersViewModel;

    self.triggerAction = function(action) {
        var callback = function() {
            $.ajax({
                url: API_BASEURL + "system",
                type: "POST",
                dataType: "json",
                data: "action=" + action.action,
                success: function() {
                    $.pnotify({title: "Success", text: "The command \""+ action.name +"\" executed successfully", type: "success"});
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    $.pnotify({title: "Error", text: "<p>The command \"" + action.name + "\" could not be executed.</p><p>Reason: <pre>" + jqXHR.responseText + "</pre></p>", type: "error"});
                }
            })
        }
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

