$(function () {
    function ActionCommandPromptViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];

        self.modal = ko.observable(undefined);

        self.text = ko.observable();
        self.buttons = ko.observableArray([]);

        self.active = ko.pureComputed(function () {
            return self.text() !== undefined;
        });
        self.visible = ko.pureComputed(function () {
            return self.modal() !== undefined;
        });

        self.requestData = function () {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_ACTION_COMMAND_PROMPT_INTERACT
                )
            )
                return;

            OctoPrint.plugins.action_command_prompt.get().done(self.fromResponse);
        };

        self.fromResponse = function (data) {
            if (data.hasOwnProperty("text") && data.hasOwnProperty("choices")) {
                self.text(data.text);
                self.buttons(data.choices);
                self.showPrompt();
            } else {
                self.text(undefined);
                self.buttons([]);
            }
        };

        self.showPrompt = function () {
            var text = self.text();
            var buttons = self.buttons();

            var opts = {
                title: gettext("Message from your printer"),
                message: text,
                selections: buttons,
                maycancel: true, // see #3171
                onselect: function (index) {
                    if (index > -1) {
                        self._select(index);
                    }
                },
                onclose: function () {
                    self.modal(undefined);
                }
            };

            self.modal(showSelectionDialog(opts));
        };

        self._select = function (index) {
            OctoPrint.plugins.action_command_prompt.select(index);
        };

        self._closePrompt = function () {
            var modal = self.modal();
            if (modal) {
                modal.modal("hide");
            }
        };

        self.onStartupComplete = function () {
            self.requestData();
        };

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_ACTION_COMMAND_PROMPT_INTERACT
                )
            )
                return;
            if (plugin !== "action_command_prompt") {
                return;
            }

            switch (data.action) {
                case "show": {
                    self.text(data.text);
                    self.buttons(data.choices);
                    self.showPrompt();
                    break;
                }
                case "close": {
                    self.text(undefined);
                    self.buttons([]);
                    self._closePrompt();
                    break;
                }
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ActionCommandPromptViewModel,
        dependencies: ["loginStateViewModel", "accessViewModel"],
        elements: ["#navbar_plugin_action_command_prompt"]
    });
});
