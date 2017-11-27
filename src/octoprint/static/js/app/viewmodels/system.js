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
                return $.Deferred().reject().promise();
            }

            return OctoPrint.system.getCommands()
                .done(self.fromCommandResponse);
        };

        self.fromCommandResponse = function(response) {
            var actions = [];
            if (response.core && response.core.length) {
                _.each(response.core, function(data) {
                    var action = _.extend({}, data);
                    action.actionSource = "core";
                    actions.push(action);
                });
                if (response.custom && response.custom.length) {
                    actions.push({action: "divider"});
                }
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
            var deferred = $.Deferred();

            var callback = function() {
                OctoPrint.system.executeCommand(commandSpec.actionSource, commandSpec.action)
                    .done(function() {
                        var text;
                        if (commandSpec.async) {
                            text = gettext("The command \"%(command)s\" was triggered asynchronously");
                        } else {
                            text = gettext("The command \"%(command)s\" executed successfully");
                        }

                        new PNotify({
                            title: "Success",
                            text: _.sprintf(text, {command: commandSpec.name}),
                            type: "success"
                        });
                        deferred.resolve(["success", arguments]);
                    })
                    .fail(function(jqXHR, textStatus, errorThrown) {
                        if (!commandSpec.hasOwnProperty("ignore") || !commandSpec.ignore) {
                            var error = "<p>" + _.sprintf(gettext("The command \"%(command)s\" could not be executed."), {command: commandSpec.name}) + "</p>";
                            error += pnotifyAdditionalInfo("<pre>" + jqXHR.responseText + "</pre>");
                            new PNotify({title: gettext("Error"), text: error, type: "error", hide: false});
                            deferred.reject(["error", arguments]);
                        } else {
                            deferred.resolve(["ignored", arguments]);
                        }
                    });
            };

            if (commandSpec.confirm) {
                showConfirmationDialog({
                    message: commandSpec.confirm,
                    onproceed: function() {
                        callback();
                    },
                    oncancel: function() {
                        deferred.reject("cancelled", arguments);
                    }
                });
            } else {
                callback();
            }

            return deferred.promise();
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
        };

        self.onEventSettingsUpdated = function() {
            if (self.loginState.isAdmin()) {
                self.requestData();
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: SystemViewModel,
        dependencies: ["loginStateViewModel"]
    });
});
