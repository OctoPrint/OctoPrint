(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var OctoPrintActionCommandPromptClient = function(base) {
        this.base = base;
    };

    OctoPrintActionCommandPromptClient.prototype.get = function(refresh, opts) {
        return this.base.get(this.base.getSimpleApiUrl("action_command_prompt"), opts);
    };

    OctoPrintActionCommandPromptClient.prototype.select = function(choice, opts) {
        var data = {
            choice: choice
        };
        return this.base.simpleApiCommand("action_command_prompt", "select", data, opts);
    };

    OctoPrintClient.registerPluginComponent("action_command_prompt", OctoPrintActionCommandPromptClient);
    return OctoPrintActionCommandPromptClient;
});

$(function() {
    function ActionCommandPromptViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];

        self._modal = undefined;

        self.requestData = function() {
            if (!self.loginState.isUser()) return;

            OctoPrint.plugins.action_command_prompt.get()
                .done(self.fromResponse);
        };

        self.fromResponse = function(data) {
            if (data.hasOwnProperty("text") && data.hasOwnProperty("choices")) {
                self._showPrompt(data.text, data.choices);
            }
        };

        self._showPrompt = function(text, buttons) {
            var opts = {
                title: gettext("Message from your printer"),
                message: text,
                selections: buttons,
                onselect: function(index) {
                    if (index > -1) {
                        self._select(index);
                    }
                },
                onclose: function() {
                    self._modal = undefined;
                }
            };

            self._modal = showSelectionDialog(opts)
        };

        self._select = function(index) {
            OctoPrint.plugins.action_command_prompt.select(index);
        };

        self._closePrompt = function() {
            if (self._modal) {
                self._modal.modal("hide");
            }
        };

        self.onStartupComplete = function() {
            self.requestData();
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (!self.loginState.isUser()) return;
            if (plugin !== "action_command_prompt") {
                return;
            }

            switch (data.action) {
                case "show": {
                    self._showPrompt(data.text, data.choices);
                    break;
                }
                case "close": {
                    self._closePrompt();
                    break;
                }
            }
        }

    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ActionCommandPromptViewModel,
        dependencies: ["loginStateViewModel"]
    });
});
