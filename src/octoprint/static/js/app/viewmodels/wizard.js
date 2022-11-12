$(function () {
    function WizardViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settingsViewModel = parameters[1];

        self.wizardDialog = undefined;
        self.reloadOverlay = undefined;

        self.allViewModels = undefined;

        self.finishing = false;
        self.wizards = [];

        self.isDialogActive = function () {
            return self.wizardDialog.is(":visible");
        };

        self.showDialog = function () {
            // only open a wizard if we have one and either are in first run OR logged in
            // as admin
            if (!CONFIG_WIZARD || (!CONFIG_FIRST_RUN && !self.loginState.isAdmin()))
                return;

            self.getWizardDetails().done(function (response) {
                callViewModels(self.allViewModels, "onWizardDetails", [response]);

                if (!self.isDialogActive()) {
                    self.wizardDialog
                        .modal({
                            minHeight: function () {
                                return Math.max(
                                    $.fn.modal.defaults.maxHeight() - 80,
                                    250
                                );
                            }
                        })
                        .css({
                            "margin-left": function () {
                                return -($(this).width() / 2);
                            }
                        });
                }

                callViewModels(self.allViewModels, "onWizardShow");

                callViewModels(self.allViewModels, "onBeforeWizardTabChange", [
                    OCTOPRINT_INITIAL_WIZARD,
                    undefined
                ]);
                callViewModels(self.allViewModels, "onAfterWizardTabChange", [
                    OCTOPRINT_INITIAL_WIZARD
                ]);
            });
        };

        self.closeDialog = function () {
            self.wizardDialog.modal("hide");
        };

        self.onStartup = function () {
            self.wizardDialog = $("#wizard_dialog");
            self.wizardDialog.on("show", function (event) {
                OctoPrint.coreui.wizardOpen = true;
            });
            self.wizardDialog.on("hidden", function (event) {
                OctoPrint.coreui.wizardOpen = false;
            });

            self.reloadOverlay = $("#reloadui_overlay");
        };

        self.onUserLoggedIn = function () {
            self.showDialog();
        };

        self.onAllBound = function (allViewModels) {
            self.allViewModels = allViewModels;
            self.wizardDialog.bootstrapWizard({
                tabClass: "nav nav-list",
                nextSelector: ".button-next",
                previousSelector: ".button-previous",
                finishSelector: ".button-finish",
                withVisible: false,
                onTabClick: function () {
                    // we don't allow clicking on the tabs
                    return false;
                },
                onTabShow: function (tab, navigation, index) {
                    if (index < 0 || tab.length == 0) {
                        return true;
                    }

                    var total = self.wizardDialog.bootstrapWizard("navigationLength");

                    if (index == total) {
                        self.wizardDialog.find(".button-next").hide();
                        self.wizardDialog
                            .find(".button-finish")
                            .show()
                            .removeClass("disabled");
                    } else {
                        self.wizardDialog.find(".button-finish").hide();
                        self.wizardDialog.find(".button-next").show();
                    }

                    var active = tab[0].id;
                    if (active != undefined) {
                        callViewModels(allViewModels, "onAfterWizardTabChange", [active]);
                    }
                },
                onTabChange: function (tab, navigation, index, nextTabIndex, nextTab) {
                    var current, next;

                    if (
                        index == undefined ||
                        index < 0 ||
                        nextTabIndex == undefined ||
                        nextTabIndex < 0 ||
                        index == nextTabIndex ||
                        tab.length == 0 ||
                        nextTab.length == 0
                    ) {
                        // let's ignore that nonsense
                        return;
                    }

                    current = tab[0].id;
                    next = nextTab[0].id;

                    if (current != undefined && next != undefined) {
                        var result = true;
                        callViewModels(
                            allViewModels,
                            "onBeforeWizardTabChange",
                            function (method) {
                                // we want to continue evaluating even if result becomes false
                                result = method(next, current) !== false && result;
                            }
                        );

                        // also trigger the onWizardTabChange event here which we misnamed and
                        // on which we misordered the parameters on during development but which might
                        // already be used somewhere - log a deprecation warning to console though
                        callViewModels(
                            allViewModels,
                            "onWizardTabChange",
                            function (method, viewModel) {
                                log.warn(
                                    "View model",
                                    viewModel,
                                    'is using deprecated callback "onWizardTabChange", please change to "onBeforeWizardTabChange"'
                                );

                                // we want to continue evaluating even if result becomes false
                                result = method(current, next) !== false && result;
                            }
                        );
                        return result;
                    }
                },
                onFinish: function (tab, navigation, index) {
                    var closeDialog = true;
                    callViewModels(
                        allViewModels,
                        "onBeforeWizardFinish",
                        function (method) {
                            // we don't need to call all methods here, one method saying that
                            // the dialog must not be closed yet is enough to stop
                            //
                            // we evaluate closeDialog first to make sure we don't call
                            // the method once it becomes false
                            closeDialog = closeDialog && method() !== false;
                        }
                    );

                    if (closeDialog) {
                        var reload = false;
                        callViewModels(
                            allViewModels,
                            "onWizardFinish",
                            function (method) {
                                // if any of our methods returns that it wants to reload
                                // we'll need to set reload to true
                                //
                                // order is important here - the method call needs to happen
                                // first, or it won't happen after the reload flag has been
                                // set once due to the || making further evaluation unnecessary
                                // then
                                reload = method() == "reload" || reload;
                            }
                        );
                        self.finishWizard().done(function () {
                            self.closeDialog();
                            if (reload) {
                                self.reloadOverlay.show();
                            }
                            callViewModels(allViewModels, "onAfterWizardFinish");
                        });
                    }
                }
            });
            self.showDialog();
        };

        self.getWizardDetails = function () {
            return OctoPrint.wizard.get().done(function (response) {
                self.wizards = _.filter(_.keys(response), function (key) {
                    return (
                        response[key] &&
                        response[key]["required"] &&
                        !response[key]["ignored"]
                    );
                });
            });
        };

        self.finishWizard = function () {
            var deferred = $.Deferred();
            self.finishing = true;

            self.settingsViewModel
                .saveData()
                .done(function () {
                    OctoPrint.wizard
                        .finish(self.wizards)
                        .done(function () {
                            deferred.resolve(arguments);
                        })
                        .fail(function () {
                            deferred.reject(arguments);
                        })
                        .always(function () {
                            self.finishing = false;
                        });
                })
                .fail(function () {
                    deferred.reject(arguments);
                });

            return deferred;
        };

        self.onSettingsPreventRefresh = function () {
            return self.isDialogActive();
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: WizardViewModel,
        dependencies: ["loginStateViewModel", "settingsViewModel"],
        elements: ["#wizard_dialog"]
    });
});
