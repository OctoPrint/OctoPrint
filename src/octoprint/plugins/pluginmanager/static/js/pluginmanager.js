(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var OctoPrintPluginManagerClient = function(base) {
        this.base = base;
    };

    OctoPrintPluginManagerClient.prototype.get = function(refresh, opts) {
        var refresh_repo, refresh_notices;
        if (_.isPlainObject(refresh)) {
            refresh_repo = refresh.repo || false;
            refresh_notices = refresh.notices || false;
        } else {
            refresh_repo = refresh;
            refresh_notices = false;
        }

        var query = [];
        if (refresh_repo) query.push("refresh_repository=true");
        if (refresh_notices) query.push("refresh_notices=true");

        return this.base.get(this.base.getSimpleApiUrl("pluginmanager") + ((query.length) ? "?" + query.join("&") : ""), opts);
    };

    OctoPrintPluginManagerClient.prototype.getWithRefresh = function(opts) {
        return this.get(true, opts);
    };

    OctoPrintPluginManagerClient.prototype.getWithoutRefresh = function(opts) {
        return this.get(false, opts);
    };

    OctoPrintPluginManagerClient.prototype.install = function(pluginUrl, dependencyLinks, opts) {
        var data = {
            url: pluginUrl,
            dependency_links: !!dependencyLinks
        };
        return this.base.simpleApiCommand("pluginmanager", "install", data, opts);
    };

    OctoPrintPluginManagerClient.prototype.reinstall = function(plugin, pluginUrl, dependencyLinks, opts) {
        var data = {
            url: pluginUrl,
            dependency_links: !!dependencyLinks,
            reinstall: plugin,
            force: true
        };
        return this.base.simpleApiCommand("pluginmanager", "install", data, opts);
    };

    OctoPrintPluginManagerClient.prototype.uninstall = function(plugin, opts) {
        var data = {
            plugin: plugin
        };
        return this.base.simpleApiCommand("pluginmanager", "uninstall", data, opts);
    };

    OctoPrintPluginManagerClient.prototype.enable = function(plugin, opts) {
        var data = {
            plugin: plugin
        };
        return this.base.simpleApiCommand("pluginmanager", "enable", data, opts);
    };

    OctoPrintPluginManagerClient.prototype.disable = function(plugin, opts) {
        var data = {
            plugin: plugin
        };
        return this.base.simpleApiCommand("pluginmanager", "disable", data, opts);
    };

    OctoPrintPluginManagerClient.prototype.upload = function(file) {
        return this.base.upload(this.base.getBlueprintUrl("pluginmanager") + "upload_archive", file);
    };

    OctoPrintClient.registerPluginComponent("pluginmanager", OctoPrintPluginManagerClient);
    return OctoPrintPluginManagerClient;
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
        self.config_noticesUrl = ko.observable();
        self.config_noticesTtl = ko.observable();
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

        self.safeMode = ko.observable();
        self.online = ko.observable();

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
        self.noticeNotifications = [];
        self.hiddenNoticeNotifications = {};
        self.noticeCount = ko.observable(0);

        self.noticeCountText = ko.pureComputed(function() {
            var count = self.noticeCount();
            if (count == 0) {
                return gettext("There are no plugin notices. Great!");
            } else if (count == 1) {
                return gettext("There is a plugin notice for one of your installed plugins.");
            } else {
                return _.sprintf(gettext("There are %(count)d plugin notices for one or more of your installed plugins."), {count: count});
            }
        });

        self.enableManagement = ko.pureComputed(function() {
            return !self.printerState.isPrinting();
        });

        self.enableToggle = function(data) {
            var command = self._getToggleCommand(data);
            var not_safemode_victim = !data.safe_mode_victim || data.safe_mode_enabled;
            var not_blacklisted = !data.blacklisted;
            return self.enableManagement() && (command == "disable" || (not_safemode_victim && not_blacklisted)) && data.key != 'pluginmanager';
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
            return self.enableManagement() && self.pipAvailable() && !self.safeMode() && self.online() && self.isCompatible(data);
        };

        self.invalidUrl = ko.pureComputed(function() {
            // supported pip install URL schemes, according to https://pip.pypa.io/en/stable/reference/pip_install/
            var allowedUrlSchemes = ["http", "https",
                                     "git", "git+http", "git+https", "git+ssh", "git+git",
                                     "hg+http", "hg+https", "hg+static-http", "hg+ssh",
                                     "svn", "svn+svn", "svn+http", "svn+https", "svn+ssh",
                                     "bzr+http", "bzr+https", "bzr+ssh", "bzr+sftp", "brz+ftp", "bzr+lp"];

            var url = self.installUrl();
            var lowerUrl = url !== undefined ? url.toLocaleLowerCase() : undefined;

            var lowerUrlStartsWithScheme = function(scheme) {
                return _.startsWith(lowerUrl, scheme + "://");
            };

            return url !== undefined && url.trim() !== ""
                && !(_.any(allowedUrlSchemes, lowerUrlStartsWithScheme));
        });

        self.enableUrlInstall = ko.pureComputed(function() {
            var url = self.installUrl();
            return self.enableManagement()
                && self.pipAvailable()
                && !self.safeMode()
                && self.online()
                && url !== undefined
                && url.trim() !== ""
                && !self.invalidUrl();
        });

        self.invalidArchive = ko.pureComputed(function() {
            var allowedArchiveExtensions = [".zip", ".tar.gz", ".tgz", ".tar"];

            var name = self.uploadFilename();
            var lowerName = name !== undefined ? name.toLocaleLowerCase() : undefined;

            var lowerNameHasExtension = function(extension) {
                return _.endsWith(lowerName, extension);
            };

            return name !== undefined
                && !(_.any(allowedArchiveExtensions, lowerNameHasExtension));
        });

        self.enableArchiveInstall = ko.pureComputed(function() {
            var name = self.uploadFilename();
            return self.enableManagement()
                && self.pipAvailable()
                && !self.safeMode()
                && name !== undefined
                && name.trim() !== ""
                && !self.invalidArchive();
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
                var response = data.result;
                if (response.result) {
                    self._markDone();
                } else {
                    self._markDone(response.reason);
                }

                self.uploadButton.unbind("click");
                self.uploadFilename(undefined);
            },
            fail: function(e, data) {
                new PNotify({
                    title: gettext("Something went wrong"),
                    text: gettext("Please consult octoprint.log for details"),
                    type: "error",
                    hide: false
                });
                self._markDone("Could not install plugin, unknown error.");
                self.uploadButton.unbind("click");
                self.uploadFilename(undefined);
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

        self.fromResponse = function(data, options) {
            self._fromPluginsResponse(data.plugins, options);
            self._fromRepositoryResponse(data.repository, options);
            self._fromPipResponse(data.pip, options);

            self.safeMode(data.safe_mode || false);
            self.online(data.online !== undefined ? data.online : true);
        };

        self._fromPluginsResponse = function(data, options) {
            var evalNotices = options.eval_notices || false;
            var ignoreNoticeHidden = options.ignore_notice_hidden || false;
            var ignoreNoticeIgnored = options.ignore_notice_ignored || false;

            if (evalNotices) self._removeAllNoticeNotifications();

            var installedPlugins = [];
            var noticeCount = 0;
            _.each(data, function(plugin) {
                installedPlugins.push(plugin.key);

                if (evalNotices && plugin.notifications && plugin.notifications.length) {
                    _.each(plugin.notifications, function(notification) {
                        noticeCount++;
                        if (!ignoreNoticeIgnored && self._isNoticeNotificationIgnored(plugin.key, notification.date)) return;
                        if (!ignoreNoticeHidden && self._isNoticeNotificationHidden(plugin.key, notification.date)) return;
                        self._showPluginNotification(plugin, notification);
                    });
                }
            });
            if (evalNotices) self.noticeCount(noticeCount);
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

        self.requestData = function(options) {
            if (!self.loginState.isAdmin()) {
                return;
            }

            if (!_.isPlainObject(options)) {
                options = {
                    refresh_repo: options,
                    refresh_notices: false,
                    eval_notices: false
                };

            }

            options.refresh_repo = options.refresh_repo || false;
            options.refresh_notices = options.refresh_notices || false;
            options.eval_notices = options.eval_notices || false;

            OctoPrint.plugins.pluginmanager.get({repo: options.refresh_repo, notices: options.refresh_notices})
                .done(function(data) {
                    self.fromResponse(data, options);
                });
        };

        self.togglePlugin = function(data) {
            if (!self.loginState.isAdmin()) {
                return;
            }

            if (!self.enableManagement()) {
                return;
            }

            if (data.key == "pluginmanager") return;

            var onSuccess = function() {
                    self.requestData();
                },
                onError = function() {
                    new PNotify({
                        title: gettext("Something went wrong"),
                        text: gettext("Please consult octoprint.log for details"),
                        type: "error",
                        hide: false
                    })
                };

            if (self._getToggleCommand(data) == "enable") {
                if (data.safe_mode_victim && !data.safe_mode_enabled) return;
                OctoPrint.plugins.pluginmanager.enable(data.key)
                    .done(onSuccess)
                    .fail(onError);
            } else {
                var perform = function() {
                    OctoPrint.plugins.pluginmanager.disable(data.key)
                        .done(onSuccess)
                        .fail(onError);
                };

                if (data.disabling_discouraged) {
                    var message = _.sprintf(gettext("You are about to disable \"%(name)s\"."), {name: data.name})
                        + "</p><p>" + data.disabling_discouraged;
                    showConfirmationDialog({
                        title: gettext("This is not recommended"),
                        message: message,
                        question: gettext("Do you still want to disable it?"),
                        cancel: gettext("Keep enabled"),
                        proceed: gettext("Disable anyway"),
                        onproceed: perform
                    })
                } else {
                    perform();
                }
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

            var onSuccess = function(response) {
                    if (response.result) {
                        self._markDone();
                    } else {
                        self._markDone(response.reason)
                    }
                    self.requestData();
                    self.installUrl("");
                },
                onError = function() {
                    self._markDone("Could not install plugin, unknown error, please consult octoprint.log for details");
                    new PNotify({
                        title: gettext("Something went wrong"),
                        text: gettext("Please consult octoprint.log for details"),
                        type: "error",
                        hide: false
                    });
                };

            if (reinstall) {
                OctoPrint.plugins.pluginmanager.reinstall(reinstall, url, followDependencyLinks)
                    .done(onSuccess)
                    .fail(onError);
            } else {
                OctoPrint.plugins.pluginmanager.install(url, followDependencyLinks)
                    .done(onSuccess)
                    .fail(onError);
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
                .done(function() {
                    self.requestData();
                })
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
            self.requestData({refresh_repo: true});
        };

        self.refreshNotices = function() {
            if (!self.loginState.isAdmin()) {
                return;
            }

            self.requestData({refresh_notices: true, eval_notices: true, ignore_notice_hidden: true, ignore_notice_ignored: true});
        };

        self.reshowNotices = function() {
            if (!self.loginState.isAdmin()) {
                return;
            }

            self.requestData({eval_notices: true, ignore_notice_hidden: true, ignore_notice_ignored: true});
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

            var notices = self.config_noticesUrl();
            if (notices != undefined && notices.trim() == "") {
                notices = null;
            }

            var noticesTtl;
            try {
                noticesTtl = parseInt(self.config_noticesTtl());
            } catch (ex) {
                noticesTtl = null;
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
                        notices: notices,
                        notices_ttl: noticesTtl,
                        pip_args: pipArgs,
                        pip_force_user: self.config_pipForceUser()
                    }
                }
            };
            self.settingsViewModel.saveData(data, function() {
                self.configurationDialog.modal("hide");
                self._copyConfig();
                self.requestData({refresh_repo: true, refresh_notices: true, eval_notices: true});
            });
        };

        self._copyConfig = function() {
            self.config_repositoryUrl(self.settingsViewModel.settings.plugins.pluginmanager.repository());
            self.config_repositoryTtl(self.settingsViewModel.settings.plugins.pluginmanager.repository_ttl());
            self.config_noticesUrl(self.settingsViewModel.settings.plugins.pluginmanager.notices());
            self.config_noticesTtl(self.settingsViewModel.settings.plugins.pluginmanager.notices_ttl());
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
            return self.isCompatible(data) ? (self.installed(data) ? gettext("Reinstall") : gettext("Install")) : (data.disabled ? gettext("Disabled") : gettext("Incompatible"));
        };

        self._displayNotification = function(response, action, titleSuccess, textSuccess, textRestart, textReload, textReconnect, titleError, textError) {
            var notification;

            var beforeClose = function(notification) {
                self.notifications = _.without(self.notifications, notification);
            };

            if (response.result) {
                if (action == "install" && response.plugin && response.plugin.blacklisted) {
                    notification = new PNotify({
                        title: titleSuccess,
                        text: textSuccess,
                        type: "warning",
                        callbacks: {
                            before_close: beforeClose
                        },
                        hide: false
                    })
                } else if (response.needs_restart) {
                    var options = {
                        title: titleSuccess,
                        text: textRestart,
                        buttons: {
                            closer: true,
                            sticker: false
                        },
                        callbacks: {
                            before_close: beforeClose
                        },
                        hide: false
                    };

                    var restartClicked = false;
                    if (self.restartCommandSpec) {
                        options.confirm = {
                            confirm: true,
                            buttons: [{
                                text: gettext("Restart now"),
                                click: function (notice) {
                                    if (restartClicked) return;
                                    restartClicked = true;
                                    showConfirmationDialog({
                                        message: gettext("<strong>This will restart your OctoPrint server.</strong></p><p>This action may disrupt any ongoing print jobs (depending on your printer's controller and general setup that might also apply to prints run directly from your printer's internal storage)."),
                                        onproceed: function() {
                                            OctoPrint.system.executeCommand("core", "restart")
                                                .done(function() {
                                                    notice.remove();
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
                                        },
                                        onclose: function() {
                                            restartClicked = false;
                                        }
                                    });
                                }
                            }]
                        }
                    }

                    notification = PNotify.singleButtonNotify(options);
                } else if (response.needs_refresh) {
                    var refreshClicked = false;
                    notification = PNotify.singleButtonNotify({
                        title: titleSuccess,
                        text: textReload,
                        confirm: {
                            confirm: true,
                            buttons: [{
                                text: gettext("Reload now"),
                                click: function () {
                                    if (refreshClicked) return;
                                    refreshClicked = true;
                                    location.reload(true);
                                }
                            }]
                        },
                        buttons: {
                            closer: true,
                            sticker: false
                        },
                        callbacks: {
                            before_close: beforeClose
                        },
                        hide: false
                    })
                } else if (response.needs_reconnect) {
                    notification = new PNotify({
                        title: titleSuccess,
                        text: textReconnect,
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
            self._scrollWorkingOutputToEnd();

            self.workingDialog.modal({keyboard: false, backdrop: "static", show: true});
        };

        self._markDone = function(error) {
            self.working(false);
            if (error) {
                self.loglines.push({line: gettext("Error!"), stream: "error"});
                self.loglines.push({line: error, stream: "error"})
            } else {
                self.loglines.push({line: gettext("Done!"), stream: "message"});
            }
            self._scrollWorkingOutputToEnd();
        };

        self._scrollWorkingOutputToEnd = function() {
            self.workingOutput.scrollTop(self.workingOutput[0].scrollHeight - self.workingOutput.height());
        };

        self._getToggleCommand = function(data) {
            var disable = (data.enabled || data.pending_enable || (data.safe_mode_victim && data.safe_mode_enabled)) && !data.pending_disable;
            return disable ? "disable" : "enable";
        };

        self.toggleButtonCss = function(data) {
            var icon = self._getToggleCommand(data) == "enable" ? "fa fa-toggle-off" : "fa fa-toggle-on";
            var disabled = (self.enableToggle(data)) ? "" : " disabled";

            return icon + disabled;
        };

        self.toggleButtonTitle = function(data) {
            var command = self._getToggleCommand(data);
            if (command == "enable") {
                if (data.blacklisted) {
                    return gettext("Blacklisted");
                } else if (data.safe_mode_victim && !data.safe_mode_enabled) {
                    return gettext("Disabled due to active safe mode");
                } else {
                    return gettext("Enable Plugin");
                }
            } else {
                return gettext("Disable Plugin");
            }
        };

        self.showPluginNotifications = function(plugin) {
            if (!plugin.notifications || plugin.notifications.length == 0) return;

            self._removeAllNoticeNotificationsForPlugin(plugin.key);
            _.each(plugin.notifications, function(notification) {
                self._showPluginNotification(plugin, notification);
            });
        };

        self.showPluginNotificationsLinkText = function(plugins) {
            if (!plugins.notifications || plugins.notifications.length == 0) return;

            var count = plugins.notifications.length;
            var importantCount = _.filter(plugins.notifications, function(notification) { return notification.important }).length;
            if (count > 1) {
                if (importantCount) {
                    return _.sprintf(gettext("There are %(count)d notices (%(important)d marked as important) available regarding this plugin - click to show!"), {count: count, important: importantCount});
                } else {
                    return _.sprintf(gettext("There are %(count)d notices available regarding this plugin - click to show!"), {count: count});
                }
            } else {
                if (importantCount) {
                    return gettext("There is an important notice available regarding this plugin - click to show!");
                } else {
                    return gettext("There is a notice available regarding this plugin - click to show!");
                }
            }
        };

        self._showPluginNotification = function(plugin, notification) {
            var name = plugin.name;
            var version = plugin.version;

            var important = notification.important;
            var link = notification.link;

            var title;
            if (important) {
                title = _.sprintf(gettext("Important notice regarding plugin \"%(name)s\""), {name: name});
            } else {
                title = _.sprintf(gettext("Notice regarding plugin \"%(name)s\""), {name: name});
            }

            var text = "";

            if (notification.versions && notification.versions.length > 0) {
                var versions = _.map(notification.versions, function(v) { return (v == version) ? "<strong>" + v + "</strong>" : v; }).join(", ");
                text += "<small>" + _.sprintf(gettext("Affected versions: %(versions)s"), {versions: versions}) + "</small>";
            } else {
                text += "<small>" + gettext("Affected versions: all") + "</small>";
            }

            text += "<p>" + notification.text + "</p>";
            if (link) {
                text += "<p><a href='" + link + "' target='_blank'>" + gettext("Read more...") + "</a></p>";
            }

            var beforeClose = function(notification) {
                if (!self.noticeNotifications[plugin.key]) return;
                self.noticeNotifications[plugin.key] = _.without(self.noticeNotifications[plugin.key], notification);
            };

            var options = {
                title: title,
                text: text,
                type: (important) ? "error" : "notice",
                before_close: beforeClose,
                hide: false,
                confirm: {
                    confirm: true,
                    buttons: [{
                        text: gettext("Later"),
                        click: function(notice) {
                            self._hideNoticeNotification(plugin.key, notification.date);
                            notice.remove();
                            notice.get().trigger("pnotify.cancel", notice);
                        }
                    }, {
                        text: gettext("Mark read"),
                        click: function(notice) {
                            self._ignoreNoticeNotification(plugin.key, notification.date);
                            notice.remove();
                            notice.get().trigger("pnotify.cancel", notice);
                        }
                    }]
                },
                buttons: {
                    sticker: false,
                    closer: false
                }
            };

            if (!self.noticeNotifications[plugin.key]) {
                self.noticeNotifications[plugin.key] = [];
            }
            self.noticeNotifications[plugin.key].push(new PNotify(options));
        };

        self._removeAllNoticeNotifications = function() {
            _.each(_.keys(self.noticeNotifications), function(key) {
                self._removeAllNoticeNotificationsForPlugin(key);
            });
        };

        self._removeAllNoticeNotificationsForPlugin = function(key) {
            if (!self.noticeNotifications[key] || !self.noticeNotifications[key].length) return;
            _.each(self.noticeNotifications[key], function(notification) {
                notification.remove();
            });
        };

        self._hideNoticeNotification = function(key, date) {
            if (!self.hiddenNoticeNotifications[key]) {
                self.hiddenNoticeNotifications[key] = [];
            }
            if (!_.contains(self.hiddenNoticeNotifications[key], date)) {
                self.hiddenNoticeNotifications[key].push(date);
            }
        };

        self._isNoticeNotificationHidden = function(key, date) {
            if (!self.hiddenNoticeNotifications[key]) return false;
            return _.any(_.map(self.hiddenNoticeNotifications[key], function(d) { return date == d; }));
        };

        var noticeLocalStorageKey = "plugin.pluginmanager.seen_notices";
        self._ignoreNoticeNotification = function(key, date) {
            if (!Modernizr.localstorage)
                return false;
            if (!self.loginState.isAdmin())
                return false;

            var currentString = localStorage[noticeLocalStorageKey];
            var current;
            if (currentString === undefined) {
                current = {};
            } else {
                current = JSON.parse(currentString);
            }
            if (!current[self.loginState.username()]) {
                current[self.loginState.username()] = {};
            }
            if (!current[self.loginState.username()][key]) {
                current[self.loginState.username()][key] = [];
            }

            if (!_.contains(current[self.loginState.username()][key], date)) {
                current[self.loginState.username()][key].push(date);
                localStorage[noticeLocalStorageKey] = JSON.stringify(current);
            }
        };

        self._isNoticeNotificationIgnored = function(key, date) {
            if (!Modernizr.localstorage)
                return false;

            if (localStorage[noticeLocalStorageKey] == undefined)
                return false;

            var knownData = JSON.parse(localStorage[noticeLocalStorageKey]);

            if (!self.loginState.isAdmin())
                return true;

            var userData = knownData[self.loginState.username()];
            if (userData === undefined)
                return false;

            return userData[key] && _.contains(userData[key], date);
        };

        self.onBeforeBinding = function() {
            self.settings = self.settingsViewModel.settings;
        };

        self.onUserLoggedIn = function(user) {
            if (user.admin) {
                self.requestData({eval_notices: true});
            } else {
                self.onUserLoggedOut();
            }
        };

        self.onUserLoggedOut = function() {
            self._closeAllNotifications();
        };

        self.onEventConnectivityChanged = function(payload) {
            self.requestData({eval_notices: true});
        };

        self._closeAllNotifications = function() {
            if (self.notifications) {
                _.each(self.notifications, function(notification) {
                    notification.remove();
                });
            }
        };

        self.onServerDisconnect = function() {
            self._closeAllNotifications();
            return true;
        };

        self.onStartup = function() {
            self.workingDialog = $("#settings_plugin_pluginmanager_workingdialog");
            self.workingOutput = $("#settings_plugin_pluginmanager_workingdialog_output");
            self.repositoryDialog = $("#settings_plugin_pluginmanager_repositorydialog");
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
                    self.loglines.push(self._preprocessLine(line));
                });
                self._scrollWorkingOutputToEnd();
            } else if (messageType == "result") {
                var titleSuccess, textSuccess, textRestart, textReload, textReconnect, titleError, textError;
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
                        textReconnect = textSuccess;
                    } else if (data.plugin && data.plugin.blacklisted) {
                        if (data.was_reinstalled) {
                            titleSuccess = _.sprintf(gettext("Plugin \"%(name)s\" reinstalled"), {name: name});
                            textSuccess = gettext("The plugin was reinstalled successfully, however it is blacklisted and therefore won't be loaded.");
                        } else {
                            titleSuccess = _.sprintf(gettext("Plugin \"%(name)s\" installed"), {name: name});
                            textSuccess = gettext("The plugin was installed successfully, however it is blacklisted and therefore won't be loaded.");
                        }
                        textRestart = textSuccess;
                        textReload = textSuccess;
                        textReconnect = textSuccess;
                    } else if (data.was_reinstalled) {
                        titleSuccess = _.sprintf(gettext("Plugin \"%(name)s\" reinstalled"), {name: name});
                        textSuccess = gettext("The plugin was reinstalled successfully");
                        textRestart = gettext("The plugin was reinstalled successfully, however a restart of OctoPrint is needed for that to take effect.");
                        textReload = gettext("The plugin was reinstalled successfully, however a reload of the page is needed for that to take effect.");
                        textReconnect = gettext("The plugin was reinstalled successfully, however a reconnect to the printer is needed for that to take effect.");
                    } else {
                        titleSuccess = _.sprintf(gettext("Plugin \"%(name)s\" installed"), {name: name});
                        textSuccess = gettext("The plugin was installed successfully");
                        textRestart = gettext("The plugin was installed successfully, however a restart of OctoPrint is needed for that to take effect.");
                        textReload = gettext("The plugin was installed successfully, however a reload of the page is needed for that to take effect.");
                        textReconnect = gettext("The plugin was installed successfully, however a reconnect to the printer is needed for that to take effect.");
                    }

                    titleError = gettext("Something went wrong");
                    var source = "unknown";
                    if (data.hasOwnProperty("source")) {
                        source = data.source;
                    }
                    var sourceType = "unknown";
                    if (data.hasOwnProperty("source_type")) {
                        sourceType = data.source_type;
                    }

                    if (data.hasOwnProperty("reason")) {
                        if (data.was_reinstalled) {
                            if (sourceType == "path") {
                                textError = _.sprintf(gettext("Reinstalling the plugin from file failed: %(reason)s"), {reason: data.reason});
                            } else {
                                textError = _.sprintf(gettext("Reinstalling the plugin from \"%(source)s\" failed: %(reason)s"), {reason: data.reason, source: source});
                            }
                        } else {
                            if (sourceType == "path") {
                                textError = _.sprintf(gettext("Installing the plugin from file failed: %(reason)s"), {reason: data.reason});
                            } else {
                                textError = _.sprintf(gettext("Installing the plugin from \"%(source)s\" failed: %(reason)s"), {reason: data.reason, source: source});
                            }
                        }
                    } else {
                        if (data.was_reinstalled) {
                            if (sourceType == "path") {
                                textError = gettext("Reinstalling the plugin from file failed, please see the log for details.");
                            } else {
                                textError = _.sprintf(gettext("Reinstalling the plugin from \"%(source)s\" failed, please see the log for details."), {source: source});
                            }
                        } else {
                            if (sourceType == "path") {
                                textError = gettext("Installing the plugin from file failed, please see the log for details.");
                            } else {
                                textError = _.sprintf(gettext("Installing the plugin from \"%(source)s\" failed, please see the log for details."), {source: source});
                            }
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
                    textReconnect = gettext("The plugin was uninstalled successfully, however a reconnect to the printer is needed for that to take effect.");

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
                    textReconnect = gettext("The plugin was enabled successfully, however a reconnect to the printer is needed for that to take effect.");

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
                    textReconnect = gettext("The plugin was disabled successfully, however a reconnect to the printer is needed for that to take effect.");

                    titleError = gettext("Something went wrong");
                    if (data.hasOwnProperty("reason")) {
                        textError = _.sprintf(gettext("Toggling the plugin failed: %(reason)s"), {reason: data.reason});
                    } else {
                        textError = gettext("Toggling the plugin failed, please see the log for details.");
                    }

                } else {
                    return;
                }

                self._displayNotification(data, action, titleSuccess, textSuccess, textRestart, textReload, textReconnect, titleError, textError);
                self.requestData();
            }
        };

        self._forcedStdoutLine = /You are using pip version .*?, however version .*? is available\.|You should consider upgrading via the '.*?' command\./;
        self._preprocessLine = function(line) {
            if (line.stream === "stderr" && line.line.match(self._forcedStdoutLine)) {
                line.stream = "stdout";
            }
            return line;
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: PluginManagerViewModel,
        dependencies: ["loginStateViewModel", "settingsViewModel", "printerStateViewModel", "systemViewModel"],
        elements: ["#settings_plugin_pluginmanager"]
    });
});
