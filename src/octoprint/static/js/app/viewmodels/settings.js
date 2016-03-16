$(function() {
    function SettingsViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.users = parameters[1];
        self.printerProfiles = parameters[2];

        self.allViewModels = [];

        self.receiving = ko.observable(false);
        self.sending = ko.observable(false);
        self.exchanging = ko.pureComputed(function() {
            return self.receiving() || self.sending();
        });
        self.outstanding = [];

        self.settingsDialog = undefined;
        self.settings_dialog_update_detected = undefined;
        self.translationManagerDialog = undefined;
        self.translationUploadElement = $("#settings_appearance_managelanguagesdialog_upload");
        self.translationUploadButton = $("#settings_appearance_managelanguagesdialog_upload_start");

        self.translationUploadFilename = ko.observable();
        self.invalidTranslationArchive = ko.pureComputed(function() {
            var name = self.translationUploadFilename();
            return name !== undefined && !(_.endsWith(name.toLocaleLowerCase(), ".zip") || _.endsWith(name.toLocaleLowerCase(), ".tar.gz") || _.endsWith(name.toLocaleLowerCase(), ".tgz") || _.endsWith(name.toLocaleLowerCase(), ".tar"));
        });
        self.enableTranslationUpload = ko.pureComputed(function() {
            var name = self.translationUploadFilename();
            return name !== undefined && name.trim() != "" && !self.invalidTranslationArchive();
        });

        self.translations = new ItemListHelper(
            "settings.translations",
            {
                "locale": function (a, b) {
                    // sorts ascending
                    if (a["locale"].toLocaleLowerCase() < b["locale"].toLocaleLowerCase()) return -1;
                    if (a["locale"].toLocaleLowerCase() > b["locale"].toLocaleLowerCase()) return 1;
                    return 0;
                }
            },
            {
            },
            "locale",
            [],
            [],
            0
        );

        self.appearance_available_colors = ko.observable([
            {key: "default", name: gettext("default")},
            {key: "red", name: gettext("red")},
            {key: "orange", name: gettext("orange")},
            {key: "yellow", name: gettext("yellow")},
            {key: "green", name: gettext("green")},
            {key: "blue", name: gettext("blue")},
            {key: "violet", name: gettext("violet")},
            {key: "black", name: gettext("black")},
            {key: "white", name: gettext("white")},
        ]);

        self.appearance_colorName = function(color) {
            switch (color) {
                case "red":
                    return gettext("red");
                case "orange":
                    return gettext("orange");
                case "yellow":
                    return gettext("yellow");
                case "green":
                    return gettext("green");
                case "blue":
                    return gettext("blue");
                case "violet":
                    return gettext("violet");
                case "black":
                    return gettext("black");
                case "white":
                    return gettext("white");
                case "default":
                    return gettext("default");
                default:
                    return color;
            }
        };

        var auto_locale = {language: "_default", display: gettext("Autodetect from browser"), english: undefined};
        self.locales = ko.observableArray([auto_locale].concat(_.sortBy(_.values(AVAILABLE_LOCALES), function(n) {
            return n.display;
        })));
        self.locale_languages = _.keys(AVAILABLE_LOCALES);

        self.api_enabled = ko.observable(undefined);
        self.api_key = ko.observable(undefined);
        self.api_allowCrossOrigin = ko.observable(undefined);

        self.appearance_name = ko.observable(undefined);
        self.appearance_color = ko.observable(undefined);
        self.appearance_colorTransparent = ko.observable();
        self.appearance_defaultLanguage = ko.observable();

        self.printer_defaultExtrusionLength = ko.observable(undefined);

        self.webcam_streamUrl = ko.observable(undefined);
        self.webcam_snapshotUrl = ko.observable(undefined);
        self.webcam_ffmpegPath = ko.observable(undefined);
        self.webcam_bitrate = ko.observable(undefined);
        self.webcam_ffmpegThreads = ko.observable(undefined);
        self.webcam_watermark = ko.observable(undefined);
        self.webcam_flipH = ko.observable(undefined);
        self.webcam_flipV = ko.observable(undefined);
        self.webcam_rotate90 = ko.observable(undefined);

        self.feature_gcodeViewer = ko.observable(undefined);
        self.feature_temperatureGraph = ko.observable(undefined);
        self.feature_waitForStart = ko.observable(undefined);
        self.feature_sendChecksum = ko.observable("print");
        self.feature_sdSupport = ko.observable(undefined);
        self.feature_sdAlwaysAvailable = ko.observable(undefined);
        self.feature_swallowOkAfterResend = ko.observable(undefined);
        self.feature_repetierTargetTemp = ko.observable(undefined);
        self.feature_disableExternalHeatupDetection = ko.observable(undefined);
        self.feature_keyboardControl = ko.observable(undefined);
        self.feature_pollWatched = ko.observable(undefined);
        self.feature_ignoreIdenticalResends = ko.observable(undefined);

        self.serial_port = ko.observable();
        self.serial_baudrate = ko.observable();
        self.serial_portOptions = ko.observableArray([]);
        self.serial_baudrateOptions = ko.observableArray([]);
        self.serial_autoconnect = ko.observable(undefined);
        self.serial_timeoutConnection = ko.observable(undefined);
        self.serial_timeoutDetection = ko.observable(undefined);
        self.serial_timeoutCommunication = ko.observable(undefined);
        self.serial_timeoutTemperature = ko.observable(undefined);
        self.serial_timeoutTemperatureTargetSet = ko.observable(undefined);
        self.serial_timeoutSdStatus = ko.observable(undefined);
        self.serial_log = ko.observable(undefined);
        self.serial_additionalPorts = ko.observable(undefined);
        self.serial_additionalBaudrates = ko.observable(undefined);
        self.serial_longRunningCommands = ko.observable(undefined);
        self.serial_checksumRequiringCommands = ko.observable(undefined);
        self.serial_helloCommand = ko.observable(undefined);
        self.serial_ignoreErrorsFromFirmware = ko.observable(undefined);
        self.serial_disconnectOnErrors = ko.observable(undefined);
        self.serial_triggerOkForM29 = ko.observable(undefined);

        self.folder_uploads = ko.observable(undefined);
        self.folder_timelapse = ko.observable(undefined);
        self.folder_timelapseTmp = ko.observable(undefined);
        self.folder_logs = ko.observable(undefined);
        self.folder_watched = ko.observable(undefined);

        self.scripts_gcode_beforePrintStarted = ko.observable(undefined);
        self.scripts_gcode_afterPrintDone = ko.observable(undefined);
        self.scripts_gcode_afterPrintCancelled = ko.observable(undefined);
        self.scripts_gcode_afterPrintPaused = ko.observable(undefined);
        self.scripts_gcode_beforePrintResumed = ko.observable(undefined);
        self.scripts_gcode_afterPrinterConnected = ko.observable(undefined);
        self.scripts_gcode_beforePrinterDisconnected = ko.observable(undefined);

        self.temperature_profiles = ko.observableArray(undefined);
        self.temperature_cutoff = ko.observable(undefined);

        self.system_actions = ko.observableArray([]);

        self.terminalFilters = ko.observableArray([]);

        self.server_commands_systemShutdownCommand = ko.observable(undefined);
        self.server_commands_systemRestartCommand = ko.observable(undefined);
        self.server_commands_serverRestartCommand = ko.observable(undefined);

        self.server_diskspace_warning = ko.observable();
        self.server_diskspace_critical = ko.observable();
        self.server_diskspace_warning_str = sizeObservable(self.server_diskspace_warning);
        self.server_diskspace_critical_str = sizeObservable(self.server_diskspace_critical);

        self.settings = undefined;
        self.lastReceivedSettings = undefined;

        self.webcam_ffmpegPathText = ko.observable();
        self.webcam_ffmpegPathOk = ko.observable(false);
        self.webcam_ffmpegPathBroken = ko.observable(false);
        self.webcam_ffmpegPathReset = function() {
            self.webcam_ffmpegPathText("");
            self.webcam_ffmpegPathOk(false);
            self.webcam_ffmpegPathBroken(false);
        };

        self.addTemperatureProfile = function() {
            self.temperature_profiles.push({name: "New", extruder:0, bed:0});
        };

        self.removeTemperatureProfile = function(profile) {
            self.temperature_profiles.remove(profile);
        };

        self.addTerminalFilter = function() {
            self.terminalFilters.push({name: "New", regex: "(Send: M105)|(Recv: ok T:)"})
        };

        self.removeTerminalFilter = function(filter) {
            self.terminalFilters.remove(filter);
        };

        self.testWebcamStreamUrl = function() {
            if (!self.webcam_streamUrl()) {
                return;
            }

            var text = gettext("If you see your webcam stream below, the entered stream URL is ok.");
            var image = $('<img src="' + self.webcam_streamUrl() + '">');
            var message = $("<p></p>")
                .append(text)
                .append(image);
            showMessageDialog({
                title: gettext("Stream test"),
                message: message
            });
        };

        self.testWebcamSnapshotUrl = function(viewModel, event) {
            if (!self.webcam_snapshotUrl()) {
                return;
            }

            var target = $(event.target);
            target.prepend('<i class="icon-spinner icon-spin"></i> ');

            var errorText = gettext("Could not retrieve snapshot URL, please double check the URL");
            var errorTitle = gettext("Snapshot test failed");

            OctoPrint.util.testUrl(self.webcam_snapshotUrl(), {method: "GET", response: true})
                .done(function(response) {
                    $("i.icon-spinner", target).remove();

                    if (!response.result) {
                        showMessageDialog({
                            title: errorTitle,
                            message: errorText
                        });
                        return;
                    }

                    var content = response.response.content;
                    var mimeType = "image/jpeg";

                    var headers = response.response.headers;
                    if (headers && headers["mime-type"]) {
                        mimeType = headers["mime-type"];
                    }

                    var text = gettext("If you see your webcam snapshot picture below, the entered snapshot URL is ok.");
                    showMessageDialog({
                        title: gettext("Snapshot test"),
                        message: $('<p>' + text + '</p><p><img src="data:' + mimeType + ';base64,' + content + '" /></p>')
                    });
                })
                .fail(function() {
                    $("i.icon-spinner", target).remove();
                    showMessageDialog({
                        title: errorTitle,
                        message: errorText
                    });
                });
        };

        self.testWebcamFfmpegPath = function() {
            if (!self.webcam_ffmpegPath()) {
                return;
            }

            OctoPrint.util.testExecutable(self.webcam_ffmpegPath())
                .done(function(response) {
                    if (!response.result) {
                        if (!response.exists) {
                            self.webcam_ffmpegPathText(gettext("The path doesn't exist"));
                        } else if (!response.typeok) {
                            self.webcam_ffmpegPathText(gettext("The path is not a file"));
                        } else if (!response.access) {
                            self.webcam_ffmpegPathText(gettext("The path is not an executable"));
                        }
                    } else {
                        self.webcam_ffmpegPathText(gettext("The path is valid"));
                    }
                    self.webcam_ffmpegPathOk(response.result);
                    self.webcam_ffmpegPathBroken(!response.result);
                });
        };

        self.onSettingsShown = function() {
            self.requestData();
        };

        self.onSettingsHidden = function() {
            self.webcam_ffmpegPathReset();
        };

        self.isDialogActive = function() {
            return self.settingsDialog.is(":visible");
        };

        self.onStartup = function() {
            self.settingsDialog = $('#settings_dialog');
            self.settingsUpdatedDialog = $('#settings_dialog_update_detected');
            self.translationManagerDialog = $('#settings_appearance_managelanguagesdialog');
            self.translationUploadElement = $("#settings_appearance_managelanguagesdialog_upload");
            self.translationUploadButton = $("#settings_appearance_managelanguagesdialog_upload_start");

            self.translationUploadElement.fileupload({
                dataType: "json",
                maxNumberOfFiles: 1,
                autoUpload: false,
                headers: OctoPrint.getRequestHeaders(),
                add: function(e, data) {
                    if (data.files.length == 0) {
                        return false;
                    }

                    self.translationUploadFilename(data.files[0].name);

                    self.translationUploadButton.unbind("click");
                    self.translationUploadButton.bind("click", function() {
                        data.submit();
                        return false;
                    });
                },
                done: function(e, data) {
                    self.translationUploadButton.unbind("click");
                    self.translationUploadFilename(undefined);
                    self.fromTranslationResponse(data.result);
                },
                fail: function(e, data) {
                    self.translationUploadButton.unbind("click");
                    self.translationUploadFilename(undefined);
                }
            });
        };

        self.onAllBound = function(allViewModels) {
            self.allViewModels = allViewModels;

            self.settingsDialog.on('show', function(event) {
                if (event.target.id == "settings_dialog") {
                    self.requestTranslationData();
                    callViewModels(allViewModels, "onSettingsShown");
                }
            });
            self.settingsDialog.on('hidden', function(event) {
                if (event.target.id == "settings_dialog") {
                    callViewModels(allViewModels, "onSettingsHidden");
                }
            });
            self.settingsDialog.on('beforeSave', function () {
                callViewModels(allViewModels, "onSettingsBeforeSave");
            });

            $(".reload_all", self.settingsUpdatedDialog).click(function(e) {
                e.preventDefault();
                self.settingsUpdatedDialog.modal("hide");
                self.requestData();
                return false;
            });
            $(".reload_nonconflicts", self.settingsUpdatedDialog).click(function(e) {
                e.preventDefault();
                self.settingsUpdatedDialog.modal("hide");
                self.requestData(undefined, true);
                return false;
            });

            // reset scroll position on tab change
            $('ul.nav-list a[data-toggle="tab"]', self.settingsDialog).on("show", function() {
                self._resetScrollPosition();
            });
        };

        self.show = function(tab) {
            // select first or specified tab
            self.selectTab(tab);

            // reset scroll position
            self._resetScrollPosition();

            // show settings, ensure centered position
            self.settingsDialog.modal({
                minHeight: function() { return Math.max($.fn.modal.defaults.maxHeight() - 80, 250); }
            }).css({
                width: 'auto',
                'margin-left': function() { return -($(this).width() /2); }
            });

            return false;
        };

        self.hide = function() {
            self.settingsDialog.modal("hide");
        };

        self.showTranslationManager = function() {
            self.translationManagerDialog.modal();
            return false;
        };

        self.requestData = function(local) {
            // handle old parameter format
            var callback = undefined;
            if (arguments.length == 2 || _.isFunction(local)) {
                var exc = new Error();
                log.warn("The callback parameter of SettingsViewModel.requestData is deprecated, the method now returns a promise, please use that instead. Stacktrace:", (exc.stack || exc.stacktrace || "<n/a>"));

                if (arguments.length == 2) {
                    callback = arguments[0];
                    local = arguments[1];
                } else {
                    callback = local;
                    local = false;
                }
            }

            // handler for any explicitely provided callbacks
            var callbackHandler = function() {
                if (!callback) return;
                try {
                    callback();
                } catch (exc) {
                    log.error("Error calling settings callback", callback, ":", (exc.stack || exc.stacktrace || exc));
                }
            };

            // if a request is already active, create a new deferred and return
            // its promise, it will be resolved in the response handler of the
            // current request
            if (self.receiving()) {
                var deferred = $.Deferred();
                self.outstanding.push(deferred);

                if (callback) {
                    // if we have a callback, we need to make sure it will
                    // get called when the deferred is resolved
                    deferred.done(callbackHandler);
                }

                return deferred.promise();
            }

            // perform the request
            self.receiving(true);
            return OctoPrint.settings.get()
                .done(function(response) {
                    self.fromResponse(response, local);

                    if (callback) {
                        var deferred = $.Deferred();
                        deferred.done(callbackHandler);
                        self.outstanding.push(deferred);
                    }

                    // resolve all promises
                    var args = arguments;
                    _.each(self.outstanding, function(deferred) {
                        deferred.resolve(args);
                    });
                    self.outstanding = [];
                })
                .fail(function() {
                    // reject all promises
                    var args = arguments;
                    _.each(self.outstanding, function(deferred) {
                        deferred.reject(args);
                    });
                    self.outstanding = [];
                })
                .always(function() {
                    self.receiving(false);
                });
        };

        self.requestTranslationData = function() {
            return OctoPrint.languages.list()
                .done(self.fromTranslationResponse);
        };

        self.fromTranslationResponse = function(response) {
            var translationsByLocale = {};
            _.each(response.language_packs, function(item, key) {
                _.each(item.languages, function(pack) {
                    var locale = pack.locale;
                    if (!_.has(translationsByLocale, locale)) {
                        translationsByLocale[locale] = {
                            locale: locale,
                            display: pack.locale_display,
                            english: pack.locale_english,
                            packs: []
                        };
                    }

                    translationsByLocale[locale]["packs"].push({
                        identifier: key,
                        display: item.display,
                        pack: pack
                    });
                });
            });

            var translations = [];
            _.each(translationsByLocale, function(item) {
                item["packs"].sort(function(a, b) {
                    if (a.identifier == "_core") return -1;
                    if (b.identifier == "_core") return 1;

                    if (a.display < b.display) return -1;
                    if (a.display > b.display) return 1;
                    return 0;
                });
                translations.push(item);
            });

            self.translations.updateItems(translations);
        };

        self.languagePackDisplay = function(item) {
            return item.display + ((item.english != undefined) ? ' (' + item.english + ')' : '');
        };

        self.languagePacksAvailable = ko.pureComputed(function() {
            return self.translations.allSize() > 0;
        });

        self.deleteLanguagePack = function(locale, pack) {
            OctoPrint.languages.delete(locale, pack)
                .done(self.fromTranslationResponse);
        };

        /**
         * Fetches the settings as currently stored in this client instance.
         */
        self.getLocalData = function() {
            var data = {};
            if (self.settings != undefined) {
                data = ko.mapping.toJS(self.settings);
            }

            // some special read functions for various observables
            var specialMappings = {
                feature: {
                    externalHeatupDetection: function() { return !self.feature_disableExternalHeatupDetection()},
                    alwaysSendChecksum: function() { return self.feature_sendChecksum() == "always"},
                    neverSendChecksum: function() { return self.feature_sendChecksum() == "never"}
                },
                serial: {
                    additionalPorts : function() { return commentableLinesToArray(self.serial_additionalPorts()) },
                    additionalBaudrates: function() { return _.map(splitTextToArray(self.serial_additionalBaudrates(), ",", true, function(item) { return !isNaN(parseInt(item)); }), function(item) { return parseInt(item); }) },
                    longRunningCommands: function() { return splitTextToArray(self.serial_longRunningCommands(), ",", true) },
                    checksumRequiringCommands: function() { return splitTextToArray(self.serial_checksumRequiringCommands(), ",", true) }
                },
                scripts: {
                    gcode: function() {
                        // we have a special handler function for the gcode scripts since the
                        // server will always send us those that have been set already, so we
                        // can't depend on all keys that we support to be present in the
                        // original request we iterate through in mapFromObservables to
                        // generate our response - hence we use our observables instead
                        //
                        // Note: If we ever introduce sub categories in the gcode scripts
                        // here (more _ after the prefix), we'll need to adjust this code
                        // to be able to cope with that, right now it only strips the prefix
                        // and uses the rest as key in the result, no recursive translation
                        // is done!
                        var result = {};
                        var prefix = "scripts_gcode_";
                        var observables = _.filter(_.keys(self), function(key) { return _.startsWith(key, prefix); });
                        _.each(observables, function(observable) {
                            var script = observable.substring(prefix.length);
                            result[script] = self[observable]();
                        });
                        return result;
                    }
                }
            };

            var mapFromObservables = function(data, mapping, keyPrefix) {
                var flag = false;
                var result = {};

                // process all key-value-pairs here
                _.forOwn(data, function(value, key) {
                    var observable = key;
                    if (keyPrefix != undefined) {
                        observable = keyPrefix + "_" + observable;
                    }

                    if (mapping && mapping[key] && _.isFunction(mapping[key])) {
                        result[key] = mapping[key]();
                        flag = true;
                    } else if (_.isPlainObject(value)) {
                        // value is another object, we'll dive deeper
                        var subresult = mapFromObservables(value, (mapping && mapping[key]) ? mapping[key] : undefined, observable);
                        if (subresult != undefined) {
                            // we only set something on our result if we got something back
                            result[key] = subresult;
                            flag = true;
                        }
                    } else if (self.hasOwnProperty(observable)) {
                        result[key] = self[observable]();
                        flag = true;
                    }
                });

                // if we set something on our result (flag is true), we return result, else we return undefined
                return flag ? result : undefined;
            };

            // map local observables based on our existing data
            var dataFromObservables = mapFromObservables(data, specialMappings);

            data = _.extend(data, dataFromObservables);
            return data;
        };

        self.fromResponse = function(response, local) {
            // server side changes to set
            var serverChangedData;

            // client side changes to keep
            var clientChangedData;

            if (local) {
                // local is true, so we'll keep all local changes and only update what's been updated server side
                serverChangedData = getOnlyChangedData(response, self.lastReceivedSettings);
                clientChangedData = getOnlyChangedData(self.getLocalData(), self.lastReceivedSettings);
            } else  {
                // local is false or unset, so we'll forcefully update with the settings from the server
                serverChangedData = response;
                clientChangedData = undefined;
            }

            // last received settings reset to response
            self.lastReceivedSettings = response;

            if (self.settings === undefined) {
                self.settings = ko.mapping.fromJS(serverChangedData);
            } else {
                ko.mapping.fromJS(serverChangedData, self.settings);
            }

            // some special apply functions for various observables
            var specialMappings = {
                appearance: {
                    defaultLanguage: function(value) {
                        self.appearance_defaultLanguage("_default");
                        if (_.includes(self.locale_languages, value)) {
                            self.appearance_defaultLanguage(value);
                        }
                    }
                },
                feature: {
                    externalHeatupDetection: function(value) { self.feature_disableExternalHeatupDetection(!value) },
                    alwaysSendChecksum: function(value) { if (value) { self.feature_sendChecksum("always")}},
                    neverSendChecksum: function(value) { if (value) { self.feature_sendChecksum("never")}}
                },
                serial: {
                    additionalPorts : function(value) { self.serial_additionalPorts(value.join("\n"))},
                    additionalBaudrates: function(value) { self.serial_additionalBaudrates(value.join(", "))},
                    longRunningCommands: function(value) { self.serial_longRunningCommands(value.join(", "))},
                    checksumRequiringCommands: function(value) { self.serial_checksumRequiringCommands(value.join(", "))}
                },
                terminalFilters: function(value) { self.terminalFilters($.extend(true, [], value)) },
                temperature: {
                    profiles: function(value) { self.temperature_profiles($.extend(true, [], value)); }
                }
            };

            var mapToObservables = function(data, mapping, local, keyPrefix) {
                if (!_.isPlainObject(data)) {
                    return;
                }

                // process all key-value-pairs here
                _.forOwn(data, function(value, key) {
                    var observable = key;
                    if (keyPrefix != undefined) {
                        observable = keyPrefix + "_" + observable;
                    }

                    var haveLocalVersion = local && local.hasOwnProperty(key);

                    if (mapping && mapping[key] && _.isFunction(mapping[key]) && !haveLocalVersion) {
                        // if we have a custom apply function for this, we'll use it
                        mapping[key](value);
                    } else if (_.isPlainObject(value)) {
                        // value is another object, we'll dive deeper
                        mapToObservables(value, (mapping && mapping[key]) ? mapping[key] : undefined, (local && local[key]) ? local[key] : undefined, observable);
                    } else if (!haveLocalVersion && self.hasOwnProperty(observable)) {
                        // if we have a matching observable, we'll use that
                        self[observable](value);
                    }
                });
            };

            mapToObservables(serverChangedData, specialMappings, clientChangedData);
        };

        self.saveData = function (data, successCallback, setAsSending) {
            var options;
            if (_.isPlainObject(successCallback)) {
                options = successCallback;
            } else {
                options = {
                    success: successCallback,
                    sending: (setAsSending == true)
                }
            }

            self.settingsDialog.trigger("beforeSave");

            self.sending(data == undefined || options.sending || false);

            if (data == undefined) {
                // we also only send data that actually changed when no data is specified
                data = getOnlyChangedData(self.getLocalData(), self.lastReceivedSettings);
            }

            return OctoPrint.settings.save(data)
                .done(function(data, status, xhr) {
                    self.receiving(true);
                    self.sending(false);
                    try {
                        self.fromResponse(data);
                        if (options.success) options.success(data, status, xhr);
                    } finally {
                        self.receiving(false);
                    }
                })
                .fail(function(xhr, status, error) {
                    self.sending(false);
                    if (options.error) options.error(xhr, status, error);
                })
                .always(function(xhr, status) {
                    if (options.complete) options.complete(xhr, status);
                });
        };

        self.onEventSettingsUpdated = function() {
            var preventSettingsRefresh = _.any(self.allViewModels, function(viewModel) {
                if (viewModel.hasOwnProperty("onSettingsPreventRefresh")) {
                    try {
                        return viewModel["onSettingsPreventRefresh"]();
                    } catch (e) {
                        log.warn("Error while calling onSettingsPreventRefresh on", viewModel, ":", e);
                        return false;
                    }
                } else {
                    return false;
                }
            });

            if (preventSettingsRefresh) {
                // if any of our viewmodels prevented this refresh, we'll just return now
                return;
            }

            if (self.isDialogActive()) {
                // dialog is open and not currently busy...
                if (self.sending() || self.receiving()) {
                    return;
                }

                if (!hasDataChanged(self.getLocalData(), self.lastReceivedSettings)) {
                    // we don't have local changes, so just fetch new data
                    self.requestData();
                } else {
                    // we have local changes, show update dialog
                    self.settingsUpdatedDialog.modal("show");
                }
            } else {
                // dialog is not open, just fetch new data
                self.requestData();
            }
        };

        self._resetScrollPosition = function() {
            $('.scrollable', self.settingsDialog).scrollTop(0);
        };

        self.selectTab = function(tab) {
            if (tab != undefined) {
                if (!_.startsWith(tab, "#")) {
                    tab = "#" + tab;
                }
                $('ul.nav-list a[href="' + tab + '"]', self.settingsDialog).tab("show");
            } else {
                $('ul.nav-list a:first', self.settingsDialog).tab("show");
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        SettingsViewModel,
        ["loginStateViewModel", "usersViewModel", "printerProfilesViewModel"],
        ["#settings_dialog", "#navbar_settings"]
    ]);
});
