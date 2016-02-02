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

        self.octoprintUnconfigured = ko.observable();
        self.octoprintUnreleased = ko.observable();

        self.config_cacheTtl = ko.observable();
        self.config_checkoutFolder = ko.observable();
        self.config_checkType = ko.observable();

        self.configurationDialog = $("#settings_plugin_softwareupdate_configurationdialog");
        self.confirmationDialog = $("#softwareupdate_confirmation_dialog");

        self.config_availableCheckTypes = [
            {"key": "github_release", "name": gettext("Release")},
            {"key": "git_commit", "name": gettext("Commit")}
        ];

        self.reloadOverlay = $("#reloadui_overlay");

        self.versions = new ItemListHelper(
            "plugin.softwareupdate.versions",
            {
                "name": function(a, b) {
                    // sorts ascending, puts octoprint first
                    if (a.key.toLocaleLowerCase() == "octoprint") return -1;
                    if (b.key.toLocaleLowerCase() == "octoprint") return 1;

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

        self.availableAndPossible = ko.computed(function() {
            return _.filter(self.versions.items(), function(info) { return info.updateAvailable && info.updatePossible; });
        });

        self.onUserLoggedIn = function() {
            self.performCheck();
        };

        self._showPopup = function(options, eventListeners) {
            self._closePopup();
            self.popup = new PNotify(options);

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

        self.savePluginSettings = function() {
            var data = {
                plugins: {
                    softwareupdate: {
                        cache_ttl: parseInt(self.config_cacheTtl()),
                        octoprint_checkout_folder: self.config_checkoutFolder(),
                        octoprint_type: self.config_checkType()
                    }
                }
            };
            self.settings.saveData(data, function() {
                self.configurationDialog.modal("hide");
                self._copyConfig();
                self.performCheck();
            });
        };

        self._copyConfig = function() {
            self.config_cacheTtl(self.settings.settings.plugins.softwareupdate.cache_ttl());
            self.config_checkoutFolder(self.settings.settings.plugins.softwareupdate.octoprint_checkout_folder());
            self.config_checkType(self.settings.settings.plugins.softwareupdate.octoprint_type());
        };

        self.fromCheckResponse = function(data, ignoreSeen, showIfNothingNew) {
            var versions = [];
            _.each(data.information, function(value, key) {
                value["key"] = key;

                if (!value.hasOwnProperty("displayName") || value.displayName == "") {
                    value.displayName = value.key;
                }
                if (!value.hasOwnProperty("displayVersion") || value.displayVersion == "") {
                    value.displayVersion = value.information.local.name;
                }
                if (!value.hasOwnProperty("releaseNotes") || value.releaseNotes == "") {
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
            if (octoprint && octoprint.hasOwnProperty("check")) {
                var check = octoprint.check;
                if (BRANCH != "master" && check["type"] == "github_release") {
                    self.octoprintUnreleased(true);
                } else {
                    self.octoprintUnreleased(false);
                }

                var checkoutFolder = (check["checkout_folder"] || "").trim();
                var updateFolder = (check["update_folder"] || "").trim();
                var checkType = check["type"] || "";
                if ((checkType == "github_release" || checkType == "git_commit") && checkoutFolder == "" && updateFolder == "") {
                    self.octoprintUnconfigured(true);
                } else {
                    self.octoprintUnconfigured(false);
                }
            }

            if (data.status == "updateAvailable" || data.status == "updatePossible") {
                var text = "<div class='softwareupdate_notification'>" + gettext("There are updates available for the following components:");

                text += "<ul class='icons-ul'>";
                _.each(self.versions.items(), function(update_info) {
                    if (update_info.updateAvailable) {
                        text += "<li>"
                            + "<i class='icon-li " + (update_info.updatePossible ? "icon-ok" : "icon-remove")+ "'></i>"
                            + "<span class='name' title='" + update_info.fullNameRemote + "'>" + update_info.fullNameRemote + "</span>"
                            + (update_info.releaseNotes ? "<a href=\"" +  update_info.releaseNotes + "\" target=\"_blank\">" + gettext("Release Notes") + "</a>" : "")
                            + "</li>";
                    }
                });
                text += "</ul>";

                text += "<small>" + gettext("Those components marked with <i class=\"icon-ok\"></i> can be updated directly.") + "</small>";

                text += "</div>";

                var options = {
                    title: gettext("Update Available"),
                    text: text,
                    hide: false
                };
                var eventListeners = {};

                if (data.status == "updatePossible" && self.loginState.isAdmin()) {
                    // if user is admin, add action buttons
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
                            click: self.update
                        }]
                    };
                    options["buttons"] = {
                        closer: false,
                        sticker: false
                    };
                }

                if (ignoreSeen || !self._hasNotificationBeenSeen(data.information)) {
                    self._showPopup(options, eventListeners);
                }
            } else if (data.status == "current") {
                if (showIfNothingNew) {
                    self._showPopup({
                        title: gettext("Everything is up-to-date"),
                        hide: false,
                        type: "success"
                    });
                } else {
                    self._closePopup();
                }
            }
        };

        self.performCheck = function(showIfNothingNew, force, ignoreSeen) {
            if (!self.loginState.isUser()) return;

            var url = PLUGIN_BASEURL + "softwareupdate/check";
            if (force) {
                url += "?force=true";
            }

            $.ajax({
                url: url,
                type: "GET",
                dataType: "json",
                success: function(data) {
                    self.fromCheckResponse(data, ignoreSeen, showIfNothingNew);
                }
            });
        };

        self._markNotificationAsSeen = function(data) {
            if (!Modernizr.localstorage)
                return false;
            localStorage["plugin.softwareupdate.seen_information"] = JSON.stringify(self._informationToRemoteVersions(data));
        };

        self._hasNotificationBeenSeen = function(data) {
            if (!Modernizr.localstorage)
                return false;

            if (localStorage["plugin.softwareupdate.seen_information"] == undefined)
                return false;

            var knownData = JSON.parse(localStorage["plugin.softwareupdate.seen_information"]);
            var freshData = self._informationToRemoteVersions(data);

            var hasBeenSeen = true;
            _.each(freshData, function(value, key) {
                if (!_.has(knownData, key) || knownData[key] != freshData[key]) {
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
            self.updateInProgress = true;

            var options = {
                title: gettext("Updating..."),
                text: gettext("Now updating, please wait."),
                icon: "icon-cog icon-spin",
                hide: false,
                buttons: {
                    closer: false,
                    sticker: false
                }
            };
            self._showPopup(options);

            var postData = {
                force: (force == true)
            };
            if (items != undefined) {
                postData.check = items;
            }

            $.ajax({
                url: PLUGIN_BASEURL + "softwareupdate/update",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify(postData),
                error: function() {
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
                },
                success: function(data) {
                    self.currentlyBeingUpdated = data.checks;
                }
            });
        };

        self.update = function(force) {
            if (self.updateInProgress) return;
            if (!self.loginState.isAdmin()) return;

            if (self.printerState.isPrinting()) {
                self._showPopup({
                    title: gettext("Can't update while printing"),
                    text: gettext("A print job is currently in progress. Updating will be prevented until it is done."),
                    type: "error"
                });
            } else {
                self.forceUpdate = (force == true);
                self.confirmationDialog.modal("show");
            }

        };

        self.confirmUpdate = function() {
            self.confirmationDialog.hide();
            self.performUpdate(self.forceUpdate,
                               _.map(self.availableAndPossible(), function(info) { return info.key }));
        };

        self.onServerDisconnect = function() {
            if (self.restartTimeout !== undefined) {
                clearTimeout(self.restartTimeout);
            }
            return true;
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
            if (plugin != "softwareupdate") {
                return;
            }

            var messageType = data.type;
            var messageData = data.data;

            var options = undefined;

            switch (messageType) {
                case "updating": {
                    console.log(JSON.stringify(messageData));

                    var name = self.currentlyBeingUpdated[messageData.target];
                    if (name == undefined) {
                        name = messageData.target;
                    }

                    self._updatePopup({
                        text: _.sprintf(gettext("Now updating %(name)s to %(version)s"), {name: name, version: messageData.version})
                    });
                    break;
                }
                case "restarting": {
                    console.log(JSON.stringify(messageData));

                    options = {
                        title: gettext("Update successful, restarting!"),
                        text: gettext("The update finished successfully and the server will now be restarted."),
                        type: "success",
                        hide: false,
                        buttons: {
                            sticker: false
                        }
                    };

                    self.waitingForRestart = true;
                    self.restartTimeout = setTimeout(function() {
                        self._showPopup({
                            title: gettext("Restart failed"),
                            text: gettext("The server apparently did not restart by itself, you'll have to do it manually. Please consult the log file on what went wrong."),
                            type: "error",
                            hide: false,
                            buttons: {
                                sticker: false
                            }
                        });
                        self.waitingForRestart = false;
                    }, 60000);

                    break;
                }
                case "restart_manually": {
                    console.log(JSON.stringify(messageData));

                    var restartType = messageData.restart_type;
                    var text = gettext("The update finished successfully, please restart OctoPrint now.");
                    if (restartType == "environment") {
                        text = gettext("The update finished successfully, please reboot the server now.");
                    }

                    options = {
                        title: gettext("Update successful, restart required!"),
                        text: text,
                        type: "success",
                        hide: false,
                        buttons: {
                            sticker: false
                        }
                    };
                    self.updateInProgress = false;
                    break;
                }
                case "restart_failed": {
                    var restartType = messageData.restart_type;
                    var text = gettext("Restarting OctoPrint failed, please restart it manually. You might also want to consult the log file on what went wrong here.");
                    if (restartType == "environment") {
                        text = gettext("Rebooting the server failed, please reboot it manually. You might also want to consult the log file on what went wrong here.");
                    }

                    options = {
                        title: gettext("Restart failed"),
                        test: gettext("The server apparently did not restart by itself, you'll have to do it manually. Please consult the log file on what went wrong."),
                        type: "error",
                        hide: false,
                        buttons: {
                            sticker: false
                        }
                    };
                    self.waitingForRestart = false;
                    self.updateInProgress = false;
                    break;
                }
                case "success": {
                    options = {
                        title: gettext("Update successful!"),
                        text: gettext("The update finished successfully."),
                        type: "success",
                        hide: false,
                        buttons: {
                            sticker: false
                        }
                    };
                    self.updateInProgress = false;
                    break;
                }
                case "error": {
                    self._showPopup({
                        title: gettext("Update failed!"),
                        text: gettext("The update did not finish successfully. Please consult the log for details."),
                        type: "error",
                        hide: false,
                        buttons: {
                            sticker: false
                        }
                    });
                    self.updateInProgress = false;
                    break;
                }
                case "update_versions": {
                    self.performCheck();
                    break;
                }
            }

            if (options != undefined) {
                self._showPopup(options);
            }
        };

    }

    // view model class, parameters for constructor, container to bind to
    ADDITIONAL_VIEWMODELS.push([
        SoftwareUpdateViewModel,
        ["loginStateViewModel", "printerStateViewModel", "settingsViewModel"],
        ["#settings_plugin_softwareupdate", "#softwareupdate_confirmation_dialog"]
    ]);
});
