$(function() {
    //~~ OctoPrint client setup
    var OctoPrint = window.OctoPrint;
    OctoPrint.options.baseurl = BASE_URL;

    var l10n = getQueryParameterByName("l10n");
    if (l10n) {
        OctoPrint.options.locale = l10n;
    }

    //~~ Initialize i18n

    var catalog = window["BABEL_TO_LOAD_EN"];
    if (catalog === undefined) {
        catalog = {messages: undefined, plural_expr: undefined, locale: undefined, domain: undefined}
    }
    babel.Translations.load(catalog).install();

    function RecoveryViewModel() {
        var self = this;

        self.systemCommands = ko.observableArray([]);

        self.request = function() {
            OctoPrint.system.getCommandsForSource("core")
                .done(function(resp) {
                    self.systemCommands(resp);
                })
        }

        self.executeSystemCommand = function(command) {
            var process = function() {
                OctoPrint.system.executeCommand(command.source, command.action);
            }

            if (command.confirm) {
                showConfirmationDialog({
                    message: command.confirm,
                    onproceed: function() {
                        process();
                    }
                });
            } else {
                process();
            }
        }

        self.request();
    }

    var viewModel = new RecoveryViewModel();
    ko.applyBindings(viewModel, document.getElementById("recovery"));
});
