$(function() {
        OctoPrint = window.OctoPrint;

        //~~ Lodash setup

        _.mixin({"sprintf": sprintf, "vsprintf": vsprintf});

        //~~ Logging setup

        log.setLevel(CONFIG_DEBUG ? "debug" : "info");

        //~~ OctoPrint client setup
        OctoPrint.options.baseurl = BASEURL;
        OctoPrint.options.apikey = UI_API_KEY;

        var l10n = getQueryParameterByName("l10n");
        if (l10n) {
            OctoPrint.options.locale = l10n;
        }

        OctoPrint.socket.onMessage("connected", function(data) {
            var payload = data.data;
            OctoPrint.options.apikey = payload.apikey;

            // update the API key directly in jquery's ajax options too,
            // to ensure the fileupload plugin and any plugins still using
            // $.ajax directly still work fine too
            UI_API_KEY = payload["apikey"];
            $.ajaxSetup({
                headers: {"X-Api-Key": UI_API_KEY}
            });
        });

        //~~ some CoreUI specific stuff we put into OctoPrint.coreui

        OctoPrint.coreui = (function() {
            var exports = {
                browserTabVisibility: undefined,
                selectedTab: undefined,
                settingsOpen: false,
                wizardOpen: false
            };

            var browserVisibilityCallbacks = [];

            var getHiddenProp = function() {
                var prefixes = ["webkit", "moz", "ms", "o"];

                // if "hidden" is natively supported just return it
                if ("hidden" in document) {
                    return "hidden"
                }

                // otherwise loop over all the known prefixes until we find one
                var vendorPrefix = _.find(prefixes, function(prefix) {
                    return (prefix + "Hidden" in document);
                });
                if (vendorPrefix !== undefined) {
                    return vendorPrefix + "Hidden";
                }

                // nothing found
                return undefined;
            };

            var isHidden = function() {
                var prop = getHiddenProp();
                if (!prop) return false;

                return document[prop];
            };

            var updateBrowserVisibility = function() {
                var visible = !isHidden();
                exports.browserTabVisible = visible;
                _.each(browserVisibilityCallbacks, function(callback) {
                    callback(visible);
                })
            };

            // register for browser visibility tracking

            var prop = getHiddenProp();
            if (prop) {
                var eventName = prop.replace(/[H|h]idden/, "") + "visibilitychange";
                document.addEventListener(eventName, updateBrowserVisibility);

                updateBrowserVisibility();
            }

            // exports

            exports.isVisible = function() { return !isHidden() };
            exports.onBrowserVisibilityChange = function(callback) {
                browserVisibilityCallbacks.push(callback);
            };

            return exports;
        })();

        //~~ AJAX setup

        // work around a stupid iOS6 bug where ajax requests get cached and only work once, as described at
        // http://stackoverflow.com/questions/12506897/is-safari-on-ios-6-caching-ajax-results
        $.ajaxPrefilter(function(options, originalOptions, jqXHR) {
            if (options.type != "GET") {
                var headers;
                if (options.hasOwnProperty("headers")) {
                    options.headers["Cache-Control"] = "no-cache";
                } else {
                    options.headers = { "Cache-Control": "no-cache" };
                }
            }
        });

        // send the current UI API key with any request
        $.ajaxSetup({
            headers: {"X-Api-Key": UI_API_KEY}
        });

        //~~ Initialize file upload plugin

        $.widget("blueimp.fileupload", $.blueimp.fileupload, {
            options: {
                dropZone: null,
                pasteZone: null
            }
        });

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

        //~~ Initialize PNotify

        PNotify.prototype.options.styling = "bootstrap2";
        PNotify.prototype.options.mouse_reset = false;

        PNotify.singleButtonNotify = function(options) {
            if (!options.confirm || !options.confirm.buttons || !options.confirm.buttons.length) {
                return new PNotify(options);
            }

            var autoDisplay = options.auto_display != false;

            var params = $.extend(true, {}, options);
            params.auto_display = false;

            var notify = new PNotify(params);
            notify.options.confirm.buttons = [notify.options.confirm.buttons[0]];
            notify.modules.confirm.makeDialog(notify, notify.options.confirm);

            if (autoDisplay) {
                notify.open();
            }
            return notify;
        };

        //~~ Initialize view models

        // the view model map is our basic look up table for dependencies that may be injected into other view models
        var viewModelMap = {};

        // Fix Function#name on browsers that do not support it (IE):
        // see: http://stackoverflow.com/questions/6903762/function-name-not-supported-in-ie
        if (!(function f() {}).name) {
            Object.defineProperty(Function.prototype, 'name', {
                get: function() {
                    return this.toString().match(/^\s*function\s*(\S*)\s*\(/)[1];
                }
            });
        }

        // helper to create a view model instance with injected constructor parameters from the view model map
        var _createViewModelInstance = function(viewModel, viewModelMap, optionalDependencyPass) {

            // mirror the requested dependencies with an array of the viewModels
            var viewModelParametersMap = function(parameter) {
                // check if parameter is found within optional array and if all conditions are met return null instead of undefined
                if (optionalDependencyPass && viewModel.optional.indexOf(parameter) !== -1 && !viewModelMap[parameter]) {
                    log.debug("Resolving optional parameter", [parameter], "without viewmodel");
                    return null; // null == "optional but not available"
                }

                return viewModelMap[parameter] || undefined; // undefined == "not available"
            };

            // try to resolve all of the view model's constructor parameters via our view model map
            var constructorParameters = _.map(viewModel.dependencies, viewModelParametersMap) || [];

            if (constructorParameters.indexOf(undefined) !== -1) {
                log.debug("Postponing", viewModel.name, "due to missing parameters:", _.keys(_.pick(_.object(viewModel.dependencies, constructorParameters), _.isUndefined)));
                return;
            }

            // transform array into object if a plugin wants it as an object
            constructorParameters = (viewModel.returnObject) ? _.object(viewModel.dependencies, constructorParameters) : constructorParameters;

            // if we came this far then we could resolve all constructor parameters, so let's construct that view model
            log.debug("Constructing", viewModel.name, "with parameters:", viewModel.dependencies);
            return new viewModel.construct(constructorParameters);
        };

        // map any additional view model bindings we might need to make
        var additionalBindings = {};
        _.each(OCTOPRINT_ADDITIONAL_BINDINGS, function(bindings) {
            var viewModelId = bindings[0];
            var viewModelBindTargets = bindings[1];
            if (!_.isArray(viewModelBindTargets)) {
                viewModelBindTargets = [viewModelBindTargets];
            }

            if (!additionalBindings.hasOwnProperty(viewModelId)) {
                additionalBindings[viewModelId] = viewModelBindTargets;
            } else {
                additionalBindings[viewModelId] = additionalBindings[viewModelId].concat(viewModelBindTargets);
            }
        });

        // helper for translating the name of a view model class into an identifier for the view model map
        var _getViewModelId = function(name){
            return name.substr(0, 1).toLowerCase() + name.substr(1); // FooBarViewModel => fooBarViewModel
        };

        // instantiation loop, will make multiple passes over the list of unprocessed view models until all
        // view models have been successfully instantiated with all of their dependencies or no changes can be made
        // any more which means not all view models can be instantiated due to missing dependencies
        var unprocessedViewModels = OCTOPRINT_VIEWMODELS.slice();
        unprocessedViewModels = unprocessedViewModels.concat(ADDITIONAL_VIEWMODELS);

        var allViewModels = [];
        var allViewModelData = [];
        var pass = 1;
        var optionalDependencyPass = false;
        log.info("Starting dependency resolution...");
        while (unprocessedViewModels.length > 0) {
            log.debug("Dependency resolution, pass #" + pass);
            var startLength = unprocessedViewModels.length;
            var postponed = [];

            // now try to instantiate every one of our as of yet unprocessed view model descriptors
            while (unprocessedViewModels.length > 0){
                var viewModel = unprocessedViewModels.shift();

                // wrap anything not object related into an object
                if(!_.isPlainObject(viewModel)) {
                    viewModel = {
                        construct: (_.isArray(viewModel)) ? viewModel[0] : viewModel,
                        dependencies: viewModel[1] || [],
                        elements: viewModel[2] || [],
                        optional: viewModel[3] || []
                    };
                }

                // make sure we have atleast a function
                if (!_.isFunction(viewModel.construct)) {
                    log.error("No function to instantiate with", viewModel);
                    continue;
                }

                // if name is not set, get name from constructor, if it's an anonymous function generate one
                viewModel.name = viewModel.name || _getViewModelId(viewModel.construct.name) || _.uniqueId("unnamedViewModel");

                // no alternative names? empty array
                viewModel.additionalNames = viewModel.additionalNames || [];

                // make sure all value's are in an array
                viewModel.dependencies = (_.isArray(viewModel.dependencies)) ? viewModel.dependencies : [viewModel.dependencies];
                viewModel.elements = (_.isArray(viewModel.elements)) ? viewModel.elements : [viewModel.elements];
                viewModel.optional = (_.isArray(viewModel.optional)) ? viewModel.optional : [viewModel.optional];
                viewModel.additionalNames = (_.isArray(viewModel.additionalNames)) ? viewModel.additionalNames : [viewModel.additionalNames];

                // make sure that we don't have two view models going by the same name
                if (_.has(viewModelMap, viewModel.name)) {
                    log.error("Duplicate name while instantiating " + viewModel.name);
                    continue;
                }

                var viewModelInstance = _createViewModelInstance(viewModel, viewModelMap, optionalDependencyPass);

                // our view model couldn't yet be instantiated, so postpone it for a bit
                if (viewModelInstance === undefined) {
                    postponed.push(viewModel);
                    continue;
                }

                // we could resolve the depdendencies and the view model is not defined yet => add it, it's now fully processed
                var viewModelBindTargets = viewModel.elements;

                if (additionalBindings.hasOwnProperty(viewModel.name)) {
                    viewModelBindTargets = viewModelBindTargets.concat(additionalBindings[viewModel.name]);
                }

                allViewModelData.push([viewModelInstance, viewModelBindTargets]);
                allViewModels.push(viewModelInstance);
                viewModelMap[viewModel.name] = viewModelInstance;

                if (viewModel.additionalNames.length) {
                    var registeredAdditionalNames = [];
                    _.each(viewModel.additionalNames, function(additionalName) {
                        if (!_.has(viewModelMap, additionalName)) {
                            viewModelMap[additionalName] = viewModelInstance;
                            registeredAdditionalNames.push(additionalName);
                        }
                    });

                    if (registeredAdditionalNames.length) {
                        log.debug("Registered", viewModel.name, "under these additional names:", registeredAdditionalNames);
                    }
                }
            }

            // anything that's now in the postponed list has to be readded to the unprocessedViewModels
            unprocessedViewModels = unprocessedViewModels.concat(postponed);

            // if we still have the same amount of items in our list of unprocessed view models it means that we
            // couldn't instantiate any more view models over a whole iteration, which in turn mean we can't resolve the
            // dependencies of remaining ones, so log that as an error and then quit the loop
            if (unprocessedViewModels.length === startLength) {
                // I'm gonna let you finish but we will do another pass with the optional dependencies flag enabled
                if (!optionalDependencyPass) {
                    log.debug("Resolving next pass with optional dependencies flag enabled");
                    optionalDependencyPass = true;
                } else {
                    log.error("Could not instantiate the following view models due to unresolvable dependencies:");
                    _.each(unprocessedViewModels, function(entry) {
                        log.error(entry.name + " (missing: " + _.filter(entry.dependencies, function(id) { return !_.has(viewModelMap, id); }).join(", ") + " )");
                    });
                    break;
                }
            }

            log.debug("Dependency resolution pass #" + pass + " finished, " + unprocessedViewModels.length + " view models left to process");
            pass++;
        }
        log.info("... dependency resolution done");

        //~~ some additional hooks and initializations

        // make sure modals max out at the window height
        $.fn.modal.defaults.maxHeight = function(){
            // subtract the height of the modal header and footer
            return $(window).height() - 165;
        };

        // jquery plugin to select all text in an element
        // originally from: http://stackoverflow.com/a/987376
        $.fn.selectText = function() {
            var doc = document;
            var element = this[0];
            var range, selection;

            if (doc.body.createTextRange) {
                range = document.body.createTextRange();
                range.moveToElementText(element);
                range.select();
            } else if (window.getSelection) {
                selection = window.getSelection();
                range = document.createRange();
                range.selectNodeContents(element);
                selection.removeAllRanges();
                selection.addRange(range);
            }
        };

        $.fn.isChildOf = function (element) {
            return $(element).has(this).length > 0;
        };

        // from http://jsfiddle.net/KyleMit/X9tgY/
        $.fn.contextMenu = function (settings) {
            return this.each(function () {
                // Open context menu
                $(this).on("contextmenu", function (e) {
                    // return native menu if pressing control
                    if (e.ctrlKey) return;

                    $(settings.menuSelector)
                        .data("invokedOn", $(e.target))
                        .data("contextParent", $(this))
                        .show()
                        .css({
                            position: "fixed",
                            left: getMenuPosition(e.clientX, 'width', 'scrollLeft'),
                            top: getMenuPosition(e.clientY, 'height', 'scrollTop'),
                            "z-index": 9999
                        }).off('click')
                        .on('click', function (e) {
                            if (e.target.tagName.toLowerCase() == "input")
                                return;

                            $(this).hide();

                            settings.menuSelected.call(this, $(this).data('invokedOn'), $(this).data('contextParent'), $(e.target));
                        });

                    return false;
                });

                //make sure menu closes on any click
                $(document).click(function () {
                    $(settings.menuSelector).hide();
                });
            });

            function getMenuPosition(mouse, direction, scrollDir) {
                var win = $(window)[direction](),
                    scroll = $(window)[scrollDir](),
                    menu = $(settings.menuSelector)[direction](),
                    position = mouse + scroll;

                // opening menu would pass the side of the page
                if (mouse + menu > win && menu < mouse)
                    position -= menu;

                return position;
            }
        };

        // Use bootstrap tabdrop for tabs and pills
        $('.nav-pills, .nav-tabs').tabdrop();

        // Allow components to react to tab change
        var onTabChange = function(current, previous) {
            log.debug("Selected OctoPrint tab changed: previous = " + previous + ", current = " + current);
            OctoPrint.coreui.selectedTab = current;
            callViewModels(allViewModels, "onTabChange", [current, previous]);
        };

        var tabs = $('#tabs a[data-toggle="tab"]');
        tabs.on('show', function (e) {
            var current = e.target.hash;
            var previous = e.relatedTarget.hash;
            onTabChange(current, previous);
        });

        tabs.on('shown', function (e) {
            var current = e.target.hash;
            var previous = e.relatedTarget.hash;
            callViewModels(allViewModels, "onAfterTabChange", [current, previous]);
        });

        onTabChange(OCTOPRINT_INITIAL_TAB);

        // Fix input element click problems on dropdowns
        $(".dropdown input, .dropdown label").click(function(e) {
            e.stopPropagation();
        });

        // prevent default action for drag-n-drop
        $(document).bind("drop dragover", function (e) {
            e.preventDefault();
        });

        // reload overlay
        $("#reloadui_overlay_reload").click(function() { location.reload(); });

        //~~ view model binding

        var bindViewModels = function() {
            log.info("Going to bind " + allViewModelData.length + " view models...");
            _.each(allViewModelData, function(viewModelData) {
                if (!Array.isArray(viewModelData) || viewModelData.length != 2) {
                    return;
                }

                var viewModel = viewModelData[0];
                var targets = viewModelData[1];

                if (targets === undefined) {
                    return;
                }

                if (!_.isArray(targets)) {
                    targets = [targets];
                }

                if (viewModel.hasOwnProperty("onBeforeBinding")) {
                    viewModel.onBeforeBinding();
                }

                if (targets != undefined) {
                    if (!_.isArray(targets)) {
                        targets = [targets];
                    }

                    viewModel._bindings = [];

                    _.each(targets, function(target) {
                        if (target == undefined) {
                            return;
                        }

                        var object;
                        if (!(target instanceof jQuery)) {
                            object = $(target);
                        } else {
                            object = target;
                        }

                        if (object == undefined || !object.length) {
                            log.info("Did not bind view model", viewModel.constructor.name, "to target", target, "since it does not exist");
                            return;
                        }

                        var element = object.get(0);
                        if (element == undefined) {
                            log.info("Did not bind view model", viewModel.constructor.name, "to target", target, "since it does not exist");
                            return;
                        }

                        try {
                            ko.applyBindings(viewModel, element);
                            viewModel._bindings.push(target);

                            if (viewModel.hasOwnProperty("onBoundTo")) {
                                viewModel.onBoundTo(target, element);
                            }

                            log.debug("View model", viewModel.constructor.name, "bound to", target);
                        } catch (exc) {
                            log.error("Could not bind view model", viewModel.constructor.name, "to target", target, ":", (exc.stack || exc));
                        }
                    });
                }

                viewModel._unbound = viewModel._bindings != undefined && viewModel._bindings.length == 0;

                if (viewModel.hasOwnProperty("onAfterBinding")) {
                    viewModel.onAfterBinding();
                }
            });

            callViewModels(allViewModels, "onAllBound", [allViewModels]);
            log.info("... binding done");

            // startup complete
            callViewModels(allViewModels, "onStartupComplete");

            // make sure we can track the browser tab visibility
            OctoPrint.coreui.onBrowserVisibilityChange(function(status) {
                log.debug("Browser tab is now " + (status ? "visible" : "hidden"));
                callViewModels(allViewModels, "onBrowserTabVisibilityChange", [status]);
            });

            log.info("Application startup complete");
        };

        if (!_.has(viewModelMap, "settingsViewModel")) {
            throw new Error("settingsViewModel is missing, can't run UI")
        }

        log.info("Initial application setup done, connecting to server...");
        var dataUpdater = new DataUpdater(allViewModels);
        dataUpdater.connect()
            .done(function() {
                log.info("Finalizing application startup");

                //~~ Starting up the app
                callViewModels(allViewModels, "onStartup");

                viewModelMap["settingsViewModel"].requestData()
                    .done(function() {
                        // There appears to be an odd race condition either in JQuery's AJAX implementation or
                        // the browser's implementation of XHR, causing a second GET request from inside the
                        // completion handler of the very same request to never get its completion handler called
                        // if ETag headers are present on the response (the status code of the request does NOT
                        // seem to matter here, only that the ETag header is present).
                        //
                        // Minimal example with which I was able to reproduce this behaviour can be found
                        // at https://gist.github.com/foosel/b2ddb9ebd71b0b63a749444651bfce3f
                        //
                        // Decoupling all consecutive calls from this done event handler hence is an easy way
                        // to avoid this problem. A zero timeout should do the trick nicely.
                        window.setTimeout(bindViewModels, 0);
                    });
            });
    }
);
