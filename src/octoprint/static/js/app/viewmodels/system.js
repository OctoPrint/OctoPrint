$(function () {
    function SystemViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];

        self.lastCommandResponse = undefined;
        self.systemActions = ko.observableArray([]);

        self.requestData = function () {
            self.requestCommandData();
        };

        self.requestCommandData = function () {
            if (!self.loginState.hasPermission(self.access.permissions.SYSTEM)) {
                return $.Deferred().reject().promise();
            }

            return OctoPrint.system.getCommands().done(self.fromCommandResponse);
        };

        self.fromCommandResponse = function (response) {
            var actions = [];
            if (response.core && response.core.length) {
                _.each(response.core, function (data) {
                    var action = _.extend({}, data);
                    action.actionSource = "core";
                    actions.push(action);
                });
                if (
                    (response.custom && response.custom.length) ||
                    (response.plugin && response.plugin.length)
                ) {
                    actions.push({action: "divider"});
                }
            }
            _.each(response.plugin, function (data) {
                var action = _.extend({}, data);
                action.actionSource = "plugin";
                actions.push(action);
                if (response.custom && response.custom.length) {
                    actions.push({action: "divider"});
                }
            });
            _.each(response.custom, function (data) {
                var action = _.extend({}, data);
                action.actionSource = "custom";
                actions.push(action);
            });
            self.lastCommandResponse = response;
            self.systemActions(actions);
        };

        self.triggerCommand = function (commandSpec) {
            if (!self.loginState.hasPermission(self.access.permissions.SYSTEM)) {
                return $.Deferred().reject().promise();
            }

            var deferred = $.Deferred();

            var callback = function () {
                OctoPrint.system
                    .executeCommand(commandSpec.actionSource, commandSpec.action)
                    .done(function () {
                        var text;
                        if (commandSpec.async) {
                            text = gettext(
                                'The command "%(command)s" was triggered asynchronously'
                            );
                        } else {
                            text = gettext(
                                'The command "%(command)s" executed successfully'
                            );
                        }

                        new PNotify({
                            title: "Success",
                            text: _.sprintf(text, {command: _.escape(commandSpec.name)}),
                            type: "success"
                        });
                        deferred.resolve(["success", arguments]);
                    })
                    .fail(function (jqXHR, textStatus, errorThrown) {
                        if (
                            !commandSpec.hasOwnProperty("ignore") ||
                            !commandSpec.ignore
                        ) {
                            var error =
                                "<p>" +
                                _.sprintf(
                                    gettext(
                                        'The command "%(command)s" could not be executed.'
                                    ),
                                    {command: _.escape(commandSpec.name)}
                                ) +
                                "</p>";
                            error += pnotifyAdditionalInfo(
                                "<pre>" + _.escape(jqXHR.responseText) + "</pre>"
                            );
                            new PNotify({
                                title: gettext("Error"),
                                text: error,
                                type: "error",
                                hide: false
                            });
                            deferred.reject(["error", arguments]);
                        } else {
                            deferred.resolve(["ignored", arguments]);
                        }
                    });
            };

            if (commandSpec.confirm) {
                showConfirmationDialog({
                    message: commandSpec.confirm,
                    onproceed: function () {
                        callback();
                    },
                    oncancel: function () {
                        deferred.reject("cancelled", arguments);
                    }
                });
            } else {
                callback();
            }

            return deferred.promise();
        };

        self.onUserPermissionsChanged =
            self.onUserLoggedIn =
            self.onUserLoggedOut =
                function (user) {
                    if (self.loginState.hasPermission(self.access.permissions.SYSTEM)) {
                        self.requestData();
                    } else {
                        self.lastCommandResponse = undefined;
                        self.systemActions([]);
                    }
                };

        self.onEventSettingsUpdated = function () {
            if (self.loginState.hasPermission(self.access.permissions.SYSTEM)) {
                self.requestData();
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: SystemViewModel,
        dependencies: ["loginStateViewModel", "accessViewModel"]
    });
});
