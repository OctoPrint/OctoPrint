$(function () {
    function ErrorTrackingViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];
        self.loginState = parameters[1];

        var notification = undefined;
        var performCheck = function () {
            if (!self.loginState.isAdmin()) return;

            // already enabled?
            if (self.settings.settings.plugins.errortracking.enabled()) return;

            // RC release channel?
            var releaseChannel =
                self.settings.settings.plugins.softwareupdate.octoprint_release_channel();
            if (releaseChannel === "rc/maintenance" || releaseChannel === "rc/devel") {
                if (notification !== undefined) return;

                // ignored?
                try {
                    var ignoredString =
                        localStorage["plugin.errortracking.notification_ignored"];
                    var ignored = false;

                    if (ignoredString) {
                        ignored = JSON.parse(ignoredString);
                    }

                    if (ignored) return;
                } catch (ex) {
                    log.error(
                        "Error while reading plugin.errortracking.notification_ignored from local storage"
                    );
                }

                // show notification
                notification = new PNotify({
                    title: gettext("Enable error reporting?"),
                    text: gettext(
                        "<p>It looks like you are tracking an OctoPrint RC release channel. It " +
                            "would be great if you would enable error reporting so that any kind of errors that occur " +
                            "with an RC can be looked into more easily. Thank you!</p>" +
                            "<p><small>You can find more information on error reporting " +
                            "under Settings > Error Tracking</small></p>"
                    ),
                    hide: false,
                    confirm: {
                        confirm: true,
                        buttons: [
                            {
                                text: gettext("Ignore"),
                                click: function () {
                                    notification.remove();
                                    notification = undefined;
                                    new PNotify({
                                        text: gettext(
                                            'You can still enable error tracking via "Settings" > "Error Tracking"'
                                        )
                                    });

                                    if (Modernizr.localstorage) {
                                        localStorage[
                                            "plugin.errortracking.notification_ignored"
                                        ] = JSON.stringify(true);
                                    }
                                }
                            },
                            {
                                text: gettext("Enable"),
                                addClass: "btn-primary",
                                click: function () {
                                    self.settings
                                        .saveData({
                                            plugins: {
                                                errortracking: {
                                                    enabled: true
                                                }
                                            }
                                        })
                                        .done(function () {
                                            notification.remove();
                                            notification = undefined;
                                            location.reload(true);
                                        });
                                }
                            }
                        ]
                    },
                    buttons: {
                        closer: false,
                        sticker: false
                    }
                });

                // not an RC release channel, close notification
            } else if (notification !== undefined) {
                notification.remove();
                notification = undefined;
            }
        };

        var subbed = false;
        self.onStartup =
            self.onUserLoggedIn =
            self.onUserLoggedOut =
                function () {
                    performCheck();
                    if (
                        self.settings &&
                        self.settings.settings &&
                        self.settings.settings.plugins &&
                        self.settings.settings.plugins.softwareupdate &&
                        !subbed
                    ) {
                        subbed = true;
                        self.settings.settings.plugins.softwareupdate.octoprint_release_channel.subscribe(
                            performCheck
                        );
                    }
                };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ErrorTrackingViewModel,
        dependencies: ["settingsViewModel", "loginStateViewModel"]
    });
});
