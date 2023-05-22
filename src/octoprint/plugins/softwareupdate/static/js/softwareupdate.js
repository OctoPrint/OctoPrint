$(function () {
    function SoftwareUpdateViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.printerState = parameters[1];
        self.settings = parameters[2];
        self.access = parameters[3];

        // optional

        self.piSupport = parameters[4]; // might be null!

        self.popup = undefined;

        self.updateInProgress = false;
        self.cancelInProgress = false;
        self.waitingForRestart = false;
        self.restartTimeout = undefined;

        self.currentlyBeingUpdated = [];
        self.queuedUpdates = ko.observableArray([]);

        self.working = ko.observable(false);
        self.workingTitle = ko.observable();
        self.workingDialog = undefined;
        self.workingOutput = undefined;
        self.loglines = ko.observableArray([]);

        self.checking = ko.observable(false);

        self.octoprintReleasedVersion = ko.observable();

        self.octoprintUnconfigured = ko.pureComputed(function () {
            return (
                self.settings.settings.plugins.softwareupdate.octoprint_type() ===
                    "git_commit" && self.error_checkoutFolder()
            );
        });
        self.octoprintUnreleased = ko.pureComputed(function () {
            return (
                self.settings.settings.plugins.softwareupdate.octoprint_type() ===
                    "github_release" && !self.octoprintReleasedVersion()
            );
        });

        self.environmentSupported = ko.observable(true);
        self.environmentVersions = ko.observableArray([]);

        self.storageSufficient = ko.observable(true);
        self.storageFree = ko.observableArray([]);

        self.cacheTimestamp = ko.observable();
        self.cacheTimestampText = ko.pureComputed(function () {
            return formatDate(self.cacheTimestamp());
        });

        self.config_cacheTtl = ko.observable();
        self.config_notifyUsers = ko.observable();
        self.config_trackedBranch = ko.observable();
        self.config_checkoutFolder = ko.observable();
        self.config_pipTarget = ko.observable();
        self.config_checkType = ko.observable();
        self.config_releaseChannel = ko.observable();
        self.config_pipEnableCheck = ko.observable();
        self.config_minimumFreeStorage = ko.observable();
        self.config_githubToken = ko.observable();
        self.config_githubTokenSet = ko.observable(false);

        self.error_checkoutFolder = ko.pureComputed(function () {
            return (
                self.config_checkType() === "git_commit" &&
                (!self.config_checkoutFolder() ||
                    self.config_checkoutFolder().trim() === "")
            );
        });

        self.enableUpdate = ko.pureComputed(function () {
            return (
                !self.updateInProgress &&
                self.environmentSupported() &&
                self.storageSufficient() &&
                !self.throttled()
            );
        });

        self.enableUpdateAll = ko.pureComputed(function () {
            return self.enableUpdate() && self.availableAndPossible().length > 0;
        });

        self.enableUpdateEnabled = ko.pureComputed(function () {
            return (
                self.enableUpdate() && self.availableAndPossibleAndEnabled().length > 0
            );
        });

        self.enableCancelQueued = ko.pureComputed(function () {
            return self.queuedUpdates().length > 0;
        });

        self.updateQueued = function (item) {
            return self.queuedUpdates().indexOf(item.key) > -1;
        };

        self.enable_configSave = ko.pureComputed(function () {
            return (
                self.config_checkType() === "github_release" ||
                self.config_checkType() === "github_commit" ||
                (self.config_checkType() === "git_commit" && !self.error_checkoutFolder())
            );
        });

        self.configurationDialog = undefined;
        self._updateClicked = false;

        self.config_availableCheckTypes = ko.observableArray([]);
        self.config_availableReleaseChannels = ko.observableArray([]);

        self.reloadOverlay = $("#reloadui_overlay");

        self.versions = new ItemListHelper(
            "plugin.softwareupdate.versions",
            {
                name: function (a, b) {
                    // sorts ascending, puts octoprint first
                    if (a.key.toLocaleLowerCase() === "octoprint") return -1;
                    if (b.key.toLocaleLowerCase() === "octoprint") return 1;

                    if (
                        a.displayName.toLocaleLowerCase() <
                        b.displayName.toLocaleLowerCase()
                    )
                        return -1;
                    if (
                        a.displayName.toLocaleLowerCase() >
                        b.displayName.toLocaleLowerCase()
                    )
                        return 1;
                    return 0;
                }
            },
            {},
            "name",
            [],
            [],
            0
        );

        self.octoprintData = {
            item: undefined,
            current: ko.observable("unknown"),
            available: ko.observable("unknown")
        };

        self.updatelog = ko.observableArray([]);

        self.availableAndPossible = ko.pureComputed(function () {
            return _.filter(self.versions.items(), function (info) {
                return info.updateAvailable && info.updatePossible;
            });
        });

        self.availableAndPossibleAndEnabled = ko.pureComputed(function () {
            return _.filter(self.versions.items(), function (info) {
                return info.updateAvailable && info.updatePossible && !info.disabled;
            });
        });

        self.availableAndQueued = ko.pureComputed(function () {
            return _.filter(self.versions.items(), function (info) {
                return (
                    info.updateAvailable &&
                    info.updatePossible &&
                    self.queuedUpdates.indexOf(info.key) > -1
                );
            });
        });

        self.throttled = ko.pureComputed(function () {
            return (
                self.piSupport &&
                self.piSupport.currentIssue() &&
                !self.settings.settings.plugins.softwareupdate.ignore_throttled()
            );
        });

        self.onUserPermissionsChanged =
            self.onUserLoggedIn =
            self.onUserLoggedOut =
                function () {
                    if (
                        self.loginState.hasPermission(
                            self.access.permissions.PLUGIN_SOFTWAREUPDATE_CHECK
                        )
                    ) {
                        self.performCheck();
                    } else {
                        self._closePopup();
                    }

                    if (self.loginState.hasPermission(self.access.permissions.ADMIN)) {
                        self.requestUpdatelog();
                    }
                };

        self._showPopup = function (options, eventListeners, singleButtonNotify) {
            singleButtonNotify = singleButtonNotify || false;

            self._closePopup();

            if (singleButtonNotify) {
                self.popup = PNotify.singleButtonNotify(options);
            } else {
                self.popup = new PNotify(options);
            }

            if (eventListeners) {
                var popupObj = self.popup.get();
                _.each(eventListeners, function (value, key) {
                    popupObj.on(key, value);
                });
            }
        };

        self._updatePopup = function (options) {
            if (self.popup === undefined) {
                self._showPopup(options);
            } else {
                self.popup.update(options);
            }
        };

        self._closePopup = function () {
            if (self.popup !== undefined) {
                self.popup.remove();
            }
        };

        self.showPluginSettings = function () {
            self._copyConfig();
            self.configurationDialog.modal();
        };

        self.deleteGithubTokenApiKey = function () {
            var data = {
                plugins: {
                    softwareupdate: {
                        credentials: {
                            github: undefined
                        }
                    }
                }
            };

            self.settings.saveData(data, {
                success: function () {
                    self.performCheck();
                },
                complete: function () {
                    self.config_githubToken("");
                    self.config_githubTokenSet(false);
                },
                sending: true
            });
        };

        self.savePluginSettings = function (viewModel, event) {
            var target = $(event.target);
            target.prepend('<i class="fa fa-spinner fa-spin"></i> ');

            var githubToken = self.config_githubToken();

            var data = {
                plugins: {
                    softwareupdate: {
                        cache_ttl: parseInt(self.config_cacheTtl()),
                        notify_users: self.config_notifyUsers(),
                        octoprint_type: self.config_checkType(),
                        octoprint_release_channel: self.config_releaseChannel(),
                        octoprint_checkout_folder: self.config_checkoutFolder(),
                        octoprint_tracked_branch: self.config_trackedBranch(),
                        octoprint_pip_target: self.config_pipTarget(),
                        pip_enable_check: self.config_pipEnableCheck(),
                        minimum_free_storage: self.config_minimumFreeStorage()
                    }
                }
            };
            if (githubToken) {
                data.plugins.softwareupdate.credentials = {github: githubToken};
            }
            self.settings.saveData(data, {
                success: function () {
                    self.configurationDialog.modal("hide");
                    self._copyConfig();
                    self.performCheck();
                },
                complete: function () {
                    $("i.fa-spinner", target).remove();
                    self.config_githubToken("");
                },
                sending: true
            });
        };

        self.onBeforeBinding = function () {
            self.queuedUpdates(
                self.settings.settings.plugins.softwareupdate.queued_updates()
            );
        };

        self._copyConfig = function () {
            var availableCheckTypes = [
                {key: "github_release", name: gettext("Release")},
                {key: "github_commit", name: gettext("Github Commit")},
                {key: "git_commit", name: gettext("Local checkout")}
            ];
            self.config_availableCheckTypes(availableCheckTypes);

            var availableReleaseChannels = [];
            _.each(
                self.settings.settings.plugins.softwareupdate.octoprint_branch_mappings(),
                function (mapping) {
                    availableReleaseChannels.push({
                        key: mapping.branch(),
                        name: gettext(mapping.name() || mapping.branch())
                    });
                }
            );
            self.config_availableReleaseChannels(availableReleaseChannels);

            self.config_cacheTtl(
                self.settings.settings.plugins.softwareupdate.cache_ttl()
            );
            self.config_notifyUsers(
                self.settings.settings.plugins.softwareupdate.notify_users()
            );

            self.config_checkType(
                self.settings.settings.plugins.softwareupdate.octoprint_type()
            );
            self.config_releaseChannel(
                self.settings.settings.plugins.softwareupdate.octoprint_release_channel()
            );
            self.config_checkoutFolder(
                self.settings.settings.plugins.softwareupdate.octoprint_checkout_folder()
            );
            self.config_trackedBranch(
                self.settings.settings.plugins.softwareupdate.octoprint_tracked_branch()
            );
            self.config_pipTarget(
                self.settings.settings.plugins.softwareupdate.octoprint_pip_target()
            );

            self.config_pipEnableCheck(
                self.settings.settings.plugins.softwareupdate.pip_enable_check()
            );

            self.config_minimumFreeStorage(
                self.settings.settings.plugins.softwareupdate.minimum_free_storage()
            );

            self.config_githubTokenSet(
                self.settings.settings.plugins.softwareupdate.credentials.github_set()
            );
        };

        self._copyConfigBack = function () {
            self.settings.settings.plugins.softwareupdate.octoprint_checkout_folder(
                self.config_checkoutFolder()
            );
            self.settings.settings.plugins.softwareupdate.octoprint_type(
                self.config_checkType()
            );
        };

        self._enrichInformation = function (key, information) {
            information["key"] = key;

            if (
                !information.hasOwnProperty("displayName") ||
                information.displayName === ""
            ) {
                information.displayName = information.key;
            }
            if (
                !information.hasOwnProperty("displayVersion") ||
                information.displayVersion === ""
            ) {
                information.displayVersion = information.information.local.name;
            }
            if (
                !information.hasOwnProperty("releaseNotes") ||
                information.releaseNotes === ""
            ) {
                information.releaseNotes = undefined;
            }

            var fullNameTemplate = gettext("%(name)s: %(version)s");
            information.fullNameLocal = _.sprintf(fullNameTemplate, {
                name: _.escape(information.displayName),
                version: _.escape(information.displayVersion)
            });

            var fullNameRemoteVars = {
                name: _.escape(information.displayName),
                version: gettext("unknown")
            };
            if (
                information.hasOwnProperty("information") &&
                information.information.hasOwnProperty("remote") &&
                information.information.remote.hasOwnProperty("name")
            ) {
                fullNameRemoteVars.version = _.escape(
                    information.information.remote.name
                );
            }
            information.fullNameRemote = _.sprintf(fullNameTemplate, fullNameRemoteVars);

            if (information.releaseChannels && information.releaseChannels.current) {
                information.releaseChannels.current = ko.observable(
                    information.releaseChannels.current
                );
                information.releaseChannels.current.subscribe(function (selected) {
                    var patch = {};
                    patch[key] = {channel: selected};
                    OctoPrint.plugins.softwareupdate.configure(patch).done(function () {
                        self.performCheck(false, false, false, [key]);
                    });
                });
            }

            information.toggleDisabled = function () {
                var patch = {};
                patch[key] = {disabled: !information.disabled};
                OctoPrint.plugins.softwareupdate.configure(patch).done(function () {
                    self.performCheck(false, false, false, [key]);
                });
            };

            information.notificationIconTitle = function () {
                var update = information.updateAvailable
                    ? gettext("Update available")
                    : gettext("Up-to-date");
                var notifications = information.disabled
                    ? gettext("notifications are muted")
                    : gettext("notifications are enabled");

                return update + " (" + notifications + ")";
            };

            return information;
        };

        self.fromCheckResponse = function (data, ignoreSeen, showIfNothingNew) {
            self.cacheTimestamp(data.timestamp);

            var versions = [];
            _.each(data.information, function (value, key) {
                self._enrichInformation(key, value);
                versions.push(value);
            });
            self.versions.updateItems(versions);

            var octoprint = data.information["octoprint"];
            self.octoprintReleasedVersion(!octoprint || octoprint.releasedVersion);

            self.environmentSupported(data.environment.supported);
            self.environmentVersions(data.environment.versions);

            self.storageSufficient(data.storage.sufficient);
            self.storageFree(data.storage.free);

            if (data.status === "inProgress") {
                self._markWorking(
                    gettext("Updating..."),
                    gettext("Updating, please wait.")
                );
                return;
            }

            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_SOFTWAREUPDATE_UPDATE
                ) &&
                !self.settings.settings.plugins.softwareupdate.notify_users()
            )
                return;

            if (data.status === "updateAvailable" || data.status === "updatePossible") {
                var text =
                    "<div class='softwareupdate_notification'>" +
                    gettext("There are updates available for the following components:");

                text += "<ul class='fa-ul'>";
                _.each(self.versions.items(), function (update_info) {
                    if (
                        update_info.updateAvailable &&
                        !update_info.disabled &&
                        update_info.compatible
                    ) {
                        text +=
                            "<li>" +
                            "<i class='fa fa-li " +
                            (update_info.updatePossible &&
                            self.environmentSupported() &&
                            self.storageSufficient()
                                ? "fa-check"
                                : "fa-remove") +
                            "'></i>" +
                            "<span class='name' title='" +
                            update_info.fullNameRemote +
                            "'>" +
                            update_info.fullNameRemote +
                            "</span>" +
                            (update_info.releaseNotes
                                ? '<a href="' +
                                  update_info.releaseNotes +
                                  '" target="_blank">' +
                                  gettext("Release Notes") +
                                  "</a>"
                                : "") +
                            "</li>";
                    }
                });
                text += "</ul>";

                if (!self.environmentSupported()) {
                    text +=
                        "<p><small>" +
                        gettext(
                            "This version of the Python environment is not supported for direct updates."
                        ) +
                        "</small></p>";
                } else if (!self.storageSufficient()) {
                    text +=
                        "<p><small>" +
                        gettext(
                            "There's currently not enough free disk space available for a direct update."
                        ) +
                        "</small></p>";
                } else {
                    text +=
                        "<p><small>" +
                        gettext(
                            'Those components marked with <i class="fa fa-check"></i> can be updated directly.'
                        ) +
                        "</small></p>";
                }

                if (
                    !self.loginState.hasPermission(
                        self.access.permissions.PLUGIN_SOFTWAREUPDATE_UPDATE
                    )
                ) {
                    text +=
                        "<p><small>" +
                        gettext(
                            "To have updates applied, get in touch with an administrator of this OctoPrint instance."
                        ) +
                        "</small></p>";
                }

                text += "</div>";

                var options = {
                    title: gettext("Update Available"),
                    text: text,
                    hide: false
                };
                var eventListeners = {};

                var singleButtonNotify = false;
                if (
                    data.status === "updatePossible" &&
                    self.loginState.hasPermission(
                        self.access.permissions.PLUGIN_SOFTWAREUPDATE_UPDATE
                    )
                ) {
                    // if update is possible and user is admin, add action buttons for ignore and update
                    options["confirm"] = {
                        confirm: true,
                        buttons: [
                            {
                                text: gettext("Ignore"),
                                click: function () {
                                    self._markNotificationAsSeen(data.information);
                                    self._showPopup({
                                        text: gettext(
                                            'You can make this message display again via "Settings" > "Software Update" > "Check for update now"'
                                        )
                                    });
                                }
                            },
                            {
                                text: gettext("Update now"),
                                addClass: "btn-primary",
                                click: function () {
                                    if (self._updateClicked) return;
                                    self._updateClicked = true;
                                    self.updateEnabled();
                                }
                            }
                        ]
                    };
                    options["buttons"] = {
                        closer: false,
                        sticker: false
                    };
                } else {
                    // if update is not possible or user is not admin, only add ignore button
                    options["confirm"] = {
                        confirm: true,
                        buttons: [
                            {
                                text: gettext("Ignore"),
                                click: function (notice) {
                                    notice.remove();
                                    self._markNotificationAsSeen(data.information);
                                }
                            }
                        ]
                    };
                    options["buttons"] = {
                        closer: false,
                        sticker: false
                    };
                    singleButtonNotify = true;
                }

                if (
                    (ignoreSeen || !self._hasNotificationBeenSeen(data.information)) &&
                    !OctoPrint.coreui.wizardOpen
                ) {
                    self._showPopup(options, eventListeners, singleButtonNotify);
                }
            } else if (data.status === "current") {
                if (showIfNothingNew) {
                    self._showPopup({
                        title: gettext("Everything is up-to-date"),
                        type: "success"
                    });
                } else {
                    self._closePopup();
                }
            }
        };

        self.performCheck = function (showIfNothingNew, force, ignoreSeen, entries) {
            self.checking(true);
            OctoPrint.plugins.softwareupdate
                .check({entries: entries, force: force})
                .done(function (data) {
                    self.fromCheckResponse(data, ignoreSeen, showIfNothingNew);
                })
                .always(function () {
                    self.checking(false);
                });
        };

        self.fromUpdatelogResponse = function (response) {
            self.updatelog(response.updatelog);
        };

        self.requestUpdatelog = function () {
            OctoPrint.plugins.softwareupdate
                .getUpdatelog()
                .done(self.fromUpdatelogResponse);
        };

        self.iconTitleForEntry = function (data) {
            if (data.updatePossible) {
                return "";
            } else if (
                !data.online &&
                data.information &&
                data.information.needs_online
            ) {
                return gettext("No internet connection");
            } else if (data.error) {
                return self.errorTextForEntry(data);
            } else {
                return gettext("Update not possible");
            }
        };

        self.errorTextForEntry = function (data) {
            if (!data.error) {
                return "";
            }

            switch (data.error) {
                case "unknown_check": {
                    return gettext("Unknown update check, configuration ok?");
                }
                case "needs_online": {
                    return gettext("Cannot check for update, need online connection");
                }
                case "network": {
                    return gettext(
                        "Network error while checking for update, please check the logs"
                    );
                }
                case "api": {
                    return gettext(
                        "API error while checking for update, please check the logs"
                    );
                }
                case "ratelimit": {
                    return gettext(
                        "Rate limit exceeded while checking for update, please try again later"
                    );
                }
                case "check": {
                    return gettext(
                        "Check internal error while checking for update, please check the logs"
                    );
                }
                case "unknown": {
                    return gettext(
                        "Unknown error while checking for update, please check the logs"
                    );
                }
                default: {
                    return "";
                }
            }
        };

        self._markNotificationAsSeen = function (data) {
            if (!Modernizr.localstorage) return false;

            var currentString = localStorage["plugin.softwareupdate.seen_information"];
            var current;
            if (currentString === undefined) {
                current = {};
            } else {
                current = JSON.parse(currentString);
            }
            current[self.loginState.username()] = self._informationToRemoteVersions(data);
            localStorage["plugin.softwareupdate.seen_information"] =
                JSON.stringify(current);
        };

        self._hasNotificationBeenSeen = function (data) {
            if (!Modernizr.localstorage) return false;

            if (localStorage["plugin.softwareupdate.seen_information"] === undefined)
                return false;

            var knownData = JSON.parse(
                localStorage["plugin.softwareupdate.seen_information"]
            );

            var userData = knownData[self.loginState.username()];
            if (userData === undefined) return false;

            var freshData = self._informationToRemoteVersions(data);

            var hasBeenSeen = true;
            _.each(freshData, function (value, key) {
                if (!_.has(userData, key) || userData[key] !== freshData[key]) {
                    hasBeenSeen = false;
                }
            });
            return hasBeenSeen;
        };

        self._informationToRemoteVersions = function (data) {
            var result = {};
            _.each(data, function (value, key) {
                result[key] = value.information.remote.value;
            });
            return result;
        };

        self.performUpdate = function (force, items) {
            if (!self.updateAccess()) return;

            self.updateInProgress = true;

            var options = {
                title: gettext("Updating..."),
                text: gettext("Now updating, please wait."),
                icon: "fa fa-cog fa-spin",
                hide: false,
                buttons: {
                    closer: false,
                    sticker: false
                }
            };
            self._showPopup(options);

            OctoPrint.plugins.softwareupdate
                .update(items, force)
                .done(function (data) {
                    if (data.hasOwnProperty("queued")) {
                        self.queuedUpdates(data.queued);
                        var message =
                            "<p>" +
                            gettext(
                                "The install of the following plugin update(s) has been queued for after current print is finished or cancelled."
                            ) +
                            '</p><p><div class="row-fluid"><ul><li>' +
                            _.map(self.availableAndQueued(), function (info) {
                                return info.displayName;
                            }).join("</li><li>") +
                            "</li></ul></div></p>";
                        self._showPopup({
                            title: gettext("Updates Queued"),
                            text: message,
                            type: "info",
                            buttons: {
                                sticker: false
                            }
                        });
                        self.updateInProgress = false;
                        return;
                    }
                    self.currentlyBeingUpdated = data.checks;
                    self._markWorking(
                        gettext("Updating..."),
                        gettext("Updating, please wait.")
                    );
                })
                .fail(function (response) {
                    self.updateInProgress = false;
                    var message =
                        "<p>" +
                        gettext(
                            "The update could not be started. Is it already active? Please consult octoprint.log for details."
                        ) +
                        "</p><pre>" +
                        _.escape(response.responseJSON.error) +
                        "</pre>";

                    self._showPopup({
                        title: gettext("Update not started!"),
                        text: message,
                        type: "error",
                        hide: false,
                        buttons: {
                            sticker: false
                        }
                    });
                });
        };

        self.updateAll = function (force) {
            return self.update(force, self.availableAndPossible());
        };

        self.updateEnabled = function (force) {
            return self.update(force, self.availableAndPossibleAndEnabled());
        };

        self.updateAccess = function () {
            return (
                self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_SOFTWAREUPDATE_UPDATE
                ) || CONFIG_FIRST_RUN
            );
        };

        self.update = function (force, items) {
            if (self.updateInProgress || !self.updateAccess()) {
                self._updateClicked = false;
                return;
            }

            if (items === undefined) {
                items = self.availableAndPossibleAndEnabled();
            }

            if (self.throttled()) {
                self._showPopup({
                    title: gettext("Can't update while throttled"),
                    text: gettext(
                        "Your system is currently throttled. OctoPrint refuses to run updates while in this state due to possible stability issues."
                    ),
                    type: "error"
                });
                self._updateClicked = false;
                return;
            }

            var html =
                "<p>" +
                gettext(
                    "This will update the following components and restart the server:"
                ) +
                "</p>";
            html += "<ul>";
            _.each(items, function (item) {
                html +=
                    "<li>" +
                    '<span class="name" title="' +
                    item.fullNameRemote +
                    '">' +
                    item.fullNameRemote +
                    "</span>";
                if (item.releaseNotes) {
                    html +=
                        '<br><a href="' +
                        item.releaseNotes +
                        '" target="_blank" rel="noreferrer noopener">' +
                        gettext("Release Notes") +
                        "</a>";
                }
                html += "</li>";
            });
            html += "</ul>";
            html +=
                "<p>" +
                gettext(
                    "Be sure to read through any linked release notes, especially those for OctoPrint since they might contain important information you need to know <strong>before</strong> upgrading."
                ) +
                "</p>" +
                "<p>" +
                gettext("Updates will be queued if currently printing,") +
                " <strong>" +
                gettext(
                    "however this action may disrupt any ongoing print if OctoPrint is not currently controlling it."
                ) +
                "</strong>" +
                "</p>" +
                "<p>" +
                gettext("Are you sure you want to proceed?") +
                "</p>";
            showConfirmationDialog({
                title: gettext("Are you sure you want to update now?"),
                html: html,
                proceed: gettext("Proceed"),
                onproceed: function () {
                    self.performUpdate(
                        force === true,
                        _.map(items, function (info) {
                            return info.key;
                        })
                    );
                },
                onclose: function () {
                    self._updateClicked = false;
                }
            });
        };

        self._showWorkingDialog = function (title) {
            if (
                !(
                    self.loginState.hasPermission(
                        self.access.permissions.PLUGIN_SOFTWAREUPDATE_CHECK
                    ) || CONFIG_FIRST_RUN
                )
            ) {
                return;
            }

            self.working(true);
            self.workingTitle(title);
            self.workingDialog.modal({keyboard: false, backdrop: "static", show: true});
        };

        self._markWorking = function (title, line, stream) {
            if (stream === undefined) {
                stream = "message";
            }

            self.loglines.removeAll();
            self.loglines.push({line: line, stream: stream});
            self._showWorkingDialog(title);
        };

        self._markDone = function (line, stream) {
            if (stream === undefined) {
                stream = "message";
            }

            self.working(false);
            self.loglines.push({line: "", stream: stream});
            self.loglines.push({line: line, stream: stream});
            self._scrollWorkingOutputToEnd();
        };

        self._scrollWorkingOutputToEnd = function () {
            self.workingOutput.scrollTop(
                self.workingOutput[0].scrollHeight - self.workingOutput.height()
            );
        };

        self.onBeforeWizardTabChange = function (next, current) {
            if (next && next === "#wizard_plugin_softwareupdate") {
                // switching to the plugin wizard tab
                self._copyConfig();
            } else if (current && current === "#wizard_plugin_softwareupdate") {
                // switching away from the plugin wizard tab
                self._copyConfigBack();
            }

            return true;
        };

        self.onAfterWizardFinish = function () {
            // we might have changed our config, so we need to refresh our check data from the server
            self.performCheck();
        };

        self.onStartup = function () {
            self.workingDialog = $("#settings_plugin_softwareupdate_workingdialog");
            self.workingOutput = $(
                "#settings_plugin_softwareupdate_workingdialog_output"
            );
            self.configurationDialog = $(
                "#settings_plugin_softwareupdate_configurationdialog"
            );
        };

        self.onServerDisconnect = function () {
            if (self.restartTimeout !== undefined) {
                clearTimeout(self.restartTimeout);
            }
            return true;
        };

        self.onEventConnectivityChanged = function (payload) {
            if (!payload || !payload.new) return;
            self.performCheck();
        };

        self.onWizardDetails = function (data) {
            if (
                data.softwareupdate &&
                data.softwareupdate.details &&
                data.softwareupdate.details.update
            ) {
                var value = data.softwareupdate.details.update;
                self._enrichInformation("octoprint", value);

                self.octoprintData.item = value;
                self.octoprintData.current(value.information.local.name);
                self.octoprintData.available(value.information.remote.name);
            }
        };

        self.onDataUpdaterReconnect = function () {
            if (self.waitingForRestart) {
                self.waitingForRestart = false;
                self.updateInProgress = false;
                if (!self.reloadOverlay.is(":visible")) {
                    self.reloadOverlay.show();
                }
            }
        };

        self.cancelQueued = function (items) {
            self.cancelInProgress = true;
            OctoPrint.plugins.softwareupdate
                .cancelQueued({
                    targets: _.map(items, function (info) {
                        return info.key;
                    })
                })
                .done(function (data) {
                    self.queuedUpdates(data.queued);
                    self.cancelInProgress = false;
                })
                .fail(function (response) {
                    console.log(response);
                    self.cancelInProgress = false;
                });
        };

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin !== "softwareupdate") {
                return;
            }

            var messageType = data.type;
            var messageData = data.data;

            var options = undefined;

            var restartType = undefined;
            var title = undefined;
            var text = undefined;

            switch (messageType) {
                // make sure we are marked as working if we get any of the in-progress messages
                case "loglines":
                case "updating":
                case "restarting":
                case "restart_manually":
                case "restart_failed":
                case "success":
                case "error": {
                    if (!self.working()) {
                        self._markWorking(
                            gettext("Updating..."),
                            gettext("Updating, please wait.")
                        );
                    }
                    break;
                }
            }

            switch (messageType) {
                case "loglines": {
                    _.each(messageData.loglines, function (line) {
                        self.loglines.push(self._preprocessLine(line));
                    });
                    self._scrollWorkingOutputToEnd();
                    break;
                }
                case "updating": {
                    text = _.sprintf(gettext("Now updating %(name)s to %(version)s"), {
                        name: _.escape(messageData.name),
                        version: _.escape(messageData.version)
                    });
                    self.loglines.push({line: "", stream: "separator"});
                    self.loglines.push({
                        line: _.repeat("+", text.length),
                        stream: "separator"
                    });
                    self.loglines.push({line: text, stream: "message"});
                    self.loglines.push({
                        line: _.repeat("+", text.length),
                        stream: "separator"
                    });
                    self._scrollWorkingOutputToEnd();
                    self._updatePopup({
                        text: text,
                        hide: false,
                        buttons: {
                            sticker: false
                        }
                    });

                    break;
                }
                case "restarting": {
                    title = gettext("Update successful, restarting!");
                    text = gettext(
                        "The update finished successfully and the server will now be restarted."
                    );

                    options = {
                        title: title,
                        text: text,
                        type: "success",
                        hide: false,
                        buttons: {
                            sticker: false
                        }
                    };

                    self.loglines.push({line: text, stream: "message"});
                    self._scrollWorkingOutputToEnd();

                    self.waitingForRestart = true;
                    self.restartTimeout = setTimeout(function () {
                        title = gettext("Restart failed");
                        text = gettext(
                            "The server apparently did not restart by itself, you'll have to do it manually. Please consult octoprint.log on what went wrong."
                        );

                        self._showPopup({
                            title: title,
                            text: text,
                            type: "error",
                            hide: false,
                            buttons: {
                                sticker: false
                            }
                        });
                        self.waitingForRestart = false;

                        self._markDone(text, "message_error");
                    }, 60000);

                    break;
                }
                case "restart_manually": {
                    restartType = messageData.restart_type;
                    text = gettext(
                        "The update finished successfully, please restart OctoPrint now."
                    );
                    if (restartType === "environment") {
                        text = gettext(
                            "The update finished successfully, please reboot the server now."
                        );
                    }

                    title = gettext("Update successful, restart required!");
                    options = {
                        title: title,
                        text: text,
                        type: "success",
                        hide: false,
                        buttons: {
                            sticker: false
                        }
                    };
                    self.updateInProgress = false;
                    self._markDone(text);
                    break;
                }
                case "restart_failed": {
                    restartType = messageData.restart_type;
                    text = gettext(
                        "Restarting OctoPrint failed, please restart it manually. You might also want to consult octoprint.log on what went wrong here."
                    );
                    if (restartType === "environment") {
                        text = gettext(
                            "Rebooting the server failed, please reboot it manually. You might also want to consult octoprint.log on what went wrong here."
                        );
                    }

                    title = gettext("Restart failed");
                    options = {
                        title: title,
                        test: text,
                        type: "error",
                        hide: false,
                        buttons: {
                            sticker: false
                        }
                    };
                    self.waitingForRestart = false;
                    self.updateInProgress = false;
                    self._markDone(text, "message_error");
                    break;
                }
                case "success": {
                    title = gettext("Update successful!");
                    text = gettext("The update finished successfully.");
                    options = {
                        title: title,
                        text: text,
                        type: "success",
                        hide: false,
                        buttons: {
                            sticker: false
                        }
                    };
                    self.updateInProgress = false;
                    self._markDone(text);
                    break;
                }
                case "error": {
                    title = gettext("Update failed!");
                    text = gettext(
                        "The update did not finish successfully. Please consult <code>octoprint.log</code> and <code>plugin_softwareupdate_console.log</code> for details."
                    );
                    self._showPopup({
                        title: title,
                        text: text,
                        type: "error",
                        hide: false,
                        buttons: {
                            sticker: false
                        }
                    });
                    self.updateInProgress = false;
                    self._markDone(text, "message_error");
                    break;
                }
                case "update_versions": {
                    self.performCheck();
                    break;
                }
                case "queued_updates":
                    {
                        if (!self.updateAccess()) {
                            return;
                        }
                        if (messageData.hasOwnProperty("targets")) {
                            self.queuedUpdates(messageData.targets);
                            var queuedUpdatesPopupOptions = {
                                title: title,
                                text: text,
                                type: "notice",
                                icon: false,
                                hide: false,
                                buttons: {
                                    closer: false,
                                    sticker: false
                                },
                                history: {
                                    history: false
                                }
                            };

                            if (
                                messageData.print_failed &&
                                messageData.targets.length > 0
                            ) {
                                queuedUpdatesPopupOptions.title = gettext(
                                    "Queued Updates Paused"
                                );
                                queuedUpdatesPopupOptions.text =
                                    '<div class="row-fluid"><ul><li>' +
                                    _.map(self.availableAndQueued(), function (info) {
                                        return info.displayName;
                                    }).join("</li><li>") +
                                    "</li></ul></div>";
                                queuedUpdatesPopupOptions.confirm = {
                                    confirm: true,
                                    buttons: [
                                        {
                                            text: gettext("Continue Updates"),
                                            addClass: "btn-block btn-primary",
                                            promptTrigger: true,
                                            click: function (notice, value) {
                                                notice.remove();
                                                notice
                                                    .get()
                                                    .trigger("pnotify.continue", [
                                                        notice,
                                                        value
                                                    ]);
                                            }
                                        },
                                        {
                                            text: gettext("Cancel Updates"),
                                            addClass: "btn-block btn-danger",
                                            promptTrigger: true,
                                            click: function (notice, value) {
                                                notice.remove();
                                                notice
                                                    .get()
                                                    .trigger("pnotify.cancel", [
                                                        notice,
                                                        value
                                                    ]);
                                            }
                                        }
                                    ]
                                };
                            } else if (
                                messageData.hasOwnProperty("timeout_value") &&
                                messageData.timeout_value > 0 &&
                                messageData.targets.length > 0
                            ) {
                                var progress_percent = Math.floor(
                                    (messageData.timeout_value / 60) * 100
                                );
                                var progress_class =
                                    progress_percent < 25
                                        ? "progress-danger"
                                        : progress_percent > 75
                                        ? "progress-success"
                                        : "progress-warning";
                                var countdownText = _.sprintf(
                                    gettext("Updating in %(sec)i secs..."),
                                    {
                                        sec: messageData.timeout_value
                                    }
                                );

                                queuedUpdatesPopupOptions.title = gettext(
                                    "Starting Queued Updates"
                                );
                                queuedUpdatesPopupOptions.text =
                                    '<div class="row-fluid"><p></p><ul><li>' +
                                    _.map(self.availableAndQueued(), function (info) {
                                        return info.displayName;
                                    }).join("</li><li>") +
                                    '</li></ul></p></div><div class="progress progress-softwareupdate ' +
                                    progress_class +
                                    '"><div class="bar">' +
                                    countdownText +
                                    '</div><div class="progress-text" style="clip-path: inset(0 0 0 ' +
                                    progress_percent +
                                    "%);-webkit-clip-path: inset(0 0 0 " +
                                    progress_percent +
                                    '%);">' +
                                    countdownText +
                                    "</div></div>";
                                queuedUpdatesPopupOptions.confirm = {
                                    confirm: true,
                                    buttons: [
                                        {
                                            text: gettext("Cancel Updates"),
                                            addClass: "btn-block btn-danger",
                                            promptTrigger: true,
                                            click: function (notice, value) {
                                                notice.remove();
                                                notice
                                                    .get()
                                                    .trigger("pnotify.cancel", [
                                                        notice,
                                                        value
                                                    ]);
                                            }
                                        },
                                        {
                                            text: "",
                                            addClass: "hidden"
                                        }
                                    ]
                                };
                            } else {
                                if (typeof self.queuedUpdatesPopup !== "undefined") {
                                    self.queuedUpdatesPopup.remove();
                                    self.queuedUpdatesPopup = undefined;
                                }
                                return;
                            }

                            if (typeof self.queuedUpdatesPopup !== "undefined") {
                                self.queuedUpdatesPopup.update(queuedUpdatesPopupOptions);
                            } else {
                                self.queuedUpdatesPopup = new PNotify(
                                    queuedUpdatesPopupOptions
                                );
                                self.queuedUpdatesPopup
                                    .get()
                                    .on("pnotify.cancel", function () {
                                        self.queuedUpdatesPopup = undefined;
                                        self.cancelQueued();
                                    });
                                self.queuedUpdatesPopup
                                    .get()
                                    .on("pnotify.continue", function () {
                                        self.queuedUpdatesPopup = undefined;
                                        self.performUpdate(true, self.queuedUpdates());
                                        self._updateClicked = false;
                                    });
                            }
                        } else {
                            if (typeof self.queuedUpdatesPopup !== "undefined") {
                                self.queuedUpdatesPopup.remove();
                                self.queuedUpdatesPopup = undefined;
                            }
                        }
                    }

                    if (options !== undefined) {
                        self._showPopup(options);
                    }
            }
            self._forcedStdoutPatterns = [
                "You are using pip version .*?, however version .*? is available.",
                "You should consider upgrading via the '.*?' command.",
                "'.*?' does not exist -- can't clean it"
            ];
            self._forcedStdoutLine = new RegExp(self._forcedStdoutPatterns.join("|"));
            self._preprocessLine = function (line) {
                if (line.stream === "stderr" && line.line.match(self._forcedStdoutLine)) {
                    line.stream = "stdout";
                }
                return line;
            };
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: SoftwareUpdateViewModel,
        dependencies: [
            "loginStateViewModel",
            "printerStateViewModel",
            "settingsViewModel",
            "accessViewModel",
            "piSupportViewModel"
        ],
        optional: ["piSupportViewModel"],
        elements: [
            "#settings_plugin_softwareupdate",
            "#softwareupdate_confirmation_dialog",
            "#wizard_plugin_softwareupdate_update",
            "#wizard_plugin_softwareupdate_settings"
        ]
    });
});
