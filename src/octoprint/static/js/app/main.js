$(function() {
        //~~ Initialize i18n
        var catalog = window["BABEL_TO_LOAD_" + LOCALE];
        if (catalog === undefined) {
            catalog = {messages: undefined, plural_expr: undefined, locale: undefined, domain: undefined}
        }
        babel.Translations.load(catalog).install();

        moment.locale(LOCALE);

        // Dummy translation requests for dynamic strings supplied by the backend
        var dummyTranslations = [
            // printer states
            gettext("Offline"),
            gettext("Opening serial port"),
            gettext("Detecting serial port"),
            gettext("Detecting baudrate"),
            gettext("Connecting"),
            gettext("Operational"),
            gettext("Printing from SD"),
            gettext("Sending file to SD"),
            gettext("Printing"),
            gettext("Paused"),
            gettext("Closed"),
            gettext("Transfering file to SD")
        ];

        PNotify.prototype.options.styling = "bootstrap2";

        // work around a stupid iOS6 bug where ajax requests get cached and only work once, as described at
        // http://stackoverflow.com/questions/12506897/is-safari-on-ios-6-caching-ajax-results
        $.ajaxSetup({
            type: 'POST',
            headers: { "cache-control": "no-cache" }
        });

        // send the current UI API key with any request
        $.ajaxSetup({
            headers: {"X-Api-Key": UI_API_KEY}
        });

        //~~ Show settings - to ensure centered
        var settingsDialog = $('#settings_dialog');
        settingsDialog.on('show', function() {
            _.each(allViewModels, function(viewModel) {
                if (viewModel.hasOwnProperty("onSettingsShown")) {
                    viewModel.onSettingsShown();
                }
            });
        });
        settingsDialog.on('hidden', function() {
            _.each(allViewModels, function(viewModel) {
                if (viewModel.hasOwnProperty("onSettingsHidden")) {
                    viewModel.onSettingsHidden();
                }
            });
        });
        $('#navbar_show_settings').click(function() {
            settingsDialog.modal()
                .css({
                    width: 'auto',
                    'margin-left': function() { return -($(this).width() /2); }
                });

            return false;
        });

        //~~ Initialize view models
        var loginStateViewModel = new LoginStateViewModel();
        var printerProfilesViewModel = new PrinterProfilesViewModel();
        var usersViewModel = new UsersViewModel(loginStateViewModel);
        var timelapseViewModel = new TimelapseViewModel(loginStateViewModel);
        var printerStateViewModel = new PrinterStateViewModel(loginStateViewModel, timelapseViewModel);
        var settingsViewModel = new SettingsViewModel(loginStateViewModel, usersViewModel, printerProfilesViewModel);
        var connectionViewModel = new ConnectionViewModel(loginStateViewModel, settingsViewModel, printerProfilesViewModel);
        var appearanceViewModel = new AppearanceViewModel(settingsViewModel, printerStateViewModel);
        var temperatureViewModel = new TemperatureViewModel(loginStateViewModel, settingsViewModel);
        var controlViewModel = new ControlViewModel(loginStateViewModel, settingsViewModel);
        var terminalViewModel = new TerminalViewModel(loginStateViewModel, settingsViewModel);
        var slicingViewModel = new SlicingViewModel(loginStateViewModel, printerProfilesViewModel);
        var gcodeFilesViewModel = new GcodeFilesViewModel(printerStateViewModel, loginStateViewModel, slicingViewModel);
        var gcodeViewModel = new GcodeViewModel(loginStateViewModel, settingsViewModel);
        var navigationViewModel = new NavigationViewModel(loginStateViewModel, appearanceViewModel, settingsViewModel, usersViewModel);
        var logViewModel = new LogViewModel(loginStateViewModel);

        // the view model map is our basic look up table for dependencies that may be injected into other view models
        var viewModelMap = {
            loginStateViewModel: loginStateViewModel,
            printerProfilesViewModel: printerProfilesViewModel,
            usersViewModel: usersViewModel,
            settingsViewModel: settingsViewModel,
            connectionViewModel: connectionViewModel,
            timelapseViewModel: timelapseViewModel,
            printerStateViewModel: printerStateViewModel,
            appearanceViewModel: appearanceViewModel,
            temperatureViewModel: temperatureViewModel,
            controlViewModel: controlViewModel,
            terminalViewModel: terminalViewModel,
            gcodeFilesViewModel: gcodeFilesViewModel,
            gcodeViewModel: gcodeViewModel,
            navigationViewModel: navigationViewModel,
            logViewModel: logViewModel,
            slicingViewModel: slicingViewModel
        };

        // helper to create a view model instance with injected constructor parameters from the view model map
        var _createViewModelInstance = function(viewModel, viewModelMap){
            var viewModelClass = viewModel[0];
            var viewModelParameters = viewModel[1];

            // now we'll try to resolve all of the view model's constructor parameters via our view model map
            var constructorParameters = _.map(viewModelParameters, function(parameter){
                return viewModelMap[parameter]
            });

            if (_.some(constructorParameters, function(parameter) { return parameter === undefined; })) {
                var _extractName = function(entry) { return entry[0]; };
                var _onlyUnresolved = function(entry) { return entry[1] === undefined; };
                var missingParameters = _.map(_.filter(_.zip(viewModelParameters, constructorParameters), _onlyUnresolved), _extractName);
                console.log("postponing", viewModel[0].name, "due to missing parameters:", missingParameters.join(", "));
                return;
            }

            // if we came this far then we could resolve all constructor parameters, so let's construct that view model
            return new viewModelClass(constructorParameters);
        };

        // helper for translating the name of a view model class into an identifier for the view model map
        var _getViewModelId = function(viewModel){
            var name = viewModel[0].name;
            return name.substr(0, 1).toLowerCase() + name.substr(1); // FooBarViewModel => fooBarViewModel
        };

        // instantiation loop, will make multiple passes over the list of unprocessed view models until all
        // view models have been successfully instantiated with all of their dependencies or no changes can be made
        // any more which means not all view models can be instantiated due to missing dependencies
        var unprocessedViewModels = ADDITIONAL_VIEWMODELS.slice();
        var additionalViewModels = [];
        var pass = 1;
        while (unprocessedViewModels.length > 0) {
            console.log("View model dependency resolution, pass #" + pass++);
            var startLength = unprocessedViewModels.length;
            var postponed = [];

            // now try to instantiate every one of our as of yet unprocessed view model descriptors
            while (unprocessedViewModels.length > 0){
                var viewModel = unprocessedViewModels.shift();
                var viewModelId = _getViewModelId(viewModel);

                // make sure that we don't have to view models going by the same name
                if (_.has(viewModelMap, viewModelId)) {
                    console.error("Duplicate class name while instantiating viewModel ", viewModelId);
                    continue;
                }

                var viewModelInstance = _createViewModelInstance(viewModel, viewModelMap);

                // our view model couldn't yet be instantiated, so postpone it for a bit
                if (viewModelInstance === undefined) {
                    postponed.push(viewModel);
                    continue;
                }

                // we could resolve the depdendencies and the view model is not defined yet => add it, it's now fully processed
                var viewModelBindTarget = viewModel[2];
                additionalViewModels.push([viewModelInstance, viewModelBindTarget]);
                viewModelMap[viewModelId] = viewModelInstance;
            }

            // anything that's now in the postponed list has to be readded to the unprocessedViewModels
            unprocessedViewModels = unprocessedViewModels.concat(postponed);

            // if we still have the same amount of items in our list of unprocessed view models it means that we
            // couldn't instantiate any more view models over a whole iteration, which in turn mean we can't resolve the
            // dependencies of remaining ones, so log that as an error and then quit the loop
            if (unprocessedViewModels.length == startLength) {
                console.error("Could not instantiate the following view models due to unresolvable dependencies:");
                _.each(unprocessedViewModels, function(entry) {
                    console.error(entry[0].name, "(missing:", _.filter(entry[1], function(id) { return !_.has(viewModelMap, id); }).join(", "), ")");
                });
                break;
            }
        }
        console.log("View model dependency resolution done");

        var allViewModels = _.values(viewModelMap);
        var dataUpdater = new DataUpdater(allViewModels);

        //~~ Temperature

        $('#tabs a[data-toggle="tab"]').on('shown', function (e) {
            temperatureViewModel.updatePlot();
            terminalViewModel.updateOutput();
        });

        //~~ File list

        $(".gcode_files").slimScroll({
            height: "306px",
            size: "5px",
            distance: "0",
            railVisible: true,
            alwaysVisible: true,
            scrollBy: "102px"
        });

        //~~ Gcode upload

        function gcode_upload_done(e, data) {
            var filename = undefined;
            var location = undefined;
            if (data.result.files.hasOwnProperty("sdcard")) {
                filename = data.result.files.sdcard.name;
                location = "sdcard";
            } else if (data.result.files.hasOwnProperty("local")) {
                filename = data.result.files.local.name;
                location = "local";
            }
            gcodeFilesViewModel.requestData(filename, location);

            if (_.endsWith(filename.toLowerCase(), ".stl")) {
                slicingViewModel.show(location, filename);
            }

            if (data.result.done) {
                $("#gcode_upload_progress .bar").css("width", "0%");
                $("#gcode_upload_progress").removeClass("progress-striped").removeClass("active");
                $("#gcode_upload_progress .bar").text("");
            }
        }

        function gcode_upload_fail(e, data) {
            var error = "<p>" + gettext("Could not upload the file. Make sure that it is a GCODE file and has the extension \".gcode\" or \".gco\" or that it is an STL file with the extension \".stl\" and slicing support is enabled and configured.") + "</p>";
            error += pnotifyAdditionalInfo("<pre>" + data.jqXHR.responseText + "</pre>");
            new PNotify({
                title: "Upload failed",
                text: error,
                type: "error",
                hide: false
            });
            $("#gcode_upload_progress .bar").css("width", "0%");
            $("#gcode_upload_progress").removeClass("progress-striped").removeClass("active");
            $("#gcode_upload_progress .bar").text("");
        }

        function gcode_upload_progress(e, data) {
            var progress = parseInt(data.loaded / data.total * 100, 10);
            $("#gcode_upload_progress .bar").css("width", progress + "%");
            $("#gcode_upload_progress .bar").text(gettext("Uploading ..."));
            if (progress >= 100) {
                $("#gcode_upload_progress").addClass("progress-striped").addClass("active");
                $("#gcode_upload_progress .bar").text(gettext("Saving ..."));
            }
        }

        function enable_local_dropzone() {
            $("#gcode_upload").fileupload({
                url: API_BASEURL + "files/local",
                dataType: "json",
                dropZone: localTarget,
                done: gcode_upload_done,
                fail: gcode_upload_fail,
                progressall: gcode_upload_progress
            });
        }

        function disable_local_dropzone() {
            $("#gcode_upload").fileupload({
                url: API_BASEURL + "files/local",
                dataType: "json",
                dropZone: null,
                done: gcode_upload_done,
                fail: gcode_upload_fail,
                progressall: gcode_upload_progress
            });
        }

        function enable_sd_dropzone() {
            $("#gcode_upload_sd").fileupload({
                url: API_BASEURL + "files/sdcard",
                dataType: "json",
                dropZone: $("#drop_sd"),
                done: gcode_upload_done,
                fail: gcode_upload_fail,
                progressall: gcode_upload_progress
            });
        }

        function disable_sd_dropzone() {
            $("#gcode_upload_sd").fileupload({
                url: API_BASEURL + "files/sdcard",
                dataType: "json",
                dropZone: null,
                done: gcode_upload_done,
                fail: gcode_upload_fail,
                progressall: gcode_upload_progress
            });
        }

        var localTarget;
        if (CONFIG_SD_SUPPORT) {
            localTarget = $("#drop_locally");
        } else {
            localTarget = $("#drop");
        }

        loginStateViewModel.isUser.subscribe(function(newValue) {
            if (newValue === true) {
                enable_local_dropzone();
            } else {
                disable_local_dropzone();
            }
        });

        if (loginStateViewModel.isUser()) {
            enable_local_dropzone();
        } else {
            disable_local_dropzone();
        }

        if (CONFIG_SD_SUPPORT) {
            printerStateViewModel.isSdReady.subscribe(function(newValue) {
                if (newValue === true && loginStateViewModel.isUser()) {
                    enable_sd_dropzone();
                } else {
                    disable_sd_dropzone();
                }
            });

            loginStateViewModel.isUser.subscribe(function(newValue) {
                if (newValue === true && printerStateViewModel.isSdReady()) {
                    enable_sd_dropzone();
                } else {
                    disable_sd_dropzone();
                }
            });

            if (printerStateViewModel.isSdReady() && loginStateViewModel.isUser()) {
                enable_sd_dropzone();
            } else {
                disable_sd_dropzone();
            }
        }

        $(document).bind("dragover", function (e) {
            var dropOverlay = $("#drop_overlay");
            var dropZone = $("#drop");
            var dropZoneLocal = $("#drop_locally");
            var dropZoneSd = $("#drop_sd");
            var dropZoneBackground = $("#drop_background");
            var dropZoneLocalBackground = $("#drop_locally_background");
            var dropZoneSdBackground = $("#drop_sd_background");
            var timeout = window.dropZoneTimeout;

            if (!timeout) {
                dropOverlay.addClass('in');
            } else {
                clearTimeout(timeout);
            }

            var foundLocal = false;
            var foundSd = false;
            var found = false;
            var node = e.target;
            do {
                if (dropZoneLocal && node === dropZoneLocal[0]) {
                    foundLocal = true;
                    break;
                } else if (dropZoneSd && node === dropZoneSd[0]) {
                    foundSd = true;
                    break;
                } else if (dropZone && node === dropZone[0]) {
                    found = true;
                    break;
                }
                node = node.parentNode;
            } while (node != null);

            if (foundLocal) {
                dropZoneLocalBackground.addClass("hover");
                dropZoneSdBackground.removeClass("hover");
            } else if (foundSd && printerStateViewModel.isSdReady()) {
                dropZoneSdBackground.addClass("hover");
                dropZoneLocalBackground.removeClass("hover");
            } else if (found) {
                dropZoneBackground.addClass("hover");
            } else {
                if (dropZoneLocalBackground) dropZoneLocalBackground.removeClass("hover");
                if (dropZoneSdBackground) dropZoneSdBackground.removeClass("hover");
                if (dropZoneBackground) dropZoneBackground.removeClass("hover");
            }

            window.dropZoneTimeout = setTimeout(function () {
                window.dropZoneTimeout = null;
                dropOverlay.removeClass("in");
                if (dropZoneLocal) dropZoneLocalBackground.removeClass("hover");
                if (dropZoneSd) dropZoneSdBackground.removeClass("hover");
                if (dropZone) dropZoneBackground.removeClass("hover");
            }, 100);
        });

        //~~ Underscore setup

        _.mixin(_.str.exports());

        //~~ knockout.js bindings

        ko.bindingHandlers.popover = {
            init: function(element, valueAccessor, allBindingsAccessor, viewModel, bindingContext) {
                var val = ko.utils.unwrapObservable(valueAccessor());

                var options = {
                    title: val.title,
                    animation: val.animation,
                    placement: val.placement,
                    trigger: val.trigger,
                    delay: val.delay,
                    content: val.content,
                    html: val.html
                };
                $(element).popover(options);
            }
        };

        ko.bindingHandlers.allowBindings = {
            init: function (elem, valueAccessor) {
                return { controlsDescendantBindings: !valueAccessor() };
            }
        };
        ko.virtualElements.allowedBindings.allowBindings = true;

        ko.bindingHandlers.slimScrolledForeach = {
            init: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
                return ko.bindingHandlers.foreach.init(element, valueAccessor(), allBindings, viewModel, bindingContext);
            },
            update: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
                setTimeout(function() {
                    $(element).slimScroll({scrollBy: 0});
                }, 10);
                return ko.bindingHandlers.foreach.update(element, valueAccessor(), allBindings, viewModel, bindingContext);
            }
        };

        ko.bindingHandlers.qrcode = {
            update: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
                var val = ko.utils.unwrapObservable(valueAccessor());

                var defaultOptions = {
                    text: "",
                    size: 200,
                    fill: "#000",
                    background: null,
                    label: "",
                    fontname: "sans",
                    fontcolor: "#000",
                    radius: 0,
                    ecLevel: "L"
                };

                var options = {};
                _.each(defaultOptions, function(value, key) {
                    options[key] = ko.utils.unwrapObservable(val[key]) || value;
                });

                $(element).empty().qrcode(options);
            }
        };

        ko.bindingHandlers.invisible = {
            init: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
                if (!valueAccessor()) return;
                ko.bindingHandlers.style.update(element, function() {
                    return { visibility: 'hidden' };
                })
            }
        };

        //~~ startup commands

        _.each(allViewModels, function(viewModel) {
            if (viewModel.hasOwnProperty("onStartup")) {
                viewModel.onStartup();
            }
        });

        loginStateViewModel.subscribe(function(change, data) {
            if ("login" == change) {
                $("#gcode_upload").fileupload("enable");

                if (data.admin) {
                    usersViewModel.requestData();
                }
            } else {
                $("#gcode_upload").fileupload("disable");
            }
        });

        //~~ view model binding

        settingsViewModel.requestData(function() {
            var viewModelsToInit = additionalViewModels.concat([
                [settingsViewModel, document.getElementById("settings_dialog")],
                [connectionViewModel, document.getElementById("connection_wrapper")],
                [printerStateViewModel, document.getElementById("state_wrapper")],
                [gcodeFilesViewModel, document.getElementById("files_wrapper")],
                [temperatureViewModel, document.getElementById("temp")],
                [controlViewModel, document.getElementById("control")],
                [gcodeViewModel, document.getElementById("gcode")],
                [terminalViewModel, document.getElementById("term")],
                [navigationViewModel, document.getElementById("navbar")],
                [appearanceViewModel, document.getElementsByTagName("head")[0]],
                [printerStateViewModel, document.getElementById("drop_overlay")],
                [logViewModel, document.getElementById("logs")],
                [timelapseViewModel, document.getElementById("timelapse")],
                [slicingViewModel, document.getElementById("slicing_configuration_dialog")]
            ]);

            // apply bindings
            var rerenderControls = false;
            _.each(viewModelsToInit, function(viewModelData) {
                if (!Array.isArray(viewModelData) || viewModelData.length != 2) {
                    return;
                }

                var viewModel = viewModelData[0];
                var targets = viewModelData[1];

                if (targets === undefined) {
                    return;
                }

                if (!Array.isArray(targets)) {
                    targets = [targets];
                }

                if (viewModel.hasOwnProperty("onBeforeBinding")) {
                    viewModel.onBeforeBinding();
                }

                _.each(targets, function(target) {
                    if (target) {
                        try {
                            ko.applyBindings(viewModel, target);
                        } catch (exc) {
                            console.log("Could not apply bindings for additional view model " + viewModel.constructor.name + ": " + exc.message);
                        }
                    } else {
                        console.log("Could not apply binding for view model " + viewModel.constructor.name + ", target does not exist");
                    }
                });

                if (viewModel.hasOwnProperty("onAfterBinding")) {
                    viewModel.onAfterBinding();
                }

                if (viewModel.hasOwnProperty("getAdditionalControls")) {
                    controlViewModel.additionalControls = controlViewModel.additionalControls.concat(viewModel.getAdditionalControls());
                    rerenderControls = true
                }
            });

            if (rerenderControls) {
                controlViewModel.rerenderControls();
            }
        });

        //~~ UI stuff

        var webcamDisableTimeout;
        $('#tabs a[data-toggle="tab"]').on('show', function (e) {
            var current = e.target;
            var previous = e.relatedTarget;

            if (current.hash == "#control") {
                clearTimeout(webcamDisableTimeout);
                var webcamImage = $("#webcam_image");
                var currentSrc = webcamImage.attr("src");
                if (currentSrc === undefined || currentSrc.trim() == "") {
                    var newSrc = CONFIG_WEBCAM_STREAM;
                    if (CONFIG_WEBCAM_STREAM.lastIndexOf("?") > -1) {
                        newSrc += "&";
                    } else {
                        newSrc += "?";
                    }
                    newSrc += new Date().getTime();

                    webcamImage.attr("src", newSrc);
                }
            } else if (previous.hash == "#control") {
                // only disable webcam stream if tab is out of focus for more than 5s, otherwise we might cause
                // more load by the constant connection creation than by the actual webcam stream
                webcamDisableTimeout = setTimeout(function() {
                    $("#webcam_image").attr("src", "");
                }, 5000);
            }
        });

        $(".accordion-toggle[data-target='#files']").click(function() {
            var files = $("#files");
            if (files.hasClass("in")) {
                files.removeClass("overflow_visible");
            } else {
                setTimeout(function() {
                    files.addClass("overflow_visible");
                }, 100);
            }
        });

        $.fn.modal.defaults.maxHeight = function(){
            // subtract the height of the modal header and footer
            return $(window).height() - 165;
        };

        // Fix input element click problem on login dialog
        $(".dropdown input, .dropdown label").click(function(e) {
            e.stopPropagation();
        });

        $(document).bind("drop dragover", function (e) {
            e.preventDefault();
        });

        $("#login_user").keyup(function(event) {
            if (event.keyCode == 13) {
                $("#login_pass").focus();
            }
        });
        $("#login_pass").keyup(function(event) {
            if (event.keyCode == 13) {
                $("#login_button").click();
            }
        });

        if (CONFIG_FIRST_RUN) {
            var firstRunViewModel = new FirstRunViewModel();
            ko.applyBindings(firstRunViewModel, document.getElementById("first_run_dialog"));
            firstRunViewModel.showDialog();
        }

    }
);

