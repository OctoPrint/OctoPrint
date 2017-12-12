(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var OctoPrintSoftwareUpdateClient = function(base) {
        this.base = base;

        var url = this.base.getBlueprintUrl("softwareupdate");
        this.checkUrl = url + "check";
        this.updateUrl = url + "update";
    };

    OctoPrintSoftwareUpdateClient.prototype.checkEntries = function(entries, force, opts) {
        if (arguments.length == 1 && _.isObject(arguments[0])) {
            var params = arguments[0];
            entries = params.entries;
            force = params.force;
            opts = params.opts;
        }

        entries = entries || [];
        if (typeof entries == "string") {
            entries = [entries];
        }

        var data = {};
        if (!!force) {
            data.force = true;
        }
        if (entries && entries.length) {
            data.check = entries.join(",");
        }
        return this.base.getWithQuery(this.checkUrl, data, opts);
    };

    OctoPrintSoftwareUpdateClient.prototype.check = function(force, opts) {
        if (arguments.length == 1 && _.isObject(arguments[0])) {
            var params = arguments[0];
            force = params.force;
            opts = params.opts;
        }

        return this.checkEntries({entries: [], force: force, opts: opts});
    };

    OctoPrintSoftwareUpdateClient.prototype.update = function(entries, force, opts) {
        if (arguments.length == 1 && _.isObject(arguments[0])) {
            var params = arguments[0];
            entries = params.entries;
            force = params.force;
            opts = params.opts;
        }

        entries = entries || [];
        if (typeof entries == "string") {
            entries = [entries];
        }

        var data = {
            entries: entries,
            force: !!force
        };
        return this.base.postJson(this.updateUrl, data, opts);
    };

    OctoPrintSoftwareUpdateClient.prototype.updateAll = function(force, opts) {
        if (arguments.length == 1 && _.isObject(arguments[0])) {
            var params = arguments[0];
            force = params.force;
            opts = params.opts;
        }

        var data = {
            force: !!force
        };
        return this.base.postJson(this.updateUrl, data, opts);
    };

    OctoPrintClient.registerPluginComponent("softwareupdate", OctoPrintSoftwareUpdateClient);
    return OctoPrintSoftwareUpdateClient;
});

$(function() {
    function SoftwareUpdateViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.printerState = parameters[1];
        self.settings = parameters[2];
        self.popup = undefined;

        self.forceUpdate = false;

        self.updateInProgress = false;
        self.waitingForRestart = false;
        self.restartTimeout = undefined;

        self.currentlyBeingUpdated = [];

        self.working = ko.observable(false);
        self.workingTitle = ko.observable();
        self.workingDialog = undefined;
        self.workingOutput = undefined;
        self.loglines = ko.observableArray([]);

        self.checking = ko.observable(false);

        self.octoprintReleasedVersion = ko.observable();

        self.octoprintUnconfigured = ko.pureComputed(function() {
            return self.error_checkoutFolder();
        });
        self.octoprintUnreleased = ko.pureComputed(function() {
            return self.settings.settings.plugins.softwareupdate.octoprint_type() === "github_release"
                && !self.octoprintReleasedVersion();
        });

        self.cacheTimestamp = ko.observable();
        self.cacheTimestampText = ko.pureComputed(function() {
            return formatDate(self.cacheTimestamp());
        });

        self.config_cacheTtl = ko.observable();
        self.config_notifyUsers = ko.observable();
        self.config_checkoutFolder = ko.observable();
        self.config_checkType = ko.observable();
        self.config_releaseChannel = ko.observable();

        self.error_checkoutFolder = ko.pureComputed(function() {
            return self.config_checkType() === "git_commit"
                && (!self.config_checkoutFolder() || self.config_checkoutFolder().trim() === '');
        });

        self.enable_configSave = ko.pureComputed(function() {
            return self.config_checkType() === "github_release"
                || (self.config_checkType() === "git_commit" && !self.error_checkoutFolder());
        });

        self.configurationDialog = undefined;
        self.confirmationDialog = undefined;
        self._updateClicked = false;

        self.config_availableCheckTypes = ko.observableArray([]);
        self.config_availableReleaseChannels = ko.observableArray([]);

        self.reloadOverlay = $("#reloadui_overlay");

        self.versions = new ItemListHelper(
            "plugin.softwareupdate.versions",
            {
                "name": function(a, b) {
                    // sorts ascending, puts octoprint first
                    if (a.key.toLocaleLowerCase() === "octoprint") return -1;
                    if (b.key.toLocaleLowerCase() === "octoprint") return 1;

                    if (a.displayName.toLocaleLowerCase() < b.displayName.toLocaleLowerCase()) return -1;
                    if (a.displayName.toLocaleLowerCase() > b.displayName.toLocaleLowerCase()) return 1;
                    return 0;
                }
            },
            {},
            "name",
            [],
            [],
            5
        );

        self.availableAndPossible = ko.pureComputed(function() {
            return _.filter(self.versions.items(), function(info) { return info.updateAvailable && info.updatePossible; });
        });

        self.onUserLoggedIn = function() {
            self.performCheck();
        };

        self.onUserLoggedOut = function() {
            self._closePopup();
        };

        self._showPopup = function(options, eventListeners, singleButtonNotify) {
            singleButtonNotify = singleButtonNotify || false;

            self._closePopup();

            if (singleButtonNotify) {
                self.popup = PNotify.singleButtonNotify(options);
            } else {
                self.popup = new PNotify(options);
            }

            if (eventListeners) {
                var popupObj = self.popup.get();
                _.each(eventListeners, function(value, key) {
                    popupObj.on(key, value);
                })
            }
        };

        self._updatePopup = function(options) {
            if (self.popup === undefined) {
                self._showPopup(options);
            } else {
                self.popup.update(options);
            }
        };

        self._closePopup = function() {
            if (self.popup !== undefined) {
                self.popup.remove();
            }
        };

        self.showPluginSettings = function() {
            self._copyConfig();
            self.configurationDialog.modal();
        };

        self.savePluginSettings = function(viewModel, event) {
            var target = $(event.target);
            target.prepend('<i class="fa fa-spinner fa-spin"></i> ');

            var data = {
                plugins: {
                    softwareupdate: {
                        cache_ttl: parseInt(self.config_cacheTtl()),
                        notify_users: self.config_notifyUsers(),
                        octoprint_type: self.config_checkType(),
                        octoprint_release_channel: self.config_releaseChannel(),
                        octoprint_checkout_folder: self.config_checkoutFolder()
                    }
                }
            };
            self.settings.saveData(data, {
                success: function() {
                    self.configurationDialog.modal("hide");
                    self._copyConfig();
                    self.performCheck();
                },
                complete: function() {
                    $("i.fa-spinner", target).remove();
                },
                sending: true
            });
        };

        self._copyConfig = function() {
            var availableCheckTypes = [{"key": "github_release", "name": gettext("Release")},
                                       {"key": "git_commit", "name": gettext("Commit")}];
            self.config_availableCheckTypes(availableCheckTypes);

            var availableReleaseChannels = [];
            _.each(self.settings.settings.plugins.softwareupdate.octoprint_branch_mappings(), function(mapping) {
                availableReleaseChannels.push({"key": mapping.branch(), "name": gettext(mapping.name() || mapping.branch())});
            });
            self.config_availableReleaseChannels(availableReleaseChannels);

            self.config_cacheTtl(self.settings.settings.plugins.softwareupdate.cache_ttl());
            self.config_notifyUsers(self.settings.settings.plugins.softwareupdate.notify_users());

            self.config_checkType(self.settings.settings.plugins.softwareupdate.octoprint_type());
            self.config_releaseChannel(self.settings.settings.plugins.softwareupdate.octoprint_release_channel());
            self.config_checkoutFolder(self.settings.settings.plugins.softwareupdate.octoprint_checkout_folder());
        };

        self._copyConfigBack = function() {
            self.settings.settings.plugins.softwareupdate.octoprint_checkout_folder(self.config_checkoutFolder());
            self.settings.settings.plugins.softwareupdate.octoprint_type(self.config_checkType());
        };

        self.fromCheckResponse = function(data, ignoreSeen, showIfNothingNew) {
            self.cacheTimestamp(data.timestamp);

            var versions = [];
            _.each(data.information, function(value, key) {
                value["key"] = key;

                if (!value.hasOwnProperty("displayName") || value.displayName === "") {
                    value.displayName = value.key;
                }
                if (!value.hasOwnProperty("displayVersion") || value.displayVersion === "") {
                    value.displayVersion = value.information.local.name;
                }
                if (!value.hasOwnProperty("releaseNotes") || value.releaseNotes === "") {
                    value.releaseNotes = undefined;
                }

                var fullNameTemplate = gettext("%(name)s: %(version)s");
                value.fullNameLocal = _.sprintf(fullNameTemplate, {name: value.displayName, version: value.displayVersion});

                var fullNameRemoteVars = {name: value.displayName, version: gettext("unknown")};
                if (value.hasOwnProperty("information") && value.information.hasOwnProperty("remote") && value.information.remote.hasOwnProperty("name")) {
                    fullNameRemoteVars.version = value.information.remote.name;
                }
                value.fullNameRemote = _.sprintf(fullNameTemplate, fullNameRemoteVars);

                versions.push(value);
            });
            self.versions.updateItems(versions);

            var octoprint = data.information["octoprint"];
            self.octoprintReleasedVersion(!octoprint || octoprint.released_version);

            if (!self.loginState.isAdmin() && !self.settings.settings.plugins.softwareupdate.notify_users()) return;

            if (data.status === "updateAvailable" || data.status === "updatePossible") {
                var text = "<div class='softwareupdate_notification'>" + gettext("There are updates available for the following components:");

                text += "<ul class='fa-ul'>";
                _.each(self.versions.items(), function(update_info) {
                    if (update_info.updateAvailable) {
                        text += "<li>"
                            + "<i class='fa fa-li " + (update_info.updatePossible ? "fa-check" : "fa-remove")+ "'></i>"
                            + "<span class='name' title='" + update_info.fullNameRemote + "'>" + update_info.fullNameRemote + "</span>"
                            + (update_info.releaseNotes ? "<a href=\"" +  update_info.releaseNotes + "\" target=\"_blank\">" + gettext("Release Notes") + "</a>" : "")
                            + "</li>";
                    }
                });
                text += "</ul>";

                text += "<p><small>" + gettext("Those components marked with <i class=\"fa fa-check\"></i> can be updated directly.") + "</small></p>";

                if (!self.loginState.isAdmin()) {
                    text += "<p><small>" + gettext("To have updates applied, get in touch with an administrator of this OctoPrint instance.") + "</small></p>";
                }

                text += "</div>";

                var options = {
                    title: gettext("Update Available"),
                    text: text,
                    hide: false
                };
                var eventListeners = {};

                var singleButtonNotify = false;
                if (data.status === "updatePossible" && self.loginState.isAdmin()) {
                    // if update is possible and user is admin, add action buttons for ignore and update
                    options["confirm"] = {
                        confirm: true,
                        buttons: [{
                            text: gettext("Ignore"),
                            click: function() {
                                self._markNotificationAsSeen(data.information);
                                self._showPopup({
                                    text: gettext("You can make this message display again via \"Settings\" > \"Software Update\" > \"Check for update now\"")
                                });
                            }
                        }, {
                            text: gettext("Update now"),
                            addClass: "btn-primary",
                            click: function() {
                                if (self._updateClicked) return;
                                self._updateClicked = true;
                                self.update();
                            }
                        }]
                    };
                    options["buttons"] = {
                        closer: false,
                        sticker: false
                    };
                } else {
                    // if update is not possible or user is not admin, only add ignore button
                    options["confirm"] = {
                        confirm: true,
                        buttons: [{
                            text: gettext("Ignore"),
                            click: function(notice) {
                                notice.remove();
                                self._markNotificationAsSeen(data.information);
                            }
                        }]
                    };
                    options["buttons"] = {
                        closer: false,
                        sticker: false
                    };
                    singleButtonNotify = true;
                }

                if ((ignoreSeen || !self._hasNotificationBeenSeen(data.information)) && !OctoPrint.coreui.wizardOpen) {
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

        self.performCheck = function(showIfNothingNew, force, ignoreSeen) {
            if (!self.loginState.isAdmin() && !self.settings.settings.plugins.softwareupdate.notify_users()) return;

            self.checking(true);
            OctoPrint.plugins.softwareupdate.check(force)
                .done(function(data) {
                    self.fromCheckResponse(data, ignoreSeen, showIfNothingNew);
                })
                .always(function() {
                    self.checking(false);
                });
        };

        self.iconTitleForEntry = function(data) {
            if (data.updatePossible) {
                return "";
            } else if (!data.online && data.information && data.information.needs_online) {
                return gettext("No internet connection");
            } else if (data.error) {
                return self.errorTextForEntry(data);
            } else {
                return gettext("Update not possible");
            }
        };

        self.errorTextForEntry = function(data) {
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
                    return gettext("Network error while checking for update");
                }
                case "unknown": {
                    return gettext("Unknown error while checking for update, please check the logs");
                }
                default: {
                    return "";
                }
            }
        };

        self._markNotificationAsSeen = function(data) {
            if (!Modernizr.localstorage)
                return false;
            if (!self.loginState.isUser())
                return false;

            var currentString = localStorage["plugin.softwareupdate.seen_information"];
            var current;
            if (currentString === undefined) {
                current = {};
            } else {
                current = JSON.parse(currentString);
            }
            current[self.loginState.username()] = self._informationToRemoteVersions(data);
            localStorage["plugin.softwareupdate.seen_information"] = JSON.stringify(current);
        };

        self._hasNotificationBeenSeen = function(data) {
            if (!Modernizr.localstorage)
                return false;

            if (localStorage["plugin.softwareupdate.seen_information"] === undefined)
                return false;

            var knownData = JSON.parse(localStorage["plugin.softwareupdate.seen_information"]);

            if (!self.loginState.isUser())
                return true;

            var userData = knownData[self.loginState.username()];
            if (userData === undefined)
                return false;

            var freshData = self._informationToRemoteVersions(data);

            var hasBeenSeen = true;
            _.each(freshData, function(value, key) {
                if (!_.has(userData, key) || userData[key] !== freshData[key]) {
                    hasBeenSeen = false;
                }
            });
            return hasBeenSeen;
        };

        self._informationToRemoteVersions = function(data) {
            var result = {};
            _.each(data, function(value, key) {
                result[key] = value.information.remote.value;
            });
            return result;
        };

        self.performUpdate = function(force, items) {
            if (!self.loginState.isAdmin()) return;

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

            OctoPrint.plugins.softwareupdate.updateAll(force, items)
                .done(function(data) {
                    self.currentlyBeingUpdated = data.checks;
                    self._markWorking(gettext("Updating..."), gettext("Updating, please wait."));
                })
                .fail(function() {
                    self.updateInProgress = false;
                    self._showPopup({
                        title: gettext("Update not started!"),
                        text: gettext("The update could not be started. Is it already active? Please consult the log for details."),
                        type: "error",
                        hide: false,
                        buttons: {
                            sticker: false
                        }
                    });
                });
        };

        self.update = function(force) {
            if (self.updateInProgress) {
                self._updateClicked = false;
                return;
            }
            if (!self.loginState.isAdmin()) {
                self._updateClicked = false;
                return;
            }

            if (self.printerState.isPrinting()) {
                self._showPopup({
                    title: gettext("Can't update while printing"),
                    text: gettext("A print job is currently in progress. Updating will be prevented until it is done."),
                    type: "error"
                });
                self._updateClicked = false;
            } else {
                self.forceUpdate = (force == true);
                self.confirmationDialog.modal("show");
            }

        };

        self.confirmUpdate = function() {
            self.performUpdate(self.forceUpdate,
                _.map(self.availableAndPossible(), function(info) { return info.key }));
            self.confirmationDialog.modal("hide");
        };

        self.confirmationHidden = function() {
            self._updateClicked = false;
        };

        self._showWorkingDialog = function(title) {
            if (!self.loginState.isAdmin()) {
                return;
            }

            self.working(true);
            self.workingTitle(title);
            self.workingDialog.modal({keyboard: false, backdrop: "static", show: true});
        };

        self._markWorking = function(title, line, stream) {
            if (stream === undefined) {
                stream = "message";
            }

            self.loglines.removeAll();
            self.loglines.push({line: line, stream: stream});
            self._showWorkingDialog(title);
        };

        self._markDone = function(line, stream) {
            if (stream === undefined) {
                stream = "message";
            }

            self.working(false);
            self.loglines.push({line: "", stream: stream});
            self.loglines.push({line: line, stream: stream});
            self._scrollWorkingOutputToEnd();
        };

        self._scrollWorkingOutputToEnd = function() {
            self.workingOutput.scrollTop(self.workingOutput[0].scrollHeight - self.workingOutput.height());
        };

        self.onBeforeWizardTabChange = function(next, current) {
            if (next && next === "#wizard_plugin_softwareupdate") {
                // switching to the plugin wizard tab
                self._copyConfig();
            } else if (current && current === "#wizard_plugin_softwareupdate") {
                // switching away from the plugin wizard tab
                self._copyConfigBack();
            }

            return true;
        };

        self.onAfterWizardFinish = function() {
            // we might have changed our config, so we need to refresh our check data from the server
            self.performCheck();
        };

        self.onStartup = function() {
            self.workingDialog = $("#settings_plugin_softwareupdate_workingdialog");
            self.workingOutput = $("#settings_plugin_softwareupdate_workingdialog_output");
            self.configurationDialog = $("#settings_plugin_softwareupdate_configurationdialog");
            self.confirmationDialog = $("#softwareupdate_confirmation_dialog");

            self.confirmationDialog.on("hidden", self.confirmationHidden);
        };

        self.onServerDisconnect = function() {
            if (self.restartTimeout !== undefined) {
                clearTimeout(self.restartTimeout);
            }
            return true;
        };

        self.onEventConnectivityChanged = function(payload) {
            if (!payload || !payload.new) return;
            self.performCheck();
        };

        self.onDataUpdaterReconnect = function() {
            if (self.waitingForRestart) {
                self.waitingForRestart = false;
                self.updateInProgress = false;
                if (!self.reloadOverlay.is(":visible")) {
                    self.reloadOverlay.show();
                }
            }
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
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
                case "loglines": {
                    if (self.working()) {
                        _.each(messageData.loglines, function(line) {
                            self.loglines.push(self._preprocessLine(line));
                        });
                        self._scrollWorkingOutputToEnd();
                    }
                    break;
                }
                case "updating": {
                    console.log(JSON.stringify(messageData));

                    if (!self.working()) {
                        self._markWorking(gettext("Updating..."), gettext("Updating, please wait."));
                    }

                    text = _.sprintf(gettext("Now updating %(name)s to %(version)s"), {name: messageData.name, version: messageData.version});
                    self.loglines.push({line: "", stream: "separator"});
                    self.loglines.push({line: _.repeat("+", text.length), stream: "separator"});
                    self.loglines.push({line: text, stream: "message"});
                    self.loglines.push({line: _.repeat("+", text.length), stream: "separator"});
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
                    console.log(JSON.stringify(messageData));

                    title = gettext("Update successful, restarting!");
                    text = gettext("The update finished successfully and the server will now be restarted.");

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
                    self.restartTimeout = setTimeout(function() {
                        title = gettext("Restart failed");
                        text = gettext("The server apparently did not restart by itself, you'll have to do it manually. Please consult the log file on what went wrong.");

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
                    console.log(JSON.stringify(messageData));

                    restartType = messageData.restart_type;
                    text = gettext("The update finished successfully, please restart OctoPrint now.");
                    if (restartType === "environment") {
                        text = gettext("The update finished successfully, please reboot the server now.");
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
                    text = gettext("Restarting OctoPrint failed, please restart it manually. You might also want to consult the log file on what went wrong here.");
                    if (restartType === "environment") {
                        text = gettext("Rebooting the server failed, please reboot it manually. You might also want to consult the log file on what went wrong here.");
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
                    text = gettext("The update did not finish successfully. Please consult the log for details.");
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
            }

            if (options !== undefined) {
                self._showPopup(options);
            }
        };

        self._forcedStdoutPatterns = ["You are using pip version .*?, however version .*? is available\.",
                                      "You should consider upgrading via the '.*?' command\.",
                                      "'.*?' does not exist -- can't clean it"];
        self._forcedStdoutLine = new RegExp(self._forcedStdoutPatterns.join("|"));
        self._preprocessLine = function(line) {
            if (line.stream === "stderr" && line.line.match(self._forcedStdoutLine)) {
                line.stream = "stdout";
            }
            return line;
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: SoftwareUpdateViewModel,
        dependencies: ["loginStateViewModel", "printerStateViewModel", "settingsViewModel"],
        elements: ["#settings_plugin_softwareupdate", "#softwareupdate_confirmation_dialog", "#wizard_plugin_softwareupdate"]
    });
});
