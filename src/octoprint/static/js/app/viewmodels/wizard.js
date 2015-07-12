$(function() {
    function WizardViewModel() {
        var self = this;

        self.wizardDialog = undefined;

        self.showDialog = function() {
            self.wizardDialog.modal({
                minHeight: function() { return Math.max($.fn.modal.defaults.maxHeight() - 80, 250); }
            }).css({
                width: 'auto',
                'margin-left': function() { return -($(this).width() /2); }
            });
        };

        self.closeDialog = function() {
            self.wizardDialog.modal("hide");
        };

        self.onStartup = function() {
            self.wizardDialog = $("#wizard_dialog");
        };

        self.onAllBound = function(allViewModels) {
            if (CONFIG_WIZARD) {
                self.wizardDialog.bootstrapWizard({
                    tabClass: "nav nav-list",
                    nextSelector: ".button-next",
                    previousSelector: ".button-previous",
                    finishSelector: ".button-finish",
                    onTabShow: function(tab, navigation, index) {
                        var total = navigation.find("li").length;
                        var current = index+1;

                        if (current >= total) {
                            self.wizardDialog.find(".button-next").hide();
                            self.wizardDialog.find(".button-finish").show().removeClass("disabled");
                        } else {
                            self.wizardDialog.find(".button-finish").hide();
                            self.wizardDialog.find(".button-next").show();
                        }
                    }
                });
                self.showDialog();
            }
        }
    }

    OCTOPRINT_VIEWMODELS.push([
        WizardViewModel,
        [],
        "#wizard_dialog"
    ]);
});
