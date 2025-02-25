$(function () {
    function HealthCheckViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];
        self.settings = parameters[2];

        self.lastCheck = undefined;
        self.checkResults = ko.observableArray();
        self.unackedCheckResults = ko.observable(false);

        self.healthCheckDialog = undefined;
        self.healthCheckDialogContent = undefined;

        self.additionalHandlers = undefined;

        self._pythonEOLNotification = undefined;

        self.alertClass = (item) => {
            switch (item.result) {
                case "warning": {
                    return "alert-warning";
                }
                case "issue": {
                    return "alert-error";
                }
                case "ok":
                default: {
                    return "alert-success";
                }
            }
        };

        self.bubbleColor = ko.pureComputed(() => {
            const checkResults = self.checkResults();
            if (checkResults.length === 0) return "#00ff00";

            const results = _.pluck(checkResults, "result");

            if (_.some(_.map(results, (x) => x === "issue"))) {
                return "#ff0000";
            }

            return "#ffff00";
        });

        self.compareCheckResult = (a, b) => {
            const tA = a.title.toUpperCase();
            const tB = b.title.toUpperCase();

            if (tA < tB) return -1;
            if (tA > tB) return +1;
            return 0;
        };

        self.warningResults = ko.pureComputed(() => {
            return _.filter(self.checkResults(), (x) => x.result === "warning").sort(
                self.compareCheckResult
            );
        });

        self.issueResults = ko.pureComputed(() => {
            return _.filter(self.checkResults(), (x) => x.result === "issue").sort(
                self.compareCheckResult
            );
        });

        self.showHealthCheckDialog = () => {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_HEALTH_CHECK_CHECK
                )
            )
                return;

            self.healthCheckDialogContent.scrollTop(0);

            if (!self.healthCheckDialog.hasClass("in")) {
                self.healthCheckDialog
                    .modal({
                        minHeight: function () {
                            return Math.max($.fn.modal.defaults.maxHeight() - 80, 250);
                        }
                    })
                    .css({
                        "margin-left": function () {
                            return -($(this).width() / 2);
                        }
                    });
            }

            return false;
        };

        self.toggleAcked = (result) => {
            result.acked(!result.acked());
            self._saveAcked();
        };

        self.ackAllCheckResults = () => {
            const results = self.checkResults();
            results.forEach((result) => {
                result.acked(true);
            });
            self._saveAcked();
        };

        self.requestData = (refresh) => {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_HEALTH_CHECK_CHECK
                )
            ) {
                return $.Deferred().reject().promise();
            }

            return OctoPrint.plugins.health_check.get(refresh).done(self.fromResponse);
        };

        self.fromResponse = (response) => {
            self.lastCheck = response.health;

            const acked = self._loadAcked();

            const results = [];
            _.each(_.keys(self.lastCheck), (key) => {
                let handler = self[`_fromResponse_${key}`];
                if (handler === undefined) {
                    handler = self.additionalHandlers[key];
                }

                if (handler === undefined) return;

                const result = self.lastCheck[key]["result"];
                const context = self.lastCheck[key]["context"];
                const hash = self.lastCheck[key]["hash"];
                if (result === "ok") return;

                const handlerResult = handler(result, context);
                if (handlerResult) {
                    handlerResult.key = key;
                    handlerResult.hash = hash;
                    handlerResult.acked = ko.observable(acked[key] === hash);
                    results.push(handlerResult);
                }
            });

            self.checkResults(results);
            self._saveAcked();
        };

        self._fromResponse_python_eol = (result, context) => {
            const COOKIE_NAME = "python_eol_notified";
            const COOKIE_VALUE = `${context.version};${context.date}`;

            if (self._pythonEOLNotification) {
                self._pythonEOLNotification.remove();
                self._pythonEOLNotification = undefined;
            }

            if (result === "ok") return;

            let eolStatement, eolTitle;
            if (context.soon) {
                eolStatement = gettext(
                    "Your Python version %(python)s is nearing its end of life (%(date)s)."
                );
                eolTitle = gettext("Soon to be outdated Python");
            } else {
                eolStatement = gettext(
                    "Your Python version %(python)s is past its end of life (%(date)s)."
                );
                eolTitle = gettext("Outdated Python");
            }

            if (context.last_octoprint) {
                octoprintStatement = _.sprintf(
                    gettext(
                        "OctoPrint %(octoprint)s will be the last version to support this Python version."
                    ),
                    {octoprint: _.escape(context.last_octoprint)}
                );
            } else {
                octoprintStatement = gettext(
                    "A future version of OctoPrint will drop support for this Python version."
                );
            }

            const html =
                "<p>" +
                _.sprintf(eolStatement, {
                    python: _.escape(context.version),
                    date: _.escape(context.date)
                }) +
                " " +
                octoprintStatement +
                " " +
                gettext("You should upgrade as soon as possible!") +
                "</p>" +
                "<p>" +
                gettext("Please refer to the FAQ for recommended upgrade workflows:") +
                "</p>" +
                "<p><a href='https://faq.octoprint.org/python-update' target='_blank' rel='noopener noreferer'>How to migrate to another Python version</a></p>";

            const notification =
                html +
                "<p><small>" +
                gettext(
                    "This will be shown again every 30 days until you have upgraded your Python."
                ) +
                "</small></p>";

            const currentCookieValue = OctoPrint.getCookie(COOKIE_NAME);
            if (currentCookieValue !== "true" && currentCookieValue !== COOKIE_VALUE) {
                self._pythonEOLNotification = new PNotify({
                    title: gettext("Warning"),
                    text: notification,
                    hide: false,
                    type: result == "warning" ? "warning" : "error"
                });
                self._pythonEOLNotification.elem.attr(
                    "data-test-id",
                    "notification-python-eol"
                );

                OctoPrint.setCookie(
                    COOKIE_NAME,
                    COOKIE_VALUE,
                    {maxage: 30 * 24 * 60 * 60} // 30d
                );
            }

            return {
                title: gettext("Outdated Python"),
                html: html,
                result: result
            };
        };

        self._fromResponse_octoprint_freshness = (result, context) => {
            if (result === "ok") return;

            const html =
                "<p>" +
                gettext("Your OctoPrint version is outdated.") +
                "</p><p>" +
                _.sprintf(
                    gettext(
                        "There are %(count)d newer releases. You have <strong>%(current)s</strong>, the latest is <strong>%(latest)s</strong>."
                    ),
                    {
                        count: context.newer.length,
                        current: context.version,
                        latest: context.newer[0]
                    }
                ) +
                "</p><p>" +
                gettext("You should update as soon as possible.") +
                "</p>";

            return {
                title: gettext("Outdated OctoPrint"),
                html: html,
                result: result
            };
        };

        self._fromResponse_filesystem_storage = (result, context) => {
            if (result === "ok") return;

            let statement, title;
            if (result === "warning") {
                title = "Storage starting to run out";
                statement = gettext(
                    "One or more folders that OctoPrint uses are starting to run out of space."
                );
            } else {
                title = "Storage close to running out";
                statement = gettext(
                    "One or more folders that OctoPrint uses are about to run out of space."
                );
            }

            const fillState = gettext("%(usage)f%% filled");
            const threshold =
                self.settings.settings.plugins.health_check.checks.filesystem_storage.warning_threshold();
            const folders = _.map(_.keys(context), (folder) => {
                const usage = context[folder];
                return (
                    "<li><code>" +
                    (usage > threshold ? "<strong>" : "") +
                    folder +
                    "</code>: " +
                    _.sprintf(fillState, {usage: usage}) +
                    (usage > threshold ? "</strong>" : "") +
                    "</li>"
                );
            });

            const html =
                "<p>" +
                statement +
                "</p>" +
                "<p><ul>" +
                folders.join("") +
                "</ul></p><p>" +
                gettext(
                    "Please free up some space to ensure OctoPrint will continue to function as expected."
                ) +
                "</p>";

            return {
                title: title,
                html: html,
                result: result
            };
        };

        self.onAllBound = function (allViewModels) {
            const additionalHandlers = {};
            callViewModels(
                allViewModels,
                "getAdditionalHealthCheckHandlers",
                function (getter) {
                    const handlers = getter();
                    _.each(_.keys(handlers), function (key) {
                        additionalHandlers[key] = handlers[key];
                    });
                }
            );
            self.additionalHandlers = additionalHandlers;
        };

        self.onStartup = function () {
            self.healthCheckDialog = $("#plugin_health_check_dialog");
            self.healthCheckDialogContent = $("#plugin_health_check_dialog_content");
        };

        self.onEventConnectivityChanged = function (payload) {
            if (!payload || !payload.new) return;
            self.triggerRequestData();
        };

        self.onEventPluginHealthCheckUpdateHealthcheck = function () {
            self.triggerRequestData();
        };

        self.onUserPermissionsChanged =
            self.onUserLoggedIn =
            self.onUserLoggedOut =
            self.triggerRequestData =
                (user) => {
                    if (
                        self.loginState.hasPermission(
                            self.access.permissions.PLUGIN_HEALTH_CHECK_CHECK
                        )
                    ) {
                        self.requestData();
                    }
                };

        self._localStorageKey = "plugin.health_check.acked_check_results";
        self._saveAcked = () => {
            const hashes = {};
            self.checkResults().forEach((result) => {
                if (result.acked()) {
                    hashes[result.key] = result.hash;
                }
            });
            saveToLocalStorage(self._localStorageKey, hashes);

            self.unackedCheckResults(
                _.filter(self.checkResults(), (x) => !x.acked()).length > 0
            );

            return hashes;
        };
        self._loadAcked = () => {
            return loadFromLocalStorage(self._localStorageKey);
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: HealthCheckViewModel,
        dependencies: ["loginStateViewModel", "accessViewModel", "settingsViewModel"],
        elements: ["#plugin_health_check_dialog", "#navbar_plugin_health_check"]
    });
});
