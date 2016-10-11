(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint"], factory);
    } else {
        factory(window.OctoPrint);
    }
})(window || this, function(OctoPrint) {
    var exports = {};

    exports.get = function(refresh, opts) {
        return OctoPrint.get(OctoPrint.getSimpleApiUrl("pluginmanager") + ((refresh) ? "?refresh_repository=true" : ""), opts);
    };

    exports.getWithRefresh = function(opts) {
        return exports.get(true, opts);
    };

    exports.getWithoutRefresh = function(opts) {
        return exports.get(false, opts);
    };

    exports.install = function(pluginUrl, dependencyLinks, opts) {
        var data = {
            url: pluginUrl,
            dependency_links: !!dependencyLinks
        };
        return OctoPrint.simpleApiCommand("pluginmanager", "install", data, opts);
    };

    exports.reinstall = function(plugin, pluginUrl, dependencyLinks, opts) {
        var data = {
            url: pluginUrl,
            dependency_links: !!dependencyLinks,
            reinstall: plugin,
            force: true
        };
        return OctoPrint.simpleApiCommand("pluginmanager", "install", data, opts);
    };

    exports.uninstall = function(plugin, opts) {
        var data = {
            plugin: plugin
        };
        return OctoPrint.simpleApiCommand("pluginmanager", "uninstall", data, opts);
    };

    exports.enable = function(plugin, opts) {
        var data = {
            plugin: plugin
        };
        return OctoPrint.simpleApiCommand("pluginmanager", "enable", data, opts);
    };

    exports.disable = function(plugin, opts) {
        var data = {
            plugin: plugin
        };
        return OctoPrint.simpleApiCommand("pluginmanager", "disable", data, opts);
    };

    exports.upload = function(file) {
        return OctoPrint.upload(OctoPrint.getBlueprintUrl("pluginmanager") + "upload_archive", file);
    };

    OctoPrint.plugins.pluginmanager = exports;
});

$(function() {
    function PluginManagerViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settingsViewModel = parameters[1];
        self.printerState = parameters[2];
        self.systemViewModel = parameters[3];

        self.config_repositoryUrl = ko.observable();
        self.config_repositoryTtl = ko.observable();
        self.config_pipAdditionalArgs = ko.observable();
        self.config_pipForceUser = ko.observable();

        self.configurationDialog = $("#settings_plugin_pluginmanager_configurationdialog");

        self.plugins = new ItemListHelper(
            "plugin.pluginmanager.installedplugins",
            {
                "name": function (a, b) {
                    // sorts ascending
                    if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase()) return -1;
                    if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase()) return 1;
                    return 0;
                }
            },
            {
            },
            "name",
            [],
            [],
            5
        );

        self.repositoryplugins = new ItemListHelper(
            "plugin.pluginmanager.repositoryplugins",
            {
                "title": function (a, b) {
                    // sorts ascending
                    if (a["title"].toLocaleLowerCase() < b["title"].toLocaleLowerCase()) return -1;
                    if (a["title"].toLocaleLowerCase() > b["title"].toLocaleLowerCase()) return 1;
                    return 0;
                },
                "published": function (a, b) {
                    // sorts descending
                    if (a["published"].toLocaleLowerCase() > b["published"].toLocaleLowerCase()) return -1;
                    if (a["published"].toLocaleLowerCase() < b["published"].toLocaleLowerCase()) return 1;
                    return 0;
                }
            },
            {
                "filter_installed": function(plugin) {
                    return !self.installed(plugin);
                },
                "filter_incompatible": function(plugin) {
                    return plugin.is_compatible.octoprint && plugin.is_compatible.os;
                }
            },
            "title",
            ["filter_installed", "filter_incompatible"],
            [],
            0
        );

        self.uploadElement = $("#settings_plugin_pluginmanager_repositorydialog_upload");
        self.uploadButton = $("#settings_plugin_pluginmanager_repositorydialog_upload_start");

        self.repositoryAvailable = ko.observable(false);

        self.repositorySearchQuery = ko.observable();
        self.repositorySearchQuery.subscribe(function() {
            self.performRepositorySearch();
        });

        self.installUrl = ko.observable();
        self.uploadFilename = ko.observable();

        self.loglines = ko.observableArray([]);
        self.installedPlugins = ko.observableArray([]);

        self.followDependencyLinks = ko.observable(false);

        self.pipAvailable = ko.observable(false);
        self.pipVersion = ko.observable();
        self.pipInstallDir = ko.observable();
        self.pipUseUser = ko.observable();
        self.pipVirtualEnv = ko.observable();
        self.pipAdditionalArgs = ko.observable();
        self.pipPython = ko.observable();

        self.pipUseUserString = ko.pureComputed(function() {
            return self.pipUseUser() ? "yes" : "no";
        });
        self.pipVirtualEnvString = ko.pureComputed(function() {
            return self.pipVirtualEnv() ? "yes" : "no";
        });

        self.working = ko.observable(false);
        self.workingTitle = ko.observable();
        self.workingDialog = undefined;
        self.workingOutput = undefined;

        self.restartCommandSpec = undefined;
        self.systemViewModel.systemActions.subscribe(function() {
            var lastResponse = self.systemViewModel.lastCommandResponse;
            if (!lastResponse || !lastResponse.core) {
                self.restartCommandSpec = undefined;
                return;
            }

            var restartSpec = _.filter(lastResponse.core, function(spec) { return spec.action == "restart" });
            self.restartCommandSpec = restartSpec != undefined && restartSpec.length > 0 ? restartSpec[0] : undefined;
        });

        self.notifications = [];

        self.enableManagement = ko.pureComputed(function() {
            return !self.printerState.isPrinting();
        });

        self.enableToggle = function(data) {
            return self.enableManagement() && data.key != 'pluginmanager';
        };

        self.enableUninstall = function(data) {
            return self.enableManagement()
                && (data.origin != "entry_point" || self.pipAvailable())
                && data.managable
                && !data.bundled
                && data.key != 'pluginmanager'
                && !data.pending_uninstall;
        };

        self.enableRepoInstall = function(data) {
            return self.enableManagement() && self.pipAvailable() && self.isCompatible(data);
        };

        self.invalidUrl = ko.pureComputed(function() {
            var url = self.installUrl();
            return url !== undefined && url.trim() != "" && !(_.startsWith(url.toLocaleLowerCase(), "http://") || _.startsWith(url.toLocaleLowerCase(), "https://"));
        });

        self.enableUrlInstall = ko.pureComputed(function() {
            var url = self.installUrl();
            return self.enableManagement() && self.pipAvailable() && url !== undefined && url.trim() != "" && !self.invalidUrl();
        });

        self.invalidArchive = ko.pureComputed(function() {
            var name = self.uploadFilename();
            return name !== undefined && !(_.endsWith(name.toLocaleLowerCase(), ".zip") || _.endsWith(name.toLocaleLowerCase(), ".tar.gz") || _.endsWith(name.toLocaleLowerCase(), ".tgz") || _.endsWith(name.toLocaleLowerCase(), ".tar"));
        });

        self.enableArchiveInstall = ko.pureComputed(function() {
            var name = self.uploadFilename();
            return self.enableManagement() && self.pipAvailable() && name !== undefined && name.trim() != "" && !self.invalidArchive();
        });

        self.uploadElement.fileupload({
            dataType: "json",
            maxNumberOfFiles: 1,
            autoUpload: false,
            add: function(e, data) {
                if (data.files.length == 0) {
                    return false;
                }

                self.uploadFilename(data.files[0].name);

                self.uploadButton.unbind("click");
                self.uploadButton.bind("click", function() {
                    self._markWorking(gettext("Installing plugin..."), gettext("Installing plugin from uploaded archive..."));
                    data.formData = {
                        dependency_links: self.followDependencyLinks()
                    };
                    data.submit();
                    return false;
                });
            },
            done: function(e, data) {
                self._markDone();
                self.uploadButton.unbind("click");
                self.uploadFilename("");
            },
            fail: function(e, data) {
                new PNotify({
                    title: gettext("Something went wrong"),
                    text: gettext("Please consult octoprint.log for details"),
                    type: "error",
                    hide: false
                });
                self._markDone();
                self.uploadButton.unbind("click");
                self.uploadFilename("");
            }
        });

        self.performRepositorySearch = function() {
            var query = self.repositorySearchQuery();
            if (query !== undefined && query.trim() != "") {
                query = query.toLocaleLowerCase();
                self.repositoryplugins.changeSearchFunction(function(entry) {
                    return entry && (entry["title"].toLocaleLowerCase().indexOf(query) > -1 || entry["description"].toLocaleLowerCase().indexOf(query) > -1);
                });
            } else {
                self.repositoryplugins.resetSearch();
            }
            return false;
        };

        self.fromResponse = function(data) {
            self._fromPluginsResponse(data.plugins);
            self._fromRepositoryResponse(data.repository);
            self._fromPipResponse(data.pip);
        };

        self._fromPluginsResponse = function(data) {
            var installedPlugins = [];
            _.each(data, function(plugin) {
                installedPlugins.push(plugin.key);
            });
            self.installedPlugins(installedPlugins);
            self.plugins.updateItems(data);
        };

        self._fromRepositoryResponse = function(data) {
            self.repositoryAvailable(data.available);
            if (data.available) {
                self.repositoryplugins.updateItems(data.plugins);
            } else {
                self.repositoryplugins.updateItems([]);
            }
        };

        self._fromPipResponse = function(data) {
            self.pipAvailable(data.available);
            if (data.available) {
                self.pipVersion(data.version);
                self.pipInstallDir(data.install_dir);
                self.pipUseUser(data.use_user);
                self.pipVirtualEnv(data.virtual_env);
                self.pipAdditionalArgs(data.additional_args);
                self.pipPython(data.python);
            } else {
                self.pipVersion(undefined);
                self.pipInstallDir(undefined);
                self.pipUseUser(undefined);
                self.pipVirtualEnv(undefined);
                self.pipAdditionalArgs(undefined);
            }
        };

        self.requestData = function(includeRepo) {
            if (!self.loginState.isAdmin()) {
                return;
            }

            OctoPrint.plugins.pluginmanager.get(includeRepo)
                .done(self.fromResponse);
        };

        self.togglePlugin = function(data) {
            if (!self.loginState.isAdmin()) {
                return;
            }

            if (!self.enableManagement()) {
                return;
            }

            if (data.key == "pluginmanager") return;

            var onSuccess = self.requestData,
                onError = function() {
                    new PNotify({
                        title: gettext("Something went wrong"),
                        text: gettext("Please consult octoprint.log for details"),
                        type: "error",
                        hide: false
                    })
                };

            if (self._getToggleCommand(data) == "enable") {
                OctoPrint.plugins.pluginmanager.enable(data.key)
                    .done(onSuccess)
                    .fail(onError);
            } else {
                OctoPrint.plugins.pluginmanager.disable(data.key)
                    .done(onSuccess)
                    .fail(onError);
            }
        };

        self.showRepository = function() {
            self.repositoryDialog.modal("show");
        };

        self.pluginDetails = function(data) {
            window.open(data.page);
        };

        self.installFromRepository = function(data) {
            if (!self.loginState.isAdmin()) {
                return;
            }

            if (!self.enableManagement()) {
                return;
            }

            self.installPlugin(data.archive, data.title, (self.installed(data) ? data.id : undefined), data.follow_dependency_links || self.followDependencyLinks());
        };

        self.installPlugin = function(url, name, reinstall, followDependencyLinks) {
            if (!self.loginState.isAdmin()) {
                return;
            }

            if (!self.enableManagement()) {
                return;
            }

            if (url === undefined) {
                url = self.installUrl();
            }
            if (!url) return;

            if (followDependencyLinks === undefined) {
                followDependencyLinks = self.followDependencyLinks();
            }

            var workTitle, workText;
            if (!reinstall) {
                workTitle = gettext("Installing plugin...");
                if (name) {
                    workText = _.sprintf(gettext("Installing plugin \"%(name)s\" from %(url)s..."), {url: url, name: name});
                } else {
                    workText = _.sprintf(gettext("Installing plugin from %(url)s..."), {url: url});
                }
            } else {
                workTitle = gettext("Reinstalling plugin...");
                workText = _.sprintf(gettext("Reinstalling plugin \"%(name)s\" from %(url)s..."), {url: url, name: name});
            }
            self._markWorking(workTitle, workText);

            var onSuccess = function() {
                    self.requestData();
                    self.installUrl("");
                },
                onError = function() {
                    new PNotify({
                        title: gettext("Something went wrong"),
                        text: gettext("Please consult octoprint.log for details"),
                        type: "error",
                        hide: false
                    });
                },
                onAlways = function() {
                    self._markDone();
                };

            if (reinstall) {
                OctoPrint.plugins.pluginmanager.reinstall(reinstall, url, followDependencyLinks)
                    .done(onSuccess)
                    .fail(onError)
                    .always(onAlways);
            } else {
                OctoPrint.plugins.pluginmanager.install(url, followDependencyLinks)
                    .done(onSuccess)
                    .fail(onError)
                    .always(onAlways);
            }
        };

        self.uninstallPlugin = function(data) {
            if (!self.loginState.isAdmin()) {
                return;
            }

            if (!self.enableManagement()) {
                return;
            }

            if (data.bundled) return;
            if (data.key == "pluginmanager") return;

            self._markWorking(gettext("Uninstalling plugin..."), _.sprintf(gettext("Uninstalling plugin \"%(name)s\""), {name: data.name}));

            OctoPrint.plugins.pluginmanager.uninstall(data.key)
                .done(self.requestData)
                .fail(function() {
                    new PNotify({
                        title: gettext("Something went wrong"),
                        text: gettext("Please consult octoprint.log for details"),
                        type: "error",
                        hide: false
                    });
                })
                .always(function() {
                    self._markDone();
                });
        };

        self.refreshRepository = function() {
            if (!self.loginState.isAdmin()) {
                return;
            }

            self.requestData(true);
        };

        self.showPluginSettings = function() {
            self._copyConfig();
            self.configurationDialog.modal();
        };

        self.savePluginSettings = function() {
            var repository = self.config_repositoryUrl();
            if (repository != undefined && repository.trim() == "") {
                repository = null;
            }

            var repositoryTtl;
            try {
                repositoryTtl = parseInt(self.config_repositoryTtl());
            } catch (ex) {
                repositoryTtl = null;
            }

            var pipArgs = self.config_pipAdditionalArgs();
            if (pipArgs != undefined && pipArgs.trim() == "") {
                pipArgs = null;
            }

            var data = {
                plugins: {
                    pluginmanager: {
                        repository: repository,
                        repository_ttl: repositoryTtl,
                        pip_args: pipArgs,
                        pip_force_user: self.config_pipForceUser()
                    }
                }
            };
            self.settingsViewModel.saveData(data, function() {
                self.configurationDialog.modal("hide");
                self._copyConfig();
                self.refreshRepository();
            });
        };

        self._copyConfig = function() {
            self.config_repositoryUrl(self.settingsViewModel.settings.plugins.pluginmanager.repository());
            self.config_repositoryTtl(self.settingsViewModel.settings.plugins.pluginmanager.repository_ttl());
            self.config_pipAdditionalArgs(self.settingsViewModel.settings.plugins.pluginmanager.pip_args());
            self.config_pipForceUser(self.settingsViewModel.settings.plugins.pluginmanager.pip_force_user());
        };

        self.installed = function(data) {
            return _.includes(self.installedPlugins(), data.id);
        };

        self.isCompatible = function(data) {
            return data.is_compatible.octoprint && data.is_compatible.os;
        };

        self.installButtonText = function(data) {
            return self.isCompatible(data) ? (self.installed(data) ? gettext("Reinstall") : gettext("Install")) : gettext("Incompatible");
        };

        self._displayNotification = function(response, titleSuccess, textSuccess, textRestart, textReload, titleError, textError) {
            var notification;

            var beforeClose = function(notification) {
                self.notifications = _.without(self.notifications, notification);
            };

            if (response.result) {
                if (response.needs_restart) {
                    var options = {
                        title: titleSuccess,
                        text: textRestart,
                        buttons: {
                            closer: false,
                            sticker: false
                        },
                        callbacks: {
                            before_close: beforeClose
                        },
                        hide: false
                    };

                    if (self.restartCommandSpec) {
                        options.confirm = {
                            confirm: true,
                            buttons: [{
                                text: gettext("Restart now"),
                                click: function () {
                                    showConfirmationDialog({
                                        message: gettext("This will restart your OctoPrint server."),
                                        onproceed: function() {
                                            OctoPrint.system.executeCommand("core", "restart")
                                                .done(function() {
                                                    new PNotify({
                                                        title: gettext("Restart in progress"),
                                                        text: gettext("The server is now being restarted in the background")
                                                    })
                                                })
                                                .fail(function() {
                                                    new PNotify({
                                                        title: gettext("Something went wrong"),
                                                        text: gettext("Trying to restart the server produced an error, please check octoprint.log for details. You'll have to restart manually.")
                                                    })
                                                });
                                        }
                                    });
                                }
                            }]
                        }
                    }

                    notification = PNotify.singleButtonNotify(options);
                } else if (response.needs_refresh) {
                    notification = PNotify.singleButtonNotify({
                        title: titleSuccess,
                        text: textReload,
                        confirm: {
                            confirm: true,
                            buttons: [{
                                text: gettext("Reload now"),
                                click: function () {
                                    location.reload(true);
                                }
                            }]
                        },
                        buttons: {
                            closer: false,
                            sticker: false
                        },
                        callbacks: {
                            before_close: beforeClose
                        },
                        hide: false
                    })
                } else {
                    notification = new PNotify({
                        title: titleSuccess,
                        text: textSuccess,
                        type: "success",
                        callbacks: {
                            before_close: beforeClose
                        },
                        hide: false
                    })
                }
            } else {
                notification = new PNotify({
                    title: titleError,
                    text: textError,
                    type: "error",
                    callbacks: {
                        before_close: beforeClose
                    },
                    hide: false
                });
            }

            self.notifications.push(notification);
        };

        self._markWorking = function(title, line) {
            self.working(true);
            self.workingTitle(title);

            self.loglines.removeAll();
            self.loglines.push({line: line, stream: "message"});

            self.workingDialog.modal("show");
        };

        self._markDone = function() {
            self.working(false);
            self.loglines.push({line: gettext("Done!"), stream: "message"});
            self._scrollWorkingOutputToEnd();
        };

        self._scrollWorkingOutputToEnd = function() {
            self.workingOutput.scrollTop(self.workingOutput[0].scrollHeight - self.workingOutput.height());
        };

        self._getToggleCommand = function(data) {
            return ((!data.enabled || data.pending_disable) && !data.pending_enable) ? "enable" : "disable";
        };

        self.toggleButtonCss = function(data) {
            var icon = self._getToggleCommand(data) == "enable" ? "icon-circle-blank" : "icon-circle";
            var disabled = (self.enableToggle(data)) ? "" : " disabled";

            return icon + disabled;
        };

        self.toggleButtonTitle = function(data) {
            return self._getToggleCommand(data) == "enable" ? gettext("Enable Plugin") : gettext("Disable Plugin");
        };

        self.onBeforeBinding = function() {
            self.settings = self.settingsViewModel.settings;
        };

        self.onUserLoggedIn = function(user) {
            if (user.admin) {
                self.requestData();
            } else {
                self.onUserLoggedOut();
            }
        };

        self.onUserLoggedOut = function() {
            if (self.notifications) {
                _.each(self.notifications, function(notification) {
                    notification.remove();
                });
            }
        };

        self.onStartup = function() {
            self.workingDialog = $("#settings_plugin_pluginmanager_workingdialog");
            self.workingOutput = $("#settings_plugin_pluginmanager_workingdialog_output");
            self.repositoryDialog = $("#settings_plugin_pluginmanager_repositorydialog");

            $("#settings_plugin_pluginmanager_repositorydialog_list").slimScroll({
                height: "306px",
                size: "5px",
                distance: "0",
                railVisible: true,
                alwaysVisible: true,
                scrollBy: "102px"
            });
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin != "pluginmanager") {
                return;
            }

            if (!self.loginState.isAdmin()) {
                return;
            }

            if (!data.hasOwnProperty("type")) {
                return;
            }

            var messageType = data.type;

            if (messageType == "loglines" && self.working()) {
                _.each(data.loglines, function(line) {
                    self.loglines.push(line);
                });
                self._scrollWorkingOutputToEnd();
            } else if (messageType == "result") {
                var titleSuccess, textSuccess, textRestart, textReload, titleError, textError;
                var action = data.action;

                var name = "Unknown";
                if (action == "install") {
                    var unknown = false;

                    if (data.hasOwnProperty("plugin")) {
                        if (data.plugin == "unknown") {
                            unknown = true;
                        } else {
                            name = data.plugin.name;
                        }
                    }

                    if (unknown) {
                        titleSuccess = _.sprintf(gettext("Plugin installed"));
                        textSuccess = gettext("A plugin was installed successfully, however it was impossible to detect which one. Please Restart OctoPrint to make sure everything will be registered properly");
                        textRestart = textSuccess;
                        textReload = textSuccess;
                    } else if (data.was_reinstalled) {
                        titleSuccess = _.sprintf(gettext("Plugin \"%(name)s\" reinstalled"), {name: name});
                        textSuccess = gettext("The plugin was reinstalled successfully");
                        textRestart = gettext("The plugin was reinstalled successfully, however a restart of OctoPrint is needed for that to take effect.");
                        textReload = gettext("The plugin was reinstalled successfully, however a reload of the page is needed for that to take effect.");
                    } else {
                        titleSuccess = _.sprintf(gettext("Plugin \"%(name)s\" installed"), {name: name});
                        textSuccess = gettext("The plugin was installed successfully");
                        textRestart = gettext("The plugin was installed successfully, however a restart of OctoPrint is needed for that to take effect.");
                        textReload = gettext("The plugin was installed successfully, however a reload of the page is needed for that to take effect.");
                    }

                    titleError = gettext("Something went wrong");
                    var url = "unknown";
                    if (data.hasOwnProperty("url")) {
                        url = data.url;
                    }

                    if (data.hasOwnProperty("reason")) {
                        if (data.was_reinstalled) {
                            textError = _.sprintf(gettext("Reinstalling the plugin from URL \"%(url)s\" failed: %(reason)s"), {reason: data.reason, url: url});
                        } else {
                            textError = _.sprintf(gettext("Installing the plugin from URL \"%(url)s\" failed: %(reason)s"), {reason: data.reason, url: url});
                        }
                    } else {
                        if (data.was_reinstalled) {
                            textError = _.sprintf(gettext("Reinstalling the plugin from URL \"%(url)s\" failed, please see the log for details."), {url: url});
                        } else {
                            textError = _.sprintf(gettext("Installing the plugin from URL \"%(url)s\" failed, please see the log for details."), {url: url});
                        }
                    }

                } else if (action == "uninstall") {
                    if (data.hasOwnProperty("plugin")) {
                        name = data.plugin.name;
                    }

                    titleSuccess = _.sprintf(gettext("Plugin \"%(name)s\" uninstalled"), {name: name});
                    textSuccess = gettext("The plugin was uninstalled successfully");
                    textRestart = gettext("The plugin was uninstalled successfully, however a restart of OctoPrint is needed for that to take effect.");
                    textReload = gettext("The plugin was uninstalled successfully, however a reload of the page is needed for that to take effect.");

                    titleError = gettext("Something went wrong");
                    if (data.hasOwnProperty("reason")) {
                        textError = _.sprintf(gettext("Uninstalling the plugin failed: %(reason)s"), {reason: data.reason});
                    } else {
                        textError = gettext("Uninstalling the plugin failed, please see the log for details.");
                    }

                } else if (action == "enable") {
                    if (data.hasOwnProperty("plugin")) {
                        name = data.plugin.name;
                    }

                    titleSuccess = _.sprintf(gettext("Plugin \"%(name)s\" enabled"), {name: name});
                    textSuccess = gettext("The plugin was enabled successfully.");
                    textRestart = gettext("The plugin was enabled successfully, however a restart of OctoPrint is needed for that to take effect.");
                    textReload = gettext("The plugin was enabled successfully, however a reload of the page is needed for that to take effect.");

                    titleError = gettext("Something went wrong");
                    if (data.hasOwnProperty("reason")) {
                        textError = _.sprintf(gettext("Toggling the plugin failed: %(reason)s"), {reason: data.reason});
                    } else {
                        textError = gettext("Toggling the plugin failed, please see the log for details.");
                    }

                } else if (action == "disable") {
                    if (data.hasOwnProperty("plugin")) {
                        name = data.plugin.name;
                    }

                    titleSuccess = _.sprintf(gettext("Plugin \"%(name)s\" disabled"), {name: name});
                    textSuccess = gettext("The plugin was disabled successfully.");
                    textRestart = gettext("The plugin was disabled successfully, however a restart of OctoPrint is needed for that to take effect.");
                    textReload = gettext("The plugin was disabled successfully, however a reload of the page is needed for that to take effect.");

                    titleError = gettext("Something went wrong");
                    if (data.hasOwnProperty("reason")) {
                        textError = _.sprintf(gettext("Toggling the plugin failed: %(reason)s"), {reason: data.reason});
                    } else {
                        textError = gettext("Toggling the plugin failed, please see the log for details.");
                    }

                } else {
                    return;
                }

                self._displayNotification(data, titleSuccess, textSuccess, textRestart, textReload, titleError, textError);
                self.requestData();
            }
        };
    }

    // view model class, parameters for constructor, container to bind to
    ADDITIONAL_VIEWMODELS.push([
        PluginManagerViewModel,
        ["loginStateViewModel", "settingsViewModel", "printerStateViewModel", "systemViewModel"],
        "#settings_plugin_pluginmanager"
    ]);
});
