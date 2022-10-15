$(function () {
    function PluginManagerViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settingsViewModel = parameters[1];
        self.printerState = parameters[2];
        self.systemViewModel = parameters[3];
        self.access = parameters[4];

        // optional
        self.piSupport = parameters[5];

        self.config_repositoryUrl = ko.observable();
        self.config_repositoryTtl = ko.observable();
        self.config_noticesUrl = ko.observable();
        self.config_noticesTtl = ko.observable();
        self.config_pipAdditionalArgs = ko.observable();
        self.config_pipForceUser = ko.observable();
        self.config_confirmUninstall = ko.observable();
        self.config_confirmDisable = ko.observable();

        self.configurationDialog = $(
            "#settings_plugin_pluginmanager_configurationdialog"
        );

        self.plugins = new ItemListHelper(
            "plugin.pluginmanager.installedplugins",
            {
                name: function (a, b) {
                    // sorts ascending
                    if (a["name"].toLocaleLowerCase() < b["name"].toLocaleLowerCase())
                        return -1;
                    if (a["name"].toLocaleLowerCase() > b["name"].toLocaleLowerCase())
                        return 1;
                    return 0;
                }
            },
            {
                "bundled": function (item) {
                    return item.bundled;
                },
                "3rdparty": function (item) {
                    return !item.bundled;
                },
                "enabled": function (item) {
                    return item.enabled;
                },
                "disabled": function (item) {
                    return !item.enabled;
                }
            },
            "name",
            [],
            [
                ["bundled", "3rdparty"],
                ["enabled", "disabled"]
            ],
            0
        );
        self.plugins.currentFilters.subscribe(function () {
            self.clearPluginsSelection();
        });
        self.pluginLookup = {};

        self.repositoryplugins = new ItemListHelper(
            "plugin.pluginmanager.repositoryplugins",
            {
                title: function (a, b) {
                    // sorts ascending
                    if (a.title.toLocaleLowerCase() < b.title.toLocaleLowerCase())
                        return -1;
                    if (a.title.toLocaleLowerCase() > b.title.toLocaleLowerCase())
                        return 1;
                    return 0;
                },
                published: function (a, b) {
                    // sorts descending
                    if (a.published.toLocaleLowerCase() > b.published.toLocaleLowerCase())
                        return -1;
                    if (a.published.toLocaleLowerCase() < b.published.toLocaleLowerCase())
                        return 1;
                    return 0;
                },
                popularity: function (a, b) {
                    // sorts descending
                    var countA =
                        a.stats && a.stats.instances_month ? a.stats.instances_month : 0;
                    var countB =
                        b.stats && b.stats.instances_month ? b.stats.instances_month : 0;

                    if (countA > countB) return -1;
                    if (countA < countB) return 1;
                    return 0;
                },
                release_date: function (a, b) {
                    // sorts descending
                    var valA =
                        a.github && a.github.latest_release
                            ? a.github.latest_release.date.toLocaleLowerCase()
                            : "";
                    var valB =
                        b.github && b.github.latest_release
                            ? b.github.latest_release.date.toLocaleLowerCase()
                            : "";

                    if (valA > valB) return -1;
                    if (valA < valB) return 1;
                    return 0;
                },
                push_date: function (a, b) {
                    // sorts descending
                    var valA = a.github ? a.github.last_push.toLocaleLowerCase() : "";
                    var valB = b.github ? b.github.last_push.toLocaleLowerCase() : "";

                    if (valA > valB) return -1;
                    if (valA < valB) return 1;
                    return 0;
                },
                stars: function (a, b) {
                    // sorts descending
                    var valA = a.github ? a.github.stars : 0;
                    var valB = b.github ? b.github.stars : 0;

                    if (valA > valB) return -1;
                    if (valA < valB) return 1;
                    return 0;
                }
            },
            {
                filter_installed: function (plugin) {
                    return !self.installed(plugin);
                },
                filter_incompatible: function (plugin) {
                    return (
                        plugin.is_compatible.octoprint &&
                        plugin.is_compatible.os &&
                        plugin.is_compatible.python
                    );
                },
                filter_abandoned: function (plugin) {
                    return !plugin.abandoned;
                }
            },
            "popularity",
            ["filter_installed", "filter_incompatible"],
            [],
            0
        );

        self.orphans = new ItemListHelper(
            "plugin.pluginmanager.orphans",
            {
                identifier: function (a, b) {
                    // sorts ascending
                    if (
                        a["identifier"].toLocaleLowerCase() <
                        b["identifier"].toLocaleLowerCase()
                    )
                        return -1;
                    if (
                        a["identifier"].toLocaleLowerCase() >
                        b["identifier"].toLocaleLowerCase()
                    )
                        return 1;
                    return 0;
                }
            },
            {},
            "identifier",
            [],
            [],
            0
        );

        self.selectedPlugins = ko.observableArray([]);

        self.uploadElement = $("#settings_plugin_pluginmanager_repositorydialog_upload");
        self.uploadButton = $(
            "#settings_plugin_pluginmanager_repositorydialog_upload_start"
        );

        self.repositoryAvailable = ko.observable(undefined);

        self.repositorySearchQuery = ko.observable();
        self.repositorySearchQuery.subscribe(function () {
            self.performRepositorySearch();
        });

        self.listingSearchQuery = ko.observable();
        self.listingSearchQuery.subscribe(function () {
            self.performListingSearch();
        });

        self.installUrl = ko.observable();
        self.uploadFilename = ko.observable();

        self.loglines = ko.observableArray([]);
        self.installedPlugins = ko.observableArray([]);

        self.followDependencyLinks = ko.observable(false);

        self.pipAvailable = ko.observable(true);
        self.pipVersion = ko.observable();
        self.pipInstallDir = ko.observable();
        self.pipUseUser = ko.observable();
        self.pipVirtualEnv = ko.observable();
        self.pipAdditionalArgs = ko.observable();
        self.pipPython = ko.observable();

        self.safeMode = ko.observable();
        self.online = ko.observable();
        self.supportedArchiveExtensions = ko.observableArray([]);
        self.supportedPythonExtensions = ko.observableArray([]);

        var createExtensionsHelp = function (extensions) {
            return _.reduce(
                extensions,
                function (result, ext, index) {
                    return (
                        result +
                        '"' +
                        ext +
                        '"' +
                        (index < extensions.length - 2
                            ? ", "
                            : index == extensions.length - 2
                            ? " " + gettext("and") + " "
                            : "")
                    );
                },
                ""
            );
        };
        self.supportedExtensionsHelp = ko.pureComputed(function () {
            var archiveExts = createExtensionsHelp(self.supportedArchiveExtensions());
            var pythonExts = createExtensionsHelp(self.supportedPythonExtensions());

            return _.sprintf(
                gettext(
                    "This does not look like a valid plugin. Valid plugins should be " +
                        "either archives installable via <code>pip</code> that " +
                        "have the extension %(archiveExtensions)s, or single file python " +
                        "plugins with the extension %(pythonExtensions)s."
                ),
                {archiveExtensions: archiveExts, pythonExtensions: pythonExts}
            );
        });

        self.requestError = ko.observable(false);

        self.pipUseUserString = ko.pureComputed(function () {
            return self.pipUseUser() ? "yes" : "no";
        });
        self.pipVirtualEnvString = ko.pureComputed(function () {
            return self.pipVirtualEnv() ? "yes" : "no";
        });

        self.working = ko.observable(false);
        self.workingTitle = ko.observable();
        self.workingDialog = undefined;
        self.workingOutput = undefined;

        self.toggling = ko.observable(false);

        self.restartCommandSpec = undefined;
        self.systemViewModel.systemActions.subscribe(function () {
            var lastResponse = self.systemViewModel.lastCommandResponse;
            if (!lastResponse || !lastResponse.core) {
                self.restartCommandSpec = undefined;
                return;
            }

            var restartSpec = _.filter(lastResponse.core, function (spec) {
                return spec.action == "restart";
            });
            self.restartCommandSpec =
                restartSpec != undefined && restartSpec.length > 0
                    ? restartSpec[0]
                    : undefined;
        });

        self.noticeNotifications = [];
        self.hiddenNoticeNotifications = {};
        self.noticeCount = ko.observable(0);

        self.notification = undefined;
        self.logContents = {
            steps: [],
            action: {
                reload: false,
                refresh: false,
                reconnect: false
            }
        };

        self.noticeCountText = ko.pureComputed(function () {
            var count = self.noticeCount();
            if (count === 0) {
                return gettext("There are no plugin notices. Great!");
            } else if (count === 1) {
                return gettext(
                    "There is a plugin notice for one of your installed plugins."
                );
            } else {
                return _.sprintf(
                    gettext(
                        "There are %(count)d plugin notices for one or more of your installed plugins."
                    ),
                    {count: count}
                );
            }
        });

        self.enableManagement = ko.pureComputed(function () {
            return !self.printerState.isBusy();
        });

        self.enableBulk = function (data) {
            return self.enableToggle(data, true) && !data.bundled;
        };

        self.enableToggle = function (data, ignoreToggling) {
            var command = self._getToggleCommand(data);
            var not_safemode_victim = !data.safe_mode_victim;
            var not_blacklisted = !data.blacklisted;
            var not_incompatible = !data.incompatible;

            ignoreToggling = !!ignoreToggling;

            return (
                self.enableManagement() &&
                (ignoreToggling || !self.toggling()) &&
                (command === "disable" ||
                    (not_safemode_victim && not_blacklisted && not_incompatible)) &&
                data.key !== "pluginmanager"
            );
        };

        self.enableUninstall = function (data) {
            return (
                self.enableManagement() &&
                (data.origin !== "entry_point" || self.pipAvailable()) &&
                data.managable &&
                !data.bundled &&
                data.key !== "pluginmanager" &&
                !data.pending_uninstall
            );
        };

        self.enableCleanup = function (data) {
            return (
                self.enableManagement() &&
                data.key !== "pluginmanager" &&
                !data.pending_uninstall
            );
        };

        self.enableRepoInstall = function (data) {
            return (
                self.pipAvailable() &&
                !self.safeMode() &&
                !self.throttled() &&
                self.online() &&
                self.isCompatible(data)
            );
        };

        self.throttled = ko.pureComputed(function () {
            return (
                self.piSupport &&
                self.piSupport.currentIssue() &&
                !self.settingsViewModel.settings.plugins.pluginmanager.ignore_throttled()
            );
        });

        self.invalidUrl = ko.pureComputed(function () {
            // supported pip install URL schemes, according to https://pip.pypa.io/en/stable/reference/pip_install/
            var allowedUrlSchemes = [
                "http",
                "https",
                "git",
                "git+http",
                "git+https",
                "git+ssh",
                "git+git",
                "hg+http",
                "hg+https",
                "hg+static-http",
                "hg+ssh",
                "svn",
                "svn+svn",
                "svn+http",
                "svn+https",
                "svn+ssh",
                "bzr+http",
                "bzr+https",
                "bzr+ssh",
                "bzr+sftp",
                "brz+ftp",
                "bzr+lp"
            ];

            var url = self.installUrl();
            var lowerUrl = url !== undefined ? url.toLocaleLowerCase() : undefined;

            var lowerUrlStartsWithScheme = function (scheme) {
                return _.startsWith(lowerUrl, scheme + "://");
            };

            return (
                url !== undefined &&
                url.trim() !== "" &&
                !_.any(allowedUrlSchemes, lowerUrlStartsWithScheme)
            );
        });

        self.enableUrlInstall = ko.pureComputed(function () {
            var url = self.installUrl();
            return (
                self.enableManagement() &&
                self.pipAvailable() &&
                !self.safeMode() &&
                !self.throttled() &&
                self.online() &&
                url !== undefined &&
                url.trim() !== "" &&
                !self.invalidUrl()
            );
        });

        self.invalidFile = ko.pureComputed(function () {
            var allowedFileExtensions = self
                .supportedArchiveExtensions()
                .concat(self.supportedPythonExtensions());

            var name = self.uploadFilename();
            var lowerName = name !== undefined ? name.toLocaleLowerCase() : undefined;

            var lowerNameHasExtension = function (extension) {
                return _.endsWith(lowerName, extension);
            };

            return (
                name !== undefined && !_.any(allowedFileExtensions, lowerNameHasExtension)
            );
        });

        self.enableFileInstall = ko.pureComputed(function () {
            var name = self.uploadFilename();
            return (
                self.enableManagement() &&
                self.pipAvailable() &&
                !self.safeMode() &&
                !self.throttled() &&
                name !== undefined &&
                name.trim() !== "" &&
                !self.invalidFile()
            );
        });

        self.uploadElement.fileupload({
            dataType: "json",
            maxNumberOfFiles: 1,
            autoUpload: false,
            add: function (e, data) {
                if (data.files.length === 0) {
                    return false;
                }

                self.uploadFilename(data.files[0].name);

                self.uploadButton.unbind("click");
                self.uploadButton.bind("click", function () {
                    self._markWorking(
                        gettext("Installing plugin..."),
                        gettext("Installing plugin from uploaded file...")
                    );
                    data.formData = {
                        dependency_links: self.followDependencyLinks()
                    };
                    data.submit();
                    return false;
                });
            },
            done: function (e, data) {
                var response = data.result;
                if (!response.in_progress) {
                    if (response.result) {
                        self._markDone();
                    } else {
                        self._markDone(response.reason);
                    }
                }

                self.uploadButton.unbind("click");
                self.uploadFilename(undefined);
            },
            fail: function (e, data) {
                if (data && data.errorThrown === "CONFLICT") {
                    // there's already a plugin being installed
                    self._markDone("There's already another plugin install in progress.");
                } else {
                    new PNotify({
                        title: gettext("Something went wrong"),
                        text: gettext("Please consult octoprint.log for details"),
                        type: "error",
                        hide: false
                    });
                    self._markDone("Could not install plugin, unknown error.");
                }
                self.uploadButton.unbind("click");
                self.uploadFilename(undefined);
            }
        });

        self.performListingSearch = function () {
            var query = self.listingSearchQuery();
            if (query !== undefined && query.trim() !== "") {
                query = query.toLocaleLowerCase();
                self.plugins.changeSearchFunction(function (entry) {
                    return (
                        entry &&
                        (entry["name"].toLocaleLowerCase().indexOf(query) > -1 ||
                            (entry.description &&
                                entry.description.toLocaleLowerCase().indexOf(query) >
                                    -1))
                    );
                });
            } else {
                self.plugins.resetSearch();
            }
        };

        self.multiInstallQueue = ko.observableArray([]);
        self.queuedInstalls = ko.observableArray([]);
        self.multiInstallRunning = ko.observable(false);
        self.multiInstallInitialSize = ko.observable(0);

        self.multiInstallValid = function () {
            return (
                self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_PLUGINMANAGER_INSTALL
                ) &&
                self.pipAvailable() &&
                !self.safeMode() &&
                !self.throttled() &&
                self.online() &&
                self.multiInstallQueue().length > 0 &&
                self.multiInstallQueue().every(self.isCompatible)
            );
        };

        self.repoInstallSelectedButtonText = function () {
            return self.multiInstallQueue().some(self.installed)
                ? "(Re)install selected"
                : "Install selected";
        };

        self.repoInstallSelectedConfirm = function () {
            if (!self.multiInstallValid()) return;

            if (self.multiInstallQueue().length === 1) {
                self.installFromRepository(self.multiInstallQueue()[0]);
                return;
            }

            var question = "<ul>";
            self.multiInstallQueue().forEach(function (plugin) {
                var action = self.installed(plugin)
                    ? gettext("Reinstall")
                    : gettext("Install");

                question += _.sprintf(
                    "<li>%(action)s <em><b>%(name)s@%(version)s</b></em></li>",
                    {
                        action: _.escape(action),
                        name: _.escape(plugin.title),
                        version: _.escape(plugin.github.latest_release.tag)
                    }
                );
            });
            question += "</ul>";

            showConfirmationDialog({
                title: gettext("Confirm installation of multiple plugins"),
                message: gettext("Please confirm you want to perform these actions:"),
                question: question,
                cancel: gettext("Cancel"),
                proceed: gettext("Install"),
                proceedClass: "primary",
                onproceed: self.startMultiInstall
            });
        };

        self.startMultiInstall = function () {
            if (self.multiInstallRunning() || !self.multiInstallValid()) return;

            self.multiInstallRunning(true);
            self.multiInstallInitialSize(self.multiInstallQueue().length);

            self._markWorking(
                gettext("Installing multiple plugins"),
                gettext("Starting installation of multiple plugins...")
            );
            self.performMultiInstallJob();
        };

        self.performMultiInstallJob = function () {
            if (!self.multiInstallRunning() || self.multiInstallQueue().length === 0)
                return;

            var plugin = self.multiInstallQueue.pop();

            self.installFromRepository(plugin);
        };

        self.alertMultiInstallJobDone = function (response) {
            if (
                !self.multiInstallRunning() ||
                response.action != "install" ||
                !response.result
            )
                return;

            if (self.multiInstallQueue().length === 0) {
                self.installUrl("");
                self.multiInstallQueue([]);
                self.multiInstallRunning(false);
                self._markDone();
            } else {
                self.performMultiInstallJob();
            }
        };

        self.performRepositorySearch = function () {
            var query = self.repositorySearchQuery();
            if (query !== undefined && query.trim() !== "") {
                query = query.toLocaleLowerCase();
                self.repositoryplugins.changeSearchFunction(function (entry) {
                    return (
                        entry &&
                        (entry["title"].toLocaleLowerCase().indexOf(query) > -1 ||
                            entry["description"].toLocaleLowerCase().indexOf(query) > -1)
                    );
                });
            } else {
                self.repositoryplugins.resetSearch();
            }
            return false;
        };

        self.fromPluginsResponse = function (data, options) {
            var evalNotices = options.eval_notices || false;
            var ignoreNoticeHidden = options.ignore_notice_hidden || false;
            var ignoreNoticeIgnored = options.ignore_notice_ignored || false;

            if (evalNotices) self._removeAllNoticeNotifications();

            var installedPlugins = [];
            var noticeCount = 0;
            var lookup = {};
            _.each(data, function (plugin) {
                lookup[plugin.key] = plugin;
                installedPlugins.push(plugin.key);

                if (evalNotices && plugin.notifications && plugin.notifications.length) {
                    _.each(plugin.notifications, function (notification) {
                        noticeCount++;
                        if (
                            !ignoreNoticeIgnored &&
                            self._isNoticeNotificationIgnored(
                                plugin.key,
                                notification.date
                            )
                        )
                            return;
                        if (
                            !ignoreNoticeHidden &&
                            self._isNoticeNotificationHidden(
                                plugin.key,
                                notification.date
                            )
                        )
                            return;
                        self._showPluginNotification(plugin, notification);
                    });
                }
            });
            if (evalNotices) self.noticeCount(noticeCount);
            self.installedPlugins(installedPlugins);
            self.plugins.updateItems(data);
            self.pluginLookup = lookup;
        };

        self.fromOrphanResponse = function (data) {
            var orphans = [];
            _.each(data, function (value, key) {
                orphans.push({
                    identifier: key,
                    settings: value.settings,
                    data: value.data
                });
            });
            self.orphans.updateItems(orphans);
        };

        self.fromRepositoryResponse = function (data) {
            self.repositoryAvailable(data.available);
            if (data.available) {
                self.repositoryplugins.updateItems(data.plugins);
            } else {
                self.repositoryplugins.updateItems([]);
            }
        };

        self.fromPipResponse = function (data) {
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

        self.fromSupportedExtensionsResponse = function (data) {
            if (!data) return;
            self.supportedArchiveExtensions(data.archive || []);
            self.supportedPythonExtensions(data.python || []);
        };

        self.dataPluginsDeferred = undefined;
        self.requestPluginData = function (options) {
            if (!_.isPlainObject(options)) {
                options = {};
            }

            if (
                self.dataPluginsDeferred &&
                self.dataPluginsDeferred.state() === "pending" &&
                !!!options.refresh
            ) {
                return self.dataPluginsDeferred.promise();
            }

            var deferred = new $.Deferred();
            if (!!!options.refresh) {
                self.dataPluginsDeferred = deferred;
            }

            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_PLUGINMANAGER_MANAGE
                )
            ) {
                deferred.fail();
                return deferred.promise();
            }

            OctoPrint.plugins.pluginmanager
                .getPlugins(!!options.refresh)
                .fail(function () {
                    self.requestError(true);
                    deferred.reject();
                })
                .done(function (data) {
                    self.requestError(false);
                    self.fromPluginsResponse(data.plugins, options);
                    self.fromPipResponse(data.pip);
                    self.fromSupportedExtensionsResponse(data.supported_extensions);
                    self.safeMode(data.safe_mode || false);
                    deferred.resolveWith(data);
                });

            return deferred.promise();
        };

        self.dataOrphansDeferred = undefined;
        self.requestOrphanData = function (options) {
            if (!_.isPlainObject(options)) {
                options = {};
            }

            if (
                self.dataOrphansDeferred &&
                self.dataOrphansDeferred.state() === "pending" &&
                !!!options.refresh
            ) {
                return self.dataOrphansDeferred.promise();
            }

            var deferred = new $.Deferred();
            if (!!!options.refresh) {
                self.dataOrphansDeferred = deferred;
            }

            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_PLUGINMANAGER_MANAGE
                )
            ) {
                deferred.fail();
                return deferred.promise();
            }

            OctoPrint.plugins.pluginmanager
                .getOrphans(!!options.refresh)
                .fail(function () {
                    deferred.reject();
                })
                .done(function (data) {
                    self.fromOrphanResponse(data.orphans);
                    deferred.resolveWith(data);
                });

            return deferred.promise();
        };

        self.dataRepositoryDeferred = undefined;
        self.requestRepositoryData = function (options) {
            if (!_.isPlainObject(options)) {
                options = {};
            }

            if (
                self.dataRepositoryDeferred &&
                self.dataRepositoryDeferred.state() === "pending" &&
                !!!options.refresh
            ) {
                return self.dataRepositoryDeferred.promise();
            }

            var deferred = new $.Deferred();
            if (!!!options.refresh) {
                self.dataRepositoryDeferred = deferred;
            }

            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_PLUGINMANAGER_MANAGE
                )
            ) {
                deferred.fail();
                return deferred.promise();
            }

            OctoPrint.plugins.pluginmanager
                .getRepository(!!options.refresh, {ifModified: true})
                .fail(function () {
                    deferred.reject();
                })
                .done(function (data, status, xhr) {
                    // Don't update if cached - requires ifModified: true to pass through
                    // the 304 status, otherwise it fakes it and produces 200 all the time.
                    if (xhr.status === 304) return;

                    self.fromRepositoryResponse(data.repository);
                    self.online(data.online !== undefined ? data.online : true);
                    deferred.resolveWith(data);
                });

            return deferred.promise();
        };

        self.togglePlugin = function (data) {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_PLUGINMANAGER_MANAGE
                )
            ) {
                return;
            }

            if (!self.enableManagement()) {
                return;
            }

            if (data.key === "pluginmanager") return;

            var onSuccess = function () {
                    self.requestPluginData().always(function () {
                        self.toggling(false);
                    });
                },
                onError = function () {
                    self.toggling(false);
                    new PNotify({
                        title: gettext("Something went wrong"),
                        text: gettext("Please consult octoprint.log for details"),
                        type: "error",
                        hide: false
                    });
                };

            var performDisabling = function () {
                if (self.toggling()) return;
                self.toggling(true);

                OctoPrint.plugins.pluginmanager
                    .disable(data.key)
                    .done(onSuccess)
                    .fail(onError);
            };
            var performEnabling = function () {
                if (data.safe_mode_victim) return;

                if (self.toggling()) return;
                self.toggling(true);

                OctoPrint.plugins.pluginmanager
                    .enable(data.key)
                    .done(onSuccess)
                    .fail(onError);
            };

            if (self._getToggleCommand(data) === "enable") {
                performEnabling();
            } else {
                // always warn if plugin is marked "disabling discouraged"
                if (data.disabling_discouraged) {
                    var message =
                        _.sprintf(gettext('You are about to disable "%(name)s".'), {
                            name: _.escape(data.name)
                        }) +
                        "</p><p>" +
                        data.disabling_discouraged;
                    showConfirmationDialog({
                        title: gettext("This is not recommended"),
                        message: message,
                        question: gettext("Do you still want to disable it?"),
                        cancel: gettext("Keep enabled"),
                        proceed: gettext("Disable anyway"),
                        onproceed: performDisabling
                    });
                }
                // warn if global "warn disabling" setting is set"
                else if (
                    self.settingsViewModel.settings.plugins.pluginmanager.confirm_disable()
                ) {
                    showConfirmationDialog({
                        message: _.sprintf(
                            gettext('You are about to disable "%(name)s"'),
                            {name: _.escape(data.name)}
                        ),
                        cancel: gettext("Keep enabled"),
                        proceed: gettext("Disable plugin"),
                        onproceed: performDisabling,
                        nofade: true
                    });
                } else {
                    // otherwise just go ahead and disable...
                    performDisabling();
                }
            }
        };

        self._bulkOperation = function (
            plugins,
            title,
            message,
            successText,
            failureText,
            statusText,
            callback,
            alreadyCheck
        ) {
            var deferred = $.Deferred();
            var promise = deferred.promise();
            var options = {
                title: title,
                message: _.sprintf(message, {count: plugins.length}),
                max: plugins.length,
                output: true
            };
            showProgressModal(options, promise);

            var handle = function (key) {
                var d = $.Deferred();

                var plugin = self.pluginLookup[key];
                if (!plugin) {
                    deferred.notify(
                        _.sprintf(
                            gettext("Can't resolve plugin with key %(key)s, skipping..."),
                            {key: key}
                        ),
                        false
                    );
                    d.reject();
                    return d.promise();
                }
                if (!self.enableBulk(plugin)) {
                    deferred.notify(
                        _.sprintf(
                            gettext(
                                "Plugin %(plugin)s doesn't support bulk operations, skipping..."
                            ),
                            {plugin: plugin.name || key}
                        ),
                        false
                    );
                    d.reject();
                    return d.promise();
                }
                if (alreadyCheck(plugin)) {
                    deferred.notify(
                        _.sprintf(
                            gettext(
                                "Plugin %(plugin)s is already %(status)s (or pending), skipping..."
                            ),
                            {
                                plugin: plugin.name || key,
                                status: statusText
                            }
                        ),
                        true
                    );
                    d.reject();
                    return d.promise();
                }

                callback(plugin)
                    .done(function () {
                        deferred.notify(
                            _.sprintf(successText, {plugin: plugin.name || key}),
                            true
                        );
                        d.resolve();
                    })
                    .fail(function () {
                        deferred.notify(
                            _.sprintf(failureText, {plugin: plugin.name || key}),
                            false
                        );
                        d.reject();
                    });
                return d.promise();
            };

            var operations = [];
            _.each(plugins, function (key) {
                operations.push(handle(key));
            });
            $.when.apply($, _.map(operations, wrapPromiseWithAlways)).done(function () {
                deferred.resolve();
                self.requestPluginData();
            });
            return promise;
        };

        self.enableSelectedPlugins = function () {
            if (self.selectedPlugins().length === 0) return;

            var callback = function (plugin) {
                return OctoPrint.plugins.pluginmanager.enable(plugin.key);
            };
            var check = function (plugin) {
                return plugin.enabled || plugin.pending_enable;
            };

            self.toggling(true);
            self._bulkOperation(
                self.selectedPlugins(),
                gettext("Enabling plugins"),
                gettext("Enabling %(count)i plugins"),
                gettext("Enabled plugin %(plugin)s..."),
                gettext("Enabling plugin %(plugin)s failed, continuing..."),
                gettext("enabled"),
                callback,
                check
            )
                .done(function () {
                    self.selectedPlugins([]);
                })
                .always(function () {
                    self.toggling(false);
                });
        };

        self.disableSelectedPlugins = function () {
            if (self.selectedPlugins().length === 0) return;

            var callback = function (plugin) {
                return OctoPrint.plugins.pluginmanager.disable(plugin.key);
            };
            var check = function (plugin) {
                return !plugin.enabled || plugin.pending_disable;
            };

            self.toggling(true);
            self._bulkOperation(
                self.selectedPlugins(),
                gettext("Disabling plugins"),
                gettext("Disabling %(count)i plugins"),
                gettext("Disabled plugin %(plugin)s..."),
                gettext("Disabling plugin %(plugin)s failed, continuing..."),
                gettext("disabled"),
                callback,
                check
            )
                .done(function () {
                    self.selectedPlugins([]);
                })
                .always(function () {
                    self.toggling(false);
                });
        };

        self.selectAllVisiblePlugins = function () {
            var selection = [];
            _.each(self.plugins.paginatedItems(), function (plugin) {
                if (!self.enableBulk(plugin)) return;
                selection.push(plugin.key);
            });
            self.selectedPlugins(selection);
        };

        self.clearPluginsSelection = function () {
            self.selectedPlugins([]);
        };

        self.showRepository = function () {
            self.repositoryDialog.modal({
                minHeight: function () {
                    return Math.max($.fn.modal.defaults.maxHeight() - 80, 250);
                },
                show: true
            });
        };

        self.pluginDetails = function (data) {
            window.open(data.page);
        };

        self.installFromRepository = function (data) {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_PLUGINMANAGER_INSTALL
                )
            ) {
                return;
            }

            self.installPlugin(
                data.archive,
                data.title,
                self.installed(data) ? data.id : undefined,
                data.follow_dependency_links || self.followDependencyLinks()
            );
        };

        self.removeFromQueue = function (plugin) {
            var data = {
                plugin: {
                    command: self.installed(plugin) ? "reinstall" : "install",
                    url: plugin.archive,
                    dependency_links:
                        plugin.follow_dependency_links || self.followDependencyLinks()
                }
            };
            OctoPrint.simpleApiCommand("pluginmanager", "clear_queued_plugin", data).done(
                function (response) {
                    self.queuedInstalls(response.queued_installs);
                }
            );
        };

        self.installPlugin = function (url, name, reinstall, followDependencyLinks) {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_PLUGINMANAGER_INSTALL
                )
            ) {
                return;
            }

            if (self.throttled()) {
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
                    workText = _.sprintf(
                        gettext('Installing plugin "%(name)s" from %(url)s...'),
                        {url: _.escape(url), name: _.escape(name)}
                    );
                } else {
                    workText = _.sprintf(gettext("Installing plugin from %(url)s..."), {
                        url: _.escape(url)
                    });
                }
            } else {
                workTitle = gettext("Reinstalling plugin...");
                workText = _.sprintf(
                    gettext('Reinstalling plugin "%(name)s" from %(url)s...'),
                    {url: _.escape(url), name: _.escape(name)}
                );
            }

            if (self.multiInstallRunning()) {
                workTitle =
                    _.sprintf("[%(index)d/%(total)d] ", {
                        index:
                            this.multiInstallInitialSize() -
                            self.multiInstallQueue().length,
                        total: this.multiInstallInitialSize()
                    }) + workTitle;
            }

            self._markWorking(workTitle, workText);

            var onSuccess = function (response) {
                    self.installUrl("");
                    if (response.hasOwnProperty("queued_installs")) {
                        self.queuedInstalls(response.queued_installs);
                        var text =
                            '<div class="row-fluid"><p>' +
                            gettext("The following plugins are queued to be installed.") +
                            "</p><ul><li>" +
                            _.map(response.queued_installs, function (info) {
                                var plugin = ko.utils.arrayFirst(
                                    self.repositoryplugins.paginatedItems(),
                                    function (item) {
                                        return item.archive === info.url;
                                    }
                                );
                                return plugin.title;
                            }).join("</li><li>") +
                            "</li></ul></div>";
                        if (typeof self.installQueuePopup !== "undefined") {
                            self.installQueuePopup.update({
                                text: text
                            });
                            if (self.installQueuePopup.state === "closed") {
                                self.installQueuePopup.open();
                            }
                        } else {
                            self.installQueuePopup = new PNotify({
                                title: gettext("Plugin installs queued"),
                                text: text,
                                type: "notice"
                            });
                        }
                        if (self.multiInstallQueue().length > 0) {
                            self.performMultiInstallJob();
                        } else {
                            self.multiInstallRunning(false);
                            self.workingDialog.modal("hide");
                            self._markDone();
                        }
                    }
                },
                onError = function (jqXHR) {
                    if (jqXHR.status === 409) {
                        // there's already a plugin being installed
                        self._markDone(
                            "There's already another plugin install in progress."
                        );
                    } else {
                        self._markDone(
                            "Could not install plugin, unknown error, please consult octoprint.log for details"
                        );
                        new PNotify({
                            title: gettext("Something went wrong"),
                            text: gettext("Please consult octoprint.log for details"),
                            type: "error",
                            hide: false
                        });
                    }
                };

            if (reinstall) {
                OctoPrint.plugins.pluginmanager
                    .reinstall(reinstall, url, followDependencyLinks)
                    .done(onSuccess)
                    .fail(onError);
            } else {
                OctoPrint.plugins.pluginmanager
                    .install(url, followDependencyLinks)
                    .done(onSuccess)
                    .fail(onError);
            }
        };

        self.uninstallPlugin = function (data) {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_PLUGINMANAGER_MANAGE
                )
            ) {
                return;
            }

            if (!self.enableUninstall(data)) {
                return;
            }

            if (data.bundled) return;
            if (data.key === "pluginmanager") return;

            // defining actual uninstall logic as functor in order to handle
            // the confirm/no-confirm logic without duplication of logic
            var performUninstall = function (cleanup) {
                self._markWorking(
                    gettext("Uninstalling plugin..."),
                    _.sprintf(gettext('Uninstalling plugin "%(name)s"'), {
                        name: _.escape(data.name)
                    })
                );

                OctoPrint.plugins.pluginmanager
                    .uninstall(data.key, cleanup)
                    .done(function () {
                        self.requestPluginData();
                    })
                    .fail(function () {
                        new PNotify({
                            title: gettext("Something went wrong"),
                            text: gettext("Please consult octoprint.log for details"),
                            type: "error",
                            hide: false
                        });
                    })
                    .always(function () {
                        self._markDone();
                    });
            };

            showConfirmationDialog({
                message: _.sprintf(
                    gettext('You are about to uninstall the plugin "%(name)s"'),
                    {name: _.escape(data.name)}
                ),
                cancel: gettext("Keep installed"),
                proceed: [gettext("Uninstall"), gettext("Uninstall & clean up data")],
                onproceed: function (button) {
                    // buttons: 0=uninstall, 1=uninstall&cleanup
                    performUninstall(button === 1);
                },
                nofade: true
            });
        };

        self.cleanupPlugin = function (data) {
            var key, name;
            if (_.isObject(data)) {
                key = data.key;
                name = data.name;
            } else {
                key = name = data;
            }

            if (!self.loginState.isAdmin()) {
                return;
            }

            if (key === "pluginmanager") return;

            var performCleanup = function () {
                self._markWorking(
                    gettext("Cleaning up plugin data..."),
                    _.sprintf(gettext('Cleaning up data of plugin "%(name)s"'), {
                        name: _.escape(name)
                    })
                );

                OctoPrint.plugins.pluginmanager
                    .cleanup(key)
                    .done(function () {
                        self.requestOrphanData();
                    })
                    .fail(function () {
                        new PNotify({
                            title: gettext("Something went wrong"),
                            text: gettext("Please consult octoprint.log for details"),
                            type: "error",
                            hide: false
                        });
                    })
                    .always(function () {
                        self._markDone();
                    });
            };

            showConfirmationDialog({
                message: _.sprintf(
                    gettext(
                        'You are about to cleanup the plugin data of "%(name)s". This operation cannot be reversed.'
                    ),
                    {name: _.escape(name)}
                ),
                cancel: gettext("Keep data"),
                proceed: gettext("Cleanup data"),
                onproceed: performCleanup,
                nofade: true
            });
        };

        self.cleanupAll = function () {
            if (!self.loginState.isAdmin()) {
                return;
            }

            var performCleanup = function () {
                var title = gettext("Cleaning up all left over plugin data...");
                self._markWorking(title, title);

                OctoPrint.plugins.pluginmanager
                    .cleanupAll()
                    .fail(function () {
                        new PNotify({
                            title: gettext("Something went wrong"),
                            text: gettext("Please consult octoprint.log for details"),
                            type: "error",
                            hide: false
                        });
                    })
                    .always(function () {
                        self._markDone();
                    });
            };

            showConfirmationDialog({
                message: gettext(
                    "You are about to cleanup left over plugin settings and data of plugins no longer installed. This operation cannot be reversed."
                ),
                cancel: gettext("Keep data"),
                proceed: gettext("Cleanup all data"),
                onproceed: performCleanup,
                nofade: true
            });
        };

        self.refreshRepository = function () {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_PLUGINMANAGER_INSTALL
                )
            ) {
                return;
            }
            self.requestRepositoryData({refresh: true});
        };

        self.refreshNotices = function () {
            if (!self.loginState.isAdmin()) {
                return;
            }

            self.requestPluginData({
                refresh: true,
                eval_notices: true,
                ignore_notice_hidden: true,
                ignore_notice_ignored: true
            });
        };

        self.reshowNotices = function () {
            if (!self.loginState.isAdmin()) {
                return;
            }

            self.requestPluginData({
                eval_notices: true,
                ignore_notice_hidden: true,
                ignore_notice_ignored: true
            });
        };

        self.showPluginSettings = function () {
            self._copyConfig();
            self.configurationDialog.modal();
        };

        self.savePluginSettings = function () {
            var repository = self.config_repositoryUrl();
            if (repository !== null && repository.trim() === "") {
                repository = null;
            }

            var repositoryTtl;
            try {
                repositoryTtl = parseInt(self.config_repositoryTtl());
            } catch (ex) {
                repositoryTtl = null;
            }

            var notices = self.config_noticesUrl();
            if (notices !== null && notices.trim() === "") {
                notices = null;
            }

            var noticesTtl;
            try {
                noticesTtl = parseInt(self.config_noticesTtl());
            } catch (ex) {
                noticesTtl = null;
            }

            var pipArgs = self.config_pipAdditionalArgs();
            if (pipArgs !== null && pipArgs.trim() === "") {
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
                        pip_force_user: self.config_pipForceUser(),
                        confirm_disable: self.config_confirmDisable()
                    }
                }
            };
            self.settingsViewModel.saveData(data, function () {
                self.configurationDialog.modal("hide");
                self._copyConfig();
                self.requestPluginData({
                    refresh: true,
                    eval_notices: true
                });
                if (self.repositoryAvailable() !== undefined) {
                    self.requestRepositoryData({
                        refresh: true
                    });
                }
            });
        };

        self._copyConfig = function () {
            self.config_repositoryUrl(
                self.settingsViewModel.settings.plugins.pluginmanager.repository()
            );
            self.config_repositoryTtl(
                self.settingsViewModel.settings.plugins.pluginmanager.repository_ttl()
            );
            self.config_noticesUrl(
                self.settingsViewModel.settings.plugins.pluginmanager.notices()
            );
            self.config_noticesTtl(
                self.settingsViewModel.settings.plugins.pluginmanager.notices_ttl()
            );
            self.config_pipAdditionalArgs(
                self.settingsViewModel.settings.plugins.pluginmanager.pip_args()
            );
            self.config_pipForceUser(
                self.settingsViewModel.settings.plugins.pluginmanager.pip_force_user()
            );
            self.config_confirmDisable(
                self.settingsViewModel.settings.plugins.pluginmanager.confirm_disable()
            );
        };

        self.installed = function (data) {
            return _.includes(self.installedPlugins(), data.id);
        };

        self.isCompatible = function (data) {
            return (
                data.is_compatible.octoprint &&
                data.is_compatible.os &&
                data.is_compatible.python
            );
        };

        self.installButtonAction = function (data) {
            if (self.enableRepoInstall(data)) {
                if (!self.installQueued(data)) {
                    self.installFromRepository(data);
                } else {
                    self.removeFromQueue(data);
                }
            } else {
                return false;
            }
        };

        self.installButtonText = function (data) {
            if (!self.isCompatible(data)) {
                if (data.disabled) {
                    return gettext("Disabled");
                } else {
                    return gettext("Incompatible");
                }
            }

            if (self.installQueued(data)) {
                return gettext("Dequeue");
            } else if (self.installed(data)) {
                return gettext("Reinstall");
            } else {
                return gettext("Install");
            }
        };

        self._processPluginManagementResult = function (response, action, plugin) {
            if (response.result) {
                if (self.queuedInstalls().length > 0 && action === "install") {
                    var plugin_dequeue = ko.utils.arrayFirst(
                        self.queuedInstalls(),
                        function (item) {
                            return item.url === response.source;
                        }
                    );
                    if (plugin_dequeue) {
                        self.queuedInstalls.remove(plugin_dequeue);
                    }
                    if (self.queuedInstalls().length === 0) {
                        self.multiInstallRunning(false);
                        self._markDone();
                    }
                } else if (self.multiInstallRunning() && action === "install") {
                    // A MultiInstall job has finished
                    self.alertMultiInstallJobDone(response);
                } else {
                    self._markDone();
                }
            } else {
                self._markDone(response.reason, response.faq);
            }

            self._displayPluginManagementNotification(response, action, plugin);
        };

        self._displayPluginManagementNotification = function (response, action, plugin) {
            self.logContents.action.restart =
                self.logContents.action.restart || response.needs_restart;
            self.logContents.action.refresh =
                self.logContents.action.refresh || response.needs_refresh;
            self.logContents.action_reconnect =
                self.logContents.action.reconnect || response.needs_reconnect;
            self.logContents.steps.push({
                action: action,
                plugin: plugin,
                result: response.result,
                faq: response.faq
            });

            var title = gettext("Plugin management log");
            var text = "<p><ul>";

            var steps = self.logContents.steps;
            if (steps.length > 5) {
                var count = steps.length - 5;
                var line;
                if (count > 1) {
                    line = gettext("%(count)d earlier actions...");
                } else {
                    line = gettext("%(count)d earlier action");
                }
                text += "<li><em>" + _.sprintf(line, {count: count}) + "</em></li>";
                steps = steps.slice(steps.length - 5);
            }

            var negativeResult = false;
            _.each(steps, function (step) {
                var line = undefined;

                switch (step.action) {
                    case "install": {
                        line = gettext("Install <em>%(plugin)s</em>: %(result)s");
                        break;
                    }
                    case "uninstall": {
                        line = gettext("Uninstall <em>%(plugin)s</em>: %(result)s");
                        break;
                    }
                    case "enable": {
                        line = gettext("Enable <em>%(plugin)s</em>: %(result)s");
                        break;
                    }
                    case "disable": {
                        line = gettext("Disable <em>%(plugin)s</em>: %(result)s");
                        break;
                    }
                    case "cleanup": {
                        line = gettext("Cleanup <em>%(plugin)s</em>: %(result)s");
                        break;
                    }
                    case "cleanup_all": {
                        line = gettext("Cleanup all: %(result)s");
                        break;
                    }
                    default: {
                        return;
                    }
                }

                text +=
                    "<li>" +
                    _.sprintf(line, {
                        plugin: _.escape(step.plugin),
                        result: step.result
                            ? '<i class="fa fa-check"></i>'
                            : '<i class="fa fa-remove"></i>'
                    }) +
                    (step.result === false && step.faq
                        ? ' (<a href="" target="_blank" rel="noopener noreferer">' +
                          gettext("Why?") +
                          "</a>)"
                        : "") +
                    "</li>";

                negativeResult = negativeResult || step.result === false;
            });
            text += "</ul></p>";

            var confirm = undefined;
            var type = "success";
            if (self.logContents.action.restart) {
                text +=
                    "<p>" +
                    gettext("A restart is needed for the changes to take effect.") +
                    "</p>";
                type = "warning";

                if (self.restartCommandSpec && !self.multiInstallRunning()) {
                    var restartClicked = false;
                    confirm = {
                        confirm: true,
                        buttons: [
                            {
                                text: gettext("Restart now"),
                                click: function (notice) {
                                    if (restartClicked) return;
                                    restartClicked = true;
                                    showConfirmationDialog({
                                        message: gettext(
                                            "<strong>This will restart your OctoPrint server.</strong></p><p>This action may disrupt any ongoing print jobs (depending on your printer's controller and general setup that might also apply to prints run directly from your printer's internal storage)."
                                        ),
                                        onproceed: function () {
                                            OctoPrint.system
                                                .executeCommand("core", "restart")
                                                .done(function () {
                                                    notice.remove();
                                                    new PNotify({
                                                        title: gettext(
                                                            "Restart in progress"
                                                        ),
                                                        text: gettext(
                                                            "The server is now being restarted in the background"
                                                        )
                                                    });
                                                })
                                                .fail(function () {
                                                    new PNotify({
                                                        title: gettext(
                                                            "Something went wrong"
                                                        ),
                                                        text: gettext(
                                                            "Trying to restart the server produced an error, please check octoprint.log for details. You'll have to restart manually."
                                                        )
                                                    });
                                                });
                                        },
                                        onclose: function () {
                                            restartClicked = false;
                                        }
                                    });
                                }
                            }
                        ]
                    };
                }
            } else if (self.logContents.action.refresh) {
                text +=
                    "<p>" +
                    gettext("A refresh is needed for the changes to take effect.") +
                    "</p>";
                type = "warning";

                if (!self.multiInstallRunning()) {
                    var refreshClicked = false;
                    confirm = {
                        confirm: true,
                        buttons: [
                            {
                                text: gettext("Reload now"),
                                click: function () {
                                    if (refreshClicked) return;
                                    refreshClicked = true;
                                    location.reload(true);
                                }
                            }
                        ]
                    };
                }
            } else if (self.logContents.action_reconnect) {
                text +=
                    "<p>" +
                    gettext(
                        "A reconnect to the printer is needed for the changes to take effect."
                    ) +
                    "</p>";
                type = "warning";
            }

            if (negativeResult) type = "error";

            var options = {
                title: title,
                text: text,
                type: type,
                hide: false
            };

            if (confirm !== undefined) {
                options.confirm = confirm;

                if (self.logNotification === undefined) {
                    self.logNotification = PNotify.singleButtonNotify(options);
                } else {
                    self.logNotification.update(options);
                    self.logNotification = PNotify.fixSingleButton(
                        self.logNotification,
                        options
                    );
                }
            } else {
                if (self.logNotification === undefined) {
                    self.logNotification = new PNotify(options);
                } else {
                    self.logNotification.update(options);
                }
            }

            // make sure the notification is visible
            if (
                self.logNotification.state !== "open" &&
                self.logNotification.state !== "opening"
            ) {
                self.logNotification.open();
            }
        };

        self._markWorking = function (title, line) {
            self.working(true);
            self.workingTitle(title);

            self.loglines.removeAll();
            self.loglines.push({line: line, stream: "message"});
            self._scrollWorkingOutputToEnd();

            self.workingDialog.modal({keyboard: false, backdrop: "static", show: true});
        };

        self._markDone = function (error, faq) {
            self.working(false);
            if (error) {
                self.loglines.push({line: gettext("Error!"), stream: "error"});
                self.loglines.push({line: error, stream: "error"});
                if (faq) {
                    self.loglines.push({
                        line: _.sprintf(
                            gettext(
                                "You can find more info on this issue in the FAQ at %(url)s"
                            ),
                            {url: faq}
                        ),
                        stream: "error"
                    });
                }
            } else {
                self.loglines.push({line: gettext("Done!"), stream: "message"});
            }
            self._scrollWorkingOutputToEnd();
        };

        self._scrollWorkingOutputToEnd = function () {
            self.workingOutput.scrollTop(
                self.workingOutput[0].scrollHeight - self.workingOutput.height()
            );
        };

        self._getToggleCommand = function (data) {
            var disable =
                (data.enabled ||
                    (data.safe_mode_victim && !data.forced_disabled) ||
                    data.pending_enable) &&
                !data.pending_disable;
            return disable ? "disable" : "enable";
        };

        self.toggleButtonCss = function (data) {
            var icon, disabled;

            if (self.toggling()) {
                icon = "fa fa-spin fa-spinner";
                disabled = " disabled";
            } else {
                icon =
                    self._getToggleCommand(data) === "enable"
                        ? "fa fa-toggle-off"
                        : "fa fa-toggle-on";
                disabled = self.enableToggle(data) ? "" : " disabled";
            }

            return icon + disabled;
        };

        self.toggleButtonTitle = function (data) {
            var command = self._getToggleCommand(data);
            if (command === "enable") {
                if (data.blacklisted) {
                    return gettext("Blacklisted");
                } else if (data.safe_mode_victim) {
                    return gettext("Disabled due to active safe mode");
                } else {
                    return gettext("Enable Plugin");
                }
            } else {
                return gettext("Disable Plugin");
            }
        };

        self.showPluginNotifications = function (plugin) {
            if (!plugin.notifications || plugin.notifications.length === 0) return;

            self._removeAllNoticeNotificationsForPlugin(plugin.key);
            _.each(plugin.notifications, function (notification) {
                self._showPluginNotification(plugin, notification);
            });
        };

        self.showPluginNotificationsLinkText = function (plugins) {
            if (!plugins.notifications || plugins.notifications.length === 0) return;

            var count = plugins.notifications.length;
            var importantCount = _.filter(plugins.notifications, function (notification) {
                return notification.important;
            }).length;
            if (count > 1) {
                if (importantCount) {
                    return _.sprintf(
                        gettext(
                            "There are %(count)d notices (%(important)d marked as important) available regarding this plugin - click to show!"
                        ),
                        {count: count, important: importantCount}
                    );
                } else {
                    return _.sprintf(
                        gettext(
                            "There are %(count)d notices available regarding this plugin - click to show!"
                        ),
                        {count: count}
                    );
                }
            } else {
                if (importantCount) {
                    return gettext(
                        "There is an important notice available regarding this plugin - click to show!"
                    );
                } else {
                    return gettext(
                        "There is a notice available regarding this plugin - click to show!"
                    );
                }
            }
        };

        self._showPluginNotification = function (plugin, notification) {
            var name = plugin.name;
            var version = plugin.version;

            var important = notification.important;
            var link = notification.link;

            var title;
            if (important) {
                title = _.sprintf(
                    gettext('Important notice regarding plugin "%(name)s"'),
                    {name: _.escape(name)}
                );
            } else {
                title = _.sprintf(gettext('Notice regarding plugin "%(name)s"'), {
                    name: _.escape(name)
                });
            }

            var text = "";

            if (notification.versions && notification.versions.length > 0) {
                var versions = _.map(notification.versions, function (v) {
                    return v === version
                        ? "<strong>" + _.escape(v) + "</strong>"
                        : _.escape(v);
                }).join(", ");
                text +=
                    "<small>" +
                    _.sprintf(gettext("Affected versions: %(versions)s"), {
                        versions: versions
                    }) +
                    "</small>";
            } else {
                text += "<small>" + gettext("Affected versions: all") + "</small>";
            }

            text += "<p>" + notification.text + "</p>";
            if (link) {
                text +=
                    "<p><a href='" +
                    link +
                    "' target='_blank'>" +
                    gettext("Read more...") +
                    "</a></p>";
            }

            var beforeClose = function (notification) {
                if (!self.noticeNotifications[plugin.key]) return;
                self.noticeNotifications[plugin.key] = _.without(
                    self.noticeNotifications[plugin.key],
                    notification
                );
            };

            var options = {
                title: title,
                text: text,
                type: important ? "error" : "notice",
                before_close: beforeClose,
                hide: false,
                confirm: {
                    confirm: true,
                    buttons: [
                        {
                            text: gettext("Later"),
                            click: function (notice) {
                                self._hideNoticeNotification(
                                    plugin.key,
                                    notification.date
                                );
                                notice.remove();
                                notice.get().trigger("pnotify.cancel", notice);
                            }
                        },
                        {
                            text: gettext("Mark read"),
                            click: function (notice) {
                                self._ignoreNoticeNotification(
                                    plugin.key,
                                    notification.date
                                );
                                notice.remove();
                                notice.get().trigger("pnotify.cancel", notice);
                            }
                        }
                    ]
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

        self._removeAllNoticeNotifications = function () {
            _.each(_.keys(self.noticeNotifications), function (key) {
                self._removeAllNoticeNotificationsForPlugin(key);
            });
        };

        self._removeAllNoticeNotificationsForPlugin = function (key) {
            if (!self.noticeNotifications[key] || !self.noticeNotifications[key].length)
                return;
            _.each(self.noticeNotifications[key], function (notification) {
                notification.remove();
            });
        };

        self._hideNoticeNotification = function (key, date) {
            if (!self.hiddenNoticeNotifications[key]) {
                self.hiddenNoticeNotifications[key] = [];
            }
            if (!_.contains(self.hiddenNoticeNotifications[key], date)) {
                self.hiddenNoticeNotifications[key].push(date);
            }
        };

        self._isNoticeNotificationHidden = function (key, date) {
            if (!self.hiddenNoticeNotifications[key]) return false;
            return _.any(
                _.map(self.hiddenNoticeNotifications[key], function (d) {
                    return date === d;
                })
            );
        };

        var noticeLocalStorageKey = "plugin.pluginmanager.seen_notices";
        self._ignoreNoticeNotification = function (key, date) {
            if (!Modernizr.localstorage) return false;
            if (!self.loginState.isAdmin()) return false;

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

        self._isNoticeNotificationIgnored = function (key, date) {
            if (!Modernizr.localstorage) return false;

            if (localStorage[noticeLocalStorageKey] === undefined) return false;

            var knownData = JSON.parse(localStorage[noticeLocalStorageKey]);

            if (!self.loginState.isAdmin()) return true;

            var userData = knownData[self.loginState.username()];
            if (userData === undefined) return false;

            return userData[key] && _.contains(userData[key], date);
        };

        self.onBeforeBinding = function () {
            self.settings = self.settingsViewModel.settings;
        };

        self.onUserPermissionsChanged =
            self.onUserLoggedIn =
            self.onUserLoggedOut =
                function () {
                    if (
                        self.loginState.hasPermission(
                            self.access.permissions.PLUGIN_PLUGINMANAGER_MANAGE
                        )
                    ) {
                        self.requestPluginData({eval_notices: true});
                    } else {
                        self._resetNotifications();
                    }
                };

        self.onSettingsShown = function () {
            if (
                self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_PLUGINMANAGER_MANAGE
                )
            ) {
                self.requestRepositoryData();
                self.requestOrphanData();
            }
        };

        self.onEventConnectivityChanged = function (payload) {
            self.requestPluginData({eval_notices: true});
        };

        self._resetNotifications = function () {
            self._closeAllNotifications();
            self.logContents.action.restart =
                self.logContents.action.reload =
                self.logContents.action.reconnect =
                    false;
            self.logContents.steps = [];
        };

        self._closeAllNotifications = function () {
            if (self.logNotification) {
                self.logNotification.remove();
            }
        };

        self.onServerDisconnect = function () {
            self._resetNotifications();
            return true;
        };

        self.onStartup = function () {
            self.workingDialog = $("#settings_plugin_pluginmanager_workingdialog");
            self.workingOutput = $("#settings_plugin_pluginmanager_workingdialog_output");
            self.repositoryDialog = $("#settings_plugin_pluginmanager_repositorydialog");
        };

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin !== "pluginmanager") {
                return;
            }

            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_PLUGINMANAGER_MANAGE
                )
            ) {
                return;
            }

            if (!data.hasOwnProperty("type")) {
                return;
            }

            var messageType = data.type;

            if (
                messageType === "loglines" &&
                (self.working() || self.queuedInstalls().length > 0)
            ) {
                _.each(data.loglines, function (line) {
                    self.loglines.push(self._preprocessLine(line));
                });
                self._scrollWorkingOutputToEnd();
            } else if (messageType === "result") {
                var action = data.action;
                var name = "Unknown";
                if (data.hasOwnProperty("plugin")) {
                    if (data.plugin !== "unknown") {
                        if (_.isPlainObject(data.plugin)) {
                            name = data.plugin.name;
                        } else {
                            name = data.plugin;
                        }
                    }
                }

                self._processPluginManagementResult(data, action, name);
                self.requestPluginData();
            } else if (messageType === "queued_installs") {
                if (data.hasOwnProperty("queued")) {
                    self.queuedInstalls(data.queued);
                    var queuedInstallsPopupOptions = {
                        title: gettext("Queued Installs"),
                        text: "",
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

                    if (data.print_failed && data.queued.length > 0) {
                        queuedInstallsPopupOptions.title = gettext(
                            "Queued Installs Paused"
                        );
                        queuedInstallsPopupOptions.text =
                            '<div class="row-fluid"><p>' +
                            gettext("The following plugins are queued to be installed.") +
                            "</p><ul><li>" +
                            _.map(self.queuedInstalls(), function (info) {
                                var plugin = ko.utils.arrayFirst(
                                    self.repositoryplugins.paginatedItems(),
                                    function (item) {
                                        return item.archive === info.url;
                                    }
                                );
                                return plugin.title;
                            }).join("</li><li>") +
                            "</li></ul></div>";
                        queuedInstallsPopupOptions.confirm = {
                            confirm: true,
                            buttons: [
                                {
                                    text: gettext("Continue Installs"),
                                    addClass: "btn-block btn-primary",
                                    promptTrigger: true,
                                    click: function (notice, value) {
                                        notice.remove();
                                        notice
                                            .get()
                                            .trigger("pnotify.continue", [notice, value]);
                                    }
                                },
                                {
                                    text: gettext("Cancel Installs"),
                                    addClass: "btn-block btn-danger",
                                    promptTrigger: true,
                                    click: function (notice, value) {
                                        notice.remove();
                                        notice
                                            .get()
                                            .trigger("pnotify.cancel", [notice, value]);
                                    }
                                }
                            ]
                        };
                    } else if (
                        data.hasOwnProperty("timeout_value") &&
                        data.timeout_value > 0 &&
                        data.queued.length > 0
                    ) {
                        var progress_percent = Math.floor(
                            (data.timeout_value / 60) * 100
                        );
                        var progress_class =
                            progress_percent < 25
                                ? "progress-danger"
                                : progress_percent > 75
                                ? "progress-success"
                                : "progress-warning";
                        var countdownText = _.sprintf(
                            gettext("Installing in %(sec)i secs..."),
                            {
                                sec: data.timeout_value
                            }
                        );

                        queuedInstallsPopupOptions.title = gettext(
                            "Starting Queued Installs"
                        );
                        queuedInstallsPopupOptions.text =
                            '<div class="row-fluid"><p>' +
                            gettext("The following plugins are going to be installed.") +
                            "</p><ul><li>" +
                            _.map(self.queuedInstalls(), function (info) {
                                var plugin = ko.utils.arrayFirst(
                                    self.repositoryplugins.paginatedItems(),
                                    function (item) {
                                        return item.archive === info.url;
                                    }
                                );
                                return plugin.title;
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
                        queuedInstallsPopupOptions.confirm = {
                            confirm: true,
                            buttons: [
                                {
                                    text: gettext("Cancel Installs"),
                                    addClass: "btn-block btn-danger",
                                    promptTrigger: true,
                                    click: function (notice, value) {
                                        notice.remove();
                                        notice
                                            .get()
                                            .trigger("pnotify.cancel", [notice, value]);
                                    }
                                },
                                {
                                    text: "",
                                    addClass: "hidden"
                                }
                            ]
                        };
                    } else if (
                        data.hasOwnProperty("timeout_value") &&
                        data.timeout_value === 0 &&
                        data.queued.length > 0
                    ) {
                        self.multiInstallRunning(true);
                        self._markWorking(
                            gettext("Installing queued plugins"),
                            gettext("Starting installation of multiple plugins...")
                        );
                        self.queuedInstallsPopup.remove();
                        self.queuedInstallsPopup = undefined;
                        return;
                    } else {
                        if (typeof self.queuedInstallsPopup !== "undefined") {
                            self.queuedInstallsPopup.remove();
                            self.queuedInstallsPopup = undefined;
                        }
                        return;
                    }

                    if (typeof self.queuedInstallsPopup !== "undefined") {
                        self.queuedInstallsPopup.update(queuedInstallsPopupOptions);
                    } else {
                        self.queuedInstallsPopup = new PNotify(
                            queuedInstallsPopupOptions
                        );
                        self.queuedInstallsPopup.get().on("pnotify.cancel", function () {
                            self.queuedInstallsPopup = undefined;
                            self.cancelQueuedInstalls();
                        });
                        self.queuedInstallsPopup
                            .get()
                            .on("pnotify.continue", function () {
                                self.queuedInstallsPopup = undefined;
                                self.performQueuedInstalls();
                            });
                    }
                }
            }
        };

        self.cancelQueuedInstalls = function () {
            OctoPrint.simpleApiCommand("pluginmanager", "clear_queued_installs", {}).done(
                function (response) {
                    self.queuedInstalls(response.queued_installs);
                }
            );
        };

        self.installQueued = function (plugin) {
            var plugin_queued = ko.utils.arrayFirst(
                self.queuedInstalls(),
                function (item) {
                    return item.url === plugin.archive;
                }
            );
            return typeof plugin_queued !== "undefined";
        };

        self.performQueuedInstalls = function () {
            self.queuedInstalls().forEach(function (plugin) {
                var queued_plugin = ko.utils.arrayFirst(
                    self.repositoryplugins.paginatedItems(),
                    function (item) {
                        return plugin.url === item.archive;
                    }
                );
                self.multiInstallQueue.push(queued_plugin);
            });
            self.startMultiInstall();
        };

        self._forcedStdoutLine =
            /You are using pip version .*?, however version .*? is available\.|You should consider upgrading via the '.*?' command\./;
        self._preprocessLine = function (line) {
            if (line.stream === "stderr" && line.line.match(self._forcedStdoutLine)) {
                line.stream = "stdout";
            }
            return line;
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: PluginManagerViewModel,
        dependencies: [
            "loginStateViewModel",
            "settingsViewModel",
            "printerStateViewModel",
            "systemViewModel",
            "accessViewModel",
            "piSupportViewModel"
        ],
        optional: ["piSupportViewModel"],
        elements: ["#settings_plugin_pluginmanager"]
    });
});
