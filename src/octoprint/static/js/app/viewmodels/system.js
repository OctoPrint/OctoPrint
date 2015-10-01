$(function() {
    function SystemViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];

        self.lastCommandResponse = undefined;
        self.systemActions = ko.observableArray([]);

        self.requestData = function() {
            self.requestCommandData();
        };

        self.requestCommandData = function() {
            if (!self.loginState.isAdmin()) {
                return;
            }

            $.ajax({
                url: API_BASEURL + "system/commands",
                type: "GET",
                dataType: "json",
                success: self.fromCommandResponse
            });
        };

        self.fromCommandResponse = function(response) {
            var actions = [];
            if (response.core && response.core.length) {
                _.each(response.core, function(data) {
                    var action = _.extend({}, data);
                    action.actionSource = "core";
                    actions.push(action);
                });
                actions.push({action: "divider"});
            }
            _.each(response.custom, function(data) {
                var action = _.extend({}, data);
                action.actionSource = "custom";
                actions.push(action);
            });
            self.lastCommandResponse = response;
            self.systemActions(actions);
        };

        self.triggerCommand = function(commandSpec) {
            var callback = function() {
                $.ajax({
                    url: commandSpec.resource,
                    type: "POST",
                    dataType: "json",
                    data: "{}",
                    contentType: "application/json; charset=UTF-8",
                    success: function() {
                        new PNotify({title: "Success", text: _.sprintf(gettext("The command \"%(command)s\" executed successfully"), {command: commandSpec.name}), type: "success"});
                    },
                    error: function(jqXHR, textStatus, errorThrown) {
                        if (!commandSpec.hasOwnProperty("ignore") || !commandSpec.ignore) {
                            var error = "<p>" + _.sprintf(gettext("The command \"%(command)s\" could not be executed."), {command: commandSpec.name}) + "</p>";
                            error += pnotifyAdditionalInfo("<pre>" + jqXHR.responseText + "</pre>");
                            new PNotify({title: gettext("Error"), text: error, type: "error", hide: false});
                        }
                    }
                })
            };
            if (commandSpec.confirm) {
                showConfirmationDialog({
                    message: commandSpec.confirm,
                    onproceed: function(e) {
                        callback();
                    }
                });
            } else {
                callback();
            }
        };

        self.onUserLoggedIn = function(user) {
            if (user.admin) {
                self.requestData();
            } else {
                self.onUserLoggedOut();
            }
        };

        self.onUserLoggedOut = function() {
            self.lastCommandResponse = undefined;
            self.systemActions([]);
        }
    }

    // view model class, parameters for constructor, container to bind to
    ADDITIONAL_VIEWMODELS.push([
        SystemViewModel,
        ["loginStateViewModel"],
        []
    ]);
});
